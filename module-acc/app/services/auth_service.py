from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.user import User
from app.utils.security import verify_password, hash_password
from app.security import create_access_token
from typing import Tuple


def init_superuser(db: Session, password: str):
    """Initialize first user (run once). Creates a default admin user if none exists."""
    existing_user = db.exec(select(User)).first()
    if existing_user:
        return existing_user

    # Create user with default username 'admin'
    user = User(username="admin", password_hash=hash_password(password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, password: str):
    """Authenticate user by password. (Simple single-user app pattern.)"""
    user = db.exec(select(User)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not registered")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong password")

    return user


def login_user(db: Session, password: str) -> Tuple[User, str]:
    """Authenticate and return (user, jwt_token)."""
    user = authenticate(db, password)
    token = create_access_token(user)
    return user, token