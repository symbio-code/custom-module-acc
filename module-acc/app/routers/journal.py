from fastapi import APIRouter, Depends, Body, HTTPException
from sqlmodel import Session
from app.database import get_session
from fastapi import Request
from app.services.journal_service import (
    create_journal_entry, list_journal_entries,
    get_journal_entry, delete_journal_entry
)
from app.security import require_role
from app.models.user import User
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

templates = Jinja2Templates(directory="frontend")

router = APIRouter(prefix="/journal")

@router.post("/")
def create_journal(payload: dict = Body(...), db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant'))):
    """Endpoint untuk membuat entri jurnal baru"""
    if not payload or not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    entry_data = payload.get("entry")
    lines = payload.get("lines", [])

    if not entry_data:
        raise HTTPException(status_code=400, detail="Missing 'entry' in payload")

    return create_journal_entry(db, entry_data, lines)

@router.get("", response_class=None)
def journal_list_page(request: Request, page: int = 1, page_size: int = 20, db: Session = Depends(get_session)):
    result = list_journal_entries(db, page, page_size)
    # prepare rows for template where needed
    rows = []
    for je in result['rows']:
        rows.append({
            'Date': je.date.isoformat(),
            'Reference': f'JE-{je.id:05d}',
            'Description': je.description or '',
            'Total Debit': '',
            'Total Credit': '',
            'Actions': f'<a hx-get="/journal/{je.id}" hx-target="#content" class="px-2 py-1 rounded border">View</a>'
        })
    return templates.TemplateResponse('pages/journal_list.html', {"request": request, "rows": rows})

@router.get('/new', response_class=HTMLResponse)
def journal_new_page(request: Request):
    return templates.TemplateResponse('pages/journal_new.html', {"request": request})

@router.get("/")
def list_journals(page: int = 1, page_size: int = 20, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant','viewer'))):
    """Endpoint untuk daftar entri jurnal"""
    return list_journal_entries(db, page, page_size)

@router.get("/{id}")
def journal_detail(id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant','viewer'))):
    """Endpoint untuk detail entri jurnal"""
    return get_journal_entry(db, id)

@router.delete("/{id}")
def delete_journal(id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin'))):
    """Endpoint untuk menghapus entri jurnal"""
    return delete_journal_entry(db, id)