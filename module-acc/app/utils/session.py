from fastapi import Response, Request, HTTPException, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models.user import User


def create_session(response: Response, user_id: int):
    """Create a simple session cookie. For this project we store the user id in a httponly cookie."""
    # In a production app, use signed cookies or server-side session store.
    response.set_cookie("session", str(user_id), httponly=True, samesite="lax")


def destroy_session(response: Response):
    response.delete_cookie("session")


def get_current_user(request: Request, db: Session = Depends(get_session)) -> User:
    sid = request.cookies.get("session")
    if not sid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        uid = int(sid)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = db.exec(select(User).where(User.id == uid)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user
