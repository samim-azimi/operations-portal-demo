from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SupportLocation, User, UserRole
from app.schemas import LocationCreate, LocationRead
from app.security import get_current_user, require_permission, require_roles

router = APIRouter(prefix="/locations", tags=["Faza Help Desk Configuration"], dependencies=[Depends(require_permission("can_access_helpdesk"))])


@router.get("", response_model=list[LocationRead])
def list_locations(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(SupportLocation)
    if not include_inactive:
        query = query.filter(SupportLocation.is_active.is_(True))
    return query.order_by(SupportLocation.sort_order, SupportLocation.name).all()


@router.post("", response_model=LocationRead, status_code=201)
def create_location(
    data: LocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if db.query(SupportLocation).filter(SupportLocation.name == data.name).first():
        raise HTTPException(409, "Location already exists")
    item = SupportLocation(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{location_id}", response_model=LocationRead)
def update_location(
    location_id: int,
    data: LocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    item = db.get(SupportLocation, location_id)
    if not item:
        raise HTTPException(404, "Location not found")
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{location_id}", status_code=204)
def remove_location(
    location_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    item = db.get(SupportLocation, location_id)
    if not item:
        raise HTTPException(404, "Location not found")
    item.is_active = False
    db.commit()
