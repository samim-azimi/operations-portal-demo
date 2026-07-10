from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TicketCategory,UserRole
from app.schemas import CategoryCreate,CategoryRead
from app.security import get_current_user,require_permission,require_roles
router=APIRouter(prefix="/categories",tags=["Faza Help Desk Configuration"],dependencies=[Depends(require_permission("can_access_helpdesk"))])
@router.get("",response_model=list[CategoryRead])
def list_categories(db:Session=Depends(get_db),_=Depends(get_current_user)): return db.query(TicketCategory).order_by(TicketCategory.name).all()
@router.post("",response_model=CategoryRead,status_code=201)
def create_category(data:CategoryCreate,db:Session=Depends(get_db),_=Depends(require_roles(UserRole.ADMIN))):
    if db.query(TicketCategory).filter(TicketCategory.name==data.name).first(): raise HTTPException(409,"Category already exists")
    item=TicketCategory(**data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item
@router.put("/{category_id}",response_model=CategoryRead)
def update_category(category_id:int,data:CategoryCreate,db:Session=Depends(get_db),_=Depends(require_roles(UserRole.ADMIN))):
    item=db.get(TicketCategory,category_id)
    if not item: raise HTTPException(404,"Category not found")
    for k,v in data.model_dump().items(): setattr(item,k,v)
    db.commit(); db.refresh(item); return item

@router.delete("/{category_id}",status_code=204)
def delete_category(category_id:int,db:Session=Depends(get_db),_=Depends(require_roles(UserRole.ADMIN))):
    item=db.get(TicketCategory,category_id)
    if not item: raise HTTPException(404,"Category not found")
    item.is_active=False
    db.commit()
