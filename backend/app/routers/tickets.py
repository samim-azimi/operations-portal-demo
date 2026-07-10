import csv
import io

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.database import get_db
from app.models import (
    Priority,
    SupportLocation,
    Ticket,
    TicketAIAnalysis,
    TicketAssignment,
    TicketAttachment,
    TicketCategory,
    TicketIntakeMetadata,
    TicketMessage,
    TicketNote,
    TicketStatus,
    User,
    UserRole,
)
from app.schemas import (
    AttachmentRead,
    MessageCreate,
    MessageRead,
    NoteCreate,
    NoteRead,
    Page,
    TicketCreate,
    TicketRead,
    TicketUpdate,
)
from app.security import get_current_user, require_permission, require_roles
from app.pagination import page_result
from app.services.ai_triage_service import AITriageService
from app.services.attachment_service import save_upload
from app.services.audit import record_audit
from app.services.email_service import (
    deliver_notification,
    queue_message_notification,
    queue_ticket_created,
    queue_ticket_update,
)
from app.services.knowledge_search import search_articles

router = APIRouter(
    prefix="/tickets",
    tags=["Help Desk"],
    dependencies=[Depends(require_permission("can_access_helpdesk"))],
)


def ticket_options():
    return (
        selectinload(Ticket.ai_analysis),
        selectinload(Ticket.notes),
        selectinload(Ticket.attachments),
        selectinload(Ticket.messages).joinedload(TicketMessage.author),
        joinedload(Ticket.assignment).joinedload(TicketAssignment.assignee),
        joinedload(Ticket.intake_metadata),
    )


def load_ticket(db: Session, ticket_id: int) -> Ticket:
    item = (
        db.query(Ticket)
        .options(*ticket_options())
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "Ticket not found")
    return item


def ensure_visible(ticket: Ticket, user: User) -> None:
    if user.role == UserRole.USER and ticket.requester_id != user.id:
        raise HTTPException(403, "You can only access your own tickets")


def run_triage(db: Session, ticket: Ticket) -> None:
    similar = search_articles(db, f"{ticket.title} {ticket.description}")
    result, provider = AITriageService().triage(ticket, similar)
    db.add(
        TicketAIAnalysis(
            ticket_id=ticket.id,
            **result.model_dump(),
            similar_issues=similar,
            provider=provider,
        )
    )
    ticket.category = result.category
    ticket.priority = Priority(result.priority)
    ticket.assigned_team = result.recommended_team
    ticket.human_approval_required = result.needs_human_approval
    record_audit(
        db,
        "AI triage completed",
        ticket_id=ticket.id,
        details={
            "provider": provider,
            "confidence": result.confidence_score,
        },
    )


def schedule_delivery(background_tasks: BackgroundTasks, ids: list[int]) -> None:
    if not settings.smtp_host:
        return
    for notification_id in ids:
        background_tasks.add_task(deliver_notification, notification_id)


def csv_safe(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text.replace("\r", " ").replace("\n", " ")


@router.get("", response_model=Page[TicketRead])
def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None, max_length=40),
    category: str | None = Query(None, max_length=80),
    focus: str | None = Query(None, pattern="^(approval|critical|low-confidence)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Ticket).options(*ticket_options())
    if user.role == UserRole.USER:
        query = query.filter(Ticket.requester_id == user.id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Ticket.title.ilike(term),
                Ticket.description.ilike(term),
                Ticket.full_name.ilike(term),
                Ticket.email.ilike(term),
                Ticket.device_name.ilike(term),
                Ticket.category.ilike(term),
            )
        )
    if status and status != "All":
        try:
            query = query.filter(Ticket.status == TicketStatus(status))
        except ValueError:
            raise HTTPException(422, "Unknown ticket status")
    if category and category != "All":
        query = query.filter(Ticket.category == category)
    if focus == "approval":
        query = query.filter(
            Ticket.human_approval_required.is_(True),
            Ticket.human_approved.is_(False),
        )
    elif focus == "critical":
        query = query.filter(Ticket.priority == Priority.CRITICAL)
    elif focus == "low-confidence":
        query = query.join(TicketAIAnalysis).filter(
            TicketAIAnalysis.confidence_score < 0.65
        )
    return page_result(
        query.order_by(Ticket.created_at.desc()), page, page_size
    )


