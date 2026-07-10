import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    AuditLog, NotificationOutbox, StockCard, StockCategory, StockItem, StockMovement, StockRequest,
    StockRequestStatusHistory, User,
)
from app.modules import permissions_for_role
from app.pagination import page_result
from app.schemas import (
    Page, StockItemCreate, StockItemRead, StockItemUpdate,
    StockRequestCreate, StockRequestDecision, StockRequestRead,
)
from app.security import get_current_user, require_permission
from app.services.image_upload_service import image_path, remove_image, save_image

router = APIRouter(
    prefix="/stock",
    tags=["Stock Management System"],
    dependencies=[Depends(require_permission("can_access_stock"))],
)


def sync_status(item: StockItem):
    if not item.is_active:
        item.status = "Inactive"
    elif item.quantity_available <= 0:
        item.status = "Out of Stock"
    elif item.quantity_available <= item.low_stock_threshold:
        item.status = "Low Stock"
    else:
        item.status = "Available"


def notify(db, user: User, subject: str, body: str, event_type: str):
    db.add(NotificationOutbox(
        recipient=user.email, subject=subject, body=body, event_type=event_type,
        status="queued",
    ))


def stock_query(db, q=None, category=None, category_id=None, location=None, status=None, include_inactive=False):
    query = db.query(StockItem)
    if not include_inactive: query = query.filter(StockItem.is_active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(StockItem.item_name.ilike(term), StockItem.specifications.ilike(term)))
    if category: query = query.filter(StockItem.category == category)
    if category_id: query = query.filter(StockItem.category_id == category_id)
    if location: query = query.filter(StockItem.location == location)
    if status: query = query.filter(StockItem.status == status)
    return query


