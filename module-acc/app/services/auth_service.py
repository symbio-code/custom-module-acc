from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.user import User
from app.utils.security import verify_password, hash_password
from app.security import create_access_token
from typing import Tuple


def init_superuser(db: Session, password: str, username: str = "admin", role: str = "admin"):
    """Initialize first user (run once). Creates a default admin user if none exists.

    Accepts optional `username` and `role` so caller can seed multiple accounts.
    """
    existing_user = db.exec(select(User)).first()
    if existing_user:
        return existing_user

    # Create user with provided username (default 'admin')
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, password: str, username: str | None = None):
    """Authenticate user by password.

    If `username` is provided, only verify that user's password. Otherwise
    falls back to scanning users and matching the password (backwards-compatible).
    """
    if username:
        stmt = select(User).where(User.username == username)
        user = db.exec(stmt).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not registered")
        try:
            if verify_password(password, user.password_hash):
                return user
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Wrong password")

    # Fallback: try to find any user whose password matches the provided password.
    users = db.exec(select(User)).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not registered")

    for user in users:
        try:
            if verify_password(password, user.password_hash):
                return user
        except Exception:
            # If verification fails for a user (malformed hash), continue to next
            continue

    # No user matched the provided password
    raise HTTPException(status_code=401, detail="Wrong password")


def login_user(db: Session, password: str, username: str | None = None) -> Tuple[User, str]:
    """Authenticate and return (user, jwt_token).

    Accepts optional `username` to authenticate a specific user.
    """
    user = authenticate(db, password, username=username)
    token = create_access_token(user)
    return user, token