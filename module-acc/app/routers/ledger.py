from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from datetime import date
from typing import Optional
from app.database import get_session
from app.services.ledger_service import (
    post_journal_entry, 
    get_ledger_for_account,
    get_ledger_for_account_simple,
    list_ledger,
    validate_account_code
)
from app.services.account_service import list_accounts
from app.security import require_role
from app.models.user import User

router = APIRouter(prefix="/ledger")
templates = Jinja2Templates(directory="frontend")

@router.get("", response_class=None)
def ledger_page(request: Request, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant','viewer'))):
    """Render General Ledger page dengan form filter dan account dropdown"""
    # Fetch all active accounts untuk dropdown
    accounts_result = list_accounts(db, page=1, page_size=1000)
    account_options = [{'code': a.code, 'name': f"{a.code} - {a.name}"} for a in accounts_result.get('rows', [])]
    
    return templates.TemplateResponse(
        'pages/ledger.html',
        {
            "request": request,
            "accounts": account_options,
            "rows": []  # empty pada load pertama
        }
    )

@router.get("/{account_code}/rows", response_class=HTMLResponse)
def ledger_rows(
    account_code: str,
    request: Request,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    opening_balance: float = Query(0.0),
    limit: int = Query(100),
    offset: int = Query(0),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('admin','accountant','viewer'))
):
    """HTMX endpoint: return HTML fragment dengan table rows GL per account"""
    try:
        # Parse dates
        from_date_obj = None
        to_date_obj = None
        if from_date:
            try:
                from_date_obj = date.fromisoformat(from_date)
            except ValueError:
                pass
        if to_date:
            try:
                to_date_obj = date.fromisoformat(to_date)
            except ValueError:
                pass
        
        # Get ledger dengan running balance
        ledger_data = get_ledger_for_account(
            db,
            account_code,
            from_date=from_date_obj,
            to_date=to_date_obj,
            opening_balance=opening_balance,
            limit=limit,
            offset=offset
        )
        
        # Render table rows fragment
        return templates.TemplateResponse(
            'components/ledger_rows.html',
            {
                "request": request,
                "rows": ledger_data['rows'],
                "account_code": account_code,
                "closing_balance": ledger_data['closing_balance']
            }
        )
    except Exception as e:
        return HTMLResponse(
            content=f'<tr><td colspan="6" class="text-red-600 p-4">Error: {str(e)}</td></tr>',
            status_code=400
        )

@router.post("/post/{journal_id}")
def post_journal(journal_id: int, db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant'))):
    """Endpoint untuk mem-posting journal entry ke ledger"""
    return post_journal_entry(db, journal_id)

@router.get("/api/all")
def ledger_all(db: Session = Depends(get_session), current_user: User = Depends(require_role('admin','accountant','viewer'))):
    """Endpoint JSON untuk mengambil semua ledger entries"""
    return list_ledger(db)

@router.get("/api/{account_code}")
def ledger_account_json(
    account_code: str,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    opening_balance: float = Query(0.0),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('admin','accountant','viewer'))
):
    """JSON endpoint untuk mengambil ledger per akun tertentu dengan running balance"""
    from_date_obj = None
    to_date_obj = None
    if from_date:
        try:
            from_date_obj = date.fromisoformat(from_date)
        except ValueError:
            pass
    if to_date:
        try:
            to_date_obj = date.fromisoformat(to_date)
        except ValueError:
            pass
    
    return get_ledger_for_account(
        db,
        account_code,
        from_date=from_date_obj,
        to_date=to_date_obj,
        opening_balance=opening_balance
    )