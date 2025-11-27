from sqlmodel import Session, select
from typing import List, Dict, Optional
from datetime import date
from fastapi import HTTPException

from app.models.account import Account
from app.models.journal import JournalEntryLine, JournalEntry
from app.models.opening_balance import OpeningBalance


def _get_opening_balance_map(db: Session, fiscal_year: int) -> Dict[str, float]:
    rows = db.exec(select(OpeningBalance).where(OpeningBalance.fiscal_year == fiscal_year)).all()
    return {r.account_code: float(r.opening_amount or 0.0) for r in rows}


def _sum_journal_lines(db: Session, from_date: date, to_date: date) -> Dict[str, Dict[str, float]]:
    """Return map account_code -> {'debit': x, 'credit': y} for the period."""
    stmt = select(JournalEntryLine, JournalEntry).join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
    stmt = stmt.where(JournalEntry.date >= from_date, JournalEntry.date <= to_date)
    rows = db.exec(stmt).all()

    sums: Dict[str, Dict[str, float]] = {}
    for jl, je in rows:
        code = jl.account_code
        if code not in sums:
            sums[code] = {'debit': 0.0, 'credit': 0.0}
        sums[code]['debit'] += float(jl.debit or 0.0)
        sums[code]['credit'] += float(jl.credit or 0.0)
    return sums


def _build_account_tree(accounts: List[Account]) -> Dict[str, List[str]]:
    children: Dict[str, List[str]] = {}
    for a in accounts:
        children.setdefault(a.parent_code or '', [])
        children.setdefault(a.code, [])
    for a in accounts:
        if a.parent_code:
            children.setdefault(a.parent_code, []).append(a.code)
    return children


def _recursive_sum(code: str, children_map: Dict[str, List[str]], data_map: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    debit = data_map.get(code, {}).get('debit', 0.0)
    credit = data_map.get(code, {}).get('credit', 0.0)
    for child in children_map.get(code, []):
        child_sum = _recursive_sum(child, children_map, data_map)
        debit += child_sum['debit']
        credit += child_sum['credit']
    return {'debit': debit, 'credit': credit}


def get_trial_balance(db: Session, from_date: Optional[date], to_date: Optional[date], page: int = 1, page_size: int = 200, fiscal_year: Optional[int] = None, include_zero: bool = False) -> Dict:
    """Compute trial balance using Account + JournalEntry + JournalEntryLine + OpeningBalance.

    Requirements:
      - from_date and to_date required
      - opening balances come from OpeningBalance for fiscal_year
      - recursive summation for group accounts
    """
    if not from_date or not to_date:
        raise HTTPException(status_code=400, detail="from_date and to_date are required")

    # Load accounts
    accounts: List[Account] = db.exec(select(Account).where(Account.is_active == True).order_by(Account.code)).all()

    # Determine fiscal year if not provided: use from_date.year
    fy = fiscal_year or from_date.year

    opening_map = _get_opening_balance_map(db, fy)

    # Sum journal lines in period
    period_sums = _sum_journal_lines(db, from_date, to_date)

    # prepare children map for recursive sums
    children_map = _build_account_tree(accounts)

    # Build per-account TB rows (use code ordering)
    rows = []
    for acc in accounts:
        code = acc.code
        # compute recursive sums (includes own and all children)
        rec = _recursive_sum(code, children_map, period_sums)
        period_debit = round(rec['debit'], 2)
        period_credit = round(rec['credit'], 2)
        opening = round(float(opening_map.get(code, 0.0) or 0.0), 2)
        closing = round(opening + period_debit - period_credit, 2)

        # skip zero lines if requested
        if not include_zero and opening == 0 and period_debit == 0 and period_credit == 0 and closing == 0:
            continue

        rows.append({
            'code': code,
            'name': acc.name,
            'level': acc.level,
            'is_group': bool(acc.is_group),
            'opening_balance': opening,
            'period_debit': period_debit,
            'period_credit': period_credit,
            'closing_balance': closing
        })

    total_debit = sum(r['period_debit'] for r in rows)
    total_credit = sum(r['period_credit'] for r in rows)

    # pagination
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return {
        'rows': page_rows,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_debit': round(total_debit, 2),
        'total_credit': round(total_credit, 2),
        'balanced': round(total_debit,2) == round(total_credit,2)
    }


def generate_trial_balance_pdf(db: Session, from_date: date, to_date: date, fiscal_year: Optional[int] = None) -> bytes:
    """Generate PDF bytes for trial balance using WeasyPrint. Returns raw PDF bytes."""
    # reuse existing get_trial_balance to compute rows
    result = get_trial_balance(db, from_date, to_date, page=1, page_size=1000000, fiscal_year=fiscal_year)

    # Render HTML via Jinja2 template located in frontend/templates/reports/
    from fastapi.templating import Jinja2Templates
    from datetime import datetime
    try:
        from weasyprint import HTML
    except Exception:
        raise RuntimeError("WeasyPrint not available")

    templates = Jinja2Templates(directory="frontend/templates")
    template = templates.env.get_template('reports/trial_balance_pdf.html')
    context = {
        'rows': result['rows'],
        'total_debit': result['total_debit'],
        'total_credit': result['total_credit'],
        'balanced': result['balanced'],
        'from_date': from_date.isoformat(),
        'to_date': to_date.isoformat(),
        'generated_at': datetime.utcnow().isoformat(),
        'company_name': 'Company Name'
    }
    html_out = template.render(context)
    pdf_bytes = HTML(string=html_out).write_pdf()
    return pdf_bytes
