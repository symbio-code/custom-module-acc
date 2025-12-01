from fastapi import APIRouter, Depends, Response, Request, Body
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
    password: str | None = None,
    payload: dict | None = Body(None),
    response: Response = None,
    db: Session = Depends(get_session)
):
    """Endpoint untuk login

    Supports HTMX: when `hx-request` header present, returns `HX-Redirect` to `/dashboard`.
    """
    # Allow password to come from query param, JSON body, or form data
    if password is None:
        payload = payload or {}
        password = payload.get('password') or request.query_params.get('password')

    if password is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Missing password")

    # Note: empty string is treated as an attempted password (will result in 401)

    user, token = login_user(db, password)
    # set httponly cookie so browser clients get the token automatically
    if response is None:
        response = Response()
    response.set_cookie("access_token", token, httponly=True, samesite="lax")

    # If the request comes from HTMX, instruct the client to redirect
    if request.headers.get("hx-request"):
        # Attach redirect header to the same response so cookies are preserved
        response.headers["HX-Redirect"] = "/dashboard"
        response.status_code = 200
        return response

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, response: Response):
    """Endpoint untuk logout

    Supports HTMX: returns `HX-Redirect` to `/login` when called by HTMX.
    """
    # Clear cookie-based token
    response.delete_cookie("access_token")

    if request.headers.get("hx-request"):
        # Attach redirect header to the same response so cookie deletion is preserved
        response.headers["HX-Redirect"] = "/login"
        response.status_code = 200
        return response

    return {"status": "logged_out"}


@router.get('/me')
def me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user (safe endpoint for frontend checks)."""
    return {"id": current_user.id, "username": current_user.username, "role": (current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role))}