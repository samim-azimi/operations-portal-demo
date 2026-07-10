from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AuditLog, Dashboard, DashboardAccess, User
from app.modules import permissions_for_role
from app.pagination import page_result
from app.schemas import Page
from app.security import get_current_user, require_permission
from app.stock_schemas import DashboardCreate, DashboardRead, DashboardUpdate

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


def validate_embed_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(422, "Dashboard embed URL must be a valid HTTPS URL")


def apply_access(dashboard: Dashboard, allowed_roles: list[str], user_ids: list[int], db: Session):
    dashboard.allowed_roles = sorted(set(allowed_roles))
    existing = {access.user_id: access for access in dashboard.accesses}
    wanted = set(user_ids)
    for user_id in wanted:
        if not db.get(User, user_id): raise HTTPException(422, f"User {user_id} was not found")
        if user_id in existing: existing[user_id].can_view = True
        else: db.add(DashboardAccess(dashboard_id=dashboard.id, user_id=user_id, can_view=True))
    for user_id, access in existing.items():
        if user_id not in wanted: db.delete(access)


@router.get("/my", response_model=Page[DashboardRead])
def my_dashboards(
    page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),
    db:Session=Depends(get_db),user:User=Depends(require_permission("can_access_dashboards")),
):
    query=db.query(Dashboard).options(joinedload(Dashboard.accesses)).filter(Dashboard.is_active.is_(True)).order_by(Dashboard.title)
    all_items=query.all()
    can_view_all="can_view_all_dashboards" in permissions_for_role(user.role)
    allowed=[dashboard for dashboard in all_items if can_view_all or user.role.value in (dashboard.allowed_roles or []) or user.id in dashboard.user_ids]
    start=(page-1)*page_size;items=allowed[start:start+page_size]
    for dashboard in items:
        db.add(AuditLog(actor_id=user.id,action="Dashboard viewed",details={"dashboard_id":dashboard.id}))
    db.commit()
    return {"items":items,"total":len(allowed),"page":page,"page_size":page_size,"pages":(len(allowed)+page_size-1)//page_size}


@router.get("", response_model=Page[DashboardRead])
def list_dashboards(
    page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),
    db:Session=Depends(get_db),_:User=Depends(require_permission("can_manage_dashboards")),
):
    return page_result(db.query(Dashboard).options(joinedload(Dashboard.accesses)).order_by(Dashboard.updated_at.desc()),page,page_size)


@router.post("", response_model=DashboardRead, status_code=201)
def create_dashboard(
    data:DashboardCreate,db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_dashboards")),
):
    validate_embed_url(data.embed_url)
    dashboard=Dashboard(**data.model_dump(exclude={"user_ids"}),created_by_id=actor.id,updated_by_id=actor.id)
    db.add(dashboard);db.flush();apply_access(dashboard,data.allowed_roles,data.user_ids,db)
    db.add(AuditLog(actor_id=actor.id,action="Dashboard created",details={"dashboard_id":dashboard.id}))
    db.commit();db.refresh(dashboard);return dashboard


@router.get("/{dashboard_id}", response_model=DashboardRead)
def get_dashboard(dashboard_id:int,db:Session=Depends(get_db),user:User=Depends(require_permission("can_access_dashboards"))):
    dashboard=db.query(Dashboard).options(joinedload(Dashboard.accesses)).filter(Dashboard.id==dashboard_id).first()
    if not dashboard:raise HTTPException(404,"Dashboard not found")
    allowed="can_view_all_dashboards" in permissions_for_role(user.role) or user.role.value in (dashboard.allowed_roles or []) or user.id in dashboard.user_ids
    if not allowed:raise HTTPException(403,"You do not have access to this dashboard")
    return dashboard


@router.put("/{dashboard_id}", response_model=DashboardRead)
def update_dashboard(
    dashboard_id:int,data:DashboardUpdate,db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_dashboards")),
):
    dashboard=db.query(Dashboard).options(joinedload(Dashboard.accesses)).filter(Dashboard.id==dashboard_id).first()
    if not dashboard:raise HTTPException(404,"Dashboard not found")
    changes=data.model_dump(exclude_unset=True)
    user_ids=changes.pop("user_ids",None);allowed_roles=changes.get("allowed_roles",dashboard.allowed_roles)
    if changes.get("embed_url"):validate_embed_url(changes["embed_url"])
    for field,value in changes.items():setattr(dashboard,field,value)
    dashboard.updated_by_id=actor.id
    if user_ids is not None:apply_access(dashboard,allowed_roles,user_ids,db)
    db.add(AuditLog(actor_id=actor.id,action="Dashboard updated",details={"dashboard_id":dashboard.id,"fields":sorted(changes)}))
    db.commit();db.refresh(dashboard);return dashboard


@router.patch("/{dashboard_id}/deactivate", response_model=DashboardRead)
def deactivate_dashboard(
    dashboard_id:int,db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_dashboards")),
):
    dashboard=db.get(Dashboard,dashboard_id)
    if not dashboard:raise HTTPException(404,"Dashboard not found")
    dashboard.is_active=False;dashboard.updated_by_id=actor.id
    db.add(AuditLog(actor_id=actor.id,action="Dashboard deactivated",details={"dashboard_id":dashboard.id}))
    db.commit();db.refresh(dashboard);return dashboard
