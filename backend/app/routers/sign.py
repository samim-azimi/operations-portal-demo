import json
import math
import re
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from io import BytesIO
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    AuditLog, FazaSignSettings, InventoryItem, SignatureAuditLog, SignatureEnvelope,
    SignatureRecipient, SignatureToken, SignedDocument, User, UserSignatureImage,
)
from app.modules import permissions_for_role
from app.schemas import UserRead
from app.security import get_current_user, require_permission
from app.services.email_service import (
    deliver_notification, queue_signature_completed, queue_signature_rejected,
    queue_signature_returned,
)
from app.services.image_upload_service import image_path, remove_image, save_image
from app.services.sign_service import (
    activate_recipient, apply_signature, audit, get_sign_settings, next_number,
    current_pdf, new_recipient_token, read_bytes, resolve_token, save_bytes, sha256_bytes, storage_path,
    verify_envelope_file,
)
from app.sign_schemas import (
    CommentAction, EnvelopeCreate, EnvelopePage, EnvelopeRead, ReviewRead,
    SignAction, SignSettingsRead, SignSettingsUpdate,
)

router = APIRouter(
    prefix="/sign", tags=["Digital Signature"],
    dependencies=[Depends(require_permission("can_access_sign"))],
)
admin_router = APIRouter(prefix="/admin/sign", tags=["Digital Signature Admin"])


def client_context(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent", "")[:500] or None,
    )


def can_view_all(user: User) -> bool:
    return "can_view_all_signature_envelopes" in permissions_for_role(user.role)


def envelope_access(db: Session, envelope_id: int, user: User) -> SignatureEnvelope:
    envelope = db.get(SignatureEnvelope, envelope_id)
    if not envelope:
        raise HTTPException(404, "Envelope not found")
    recipient = db.query(SignatureRecipient.id).filter(
        SignatureRecipient.envelope_db_id == envelope.id,
        SignatureRecipient.user_id == user.id,
    ).first()
    if envelope.created_by_id != user.id and not recipient and not can_view_all(user):
        raise HTTPException(403, "You cannot view this envelope")
    return envelope


def safe_download_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:120]


@router.get("/profile/signature")
def signature_profile(user: User = Depends(get_current_user)):
    return {
        "has_signature": bool(user.signature_image),
        "signature_image_url": user.signature_image_url,
        "updated_at": user.signature_image.updated_at if user.signature_image else None,
    }


@router.get("/profile/signature/file")
def signature_file(
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    image = db.query(UserSignatureImage).filter_by(user_id=user.id).first()
    if not image:
        raise HTTPException(404, "Signature image not found")
    return FileResponse(
        image_path("signatures", image.stored_name),
        media_type=image.mime_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/profile/signature")
async def upload_signature(
    file: UploadFile = File(...), db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_upload_own_signature")),
):
    sign_settings = get_sign_settings(db)
    saved = await save_image(file, "signatures", sign_settings.max_signature_image_size)
    image = db.query(UserSignatureImage).filter_by(user_id=user.id).first()
    if image:
        remove_image("signatures", image.stored_name)
        image.stored_name = saved["stored_name"]
        image.mime_type = saved["mime_type"]
        image.size_bytes = saved["size_bytes"]
        image.updated_at = datetime.now(timezone.utc)
    else:
        image = UserSignatureImage(user_id=user.id, **saved)
        db.add(image)
    db.flush()
    db.add(AuditLog(
        actor_id=user.id, action="Signature image uploaded",
        details={"mime_type": saved["mime_type"], "size_bytes": saved["size_bytes"]},
    ))
    db.commit()
    return {"signature_image_url": "/api/sign/profile/signature/file", "updated_at": image.updated_at}


@router.delete("/profile/signature", status_code=204)
def delete_signature(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_upload_own_signature")),
):
    image = db.query(UserSignatureImage).filter_by(user_id=user.id).first()
    if image:
        remove_image("signatures", image.stored_name)
        db.delete(image)
        db.add(AuditLog(actor_id=user.id, action="Signature image removed", details={}))
        db.commit()


@router.get("/users", response_model=list[UserRead])
def signer_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("can_create_signature_envelope")),
):
    return db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()


