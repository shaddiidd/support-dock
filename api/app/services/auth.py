from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    statement = select(User).where(User.email == normalize_email(email))
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.get(User, user_id)


def register_user(db: Session, payload: RegisterRequest) -> User:
    user = User(
        name=payload.name.strip(),
        email=normalize_email(payload.email),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