@router.get("/items/export/csv")
def export_stock(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_export_stock")),
):
    items = stock_query(db, include_inactive=True).order_by(StockItem.item_name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["item name","category","specifications","quantity available","unit","location","responsible person","status","notes","updated date"])
    for item in items:
        writer.writerow([item.item_name,item.category,item.specifications or "",item.quantity_available,item.unit,item.location,item.responsible_person_name or "",item.status,item.notes or "",item.updated_at.isoformat()])
    db.add(AuditLog(actor_id=actor.id, action="Stock CSV exported", details={"records": len(items)})); db.commit()
    return StreamingResponse(iter(["\ufeff"+output.getvalue()]),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":'attachment; filename="operations-stock.csv"'})


@router.get("/requests/export/csv")
def export_requests(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_export_stock")),
):
    rows = db.query(StockRequest).options(joinedload(StockRequest.requested_by), joinedload(StockRequest.item)).order_by(StockRequest.request_date.desc()).all()
    output=io.StringIO(); writer=csv.writer(output)
    writer.writerow(["request number","requested by","department","location","item","quantity","status","approved by","delivered by","request date","decision date","delivery date"])
    for row in rows:
        writer.writerow([row.request_number,row.requested_by_name,row.department or "",row.location,row.item_name,row.requested_quantity,row.status,row.approved_by_name or "",row.delivered_by_name or "",row.request_date.isoformat(),row.decision_date.isoformat() if row.decision_date else "",row.delivery_date.isoformat() if row.delivery_date else ""])
    db.add(AuditLog(actor_id=actor.id, action="Stock requests CSV exported", details={"records":len(rows)})); db.commit()
    return StreamingResponse(iter(["\ufeff"+output.getvalue()]),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":'attachment; filename="operations-stock-requests.csv"'})


@router.get("/items", response_model=Page[StockItemRead])
def list_items(
    page:int=Query(1,ge=1), page_size:int=Query(24,ge=1,le=100),
    q:str|None=Query(None,max_length=200), category:str|None=None, category_id:int|None=None, location:str|None=None,
    status:str|None=None, include_inactive:bool=False, db:Session=Depends(get_db),
):
    return page_result(stock_query(db,q,category,category_id,location,status,include_inactive).order_by(StockItem.updated_at.desc()),page,page_size)


@router.post("/items", response_model=StockItemRead, status_code=201)
def create_item(
    data:StockItemCreate, db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_stock")),
):
    values=data.model_dump()
    if data.category_id:
        category=db.get(StockCategory,data.category_id)
        if not category or not category.is_active: raise HTTPException(422,"Stock category not found")
        values["category"]=category.name
    item=StockItem(**values); sync_status(item); db.add(item); db.flush()
    db.add(AuditLog(actor_id=actor.id,action="Stock item created",details={"stock_item_id":item.id})); db.commit(); db.refresh(item); return item


@router.put("/items/{item_id}", response_model=StockItemRead)
def update_item(
    item_id:int,data:StockItemUpdate,db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_stock")),
):
    item=db.get(StockItem,item_id)
    if not item: raise HTTPException(404,"Stock item not found")
    changes=data.model_dump(exclude_unset=True)
    if changes.get("category_id"):
        category=db.get(StockCategory,changes["category_id"])
        if not category: raise HTTPException(422,"Stock category not found")
        changes["category"]=category.name
    for field,value in changes.items(): setattr(item,field,value)
    sync_status(item)
    db.add(AuditLog(actor_id=actor.id,action="Stock item updated",details={"stock_item_id":item.id,"fields":sorted(changes)})); db.commit(); db.refresh(item); return item


@router.patch("/items/{item_id}/deactivate", response_model=StockItemRead)
def deactivate_item(
    item_id:int,db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_stock")),
):
    item=db.get(StockItem,item_id)
    if not item: raise HTTPException(404,"Stock item not found")
    item.is_active=False; sync_status(item)
    db.add(AuditLog(actor_id=actor.id,action="Stock item deactivated",details={"stock_item_id":item.id})); db.commit(); db.refresh(item); return item


@router.post("/items/{item_id}/picture", response_model=StockItemRead)
async def upload_item_picture(
    item_id:int,file:UploadFile=File(...),db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_manage_stock")),
):
    item=db.get(StockItem,item_id)
    if not item: raise HTTPException(404,"Stock item not found")
    saved=await save_image(file,"stock"); remove_image("stock",item.picture_stored_name)
    item.picture_stored_name=saved["stored_name"]
    db.add(AuditLog(actor_id=actor.id,action="Stock item picture updated",details={"stock_item_id":item.id})); db.commit(); db.refresh(item); return item


@router.get("/items/{item_id}/picture")
def get_item_picture(item_id:int,db:Session=Depends(get_db),_:User=Depends(get_current_user)):
    item=db.get(StockItem,item_id)
    if not item or not item.picture_stored_name: raise HTTPException(404,"Picture not found")
    return FileResponse(image_path("stock",item.picture_stored_name),headers={"Cache-Control":"private, max-age=300","X-Content-Type-Options":"nosniff"})


def request_query(db):
    return db.query(StockRequest).options(joinedload(StockRequest.requested_by),joinedload(StockRequest.item),joinedload(StockRequest.approved_by),joinedload(StockRequest.delivered_by))


@router.get("/requests/my", response_model=Page[StockRequestRead])
def list_my_requests(
    page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),status:str|None=None,
    db:Session=Depends(get_db),user:User=Depends(get_current_user),
):
    query=request_query(db).filter(StockRequest.requested_by_id==user.id)
    if status: query=query.filter(StockRequest.status==status)
    return page_result(query.order_by(StockRequest.request_date.desc()),page,page_size)


@router.get("/requests", response_model=Page[StockRequestRead])
def list_all_requests(
    page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),status:str|None=None,
    db:Session=Depends(get_db),
    user:User=Depends(require_permission("can_view_all_stock_requests")),
):
    query=request_query(db)
    if status: query=query.filter(StockRequest.status==status)
    return page_result(query.order_by(StockRequest.request_date.desc()),page,page_size)


