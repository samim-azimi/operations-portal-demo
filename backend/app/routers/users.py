import csv
import io
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database import get_db
from app.models import AuditLog, User, UserRole
from app.schemas import BulkImportResult, BulkImportRow, Page, UserCreate, UserRead, UserUpdate
from app.pagination import page_result
from app.security import hash_password, require_roles

router = APIRouter(prefix="/users", tags=["Users"])
ADMIN_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN}
ASSIGNEE_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT}

@router.get("/assignees", response_model=list[UserRead])
def list_assignees(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
):
    return (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            User.role.in_(list(ASSIGNEE_ROLES)),
        )
        .order_by(User.full_name)
        .all()
    )


@router.get("", response_model=Page[UserRead])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    q: str | None = Query(None, max_length=200),
    role: UserRole | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = db.query(User).filter(~User.email.like("deleted-%@invalid.local"))
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                User.department.ilike(term),
            )
        )
    if role:
        query = query.filter(User.role == role)
    return page_result(query.order_by(User.created_at.desc()), page, page_size)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
):
    email = str(data.email).strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already exists")
    user = User(
        **data.model_dump(exclude={"password", "email"}),
        email=email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="User created",
            details={"user_id": user.id, "role": user.role.value},
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Upload a CSV file")
    content = await file.read(1_048_577)
    await file.close()
    if len(content) > 1_048_576:
        raise HTTPException(413, "CSV files must be smaller than 1 MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "CSV must use UTF-8 encoding")
    reader = csv.DictReader(io.StringIO(text))
    required = {"full_name", "email"}
    if not reader.fieldnames or not required.issubset(
        {name.strip().lower() for name in reader.fieldnames}
    ):
        raise HTTPException(422, "CSV requires full_name and email columns")
    results: list[BulkImportRow] = []
    created = skipped = failed = 0
    for row_number, raw in enumerate(reader, start=2):
        if row_number > 1001:
            raise HTTPException(413, "A CSV import can contain at most 1,000 users")
        row = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in raw.items()
        }
        email = row.get("email", "").lower()
        if db.query(User).filter(User.email == email).first():
            skipped += 1
            results.append(
                BulkImportRow(
                    row=row_number,
                    email=email,
                    status="skipped",
                    detail="Email already exists",
                )
            )
            continue
        temporary_password = secrets.token_urlsafe(12)
        try:
            payload = UserCreate(
                full_name=row.get("full_name", ""),
                email=email,
                department=row.get("department") or None,
                role=UserRole(row.get("role", "user").lower()),
                password=temporary_password,
                is_active=True,
            )
            user = User(
                **payload.model_dump(exclude={"password"}),
                password_hash=hash_password(temporary_password),
            )
            db.add(user)
            db.flush()
            created += 1
            results.append(
                BulkImportRow(
                    row=row_number,
                    email=email,
                    temporary_password=temporary_password,
                    status="created",
                )
            )
        except (ValidationError, ValueError) as exc:
            failed += 1
            results.append(
                BulkImportRow(
                    row=row_number,
                    email=email or "invalid@example.invalid",
                    status="failed",
                    detail=str(exc)[:300],
                )
            )
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="Users bulk imported",
            details={"created": created, "skipped": skipped, "failed": failed},
        )
    )
    db.commit()
    return BulkImportResult(
        created=created, skipped=skipped, failed=failed, rows=results
    )


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.get(User, user_id)
    if not user or user.email.endswith("@invalid.local"):
        raise HTTPException(404, "User not found")
    updates = data.model_dump(exclude_unset=True)
    if "email" in updates:
        email = str(updates["email"]).lower()
        duplicate = (
            db.query(User)
            .filter(User.email == email, User.id != user.id)
            .first()
        )
        if duplicate:
            raise HTTPException(409, "Email already exists")
        updates["email"] = email
    if user.id == actor.id and (
        updates.get("role") not in {None, *ADMIN_ROLES}
        or updates.get("is_active") is False
    ):
        raise HTTPException(409, "You cannot remove your own admin access")
    if (
        user.role in ADMIN_ROLES
        and updates.get("role") not in {None, *ADMIN_ROLES}
    ):
        active_admins = (
            db.query(User)
            .filter(User.role.in_(list(ADMIN_ROLES)), User.is_active.is_(True))
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(409, "At least one active admin is required")
    for field, value in updates.items():
        setattr(user, field, value)
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="User updated",
            details={"user_id": user.id, "fields": sorted(updates)},
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.get(User, user_id)
    if not user or user.email.endswith("@invalid.local"):
        raise HTTPException(404, "User not found")
    if user.id == actor.id:
        raise HTTPException(409, "You cannot remove your own account")
    if user.role in ADMIN_ROLES and user.is_active:
        active_admins = (
            db.query(User)
            .filter(User.role.in_(list(ADMIN_ROLES)), User.is_active.is_(True))
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(409, "At least one active admin is required")
    removed_id = user.id
    user.is_active = False
    user.full_name = "Removed user"
    user.email = f"deleted-{user.id}@invalid.local"
    user.department = None
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="User removed",
            details={"user_id": removed_id},
        )
    )
    db.commit()


@router.patch("/{user_id}/active", response_model=UserRead)
def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == actor.id:
        raise HTTPException(409, "You cannot disable your own account")
    if user.role in ADMIN_ROLES and user.is_active:
        active_admins = (
            db.query(User)
            .filter(User.role.in_(list(ADMIN_ROLES)), User.is_active.is_(True))
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(409, "At least one active admin is required")
    user.is_active = not user.is_active
    db.add(
        AuditLog(
            actor_id=actor.id,
            action="User access changed",
            details={"user_id": user.id, "is_active": user.is_active},
        )
    )
    db.commit()
    db.refresh(user)
    return user
