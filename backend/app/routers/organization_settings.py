from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, OrganizationSettings, User, utcnow
from app.schemas import OrganizationSettingsRead, OrganizationSettingsUpdate
from app.security import require_permission
from app.services.image_upload_service import image_path, remove_image, save_image

router = APIRouter(prefix="/organization-settings", tags=["Organization Branding"])


def get_or_create(db: Session) -> OrganizationSettings:
    settings = db.query(OrganizationSettings).first()
    if not settings:
        settings = OrganizationSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=OrganizationSettingsRead)
def read_settings(db: Session = Depends(get_db)):
    return get_or_create(db)


@router.put("", response_model=OrganizationSettingsRead)
def update_settings(
    data: OrganizationSettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    settings = get_or_create(db)
    previous_theme = settings.theme_id
    for field, value in data.model_dump().items():
        setattr(settings, field, value)
    settings.updated_by = actor.id
    settings.updated_at = utcnow()
    action = "Theme changed" if previous_theme != settings.theme_id else "Organization branding updated"
    db.add(AuditLog(actor_id=actor.id, action=action, details={"theme_id": settings.theme_id}))
    db.commit()
    db.refresh(settings)
    return settings


async def save_logo(kind: str, file: UploadFile, db: Session, actor: User):
    saved = await save_image(file, "branding")
    settings = get_or_create(db)
    field = "logo_stored_name" if kind == "logo" else "small_logo_stored_name"
    remove_image("branding", getattr(settings, field))
    setattr(settings, field, saved["stored_name"])
    settings.updated_by = actor.id
    settings.updated_at = utcnow()
    action = "Organization logo uploaded" if kind == "logo" else "Collapsed sidebar icon uploaded"
    db.add(AuditLog(actor_id=actor.id, action=action, details={}))
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/logo", response_model=OrganizationSettingsRead)
async def upload_logo(
    file: UploadFile = File(...), db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    return await save_logo("logo", file, db, actor)


@router.post("/small-logo", response_model=OrganizationSettingsRead)
async def upload_small_logo(
    file: UploadFile = File(...), db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    return await save_logo("small_logo", file, db, actor)


@router.post("/collapsed-sidebar-icon", response_model=OrganizationSettingsRead)
async def upload_collapsed_sidebar_icon(
    file: UploadFile = File(...), db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    return await save_logo("small_logo", file, db, actor)


def delete_logo(kind: str, db: Session, actor: User):
    settings = get_or_create(db)
    field = "logo_stored_name" if kind == "logo" else "small_logo_stored_name"
    remove_image("branding", getattr(settings, field))
    setattr(settings, field, None)
    settings.updated_by = actor.id
    settings.updated_at = utcnow()
    action = "Organization logo removed" if kind == "logo" else "Collapsed sidebar icon removed"
    db.add(AuditLog(actor_id=actor.id, action=action, details={}))
    db.commit()


@router.delete("/logo", status_code=204)
def remove_logo(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    delete_logo("logo", db, actor)


@router.delete("/small-logo", status_code=204)
def remove_small_logo(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    delete_logo("small_logo", db, actor)


@router.delete("/collapsed-sidebar-icon", status_code=204)
def remove_collapsed_sidebar_icon(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("can_manage_organization_branding")),
):
    delete_logo("small_logo", db, actor)


@router.get("/{kind}/file")
def read_logo(kind: str, db: Session = Depends(get_db)):
    if kind not in {"logo", "small-logo", "collapsed-sidebar-icon"}:
        raise HTTPException(404, "Logo not found")
    settings = get_or_create(db)
    stored = settings.logo_stored_name if kind == "logo" else settings.small_logo_stored_name
    if not stored:
        raise HTTPException(404, "Logo not found")
    return FileResponse(
        image_path("branding", stored),
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
