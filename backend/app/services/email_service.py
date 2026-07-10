from __future__ import annotations

import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import NotificationOutbox, Ticket, User, UserRole


def _ticket_link(ticket_id: int) -> str:
    return f"{settings.public_app_url.rstrip('/')}/tickets/{ticket_id}"


def queue_email(
    db: Session,
    recipient: str,
    subject: str,
    body: str,
    event_type: str,
    ticket_id: int | None = None,
) -> NotificationOutbox:
    notification = NotificationOutbox(
        recipient=recipient.strip().lower(),
        subject=subject[:255],
        body=body,
        event_type=event_type,
        ticket_id=ticket_id,
        status="queued" if settings.smtp_host else "awaiting_configuration",
    )
    db.add(notification)
    db.flush()
    return notification


def admin_recipients(db: Session) -> set[str]:
    configured = set(settings.notification_admin_email_list)
    database_admins = {
        email
        for (email,) in db.query(User.email)
        .filter(
            User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]),
            User.is_active.is_(True),
        )
        .all()
    }
    return configured | database_admins


def queue_ticket_created(db: Session, ticket: Ticket) -> list[int]:
    ids: list[int] = []
    user_message = (
        f"Hello {ticket.full_name},\n\n"
        f"Your support request #{ticket.id:04d} has been received.\n"
        f"Title: {ticket.title}\n"
        f"Priority: {ticket.priority.value}\n"
        f"Status: {ticket.status.value}\n\n"
        f"Track the request here: {_ticket_link(ticket.id)}\n\n"
        "Please reply inside the ticket if the support team asks for more information."
    )
    ids.append(
        queue_email(
            db,
            ticket.email,
            f"Support request #{ticket.id:04d} received",
            user_message,
            "ticket_created_user",
            ticket.id,
        ).id
    )
    admin_message = (
        f"A new support request #{ticket.id:04d} was submitted.\n\n"
        f"Requester: {ticket.full_name} ({ticket.email})\n"
        f"Department: {ticket.department}\n"
        f"Location: {ticket.location}\n"
        f"Title: {ticket.title}\n"
        f"Description: {ticket.description}\n"
        f"Priority: {ticket.priority.value}\n"
        f"Category: {ticket.category}\n\n"
        f"Open ticket: {_ticket_link(ticket.id)}"
    )
    for recipient in admin_recipients(db):
        ids.append(
            queue_email(
                db,
                recipient,
                f"New ticket #{ticket.id:04d}: {ticket.title}",
                admin_message,
                "ticket_created_admin",
                ticket.id,
            ).id
        )
    return ids


def queue_ticket_update(
    db: Session, ticket: Ticket, change_summary: str
) -> list[int]:
    message = (
        f"Hello {ticket.full_name},\n\n"
        f"Your support request #{ticket.id:04d} has been updated.\n"
        f"{change_summary}\n\n"
        f"Current status: {ticket.status.value}\n"
        f"Assigned specialist: {ticket.assigned_user_name or 'Not assigned yet'}\n\n"
        f"View the latest activity: {_ticket_link(ticket.id)}"
    )
    notification = queue_email(
        db,
        ticket.email,
        f"Update on support request #{ticket.id:04d}",
        message,
        "ticket_updated",
        ticket.id,
    )
    return [notification.id]


def queue_message_notification(
    db: Session, ticket: Ticket, author: User, message_text: str
) -> list[int]:
    recipients: set[str]
    if author.role == UserRole.USER:
        recipients = admin_recipients(db)
        if ticket.assignment and ticket.assignment.assignee:
            recipients.add(ticket.assignment.assignee.email)
    else:
        recipients = {ticket.email}
    body = (
        f"{author.full_name} added a message to support request #{ticket.id:04d}.\n\n"
        f"{message_text}\n\n"
        f"Open the conversation: {_ticket_link(ticket.id)}"
    )
    return [
        queue_email(
            db,
            recipient,
            f"New message on ticket #{ticket.id:04d}",
            body,
            "ticket_message",
            ticket.id,
        ).id
        for recipient in recipients
        if recipient.lower() != author.email.lower()
    ]


def _queue_sign_email(db: Session, recipient: str, subject: str, body: str, event_type: str):
    item = queue_email(db, recipient, subject, body, event_type)
    if not settings.smtp_host and settings.environment.lower() == "development":
        print(f"[Digital Signature development email]\nTo: {recipient}\nSubject: {subject}\n{body}")
    return item


def queue_signature_request(db: Session, envelope, recipient, signing_url: str):
    body = (
        f"Dear {recipient.full_name},\n\n"
        "A document is waiting for your signature in Operations Portal.\n\n"
        f"Document: {envelope.title}\n"
        f"Envelope ID: {envelope.envelope_id}\n"
        f"Status: Pending Signature\n\n"
        f"Review and sign: {signing_url}\n\n"
        "You must log in using the organizational account assigned to this request.\n\n"
        "Best regards,\nOperations Portal"
    )
    return _queue_sign_email(
        db, recipient.email,
        f"Signature Required - {envelope.document_reference_id or envelope.envelope_id}",
        body, "signature_required",
    )


def queue_signature_completed(db: Session, envelope, recipient_email: str):
    return _queue_sign_email(
        db, recipient_email, f"Signing completed - {envelope.envelope_id}",
        f"The signing envelope {envelope.envelope_id} ({envelope.title}) is completed.",
        "signature_completed",
    )


def queue_signature_rejected(db: Session, envelope, recipient_email: str, comment: str):
    return _queue_sign_email(
        db, recipient_email, f"Signing rejected - {envelope.envelope_id}",
        f"The envelope {envelope.envelope_id} was rejected.\n\nComment: {comment}",
        "signature_rejected",
    )


def queue_signature_returned(db: Session, envelope, recipient_email: str, comment: str):
    return _queue_sign_email(
        db, recipient_email, f"Returned for correction - {envelope.envelope_id}",
        f"The envelope {envelope.envelope_id} was returned for correction.\n\nComment: {comment}",
        "signature_returned",
    )


def deliver_notification(notification_id: int) -> None:
    db = SessionLocal()
    try:
        item = db.get(NotificationOutbox, notification_id)
        if not item or item.status == "sent":
            return
        item.attempts += 1
        if not settings.smtp_host:
            item.status = "awaiting_configuration"
            item.last_error = "SMTP_HOST is not configured"
            db.commit()
            return
        message = EmailMessage()
        message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
        message["To"] = item.recipient
        message["Subject"] = item.subject
        message.set_content(item.body)
        with smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=15
        ) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        item.status = "sent"
        item.sent_at = datetime.now(timezone.utc)
        item.last_error = None
        db.commit()
    except Exception as exc:
        if "item" in locals() and item:
            item.status = "failed"
            item.last_error = str(exc)[:500]
            db.commit()
    finally:
        db.close()