@router.post("/envelopes", response_model=EnvelopeRead, status_code=201)
async def create_envelope(
    metadata: str = Form(...), file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_create_signature_envelope")),
):
    try:
        data = EnvelopeCreate.model_validate(json.loads(metadata))
    except Exception as exc:
        raise HTTPException(422, f"Invalid envelope metadata: {exc}") from exc
    if len({item.routing_order for item in data.recipients}) != len(data.recipients):
        raise HTTPException(422, "Recipient routing order must be unique")
    content = await file.read(15_728_640)
    await file.close()
    if not content.startswith(b"%PDF-"):
        raise HTTPException(415, "Digital Signature accepts PDF documents only")
    if len(content) > 15_000_000:
        raise HTTPException(413, "Signing documents must be smaller than 15 MB")
    sign_settings = get_sign_settings(db)
    if not sign_settings.is_enabled:
        raise HTTPException(503, "Digital Signature is disabled")
    users = {user.id: user for user in db.query(User).filter(
        User.id.in_([item.user_id for item in data.recipients]), User.is_active.is_(True)
    ).all()}
    if len(users) != len({item.user_id for item in data.recipients}):
        raise HTTPException(422, "One or more signers were not found")
    stored = save_bytes("original-documents", content, ".pdf")
    document_hash = sha256_bytes(content)
    envelope = SignatureEnvelope(
        envelope_id=next_number(db, SignatureEnvelope, "envelope_id", "ENV"),
        document_type=data.document_type, document_reference_id=data.document_reference_id,
        title=data.title, subject=data.subject, message=data.message, status="draft",
        routing_mode=data.routing_mode, original_pdf_path=stored,
        original_pdf_hash=document_hash, current_document_hash=document_hash,
        created_by_id=actor.id,
    )
    db.add(envelope)
    db.flush()
    for recipient_data in sorted(data.recipients, key=lambda item: item.routing_order):
        signer = users[recipient_data.user_id]
        default_y = min(0.06 + ((recipient_data.routing_order - 1) % 4) * 0.18, 0.72)
        db.add(SignatureRecipient(
            envelope_db_id=envelope.id, user_id=signer.id,
            full_name=signer.full_name, email=signer.email,
            role_name=recipient_data.role_name, routing_order=recipient_data.routing_order,
            signature_page=recipient_data.signature_page if recipient_data.signature_page is not None else -1,
            signature_x=recipient_data.signature_x if recipient_data.signature_x is not None else 0.61,
            signature_y=recipient_data.signature_y if recipient_data.signature_y is not None else default_y,
            signature_width=recipient_data.signature_width if recipient_data.signature_width is not None else 0.32,
            signature_height=recipient_data.signature_height if recipient_data.signature_height is not None else 0.16,
        ))
    db.flush()
    audit(db, envelope, "envelope created", user_id=actor.id, details={"original_pdf_hash": document_hash})
    db.commit()
    db.refresh(envelope)
    return envelope


@router.get("/envelopes", response_model=EnvelopePage)
def list_envelopes(
    q: str | None = None, status: str | None = None, document_type: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    query = db.query(SignatureEnvelope)
    if not can_view_all(user):
        own_ids = db.query(SignatureRecipient.envelope_db_id).filter(SignatureRecipient.user_id == user.id)
        query = query.filter(or_(SignatureEnvelope.created_by_id == user.id, SignatureEnvelope.id.in_(own_ids)))
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(SignatureEnvelope.envelope_id.ilike(term), SignatureEnvelope.title.ilike(term), SignatureEnvelope.document_reference_id.ilike(term)))
    if status:
        query = query.filter(SignatureEnvelope.status == status)
    if document_type:
        query = query.filter(SignatureEnvelope.document_type == document_type)
    total = query.count()
    items = query.order_by(SignatureEnvelope.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return EnvelopePage(items=items, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total / page_size)))


