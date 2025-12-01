from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.database import get_session
from app.models.account import Account
from app.services.account_service import (
    create_account, list_accounts, update_account,
    delete_account, get_account
)
from app.security import require_role
from app.models.user import User

router = APIRouter(prefix="/accounts")
templates = Jinja2Templates(directory="frontend")


@router.get("", response_class=None)
def accounts_page(request: Request, page: int = 1, page_size: int = 50, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant','viewer'))):
    """Render the Chart of Accounts page (HTMX + full page)."""
    result = list_accounts(db, page, page_size)
    # determine role string early (used when rendering actions)
    role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    # prepare rows for table.html component as list of dicts
    table_rows = []
    for a in result['rows']:
        actions_html = ''
        # Edit button (HTMX fragment)
        if role in ['admin','accountant']:
            actions_html += f'<button hx-get="/accounts/{a.id}/edit" hx-target="#content" class="px-2 py-1 rounded border mr-2">Edit</button>'
        # Delete via confirm modal (HTMX)
        if role == 'admin':
            actions_html += f'<button hx-get="/accounts/{a.id}/delete_confirm" hx-target="#modal" class="px-2 py-1 rounded border text-red-600">Delete</button>'

        table_rows.append({
            'Code': a.code,
            'Name': a.name,
            'Type': a.account_type,
            'Level': a.level,
            'Is Group': 'Yes' if a.is_group else 'No',
            'Active': 'Yes' if a.is_active else 'No',
            'Actions': actions_html
        })

    return templates.TemplateResponse('pages/accounts.html', {"request": request, "table_rows": table_rows, "role": role})


@router.get('/new')
def account_new(request: Request, current_user: User = Depends(require_role('admin','accountant'))):
    """Return a fragment with account creation form for HTMX."""
    return templates.TemplateResponse('components/account_form.html', {"request": request})


@router.get("/{id}/delete_confirm")
def delete_confirm(request: Request, id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin'))):
    acc = get_account(db, id)
    if not acc:
        return HTMLResponse(content="Not found", status_code=404)
    return templates.TemplateResponse('components/confirm_delete.html', {"request": request, "account": acc})

@router.post("")
@router.post("/")
def create(data: Account, request: Request, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant'))):
    """Create account. If called via HTMX, respond with HX-Redirect to refresh list."""
    acc = create_account(db, data)
    if request.headers.get("hx-request"):
        return HTMLResponse(content="", status_code=200, headers={"HX-Redirect": "/accounts"})
    return acc

@router.get("/")
def list_all(
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    sort_by: str = "code",
    sort_dir: str = "asc",
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('admin','accountant','viewer'))
):
    return list_accounts(
        db, page, page_size, search, sort_by, sort_dir
    )

@router.get("/{id}")
def detail(id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant','viewer'))):
    return get_account(db, id)

@router.put("/{id}")
def update(id: int, data: dict, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant'))):
    return update_account(db, id, data)


@router.get("/{id}/edit")
def edit_form(request: Request, id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant'))):
    """Return HTMX fragment with pre-filled edit form."""
    acc = get_account(db, id)
    if not acc:
        return HTMLResponse(content="Account not found", status_code=404)
    return templates.TemplateResponse('components/account_edit.html', {"request": request, "account": acc})


@router.post("/{id}/edit")
def edit_submit(request: Request, id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant'))):
    """Handle HTMX form submit for edit (accepts form-encoded fields)."""
    form = {}
    try:
        # request.form() may be coroutine; handle in sync context
        form_obj = request.form()
        import asyncio
        if asyncio.iscoroutine(form_obj):
            form = asyncio.get_event_loop().run_until_complete(form_obj)
        else:
            form = form_obj
    except Exception:
        form = {}

    payload = {k: form.get(k) for k in ['name','account_type','parent_code','is_group','is_active'] if form.get(k) is not None}
    # convert flags
    if 'is_group' in payload:
        payload['is_group'] = True if payload['is_group'] in ('on','true','1','yes') else False
    if 'is_active' in payload:
        payload['is_active'] = True if payload['is_active'] in ('on','true','1','yes') else False

    updated = update_account(db, id, payload)
    if request.headers.get("hx-request"):
        return HTMLResponse(content="", status_code=200, headers={"HX-Redirect": "/accounts"})
    return updated


@router.post("/{id}/delete")
def delete_htmx(id: int, request: Request, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin'))):
    """Delete account via HTMX-friendly endpoint."""
    ok = delete_account(db, id)
    if request.headers.get("hx-request"):
        return HTMLResponse(content="", status_code=200, headers={"HX-Redirect": "/accounts"})
    return {"deleted": ok}

@router.delete("/{id}")
def delete(id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin'))):
    return delete_account(db, id)