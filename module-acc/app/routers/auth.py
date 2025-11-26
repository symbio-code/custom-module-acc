from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.database import get_session
from app.services.auth_service import init_superuser, login_user
from app.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth")


@router.post("/init")
def initialize_superuser(password: str, db: Session = Depends(get_session)):
    """Endpoint untuk inisialisasi user pertama (sekali saja)"""
    return init_superuser(db, password)


@router.post("/login")
def login(
    request: Request,
    password: str,
    response: Response,
    db: Session = Depends(get_session)
):
    """Endpoint untuk login

    Supports HTMX: when `hx-request` header present, returns `HX-Redirect` to `/dashboard`.
    """
    user, token = login_user(db, password)
    # set httponly cookie so browser clients get the token automatically
    response.set_cookie("access_token", token, httponly=True, samesite="lax")

    # If the request comes from HTMX, instruct the client to redirect
    if request.headers.get("hx-request"):
        return HTMLResponse(content="", status_code=200, headers={"HX-Redirect": "/dashboard"})

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, response: Response):
    """Endpoint untuk logout

    Supports HTMX: returns `HX-Redirect` to `/login` when called by HTMX.
    """
    # Clear cookie-based token
    response.delete_cookie("access_token")

    if request.headers.get("hx-request"):
        return HTMLResponse(content="", status_code=200, headers={"HX-Redirect": "/login"})

    return {"status": "logged_out"}


@router.get('/me')
def me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user (safe endpoint for frontend checks)."""
    return {"id": current_user.id, "username": current_user.username, "role": (current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role))}