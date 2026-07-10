from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User, UserRole
from app.pagination import page_result
from app.schemas import AuditLogRead, Page
from app.security import require_permission, require_roles

router = APIRouter(
    prefix="/audit-logs",
    tags=["Faza Administration"],
    dependencies=[Depends(require_permission("can_access_admin"))],
)


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    actor_id: int | None = None,
    ticket_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = db.query(AuditLog)
    if actor_id is not None:
        query = query.filter(AuditLog.actor_id == actor_id)
    if ticket_id is not None:
        query = query.filter(AuditLog.ticket_id == ticket_id)
    return page_result(
        query.order_by(AuditLog.created_at.desc()), page, page_size
    )
