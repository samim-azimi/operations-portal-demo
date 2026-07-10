from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    InventoryItem, KnowledgeBaseArticle, NotificationOutbox, SignatureEnvelope,
    StockItem, StockRequest, Ticket, TicketStatus, User, UserRole,
)
from app.modules import MODULES, permissions_for_role
from app.schemas import WorkspaceSummary
from app.security import require_permission

router = APIRouter(
    prefix="/workspace",
    tags=["Operations Portal"],
    dependencies=[Depends(require_permission("can_access_workspace"))],
)

def grouped_counts(query, column) -> dict[str, int]:
    return {
        getattr(value, "value", value): count
        for value, count in query.with_entities(column, func.count()).group_by(column).all()
    }


@router.get("/summary", response_model=WorkspaceSummary)
def workspace_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_access_workspace")),
):
    permissions = permissions_for_role(user.role)
    modules = [
        module
        for module in MODULES
        if module.status != "hidden"
        and module.required_permission in permissions
    ]
    open_count = None
    recent_activity = []
    module_insights = {}
    if "can_access_helpdesk" in permissions:
        ticket_query = db.query(Ticket)
        if user.role == UserRole.USER:
            ticket_query = ticket_query.filter(Ticket.requester_id == user.id)
        module_insights["helpdesk"] = grouped_counts(ticket_query, Ticket.status)
        open_count = ticket_query.filter(
            Ticket.status.notin_(
                [TicketStatus.RESOLVED, TicketStatus.CLOSED]
            )
        ).count()
        recent = (
            ticket_query.with_entities(
                Ticket.id,
                Ticket.title,
                Ticket.status,
                Ticket.updated_at,
            )
            .order_by(Ticket.updated_at.desc())
            .limit(5)
            .all()
        )
        recent_activity = [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status.value,
                "updated_at": item.updated_at,
                "module": "helpdesk",
            }
            for item in recent
        ]
    if "can_access_inventory" in permissions:
        inventory_query = db.query(InventoryItem).filter(InventoryItem.is_active.is_(True))
        if "can_manage_inventory" not in permissions:
            inventory_query = inventory_query.filter(InventoryItem.assigned_user_id == user.id)
        module_insights["inventory"] = grouped_counts(inventory_query, InventoryItem.status)
    if "can_access_stock" in permissions:
        stock_query = db.query(StockRequest)
        if "can_manage_stock" not in permissions and "can_view_all_stock_requests" not in permissions:
            stock_query = stock_query.filter(StockRequest.requested_by_id == user.id)
        module_insights["stock"] = grouped_counts(stock_query, StockRequest.status)
    notification_count = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.recipient == user.email,
            NotificationOutbox.status.in_(
                ["queued", "awaiting_configuration", "failed"]
            ),
        )
        .count()
    )
    return {
        "accessible_modules": len(modules),
        "active_modules": sum(
            module.status == "active" for module in modules
        ),
        "open_helpdesk_tickets": open_count,
        "notification_count": notification_count,
        "recent_activity": recent_activity,
        "my_asset_count": db.query(InventoryItem).filter(
            InventoryItem.is_active.is_(True), InventoryItem.assigned_user_id == user.id,
        ).count(),
        "my_stock_request_count": db.query(StockRequest).filter(
            StockRequest.requested_by_id == user.id,
        ).count(),
        "my_ticket_count": db.query(Ticket).filter(Ticket.requester_id == user.id).count(),
        "module_insights": module_insights,
    }


def search_result(module: str, title: str, subtitle: str, route: str) -> dict:
    return {"module": module, "title": title, "subtitle": subtitle, "route": route}


