from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.user import User


class UserRepository:
    def list_all(self, db: Session) -> list[User]:
        statement = select(User).order_by(User.created_at.desc(), User.id.desc())
        return list(db.execute(statement).scalars().all())

    def get_by_email(self, db: Session, email: str) -> User | None:
        normalized_email = str(email or "").strip().lower()
        statement = select(User).where(func.lower(User.email) == normalized_email)
        return db.execute(statement).scalar_one_or_none()

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return db.execute(statement).scalar_one_or_none()

    def create(self, db: Session, full_name: str, email: str, password_hash: str, role: str = "customer") -> User:
        user = User(full_name=full_name.strip(), email=email.strip().lower(), password_hash=password_hash, role=role)
        db.add(user)
        return user

    def delete(self, db: Session, user: User) -> None:
        db.delete(user)
