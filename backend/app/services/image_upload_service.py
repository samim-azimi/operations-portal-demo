from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.services.attachment_service import validate_type

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


async def save_image(upload: UploadFile, folder: str, max_bytes: int = 3_145_728) -> dict:
    mime_type = (upload.content_type or "").lower()
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, "Use a JPG, PNG, or WEBP image.")
    content = await upload.read(max_bytes + 1)
    await upload.close()
    if not content:
        raise HTTPException(422, "The uploaded image is empty.")
    if len(content) > max_bytes:
        raise HTTPException(413, "Images must be smaller than 3 MB.")
    extension = validate_type(Path(upload.filename or "image").name, mime_type, content)
    directory = (settings.upload_directory / folder).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    path = (directory / stored_name).resolve()
    if directory not in path.parents:
        raise HTTPException(400, "Invalid upload path.")
    path.write_bytes(content)
    return {"stored_name": stored_name, "mime_type": mime_type, "size_bytes": len(content)}


def image_path(folder: str, stored_name: str) -> Path:
    directory = (settings.upload_directory / folder).resolve()
    path = (directory / Path(stored_name).name).resolve()
    if directory not in path.parents or not path.is_file():
        raise HTTPException(404, "Image not found")
    return path


def remove_image(folder: str, stored_name: str | None) -> None:
    if not stored_name:
        return
    try:
        image_path(folder, stored_name).unlink(missing_ok=True)
    except HTTPException:
        pass