@router.get("/search")
def workspace_search(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_access_workspace")),
):
    """Permission-aware portal search used only by the Workspace dashboard."""
    permissions = permissions_for_role(user.role)
    term = f"%{q.strip()}%"
    results: list[dict] = []

    for module in MODULES:
        if module.status != "hidden" and module.required_permission in permissions:
            if q.lower() in f"{module.name} {module.description} {module.category}".lower():
                results.append(search_result(
                    "Module", module.short_name or module.name, module.description, module.route,
                ))

    if "can_access_helpdesk" in permissions:
        ticket_query = db.query(Ticket)
        if user.role == UserRole.USER:
            ticket_query = ticket_query.filter(Ticket.requester_id == user.id)
        tickets = (
            ticket_query
            .filter(or_(Ticket.title.ilike(term), Ticket.description.ilike(term), Ticket.email.ilike(term)))
            .order_by(Ticket.updated_at.desc())
            .limit(limit)
            .all()
        )
        results.extend(search_result(
            "Help Desk", item.title, f"{item.status.value} · {item.email}", f"/tickets/{item.id}",
        ) for item in tickets)

    if "can_access_inventory" in permissions:
        inventory_query = db.query(InventoryItem).filter(InventoryItem.is_active.is_(True))
        if "can_manage_inventory" not in permissions:
            inventory_query = inventory_query.filter(InventoryItem.assigned_user_id == user.id)
        assets = (
            inventory_query
            .filter(or_(
                InventoryItem.designation.ilike(term),
                InventoryItem.serial_number.ilike(term),
                InventoryItem.brand.ilike(term),
                InventoryItem.model.ilike(term),
                InventoryItem.user_name.ilike(term),
            ))
            .order_by(InventoryItem.updated_at.desc())
            .limit(limit)
            .all()
        )
        results.extend(search_result(
            "IMS", item.designation, f"{item.logistics_code} · {item.status}", "/inventory/my-assets" if "can_manage_inventory" not in permissions else "/inventory",
        ) for item in assets)

    if "can_access_stock" in permissions:
        request_query = db.query(StockRequest)
        if "can_manage_stock" not in permissions and "can_view_all_stock_requests" not in permissions:
            request_query = request_query.filter(StockRequest.requested_by_id == user.id)
        stock_requests = (
            request_query
            .join(StockItem, StockRequest.item_id == StockItem.id)
            .filter(or_(StockRequest.request_number.ilike(term), StockItem.item_name.ilike(term), StockRequest.reason.ilike(term)))
            .order_by(StockRequest.updated_at.desc())
            .limit(limit)
            .all()
        )
        results.extend(search_result(
            "Stock", item.request_number, f"{item.status} · {item.requested_quantity}", "/stock/my-requests",
        ) for item in stock_requests)

    if "can_access_knowledge" in permissions:
        articles = (
            db.query(KnowledgeBaseArticle)
            .filter(or_(
                KnowledgeBaseArticle.title.ilike(term),
                KnowledgeBaseArticle.problem_description.ilike(term),
                KnowledgeBaseArticle.solution.ilike(term),
            ))
            .order_by(KnowledgeBaseArticle.updated_at.desc())
            .limit(limit)
            .all()
        )
        results.extend(search_result(
            "Knowledge", item.title, item.category, "/knowledge",
        ) for item in articles)

    if "can_access_sign" in permissions:
        envelope_query = db.query(SignatureEnvelope)
        if "can_view_all_signature_envelopes" not in permissions:
            envelope_query = envelope_query.filter(SignatureEnvelope.recipients.any(user_id=user.id))
        envelopes = (
            envelope_query
            .filter(or_(
                SignatureEnvelope.envelope_id.ilike(term),
                SignatureEnvelope.title.ilike(term),
                SignatureEnvelope.document_reference_id.ilike(term),
            ))
            .order_by(SignatureEnvelope.updated_at.desc())
            .limit(limit)
            .all()
        )
        results.extend(search_result(
            "Sign", item.title, f"{item.envelope_id} · {item.status}", f"/sign/envelopes/{item.id}",
        ) for item in envelopes)

    return {"query": q, "items": results[:limit]}
