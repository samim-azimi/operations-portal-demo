from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    FazaSignSettings, SignatureAuditLog, SignatureEnvelope, SignatureRecipient,
    SignatureToken, SignedDocument, User,
)
from app.services.email_service import queue_signature_request
from app.services.sign_pdf_service import append_signature_page


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def storage_path(folder: str, stored_name: str) -> Path:
    directory = (settings.upload_directory / folder).resolve()
    path = (directory / Path(stored_name).name).resolve()
    if directory not in path.parents:
        raise HTTPException(400, "Invalid signing document path")
    return path


def save_bytes(folder: str, content: bytes, extension: str) -> str:
    directory = (settings.upload_directory / folder).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    storage_path(folder, stored_name).write_bytes(content)
    return stored_name


def read_bytes(folder: str, stored_name: str) -> bytes:
    path = storage_path(folder, stored_name)
    if not path.is_file():
        raise HTTPException(404, "Signing document not found")
    return path.read_bytes()


def get_sign_settings(db: Session) -> FazaSignSettings:
    item = db.query(FazaSignSettings).first()
    if not item:
        item = FazaSignSettings()
        db.add(item)
        db.flush()
    return item


def next_number(db: Session, model, field_name: str, prefix: str) -> str:
    year = datetime.now(timezone.utc).year
    starts = f"{prefix}-{year}-"
    field = getattr(model, field_name)
    latest = db.query(field).filter(field.like(f"{starts}%")).order_by(field.desc()).first()
    number = int(latest[0].rsplit("-", 1)[-1]) + 1 if latest else 1
    return f"{starts}{number:06d}"


def audit(
    db: Session, envelope: SignatureEnvelope, action: str, *,
    user_id: int | None = None, recipient_id: int | None = None,
    ip_address: str | None = None, user_agent: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(SignatureAuditLog(
        envelope_db_id=envelope.id, recipient_id=recipient_id, user_id=user_id,
        action=action, details=details or {}, ip_address=ip_address,
        user_agent=(user_agent or "")[:500] or None,
    ))


def new_recipient_token(db: Session, envelope: SignatureEnvelope, recipient: SignatureRecipient) -> tuple[str, str]:
    raw = secrets.token_urlsafe(36)
    token_hash = sha256_bytes(raw.encode())
    expiry = get_sign_settings(db).default_token_expiry_hours
    db.query(SignatureToken).filter(
        SignatureToken.recipient_id == recipient.id,
        SignatureToken.used_at.is_(None),
    ).update({"is_revoked": True})
    db.add(SignatureToken(
        envelope_db_id=envelope.id, recipient_id=recipient.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expiry),
    ))
    url = f"{settings.signing_link_base_url.rstrip('/')}/{raw}"
    return raw, url


def activate_recipient(db: Session, envelope: SignatureEnvelope, recipient: SignatureRecipient) -> tuple[str, int | None]:
    recipient.status = "sent"
    _, url = new_recipient_token(db, envelope, recipient)
    notification = (
        queue_signature_request(db, envelope, recipient, url)
        if get_sign_settings(db).email_notification_enabled else None
    )
    audit(
        db, envelope, "email sent to signer", recipient_id=recipient.id,
        details={
            "recipient": recipient.email,
            "delivery": "development_console" if settings.environment == "development" else "email_outbox",
        },
    )
    return url, notification.id if notification else None


def resolve_token(db: Session, raw_token: str, user: User) -> tuple[SignatureToken, SignatureEnvelope, SignatureRecipient]:
    token_hash = sha256_bytes(raw_token.encode())
    token = db.query(SignatureToken).filter(SignatureToken.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)
    if not token or token.is_revoked or token.used_at or token.expires_at.replace(tzinfo=token.expires_at.tzinfo or timezone.utc) <= now:
        raise HTTPException(410, "This signing link is invalid or expired")
    recipient = db.get(SignatureRecipient, token.recipient_id)
    envelope = db.get(SignatureEnvelope, token.envelope_db_id)
    if not recipient or not envelope:
        raise HTTPException(404, "Signing request not found")
    if recipient.user_id != user.id or recipient.email.lower() != user.email.lower():
        raise HTTPException(403, "This signing request belongs to another user")
    if recipient.status not in {"sent", "viewed"}:
        raise HTTPException(409, "This recipient cannot act on the envelope")
    return token, envelope, recipient


def current_pdf(db: Session, envelope: SignatureEnvelope) -> tuple[bytes, str]:
    latest = db.query(SignedDocument).filter(
        SignedDocument.envelope_db_id == envelope.id
    ).order_by(SignedDocument.version_number.desc()).first()
    if latest:
        return read_bytes("signed-documents", latest.file_path), latest.file_hash
    return read_bytes("original-documents", envelope.original_pdf_path), envelope.original_pdf_hash


def apply_signature(
    db: Session, envelope: SignatureEnvelope, recipient: SignatureRecipient,
    user: User, typed_name: str | None,
) -> SignedDocument:
    source, source_hash = current_pdf(db, envelope)
    signature_path = None
    snapshot_name = None
    if user.signature_image:
        source_signature = storage_path("signatures", user.signature_image.stored_name)
        if source_signature.is_file():
            snapshot_name = save_bytes("signatures", source_signature.read_bytes(), source_signature.suffix)
            signature_path = storage_path("signatures", snapshot_name)
    sign_settings = get_sign_settings(db)
    if sign_settings.require_signature_image and not signature_path:
        raise HTTPException(422, "A saved signature image is required")
    verification = next_number(db, SignatureRecipient, "verification_number", "SIG")
    now = datetime.now(timezone.utc)
    version = db.query(SignedDocument).filter(SignedDocument.envelope_db_id == envelope.id).count() + 1
    signed = append_signature_page(
        source,
        envelope_id=envelope.envelope_id,
        verification_number=verification,
        signer_name=user.full_name,
        signer_email=user.email,
        role_name=recipient.role_name,
        signed_at=now.strftime("%Y-%m-%d %H:%M UTC"),
        document_hash=source_hash,
        signature_image_path=signature_path,
        typed_name=typed_name,
        signature_page=recipient.signature_page,
        signature_x=recipient.signature_x,
        signature_y=recipient.signature_y,
        signature_width=recipient.signature_width,
        signature_height=recipient.signature_height,
        add_envelope_label=version == 1,
    )
    signed_hash = sha256_bytes(signed)
    stored_name = save_bytes("signed-documents", signed, ".pdf")
    document = SignedDocument(
        envelope_db_id=envelope.id, version_number=version, file_path=stored_name,
        file_hash=signed_hash, created_after_recipient_id=recipient.id,
    )
    db.add(document)
    recipient.verification_number = verification
    recipient.signature_image_path_snapshot = snapshot_name
    recipient.document_hash_at_action = source_hash
    recipient.signed_at = now
    recipient.status = "signed"
    envelope.current_document_hash = signed_hash
    envelope.final_signed_pdf_path = stored_name
    envelope.final_signed_pdf_hash = signed_hash
    return document


def verify_envelope_file(envelope: SignatureEnvelope) -> bool:
    if not envelope.final_signed_pdf_path or not envelope.final_signed_pdf_hash:
        return False
    try:
        return sha256_bytes(read_bytes("signed-documents", envelope.final_signed_pdf_path)) == envelope.final_signed_pdf_hash
    except HTTPException:
        return False
