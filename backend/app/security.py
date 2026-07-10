from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.modules import permissions_for_role

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=19_456,
    argon2__time_cost=2,
    argon2__parallelism=1,
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def verify_and_upgrade_password(
    plain: str, hashed: str
) -> tuple[bool, str | None]:
    return pwd_context.verify_and_update(plain, hashed)


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": expires,
        "jti": str(uuid4()),
        "type": "access",
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=ALGORITHM
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        401,
        "Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        if payload.get("type") != "access":
            raise credentials_error
        user_id = int(payload.get("sub", ""))
    except (JWTError, ValueError):
        raise credentials_error
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != UserRole.SUPER_ADMIN and user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return dependency


def require_permission(permission: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if permission not in permissions_for_role(user.role):
            raise HTTPException(403, "You do not have access to this Faza module")
        return user
    return dependency
