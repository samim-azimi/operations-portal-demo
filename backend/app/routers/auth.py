from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.schemas import Token, UserRead
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_and_upgrade_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
DUMMY_HASH = hash_password("not-a-real-user-password")


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    valid, upgraded_hash = verify_and_upgrade_password(
        form.password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Incorrect email or password")
    if upgraded_hash:
        user.password_hash = upgraded_hash
    db.add(
        AuditLog(
            actor_id=user.id,
            action="User signed in",
            details={
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "")[:200],
            },
        )
    )
    db.commit()
    return Token(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