@router.post("/requests", response_model=StockRequestRead, status_code=201)
def create_request(
    data:StockRequestCreate,db:Session=Depends(get_db),
    user:User=Depends(require_permission("can_request_stock")),
):
    item=db.get(StockItem,data.item_id)
    if not item or not item.is_active: raise HTTPException(404,"Stock item not found")
    if item.category_record and not item.category_record.is_active:
        raise HTTPException(409,"This stock category is inactive")
    if item.quantity_available<=0: raise HTTPException(409,"This item is out of stock")
    if data.requested_quantity>item.quantity_available: raise HTTPException(409,"Requested quantity is higher than available stock")
    request=StockRequest(
        request_number="PENDING",requested_by_id=user.id,department=user.department,
        location=data.location,item_id=item.id,requested_quantity=data.requested_quantity,reason=data.reason,
    )
    db.add(request); db.flush(); request.request_number=f"STK-{datetime.now(timezone.utc):%Y%m}-{request.id:05d}"
    db.add(StockRequestStatusHistory(request_id=request.id,status="Pending",changed_by_id=user.id))
    db.add(AuditLog(actor_id=user.id,action="Stock request submitted",details={"stock_request_id":request.id,"item_id":item.id}))
    notify(db,user,f"Stock request {request.request_number} received",f"Your request for {data.requested_quantity} × {item.item_name} is pending review.","stock_request_submitted")
    db.commit(); db.refresh(request); return request


@router.patch("/requests/{request_id}", response_model=StockRequestRead)
def decide_request(
    request_id:int,data:StockRequestDecision,db:Session=Depends(get_db),
    actor:User=Depends(require_permission("can_approve_stock_requests")),
):
    request=db.query(StockRequest).options(joinedload(StockRequest.item),joinedload(StockRequest.requested_by)).filter(StockRequest.id==request_id).first()
    if not request: raise HTTPException(404,"Stock request not found")
    if request.status in {"Delivered","Rejected","Cancelled"}: raise HTTPException(409,"This request is already final")
    now=datetime.now(timezone.utc)
    if data.status=="Delivered":
        if request.status not in {"Approved","Ready for Pickup"}: raise HTTPException(409,"Approve the request before delivery")
        if request.item.quantity_available<request.requested_quantity: raise HTTPException(409,"Not enough stock is available for delivery")
        request.item.quantity_available-=request.requested_quantity; sync_status(request.item)
        request.delivered_by_id=actor.id; request.delivery_date=now
        card=db.query(StockCard).filter_by(stock_item_id=request.item_id,is_active=True).first()
        db.add(StockMovement(
            stock_item_id=request.item_id,stock_request_id=request.id,
            stock_card_id=card.id if card else None,movement_type="OUT",
            quantity_change=-request.requested_quantity,quantity_out=request.requested_quantity,
            movement_date=now.date(),month_number=now.month,year=now.year,
            destination=request.location,comments=f"Delivered request {request.request_number}",
            source_reference_type="stock_request",source_reference_id=request.id,
            mission="DEMO MISSION",base=request.location,performed_by_id=actor.id,
        ))
        if request.item.status=="Low Stock":
            db.add(NotificationOutbox(recipient=actor.email,subject=f"Low stock: {request.item.item_name}",body=f"{request.item.quantity_available} {request.item.unit} remain.",event_type="stock_low",status="queued"))
    if data.status in {"Approved","Rejected"}:
        request.approved_by_id=actor.id; request.decision_date=now
    request.status=data.status; request.notes=data.notes
    db.add(StockRequestStatusHistory(request_id=request.id,status=data.status,changed_by_id=actor.id,note=data.notes))
    action={"Approved":"approved","Rejected":"rejected","Delivered":"delivered","Ready for Pickup":"ready","Cancelled":"cancelled"}[data.status]
    db.add(AuditLog(actor_id=actor.id,action=f"Stock request {action}",details={"stock_request_id":request.id}))
    notify(db,request.requested_by,f"Stock request {request.request_number}: {data.status}",f"Your request for {request.item.item_name} is now {data.status}.",f"stock_request_{action}")
    db.commit(); db.refresh(request); return request

