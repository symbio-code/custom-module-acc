import os
from datetime import datetime, timedelta
from typing import Optional, List

import jwt
from fastapi import HTTPException, Request, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User

SECRET = os.getenv("SECRET_KEY", "secret123")
ALGORITHM = "HS256"


def create_access_token(user: User, expires_hours: int = 12) -> str:
    """Create a JWT access token for `user`."""
    exp = datetime.utcnow() + timedelta(hours=expires_hours)
    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    payload = {"sub": user.username, "role": role_value, "exp": exp}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _get_token_from_request(request: Request) -> Optional[str]:
    """Try to read Bearer token from Authorization header, otherwise from cookie `access_token`."""
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    cookie = request.cookies.get("access_token")
    if cookie:
        return cookie
    return None


def get_current_user(request: Request, db: Session = Depends(get_session)) -> User:
    token = _get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: List[str]):
    """Dependency factory that ensures the current user has one of the given roles.

    Usage: `Depends(require_role("admin", "accountant"))`
    """

    def _dep(current_user: User = Depends(get_current_user)):
        user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user

    return _dep