@router.get("/export.csv")
def export_tickets(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
):
    tickets = (
        db.query(Ticket)
        .options(*ticket_options())
        .order_by(Ticket.created_at.desc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ticket_number",
            "created_at",
            "requester",
            "email",
            "department",
            "location",
            "device_tag",
            "title",
            "description",
            "requested_category",
            "ai_category",
            "priority",
            "status",
            "assigned_team",
            "assigned_specialist",
            "approval_required",
            "approval_completed",
            "ai_confidence",
            "resolution_notes",
        ]
    )
    for ticket in tickets:
        writer.writerow(
            [
                f"{ticket.id:04d}",
                ticket.created_at.isoformat(),
                csv_safe(ticket.full_name),
                csv_safe(ticket.email),
                csv_safe(ticket.department),
                csv_safe(ticket.location),
                csv_safe(ticket.device_name),
                csv_safe(ticket.title),
                csv_safe(ticket.description),
                csv_safe(ticket.requested_category),
                csv_safe(ticket.category),
                ticket.priority.value,
                ticket.status.value,
                csv_safe(ticket.assigned_team),
                csv_safe(ticket.assigned_user_name),
                "Yes" if ticket.human_approval_required else "No",
                "Yes" if ticket.human_approved else "No",
                (
                    round(ticket.ai_analysis.confidence_score, 3)
                    if ticket.ai_analysis
                    else ""
                ),
                csv_safe(ticket.resolution_notes),
            ]
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="helixdesk-tickets.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("", response_model=TicketRead, status_code=201)
def create_ticket(
    data: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    location_count = db.query(SupportLocation).filter(
        SupportLocation.is_active.is_(True)
    ).count()
    if location_count and not db.query(SupportLocation).filter(
        SupportLocation.name == data.location,
        SupportLocation.is_active.is_(True),
    ).first():
        raise HTTPException(422, "Select an active support location")
    if data.category and db.query(TicketCategory).count() and not db.query(
        TicketCategory
    ).filter(
        TicketCategory.name == data.category,
        TicketCategory.is_active.is_(True),
    ).first():
        raise HTTPException(422, "Select an active ticket category")
    ticket = Ticket(
        requester_id=user.id,
        full_name=user.full_name,
        email=user.email,
        department=user.department or "Not specified",
        location=data.location,
        device_name=data.device_name,
        title=data.title,
        description=data.description,
        urgency=data.urgency,
        attachment_url=data.attachment_url,
        category=data.category or "Other",
    )
    db.add(ticket)
    db.flush()
    db.add(
        TicketIntakeMetadata(
            ticket_id=ticket.id, requested_category=data.category
        )
    )
    record_audit(
        db,
        "Ticket created",
        user.id,
        ticket.id,
        {"title": ticket.title, "requested_category": data.category},
    )
    run_triage(db, ticket)
    db.flush()
    notification_ids = queue_ticket_created(db, ticket)
    db.commit()
    schedule_delivery(background_tasks, notification_ids)
    return load_ticket(db, ticket.id)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = load_ticket(db, ticket_id)
    ensure_visible(ticket, user)
    return ticket


@router.post("/{ticket_id}/triage", response_model=TicketRead)
def retriage(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
):
    ticket = load_ticket(db, ticket_id)
    if ticket.ai_analysis:
        db.delete(ticket.ai_analysis)
        db.flush()
    run_triage(db, ticket)
    record_audit(db, "AI triage requested", user.id, ticket.id)
    db.commit()
    return load_ticket(db, ticket.id)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
):
    ticket = load_ticket(db, ticket_id)
    before = {
        "category": ticket.category,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "assigned_user": ticket.assigned_user_name,
    }
    if data.accept_ai_recommendation and ticket.ai_analysis:
        ticket.category = ticket.ai_analysis.category
        ticket.priority = Priority(ticket.ai_analysis.priority)
        ticket.assigned_team = ticket.ai_analysis.recommended_team
    for field in ["category", "priority", "assigned_team", "resolution_notes"]:
        value = getattr(data, field)
        if value is not None:
            setattr(ticket, field, value)
    if "assigned_user_id" in data.model_fields_set:
        if data.assigned_user_id is None:
            if ticket.assignment:
                db.delete(ticket.assignment)
                db.flush()
        else:
            assignee = db.get(User, data.assigned_user_id)
            if (
                not assignee
                or not assignee.is_active
                or assignee.role not in {
                    UserRole.ADMIN,
                    UserRole.SUPER_ADMIN,
                    UserRole.SUPPORT,
                }
            ):
                raise HTTPException(422, "Select an active admin or support agent")
            if ticket.assignment:
                ticket.assignment.assignee_id = assignee.id
                ticket.assignment.assigned_by_id = user.id
            else:
                ticket.assignment = TicketAssignment(
                    assignee_id=assignee.id, assigned_by_id=user.id
                )
            db.flush()
    if data.human_approved is not None:
        ticket.human_approved = data.human_approved
        if data.human_approved:
            record_audit(
                db, "Human approval completed", user.id, ticket.id
            )
    if data.status is not None:
        if (
            data.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}
            and ticket.human_approval_required
            and not ticket.human_approved
        ):
            raise HTTPException(
                409,
                "Human approval is required before resolving this ticket",
            )
        if data.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED} and not (
            data.resolution_notes or ticket.resolution_notes
        ):
            raise HTTPException(422, "Resolution notes are required")
        ticket.status = data.status
    db.flush()
    after = {
        "category": ticket.category,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "assigned_user": ticket.assigned_user_name,
    }
    changes = []
    for field, new_value in after.items():
        if before[field] != new_value:
            changes.append(
                f"{field.replace('_', ' ').title()}: {new_value or 'Unassigned'}"
            )
            record_audit(
                db,
                f"{field.replace('_', ' ').title()} changed",
                user.id,
                ticket.id,
                {"from": before[field], "to": new_value},
            )
    if ticket.status == TicketStatus.CLOSED and before["status"] != "Closed":
        record_audit(db, "Ticket closed", user.id, ticket.id)
    notification_ids = (
        queue_ticket_update(db, ticket, "\n".join(changes))
        if changes
        else []
    )
    db.commit()
    schedule_delivery(background_tasks, notification_ids)
    return load_ticket(db, ticket.id)


