from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Priority,
    Ticket,
    TicketAIAnalysis,
    TicketStatus,
    UserRole,
)
from app.routers.tickets import ticket_options
from app.schemas import DashboardStats
from app.security import require_permission, require_roles

router = APIRouter(
    prefix="/dashboard",
    tags=["Faza Help Desk Dashboard"],
    dependencies=[Depends(require_permission("can_access_helpdesk"))],
)


def grouped_counts(db: Session, column) -> dict[str, int]:
    return {
        (key.value if hasattr(key, "value") else str(key)): count
        for key, count in db.query(column, func.count(Ticket.id))
        .group_by(column)
        .all()
    }


@router.get("/stats", response_model=DashboardStats)
def stats(
    db: Session = Depends(get_db),
    _: object = Depends(
        require_roles(
            UserRole.ADMIN, UserRole.SUPPORT, UserRole.MANAGER
        )
    ),
):
    inactive = [TicketStatus.CLOSED, TicketStatus.RESOLVED]
    active_filter = Ticket.status.notin_(inactive)
    total = db.query(func.count(Ticket.id)).scalar() or 0
    open_count = (
        db.query(func.count(Ticket.id)).filter(active_filter).scalar() or 0
    )
    analysis_count = (
        db.query(func.count(TicketAIAnalysis.id)).scalar() or 0
    )
    average_confidence = (
        db.query(func.avg(TicketAIAnalysis.confidence_score)).scalar() or 0
    )
    by_team = {
        team or "Unassigned": count
        for team, count in db.query(
            Ticket.assigned_team, func.count(Ticket.id)
        )
        .filter(active_filter)
        .group_by(Ticket.assigned_team)
        .all()
    }
    recent = (
        db.query(Ticket)
        .options(*ticket_options())
        .order_by(Ticket.created_at.desc())
        .limit(8)
        .all()
    )
    return DashboardStats(
        total_tickets=total,
        open_tickets=open_count,
        resolved_tickets=(
            db.query(func.count(Ticket.id))
            .filter(Ticket.status == TicketStatus.RESOLVED)
            .scalar()
            or 0
        ),
        closed_tickets=(
            db.query(func.count(Ticket.id))
            .filter(Ticket.status == TicketStatus.CLOSED)
            .scalar()
            or 0
        ),
        critical_tickets=(
            db.query(func.count(Ticket.id))
            .filter(
                active_filter, Ticket.priority == Priority.CRITICAL
            )
            .scalar()
            or 0
        ),
        high_risk_tickets=(
            db.query(func.count(Ticket.id))
            .filter(
                active_filter,
                Ticket.priority.in_(
                    [Priority.HIGH, Priority.CRITICAL]
                ),
            )
            .scalar()
            or 0
        ),
        pending_approval=(
            db.query(func.count(Ticket.id))
            .filter(
                active_filter,
                Ticket.human_approval_required.is_(True),
                Ticket.human_approved.is_(False),
            )
            .scalar()
            or 0
        ),
        low_confidence_tickets=(
            db.query(func.count(Ticket.id))
            .join(TicketAIAnalysis)
            .filter(
                active_filter,
                TicketAIAnalysis.confidence_score < 0.65,
            )
            .scalar()
            or 0
        ),
        unassigned_tickets=(
            db.query(func.count(Ticket.id))
            .filter(active_filter, Ticket.assigned_team.is_(None))
            .scalar()
            or 0
        ),
        average_ai_confidence=round(float(average_confidence), 3),
        automation_coverage=(
            round(analysis_count / total, 3) if total else 0
        ),
        by_category=grouped_counts(db, Ticket.category),
        by_priority=grouped_counts(db, Ticket.priority),
        by_status=grouped_counts(db, Ticket.status),
        by_team=by_team,
        recent_tickets=recent,
    )
