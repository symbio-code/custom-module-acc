from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from datetime import date
from typing import Optional

from app.database import get_session
from app.services.trial_balance_service import get_trial_balance, generate_trial_balance_pdf
from app.services.profit_loss_service import get_profit_loss, generate_profit_loss_pdf
from app.services.balance_sheet_service import get_balance_sheet, generate_balance_sheet_pdf
from app.security import require_role
from app.models.user import User

from io import BytesIO
try:
    from weasyprint import HTML, CSS
except Exception:
    HTML = None
    CSS = None

router = APIRouter(prefix="/report")
templates = Jinja2Templates(directory="frontend")


@router.get('/trial-balance', response_class=JSONResponse)
def trial_balance_json(
    from_date: str = Query(...),
    to_date: str = Query(...),
    page: int = Query(1),
    page_size: int = Query(200),
    fiscal_year: Optional[int] = Query(None),
    include_zero: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('viewer','accountant','admin'))
):
    # parse dates
    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid from_date/to_date format (expected YYYY-MM-DD)"})

    result = get_trial_balance(db, from_date_obj, to_date_obj, page=page, page_size=page_size, fiscal_year=fiscal_year, include_zero=include_zero)
    return JSONResponse(content=result)


@router.get('/trial-balance/html', response_class=HTMLResponse)
def trial_balance_html(
    request: Request,
    from_date: str = Query(...),
    to_date: str = Query(...),
    page: int = Query(1),
    page_size: int = Query(200),
    fiscal_year: Optional[int] = Query(None),
    include_zero: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('viewer','accountant','admin'))
):
    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return HTMLResponse(content="<div class='p-4 text-red-600'>Invalid date format</div>", status_code=400)

    result = get_trial_balance(db, from_date_obj, to_date_obj, page=page, page_size=page_size, fiscal_year=fiscal_year, include_zero=include_zero)
    # render partial rows
    return templates.TemplateResponse('components/tables/trial_balance_table.html', {"request": request, "rows": result['rows'], "total_debit": result['total_debit'], "total_credit": result['total_credit'], "balanced": result['balanced']})


@router.get('/trial-balance/pdf')
def trial_balance_pdf(
    from_date: str = Query(...),
    to_date: str = Query(...),
    fiscal_year: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('accountant','admin'))
):
    # PDF export using WeasyPrint
    if HTML is None:
        return JSONResponse(status_code=500, content={"detail": "WeasyPrint not available (missing dependency)"})

    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid from_date/to_date format (expected YYYY-MM-DD)"})

    try:
        pdf_bytes = generate_trial_balance_pdf(db, from_date_obj, to_date_obj, fiscal_year=fiscal_year)
    except RuntimeError:
        return JSONResponse(status_code=500, content={"detail": "WeasyPrint not available (missing dependency)"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"PDF generation failed: {str(e)}"})

    buf = BytesIO(pdf_bytes)
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="trial_balance.pdf"'
    })


@router.get('/profit-loss', response_class=JSONResponse)
def profit_loss_json(
    from_date: str = Query(...),
    to_date: str = Query(...),
    page: int = Query(1),
    page_size: int = Query(200),
    include_zero: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('viewer','accountant','admin'))
):
    """Get Profit & Loss report as JSON."""
    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid from_date/to_date format (expected YYYY-MM-DD)"})

    result = get_profit_loss(db, from_date_obj, to_date_obj, page=page, page_size=page_size, include_zero=include_zero)
    return JSONResponse(content=result)


@router.get('/profit-loss/html', response_class=HTMLResponse)
def profit_loss_html(
    request: Request,
    from_date: str = Query(...),
    to_date: str = Query(...),
    page: int = Query(1),
    page_size: int = Query(200),
    include_zero: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('viewer','accountant','admin'))
):
    """Get Profit & Loss report as HTMX-ready HTML fragment."""
    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return HTMLResponse(content="<div class='p-4 text-red-600'>Invalid date format</div>", status_code=400)

    result = get_profit_loss(db, from_date_obj, to_date_obj, page=page, page_size=page_size, include_zero=include_zero)
    return templates.TemplateResponse('components/tables/profit_loss_table.html', {
        "request": request,
        "rows": result['rows'],
        "total_revenue": result['total_revenue'],
        "total_expense": result['total_expense'],
        "net_profit": result['net_profit']
    })


@router.get('/profit-loss/pdf')
def profit_loss_pdf(
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('accountant','admin'))
):
    """Get Profit & Loss report as PDF using WeasyPrint."""
    if HTML is None:
        return JSONResponse(status_code=500, content={"detail": "WeasyPrint not available (missing dependency)"})

    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid from_date/to_date format (expected YYYY-MM-DD)"})

    try:
        pdf_bytes = generate_profit_loss_pdf(db, from_date_obj, to_date_obj)
    except RuntimeError:
        return JSONResponse(status_code=500, content={"detail": "WeasyPrint not available (missing dependency)"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"PDF generation failed: {str(e)}"})

    buf = BytesIO(pdf_bytes)
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="profit_loss.pdf"'
    })


@router.get('/balance-sheet/pdf')
def balance_sheet_pdf(
    from_date: str = Query(...),
    to_date: str = Query(...),
    fiscal_year: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_role('accountant','admin'))
):
    """Get Balance Sheet report as PDF using WeasyPrint."""
    try:
        from_date_obj = date.fromisoformat(from_date)
        to_date_obj = date.fromisoformat(to_date)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid from_date/to_date format (expected YYYY-MM-DD)"})

    try:
        pdf_bytes = generate_balance_sheet_pdf(db, from_date_obj, to_date_obj, fiscal_year=fiscal_year)
    except RuntimeError:
        return JSONResponse(status_code=500, content={"detail": "WeasyPrint not available (missing dependency)"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"PDF generation failed: {str(e)}"})

    buf = BytesIO(pdf_bytes)
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="balance_sheet.pdf"'
    })
