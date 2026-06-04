from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user
from src.schemas.auth_schema import AuthResponse, CurrentUserResponse, LoginRequest, RegisterRequest, UserPublic
from src.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    auth_payload = auth_service.register(db, payload.full_name, payload.email, payload.password)
    return AuthResponse(success=True, message="Register successfully", data=auth_payload)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    auth_payload = auth_service.login(db, payload.email, payload.password)
    return AuthResponse(success=True, message="Login successfully", data=auth_payload)


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user = Depends(get_current_user)) -> CurrentUserResponse:
    user_public = UserPublic.model_validate(current_user)
    return CurrentUserResponse(success=True, message="Current user fetched", data=user_public)
