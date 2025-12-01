from fastapi import APIRouter, Request, Response, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_session
from app.services.auth_service import init_superuser, login_user
from app.security import get_current_user

templates = Jinja2Templates(directory="frontend")
router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    """Render login page"""
    return templates.TemplateResponse("pages/login.html", {"request": request})


@router.post("/login")
def login_post(request: Request, response: Response, password: str = None, username: str = None, db: Session = Depends(get_session)):
    """Handle form POST from login page. Field name expected: 'password'.

    On success set a session cookie and redirect to /dashboard.
    """
    if password is None:
        # Try to extract from form body
        form = {}
        try:
            form = request.form()
        except Exception:
            pass
        # request.form() returns a coroutine in FastAPI sync context; safe fallback: read manually
    try:
        # Prefer direct parameter (FastAPI will populate), otherwise read form
        if password is None:
            form = request._form if hasattr(request, '_form') else None
            if not form:
                # best-effort: try awaitable in async context
                import asyncio
                if asyncio.iscoroutine(form):
                    form = asyncio.get_event_loop().run_until_complete(form)
            password = (form.get('password') if form else None)
        if username is None:
            # extract username from form if present
            if 'form' in locals() and form:
                username = form.get('username')
            else:
                username = request.query_params.get('username')
    except Exception:
        password = None

    if not password:
        # re-render login with message
        return templates.TemplateResponse("pages/login.html", {"request": request, "error": "Password required"}, status_code=400)

    try:
        user, token = login_user(db, password, username=username)
    except Exception as exc:
        # On any auth error, re-render login with the error message
        msg = str(exc)
        # If it's an HTTPException, prefer its detail
        try:
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                msg = exc.detail
        except Exception:
            pass
        return templates.TemplateResponse("pages/login.html", {"request": request, "error": msg}, status_code=getattr(exc, 'status_code', 400))

    response.set_cookie("access_token", token, httponly=True, samesite="lax")

    # If this was an HTMX request, instruct client to redirect
    if request.headers.get("hx-request"):
        headers = {"HX-Redirect": "/dashboard"}
        return HTMLResponse(content="", status_code=200, headers=headers)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(response: Response):
    # clear access token cookie
    response.delete_cookie("access_token")
    # HTMX-aware response can use HX-Redirect header
    headers = {"HX-Redirect": "/login"}
    return HTMLResponse(content="", status_code=200, headers=headers)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_session), user=Depends(get_current_user)):
    # sample data - in practice use services to fetch real rows
    rows = [
        {"Date": "Oct 26, 2023", "Reference": "JE-00125", "Description": "Office Supplies", "Total Debit": "$1,500.00", "Total Credit": "$1,500.00"}
    ]
    # pass role as simple string to templates for easy conditional checks
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    return templates.TemplateResponse("pages/dashboard.html", {"request": request, "rows": rows, "user": user, "role": role})


@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("pages/profile.html", {"request": request, "user": user})


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("pages/settings.html", {"request": request, "user": user})


@router.get("/profile/panel", response_class=HTMLResponse)
def profile_panel(request: Request, user=Depends(get_current_user)):
    """Return a small HTML fragment for the sidebar profile panel (HTMX target)."""
    return templates.TemplateResponse("components/profile_panel.html", {"request": request, "user": user})
