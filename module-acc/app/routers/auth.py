from fastapi import APIRouter, Depends, Response, Request, Body
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.database import get_session
from app.services.auth_service import init_superuser, login_user
from app.utils.security import hash_password
from app.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth")


@router.post("/init")
def initialize_superuser(
    password: str,
    username: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_session),
):
    """Endpoint untuk inisialisasi user pertama (sekali saja).

    Accepts optional `username` and `role` to seed specific accounts.
    """
    uname = username or "admin"
    r = role or "admin"
    return init_superuser(db, password, username=uname, role=r)


@router.post("/seed")
def seed_users(db: Session = Depends(get_session)):
    """Create sample users for local development: admin, acct, viewer.

    Passwords are documented in tests: admin_pass, acct_pass, viewer_pass.
    This endpoint is idempotent (will not override existing users).
    """
    created = []
    try:
        u = init_superuser(db, "admin_pass", username="admin", role="admin")
        created.append(u.username)
    except Exception:
        pass
    # helper to create if not exists
    from app.models.user import User
    from sqlmodel import select

    def ensure_user(username, password, role):
        stmt = select(User).where(User.username == username)
        if not db.exec(stmt).first():
            user = User(username=username, password_hash=hash_password(password), role=role)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        return None

    u2 = ensure_user("acct", "acct_pass", "accountant")
    if u2:
        created.append(u2.username)
    u3 = ensure_user("viewer", "viewer_pass", "viewer")
    if u3:
        created.append(u3.username)

    return {"created": created}


@router.post("/login")
async def login(
    request: Request,
    password: str | None = None,
    username: str | None = None,
    payload: dict | None = Body(None),
    response: Response = None,
    db: Session = Depends(get_session),
):
    """Endpoint untuk login

    Supports HTMX: when `hx-request` header present, returns `HX-Redirect` to `/dashboard`.
    """
    # Allow password to come from query param, JSON body, or form data
    if password is None:
        payload = payload or {}
        # Try JSON body first
        password = payload.get('password') if payload else None
        username = payload.get('username') if payload else None
        # Try query params next
        if not password:
            password = request.query_params.get('password')
        if not username:
            username = request.query_params.get('username')

        # Finally, if the request is a form submission, await form() and extract
        content_type = request.headers.get('content-type', '')
        if (not password or not username) and ('application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type):
            form = await request.form()
            if not password:
                password = form.get('password')
            if not username:
                username = form.get('username')

    if password is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Missing password")

    # Note: empty string is treated as an attempted password (will result in 401)

    user, token = login_user(db, password, username=username)
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