import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

from pypdf import PdfReader
from reportlab.pdfgen import canvas

from app.config import settings
from app.models import SignatureEnvelope, SignatureToken, User
from app.services.sign_service import storage_path
from conftest import TestingSession


def sample_pdf() -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.setTitle("Purchase Request")
    pdf.drawString(72, 760, "PR-2026-0007 - Equipment request")
    pdf.drawString(72, 730, "This document requires sequential internal approval.")
    pdf.save()
    return output.getvalue()


def create_envelope(client, headers, recipient_emails=("manager@test.com", "user@test.com")):
    db = TestingSession()
    users = [db.query(User).filter_by(email=email).one() for email in recipient_emails]
    metadata = {
        "document_type": "purchase_request",
        "document_reference_id": "PR-2026-0007",
        "title": "Equipment purchase request",
        "subject": "Approval required",
        "message": "Please review the attached request.",
        "routing_mode": "sequential",
        "recipients": [
            {"user_id": user.id, "role_name": "Approver", "routing_order": index + 1}
            for index, user in enumerate(users)
        ],
    }
    db.close()
    return client.post(
        "/api/sign/envelopes",
        data={"metadata": json.dumps(metadata)},
        files={"file": ("request.pdf", sample_pdf(), "application/pdf")},
        headers=headers,
    )


