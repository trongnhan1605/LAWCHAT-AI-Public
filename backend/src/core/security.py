from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import AuthenticationException, AuthorizationException
from src.repositories.user_repository import UserRepository

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise AuthenticationException("Invalid or expired token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise AuthenticationException("Missing access token")

    payload = decode_access_token(credentials.credentials)
    email = payload.get("sub")
    if not email:
        raise AuthenticationException("Invalid token payload")

    user = UserRepository().get_by_email(db, email)
    if user is None:
        raise AuthenticationException("User not found")

    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except AuthenticationException:
        return None


def require_roles(*allowed_roles: str) -> Callable:
    normalized_roles = {role.strip().lower() for role in allowed_roles}

    def dependency(current_user=Depends(get_current_user)):
        if str(current_user.role).strip().lower() not in normalized_roles:
            raise AuthorizationException("You do not have permission to access this resource")
        return current_user

    return dependency
