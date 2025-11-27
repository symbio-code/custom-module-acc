from sqlmodel import Session, select
from typing import List, Dict, Optional
from datetime import date
from fastapi import HTTPException

from app.models.account import Account
from app.models.ledger import LedgerEntry
from app.models.opening_balance import OpeningBalance


def _get_opening_balance_map(db: Session, fiscal_year: int) -> Dict[str, float]:
    rows = db.exec(select(OpeningBalance).where(OpeningBalance.fiscal_year == fiscal_year)).all()
    return {r.account_code: float(r.opening_amount or 0.0) for r in rows}


def _sum_ledger_entries(db: Session, from_date: date, to_date: date) -> Dict[str, Dict[str, float]]:
    stmt = select(LedgerEntry).where(LedgerEntry.date >= from_date, LedgerEntry.date <= to_date)
    rows = db.exec(stmt).all()
    sums: Dict[str, Dict[str, float]] = {}
    for le in rows:
        code = le.account_code
        if code not in sums:
            sums[code] = {'debit': 0.0, 'credit': 0.0}
        sums[code]['debit'] += float(le.debit or 0.0)
        sums[code]['credit'] += float(le.credit or 0.0)
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


def get_balance_sheet(db: Session, from_date: Optional[date], to_date: Optional[date], page: int = 1, page_size: int = 200, fiscal_year: Optional[int] = None, include_zero: bool = False) -> Dict:
    """Compute Balance Sheet rows using Account + LedgerEntry + OpeningBalance.

    Returns a dict with sections: assets, liabilities, equity and totals.
    """
    if not from_date or not to_date:
        raise HTTPException(status_code=400, detail="from_date and to_date are required")

    # Load accounts for balance sheet types
    accounts: List[Account] = db.exec(
        select(Account).where(Account.is_active == True, Account.account_type.in_(["asset", "liability", "equity"]))
        .order_by(Account.code)
    ).all()

    fy = fiscal_year or from_date.year
    opening_map = _get_opening_balance_map(db, fy)
    period_sums = _sum_ledger_entries(db, from_date, to_date)
    children_map = _build_account_tree(accounts)

    assets_rows = []
    liabilities_rows = []
    equity_rows = []

    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0

    for acc in accounts:
        code = acc.code
        rec = _recursive_sum(code, children_map, period_sums)
        debit = round(rec['debit'], 2)
        credit = round(rec['credit'], 2)
        opening = round(float(opening_map.get(code, 0.0) or 0.0), 2)
        closing = round(opening + debit - credit, 2)

        if not include_zero and opening == 0 and debit == 0 and credit == 0 and closing == 0:
            continue

        row = {
            'code': code,
            'name': acc.name,
            'level': acc.level,
            'is_group': bool(acc.is_group),
            'account_type': acc.account_type,
            'opening_balance': opening,
            'period_debit': debit,
            'period_credit': credit,
            'closing_balance': closing
        }

        if acc.account_type == 'asset':
            assets_rows.append(row)
            total_assets += closing
        elif acc.account_type == 'liability':
            liabilities_rows.append(row)
            total_liabilities += closing
        elif acc.account_type == 'equity':
            equity_rows.append(row)
            total_equity += closing

    # pagination (apply to concatenated rows if needed)
    all_rows = assets_rows + liabilities_rows + equity_rows
    total = len(all_rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = all_rows[start:end]

    return {
        'assets': assets_rows,
        'liabilities': liabilities_rows,
        'equity': equity_rows,
        'total_assets': round(total_assets, 2),
        'total_liabilities': round(total_liabilities, 2),
        'total_equity': round(total_equity, 2),
        'balanced': round(total_assets, 2) == round((total_liabilities + total_equity), 2),
        'total': total,
        'page': page,
        'page_size': page_size
    }


def generate_balance_sheet_pdf(db: Session, from_date: date, to_date: date, fiscal_year: Optional[int] = None) -> bytes:
    """Generate Balance Sheet PDF bytes using WeasyPrint."""
    from fastapi.templating import Jinja2Templates
    from datetime import datetime
    try:
        from weasyprint import HTML
    except Exception:
        raise RuntimeError("WeasyPrint not available")

    result = get_balance_sheet(db, from_date, to_date, page=1, page_size=1000000, fiscal_year=fiscal_year)
    templates = Jinja2Templates(directory="frontend/templates")
    template = templates.env.get_template('reports/balance_sheet_pdf.html')
    context = {
        'assets': result['assets'],
        'liabilities': result['liabilities'],
        'equity': result['equity'],
        'total_assets': result['total_assets'],
        'total_liabilities': result['total_liabilities'],
        'total_equity': result['total_equity'],
        'balanced': result['balanced'],
        'from_date': from_date.isoformat(),
        'to_date': to_date.isoformat(),
        'generated_at': datetime.utcnow().isoformat(),
        'company_name': 'Company Name'
    }
    html_out = template.render(context)
    pdf_bytes = HTML(string=html_out).write_pdf()
    return pdf_bytes