def raw_token(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def test_signature_image_upload_validation_and_remove(client, user_headers):
    uploaded = client.post(
        "/api/sign/profile/signature",
        files={"file": ("signature.png", b"\x89PNG\r\n\x1a\nsignature", "image/png")},
        headers=user_headers,
    )
    assert uploaded.status_code == 200
    profile = client.get("/api/sign/profile/signature", headers=user_headers).json()
    assert profile["has_signature"] is True
    served = client.get("/api/sign/profile/signature/file", headers=user_headers)
    assert served.status_code == 200 and served.content.endswith(b"signature")
    invalid = client.post(
        "/api/sign/profile/signature",
        files={"file": ("signature.exe", b"MZ", "application/octet-stream")},
        headers=user_headers,
    )
    assert invalid.status_code == 415
    assert client.delete("/api/sign/profile/signature", headers=user_headers).status_code == 204
    assert client.get("/api/sign/profile/signature", headers=user_headers).json()["has_signature"] is False


def test_authorized_envelope_creation_and_secure_token(client, super_headers, user_headers):
    assert create_envelope(client, user_headers).status_code == 403
    created = create_envelope(client, super_headers)
    assert created.status_code == 201
    body = created.json()
    assert body["envelope_id"].startswith(f"ENV-{datetime.now().year}-")
    assert [item["routing_order"] for item in body["recipients"]] == [1, 2]
    assert body["original_pdf_hash"] == body["current_document_hash"]
    sent = client.post(f"/api/sign/envelopes/{body['id']}/send", headers=super_headers)
    assert sent.status_code == 200 and sent.json()["signing_url"]
    token = raw_token(sent.json()["signing_url"])
    db = TestingSession()
    stored = db.query(SignatureToken).one()
    assert stored.token_hash != token and len(stored.token_hash) == 64
    db.close()
    assert client.get(f"/api/sign/review/{token}", headers=user_headers).status_code == 403


def test_assigned_signer_can_open_review_from_portal(client, super_headers, manager_headers, user_headers):
    envelope = create_envelope(client, super_headers, ("manager@test.com",)).json()
    client.post(f"/api/sign/envelopes/{envelope['id']}/send", headers=super_headers)
    assert client.post(
        f"/api/sign/envelopes/{envelope['id']}/my-review-link",
        headers=user_headers,
    ).status_code == 403
    portal_link = client.post(
        f"/api/sign/envelopes/{envelope['id']}/my-review-link",
        headers=manager_headers,
    )
    assert portal_link.status_code == 200
    review_path = portal_link.json()["review_path"]
    assert review_path.startswith("/sign/review/")
    token = review_path.rsplit("/", 1)[-1]
    assert client.get(f"/api/sign/review/{token}", headers=manager_headers).status_code == 200
    signed = client.post(
        f"/api/sign/review/{token}/sign",
        json={"confirmed_review": True, "typed_name": "Manager"},
        headers=manager_headers,
    )
    assert signed.status_code == 200 and signed.json()["status"] == "completed"


def test_sequential_signing_generates_pdf_hashes_and_verification(
    client, super_headers, manager_headers, user_headers
):
    envelope = create_envelope(client, super_headers).json()
    first = client.post(f"/api/sign/envelopes/{envelope['id']}/send", headers=super_headers).json()
    manager_token = raw_token(first["signing_url"])
    review = client.get(f"/api/sign/review/{manager_token}", headers=manager_headers)
    assert review.status_code == 200
    assert review.json()["recipient"]["signature_page"] == -1
    assert 0 <= review.json()["recipient"]["signature_x"] < 1
    viewed = client.post(
        f"/api/sign/review/{manager_token}/viewed",
        headers={**manager_headers, "User-Agent": "Demo-Test-Browser"},
    )
    assert viewed.status_code == 200
    first_signed = client.post(
        f"/api/sign/review/{manager_token}/sign",
        json={"confirmed_review": True, "typed_name": "Manager"},
        headers={**manager_headers, "User-Agent": "Demo-Test-Browser"},
    )
    assert first_signed.status_code == 200
    assert first_signed.json()["status"] == "in_progress"
    assert first_signed.json()["verification_number"].startswith(f"SIG-{datetime.now().year}-")
    user_token = raw_token(first_signed.json()["next_signing_url"])
    final_signed = client.post(
        f"/api/sign/review/{user_token}/sign",
        json={"confirmed_review": True, "typed_name": "User"},
        headers=user_headers,
    )
    assert final_signed.status_code == 200 and final_signed.json()["status"] == "completed"
    detail = client.get(f"/api/sign/envelopes/{envelope['id']}", headers=super_headers).json()
    assert detail["final_signed_pdf_hash"] and detail["current_document_hash"] == detail["final_signed_pdf_hash"]
    assert all(item["verification_number"] for item in detail["recipients"])
    signed_pdf = client.get(f"/api/sign/envelopes/{envelope['id']}/download-signed", headers=user_headers)
    assert signed_pdf.status_code == 200 and signed_pdf.content.startswith(b"%PDF")
    rendered = PdfReader(BytesIO(signed_pdf.content))
    assert len(rendered.pages) == 1
    signed_text = rendered.pages[0].extract_text()
    assert "Signed by:" in signed_text and detail["recipients"][1]["verification_number"] in signed_text
    verified = client.get(
        "/api/sign/verify",
        params={"envelope_id": detail["envelope_id"], "verification_number": detail["recipients"][0]["verification_number"]},
        headers=user_headers,
    )
    assert verified.status_code == 200 and verified.json()["stored_hash_valid"] is True
    audit = client.get(f"/api/sign/envelopes/{envelope['id']}/audit", headers=super_headers).json()
    assert any(item["action"] == "signer signed document" and item["user_agent"] == "Demo-Test-Browser" for item in audit)


def test_reject_return_comments_and_expired_token(client, super_headers, manager_headers):
    envelope = create_envelope(client, super_headers, ("manager@test.com",)).json()
    token = raw_token(client.post(f"/api/sign/envelopes/{envelope['id']}/send", headers=super_headers).json()["signing_url"])
    assert client.post(f"/api/sign/review/{token}/reject", json={"comment": ""}, headers=manager_headers).status_code == 422
    rejected = client.post(
        f"/api/sign/review/{token}/reject",
        json={"comment": "Budget evidence is missing"},
        headers=manager_headers,
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"

    second = create_envelope(client, super_headers, ("manager@test.com",)).json()
    token2 = raw_token(client.post(f"/api/sign/envelopes/{second['id']}/send", headers=super_headers).json()["signing_url"])
    returned = client.post(
        f"/api/sign/review/{token2}/return",
        json={"comment": "Correct the project code"},
        headers=manager_headers,
    )
    assert returned.status_code == 200 and returned.json()["status"] == "returned"

    third = create_envelope(client, super_headers, ("manager@test.com",)).json()
    token3 = raw_token(client.post(f"/api/sign/envelopes/{third['id']}/send", headers=super_headers).json()["signing_url"])
    db = TestingSession()
    record = db.query(SignatureToken).filter(SignatureToken.token_hash.isnot(None)).order_by(SignatureToken.id.desc()).first()
    record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit(); db.close()
    assert client.get(f"/api/sign/review/{token3}", headers=manager_headers).status_code == 410


def test_hash_verification_detects_changed_signed_file(client, super_headers, manager_headers):
    envelope = create_envelope(client, super_headers, ("manager@test.com",)).json()
    token = raw_token(client.post(f"/api/sign/envelopes/{envelope['id']}/send", headers=super_headers).json()["signing_url"])
    client.post(
        f"/api/sign/review/{token}/sign",
        json={"confirmed_review": True, "typed_name": "Manager"},
        headers=manager_headers,
    )
    db = TestingSession()
    stored = db.get(SignatureEnvelope, envelope["id"])
    path = storage_path("signed-documents", stored.final_signed_pdf_path)
    path.write_bytes(path.read_bytes() + b"tampered")
    envelope_code = stored.envelope_id
    db.close()
    result = client.get("/api/sign/verify", params={"envelope_id": envelope_code}, headers=manager_headers)
    assert result.status_code == 200 and result.json()["stored_hash_valid"] is False

