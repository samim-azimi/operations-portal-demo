from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NotificationOutbox, User, UserRole
from app.schemas import NotificationRead
from app.security import require_roles
from app.services.email_service import deliver_notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/outbox", response_model=list[NotificationRead])
def outbox(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    return (
        db.query(NotificationOutbox)
        .order_by(NotificationOutbox.created_at.desc())
        .limit(200)
        .all()
    )


@router.post("/outbox/{notification_id}/retry", response_model=NotificationRead)
def retry(
    notification_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    item = db.get(NotificationOutbox, notification_id)
    if not item:
        raise HTTPException(404, "Notification not found")
    item.status = "queued"
    item.last_error = None
    db.commit()
    db.refresh(item)
    background_tasks.add_task(deliver_notification, item.id)
    return item
