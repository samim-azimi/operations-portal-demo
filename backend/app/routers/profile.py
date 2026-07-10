from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User, UserProfileImage
from app.schemas import UserRead
from app.security import get_current_user
from app.services.image_upload_service import image_path, remove_image, save_image

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserRead)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.post("/picture", response_model=UserRead)
async def update_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    saved = await save_image(file, "profiles")
    old = user.profile_image
    if old:
        remove_image("profiles", old.stored_name)
        old.stored_name = saved["stored_name"]
        old.mime_type = saved["mime_type"]
        old.size_bytes = saved["size_bytes"]
    else:
        db.add(UserProfileImage(user_id=user.id, **saved))
    db.add(AuditLog(actor_id=user.id, action="Profile picture updated", details={}))
    db.commit()
    db.refresh(user)
    return user


@router.delete("/picture", status_code=204)
def delete_profile_picture(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.profile_image:
        remove_image("profiles", user.profile_image.stored_name)
        db.delete(user.profile_image)
        db.add(AuditLog(actor_id=user.id, action="Profile picture removed", details={}))
        db.commit()


@router.get("/picture/{user_id}")
def get_profile_picture(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if not user or not user.profile_image:
        raise HTTPException(404, "Profile picture not found")
    return FileResponse(
        image_path("profiles", user.profile_image.stored_name),
        media_type=user.profile_image.mime_type,
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