@router.post("/{ticket_id}/messages", response_model=MessageRead, status_code=201)
def add_message(
    ticket_id: int,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = load_ticket(db, ticket_id)
    ensure_visible(ticket, user)
    message = TicketMessage(
        ticket_id=ticket.id, author_id=user.id, content=data.content.strip()
    )
    db.add(message)
    db.flush()
    record_audit(
        db,
        "Ticket message added",
        user.id,
        ticket.id,
        {"message_id": message.id},
    )
    notification_ids = queue_message_notification(
        db, ticket, user, message.content
    )
    db.commit()
    db.refresh(message)
    schedule_delivery(background_tasks, notification_ids)
    return message


@router.post("/{ticket_id}/notes", response_model=NoteRead, status_code=201)
def add_note(
    ticket_id: int,
    data: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
):
    load_ticket(db, ticket_id)
    note = TicketNote(
        ticket_id=ticket_id, author_id=user.id, **data.model_dump()
    )
    db.add(note)
    record_audit(db, "Internal note added", user.id, ticket_id)
    db.commit()
    db.refresh(note)
    return note


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentRead,
    status_code=201,
)
async def upload_attachment(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = load_ticket(db, ticket_id)
    ensure_visible(ticket, user)
    if len(ticket.attachments) >= settings.max_files_per_ticket:
        raise HTTPException(
            409,
            f"A ticket can have at most {settings.max_files_per_ticket} attachments",
        )
    metadata = await save_upload(file)
    attachment = TicketAttachment(
        ticket_id=ticket.id, uploader_id=user.id, **metadata
    )
    db.add(attachment)
    db.flush()
    record_audit(
        db,
        "Attachment uploaded",
        user.id,
        ticket.id,
        {"name": metadata["original_name"], "sha256": metadata["sha256"]},
    )
    notification_ids = queue_message_notification(
        db,
        ticket,
        user,
        f"Uploaded file: {metadata['original_name']}",
    )
    db.commit()
    db.refresh(attachment)
    schedule_delivery(background_tasks, notification_ids)
    return attachment


@router.get("/{ticket_id}/attachments/{attachment_id}")
def download_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = load_ticket(db, ticket_id)
    ensure_visible(ticket, user)
    attachment = db.get(TicketAttachment, attachment_id)
    if not attachment or attachment.ticket_id != ticket.id:
        raise HTTPException(404, "Attachment not found")
    path = (settings.upload_directory / attachment.stored_name).resolve()
    if (
        settings.upload_directory not in path.parents
        or not path.is_file()
    ):
        raise HTTPException(404, "Attachment file not found")
    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{ticket_id}/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = load_ticket(db, ticket_id)
    ensure_visible(ticket, user)
    attachment = db.get(TicketAttachment, attachment_id)
    if not attachment or attachment.ticket_id != ticket.id:
        raise HTTPException(404, "Attachment not found")
    if (
        user.role == UserRole.USER
        and attachment.uploader_id != user.id
    ):
        raise HTTPException(403, "You can only delete your own attachments")
    path = (settings.upload_directory / attachment.stored_name).resolve()
    if settings.upload_directory in path.parents:
        path.unlink(missing_ok=True)
    db.delete(attachment)
    record_audit(
        db,
        "Attachment deleted",
        user.id,
        ticket.id,
        {"name": attachment.original_name},
    )
    db.commit()