@router.get("/envelopes/{envelope_id}", response_model=EnvelopeRead)
def envelope_detail(
    envelope_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    return envelope_access(db, envelope_id, user)


@router.post("/envelopes/{envelope_id}/my-review-link")
def create_my_review_link(
    envelope_id: int, request: Request, db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_sign_documents")),
):
    """Let the assigned signer continue safely from inside their portal.

    A fresh one-recipient token is issued because raw signing tokens are never
    stored. Existing unused links for this recipient are revoked.
    """
    envelope = envelope_access(db, envelope_id, user)
    recipient = db.query(SignatureRecipient).filter_by(
        envelope_db_id=envelope.id, user_id=user.id,
    ).first()
    if not recipient:
        raise HTTPException(403, "This document is not assigned to you")
    if recipient.status not in {"sent", "viewed"}:
        raise HTTPException(409, "This document is not currently waiting for your signature")
    raw_token, _ = new_recipient_token(db, envelope, recipient)
    ip, agent = client_context(request)
    audit(
        db, envelope, "signer opened request from portal",
        user_id=user.id, recipient_id=recipient.id,
        ip_address=ip, user_agent=agent,
    )
    db.commit()
    return {"review_path": f"/sign/review/{raw_token}"}


@router.post("/envelopes/{envelope_id}/send")
def send_envelope(
    envelope_id: int, background: BackgroundTasks, request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_send_signature_envelope")),
):
    envelope = envelope_access(db, envelope_id, actor)
    if envelope.status != "draft":
        raise HTTPException(409, "Only draft envelopes can be sent")
    first = sorted(envelope.recipients, key=lambda item: item.routing_order)[0]
    signing_url, notification_id = activate_recipient(db, envelope, first)
    envelope.status = "pending"
    ip, agent = client_context(request)
    audit(db, envelope, "envelope sent", user_id=actor.id, recipient_id=first.id, ip_address=ip, user_agent=agent)
    db.commit()
    if notification_id:
        background.add_task(deliver_notification, notification_id)
    return {"status": envelope.status, "signing_url": signing_url if settings.environment == "development" else None}


@router.post("/envelopes/{envelope_id}/cancel")
def cancel_envelope(
    envelope_id: int, request: Request, db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_cancel_signature_envelope")),
):
    envelope = envelope_access(db, envelope_id, actor)
    if envelope.status in {"completed", "rejected", "cancelled"}:
        raise HTTPException(409, "This envelope can no longer be cancelled")
    envelope.status = "cancelled"
    db.query(SignatureToken).filter(SignatureToken.envelope_db_id == envelope.id).update({"is_revoked": True})
    ip, agent = client_context(request)
    audit(db, envelope, "envelope cancelled", user_id=actor.id, ip_address=ip, user_agent=agent)
    db.commit()
    return {"status": "cancelled"}


@router.get("/envelopes/{envelope_id}/audit")
def envelope_audit(
    envelope_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    envelope = envelope_access(db, envelope_id, user)
    rows = db.query(SignatureAuditLog).filter_by(envelope_db_id=envelope.id).order_by(SignatureAuditLog.created_at).all()
    return [{"id": row.id, "action": row.action, "recipient_id": row.recipient_id, "user_id": row.user_id, "details": row.details, "ip_address": row.ip_address, "user_agent": row.user_agent, "created_at": row.created_at} for row in rows]


def document_download(envelope: SignatureEnvelope, signed: bool):
    if signed:
        if not envelope.final_signed_pdf_path:
            raise HTTPException(404, "No signed PDF is available")
        path = storage_path("signed-documents", envelope.final_signed_pdf_path)
        suffix = "signed"
    else:
        path = storage_path("original-documents", envelope.original_pdf_path)
        suffix = "original"
    if not path.is_file():
        raise HTTPException(404, "Document file not found")
    return FileResponse(path, media_type="application/pdf", filename=safe_download_name(f"{envelope.envelope_id}_{suffix}.pdf"), headers={"Cache-Control": "private, no-store"})


@router.get("/envelopes/{envelope_id}/download-original")
def download_original(envelope_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    envelope = envelope_access(db, envelope_id, user)
    audit(db, envelope, "document downloaded", user_id=user.id, details={"version": "original"})
    db.commit()
    return document_download(envelope, False)


@router.get("/envelopes/{envelope_id}/download-signed")
def download_signed(envelope_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    envelope = envelope_access(db, envelope_id, user)
    audit(db, envelope, "document downloaded", user_id=user.id, details={"version": "signed"})
    db.commit()
    return document_download(envelope, True)


@router.get("/review/{raw_token}", response_model=ReviewRead)
def review_signing_request(
    raw_token: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _, envelope, recipient = resolve_token(db, raw_token, user)
    ip, agent = client_context(request)
    audit(db, envelope, "signer opened signing link", user_id=user.id, recipient_id=recipient.id, ip_address=ip, user_agent=agent)
    db.commit()
    return ReviewRead(
        envelope=envelope, recipient=recipient, can_act=True,
        document_url=f"/api/sign/review/{raw_token}/document",
    )


@router.get("/review/{raw_token}/document")
def review_document(raw_token: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _, envelope, _ = resolve_token(db, raw_token, user)
    content, _ = current_pdf(db, envelope)
    return StreamingResponse(BytesIO(content), media_type="application/pdf", headers={"Cache-Control": "private, no-store"})


@router.post("/review/{raw_token}/viewed")
def viewed(
    raw_token: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _, envelope, recipient = resolve_token(db, raw_token, user)
    recipient.viewed_at = recipient.viewed_at or datetime.now(timezone.utc)
    recipient.status = "viewed"
    ip, agent = client_context(request)
    audit(db, envelope, "signer viewed document", user_id=user.id, recipient_id=recipient.id, ip_address=ip, user_agent=agent)
    db.commit()
    return {"status": "viewed"}


@router.post("/review/{raw_token}/sign")
def sign(
    raw_token: str, data: SignAction, request: Request, background: BackgroundTasks,
    db: Session = Depends(get_db), user: User = Depends(require_permission("can_sign_documents")),
):
    if not data.confirmed_review:
        raise HTTPException(422, "Confirm that you reviewed the document")
    token, envelope, recipient = resolve_token(db, raw_token, user)
    ip, agent = client_context(request)
    apply_signature(db, envelope, recipient, user, data.typed_name)
    token.used_at = datetime.now(timezone.utc)
    recipient.ip_address, recipient.user_agent = ip, agent
    audit(db, envelope, "signer signed document", user_id=user.id, recipient_id=recipient.id, ip_address=ip, user_agent=agent, details={"verification_number": recipient.verification_number})
    audit(db, envelope, "signed PDF generated", user_id=user.id, recipient_id=recipient.id, details={"signed_pdf_hash": envelope.final_signed_pdf_hash})
    next_recipient = next((item for item in envelope.recipients if item.routing_order > recipient.routing_order and item.status == "pending"), None)
    next_url = None
    notification_ids = []
    if next_recipient:
        next_url, notification_id = activate_recipient(db, envelope, next_recipient)
        if notification_id:
            notification_ids.append(notification_id)
        envelope.status = "in_progress"
    else:
        envelope.status = "completed"
        envelope.completed_at = datetime.now(timezone.utc)
        if envelope.document_type == "asset_form" and envelope.document_reference_id:
            match = re.fullmatch(r"ASSET-FORM-(\d+)-(ALLOCATION|RETURN)", envelope.document_reference_id)
            if match:
                staff_user_id, phase = int(match.group(1)), match.group(2)
                new_status = "Allocated" if phase == "ALLOCATION" else "In Stock"
                changed = db.query(InventoryItem).filter(
                    InventoryItem.assigned_user_id == staff_user_id,
                    InventoryItem.is_active.is_(True),
                ).update({"status": new_status}, synchronize_session=False)
                db.add(AuditLog(
                    actor_id=user.id,
                    action="Asset lifecycle signature completed",
                    details={"user_id": staff_user_id, "phase": phase.lower(), "assets_updated": changed, "status": new_status},
                ))
        audit(db, envelope, "envelope completed", user_id=user.id)
        creator = db.get(User, envelope.created_by_id)
        if creator:
            notification_ids.append(queue_signature_completed(db, envelope, creator.email).id)
    db.commit()
    for notification_id in notification_ids:
        background.add_task(deliver_notification, notification_id)
    return {"status": envelope.status, "verification_number": recipient.verification_number, "next_signing_url": next_url if settings.environment == "development" else None}


def terminal_action(raw_token: str, data: CommentAction, request: Request, db: Session, user: User, action: str):
    token, envelope, recipient = resolve_token(db, raw_token, user)
    token.used_at = datetime.now(timezone.utc)
    recipient.status = "rejected" if action == "reject" else "returned"
    recipient.comment = data.comment
    recipient.ip_address, recipient.user_agent = client_context(request)
    envelope.status = "rejected" if action == "reject" else "returned"
    ip, agent = client_context(request)
    audit(db, envelope, f"signer {recipient.status} document", user_id=user.id, recipient_id=recipient.id, ip_address=ip, user_agent=agent, details={"comment": data.comment})
    creator = db.get(User, envelope.created_by_id)
    notification = None
    if creator:
        notification = queue_signature_rejected(db, envelope, creator.email, data.comment) if action == "reject" else queue_signature_returned(db, envelope, creator.email, data.comment)
    db.commit()
    return {"status": envelope.status, "notification_id": notification.id if notification else None}


@router.post("/review/{raw_token}/reject")
def reject(raw_token: str, data: CommentAction, request: Request, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(require_permission("can_sign_documents"))):
    result = terminal_action(raw_token, data, request, db, user, "reject")
    if result["notification_id"]:
        background.add_task(deliver_notification, result["notification_id"])
    return {"status": result["status"]}


@router.post("/review/{raw_token}/return")
def return_for_correction(raw_token: str, data: CommentAction, request: Request, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(require_permission("can_sign_documents"))):
    result = terminal_action(raw_token, data, request, db, user, "return")
    if result["notification_id"]:
        background.add_task(deliver_notification, result["notification_id"])
    return {"status": result["status"]}


@router.get("/verify")
def verify(
    envelope_id: str, verification_number: str | None = None, document_hash: str | None = None,
    db: Session = Depends(get_db), user: User = Depends(require_permission("can_verify_signed_documents")),
):
    envelope = db.query(SignatureEnvelope).filter(SignatureEnvelope.envelope_id == envelope_id).first()
    if not envelope:
        raise HTTPException(404, "Envelope not found")
    recipients = envelope.recipients
    if verification_number and not any(item.verification_number == verification_number for item in recipients):
        raise HTTPException(404, "Verification number not found in this envelope")
    stored_hash_valid = verify_envelope_file(envelope)
    supplied_hash_valid = None if not document_hash else document_hash.lower() in {
        envelope.original_pdf_hash.lower(), (envelope.final_signed_pdf_hash or "").lower()
    }
    audit(db, envelope, "verification checked", user_id=user.id, details={"verification_number": verification_number, "document_hash_supplied": bool(document_hash)})
    db.commit()
    creator = db.get(User, envelope.created_by_id)
    return {
        "envelope_id": envelope.envelope_id, "status": envelope.status,
        "title": envelope.title, "document_type": envelope.document_type,
        "created_by": creator.full_name if creator else None,
        "completed_at": envelope.completed_at,
        "stored_hash_valid": stored_hash_valid,
        "supplied_hash_valid": supplied_hash_valid,
        "signers": [{"full_name": item.full_name, "verification_number": item.verification_number, "signed_at": item.signed_at, "status": item.status} for item in recipients],
    }


@admin_router.get("/settings", response_model=SignSettingsRead)
def admin_sign_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("can_manage_sign_settings")),
):
    item = get_sign_settings(db)
    db.commit()
    db.refresh(item)
    return item


@admin_router.put("/settings", response_model=SignSettingsRead)
def update_admin_sign_settings(
    data: SignSettingsUpdate, db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_sign_settings")),
):
    item = get_sign_settings(db)
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    item.updated_by_id = actor.id
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item
