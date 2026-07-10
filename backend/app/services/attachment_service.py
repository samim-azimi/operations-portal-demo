from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_TYPES = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "text/plain": {".txt", ".log"},
    "application/octet-stream": {".txt", ".log"},
}

MAGIC_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),
    "application/pdf": (b"%PDF-",),
}


def safe_display_name(filename: str | None) -> str:
    raw = Path(filename or "attachment").name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", raw).strip(" .")
    return (cleaned or "attachment")[:255]


def validate_type(filename: str, mime_type: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    allowed_extensions = ALLOWED_TYPES.get(mime_type)
    if not allowed_extensions or extension not in allowed_extensions:
        raise HTTPException(
            415,
            "Unsupported file type. Use PNG, JPG, WEBP, PDF, TXT, or LOG.",
        )
    signatures = MAGIC_SIGNATURES.get(mime_type)
    if signatures and not any(content.startswith(sig) for sig in signatures):
        if not (
            mime_type == "image/webp"
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        ):
            raise HTTPException(415, "File contents do not match its type.")
    if mime_type in {"text/plain", "application/octet-stream"} and b"\x00" in content[:4096]:
        raise HTTPException(415, "Binary content is not allowed as a text file.")
    return extension


async def save_upload(upload: UploadFile) -> dict:
    original_name = safe_display_name(upload.filename)
    mime_type = (upload.content_type or "").lower()
    content = await upload.read(settings.max_upload_bytes + 1)
    await upload.close()
    if not content:
        raise HTTPException(422, "The uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            413,
            f"Files must be smaller than {settings.max_upload_bytes // 1_048_576} MB.",
        )
    extension = validate_type(original_name, mime_type, content)
    if mime_type == "application/octet-stream":
        mime_type = "text/plain"
    stored_name = f"{uuid4().hex}{extension}"
    directory = settings.upload_directory
    directory.mkdir(parents=True, exist_ok=True)
    path = (directory / stored_name).resolve()
    if directory not in path.parents:
        raise HTTPException(400, "Invalid file path.")
    path.write_bytes(content)
    return {
        "original_name": original_name,
        "stored_name": stored_name,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
