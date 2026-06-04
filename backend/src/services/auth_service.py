from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import AuthenticationException, ConflictException
from src.core.security import create_access_token, hash_password, verify_password
from src.repositories.user_repository import UserRepository
from src.schemas.auth_schema import AuthPayload, UserPublic


class AuthService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def register(self, db: Session, full_name: str, email: str, password: str) -> AuthPayload:
        existing_user = self.user_repository.get_by_email(db, email)
        if existing_user is not None:
            raise ConflictException("Email already exists")

        user = self.user_repository.create(
            db=db,
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
        )

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictException("Email already exists") from exc

        db.refresh(user)
        return self._build_auth_payload(user)

    def login(self, db: Session, email: str, password: str) -> AuthPayload:
        user = self.user_repository.get_by_email(db, email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationException("Invalid email or password")

        return self._build_auth_payload(user)

    def _build_auth_payload(self, user) -> AuthPayload:
        access_token = create_access_token(user.email)
        user_public = UserPublic.model_validate(user)
        return AuthPayload(access_token=access_token, user=user_public)


auth_service = AuthService()
