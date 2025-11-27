from sqlmodel import Session, select
from typing import List, Dict, Optional
from datetime import date
from fastapi import HTTPException

from app.models.account import Account
from app.models.journal import JournalEntryLine, JournalEntry


def _sum_journal_lines_for_pl(db: Session, from_date: date, to_date: date) -> Dict[str, Dict[str, float]]:
    """Return map account_code -> {'debit': x, 'credit': y} for P&L period."""
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
    """Build parent->children mapping."""
    children: Dict[str, List[str]] = {}
    for a in accounts:
        children.setdefault(a.parent_code or '', [])
        children.setdefault(a.code, [])
    for a in accounts:
        if a.parent_code:
            children.setdefault(a.parent_code, []).append(a.code)
    return children


def _recursive_sum(code: str, children_map: Dict[str, List[str]], data_map: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Recursively sum debit/credit including children."""
    debit = data_map.get(code, {}).get('debit', 0.0)
    credit = data_map.get(code, {}).get('credit', 0.0)
    for child in children_map.get(code, []):
        child_sum = _recursive_sum(child, children_map, data_map)
        debit += child_sum['debit']
        credit += child_sum['credit']
    return {'debit': debit, 'credit': credit}


def get_profit_loss(
    db: Session,
    from_date: Optional[date],
    to_date: Optional[date],
    page: int = 1,
    page_size: int = 200,
    include_zero: bool = False
) -> Dict:
    """Compute Profit & Loss (Income Statement) for the given period.
    
    Requirements:
      - from_date and to_date required
      - filters accounts by account_type in ('revenue', 'expense')
      - sums period debit/credit from journal entry lines
      - recursively aggregates for group accounts
      - returns rows organized by Revenue, Expense sections
      - computes Net Profit = Total Revenue - Total Expense
      - supports pagination and include_zero filter
    
    Sign convention:
      - Revenue: reported as credit amounts (positive values)
      - Expense: reported as debit amounts (positive values)
      - Net Profit: revenue_total - expense_total (positive = profit)
    """
    if not from_date or not to_date:
        raise HTTPException(status_code=400, detail="from_date and to_date are required")

    # Load only revenue and expense accounts
    accounts: List[Account] = db.exec(
        select(Account)
        .where(Account.is_active == True, Account.account_type.in_(["revenue", "expense"]))
        .order_by(Account.code)
    ).all()

    if not accounts:
        return {
            'rows': [],
            'total_revenue': 0.0,
            'total_expense': 0.0,
            'net_profit': 0.0,
            'total': 0,
            'page': page,
            'page_size': page_size
        }

    # Sum journal lines in period
    period_sums = _sum_journal_lines_for_pl(db, from_date, to_date)

    # Build children map for recursive sums
    children_map = _build_account_tree(accounts)

    # Build rows: Revenue section first, then Expense section
    rows = []
    revenue_total = 0.0
    expense_total = 0.0

    # Add section header or organize by account_type
    for acc in accounts:
        code = acc.code
        rec = _recursive_sum(code, children_map, period_sums)
        debit = round(rec['debit'], 2)
        credit = round(rec['credit'], 2)

        # Sign convention:
        # Revenue: use credit as the "positive" amount
        # Expense: use debit as the "positive" amount
        if acc.account_type == 'revenue':
            amount = credit  # or (credit - debit) if you want net direction
            revenue_total += amount
        elif acc.account_type == 'expense':
            amount = debit  # or (debit - credit) if you want net direction
            expense_total += amount
        else:
            amount = 0.0

        # Skip zero lines if requested
        if not include_zero and debit == 0 and credit == 0 and amount == 0:
            continue

        rows.append({
            'code': code,
            'name': acc.name,
            'level': acc.level,
            'is_group': bool(acc.is_group),
            'account_type': acc.account_type,
            'period_debit': debit,
            'period_credit': credit,
            'amount': amount  # sign-adjusted amount (positive for both revenue/expense)
        })

    # Compute Net Profit
    net_profit = round(revenue_total - expense_total, 2)

    # Pagination
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return {
        'rows': page_rows,
        'total_revenue': round(revenue_total, 2),
        'total_expense': round(expense_total, 2),
        'net_profit': net_profit,
        'total': total,
        'page': page,
        'page_size': page_size
    }


def generate_profit_loss_pdf(db: Session, from_date: date, to_date: date) -> bytes:
    """Generate Profit & Loss PDF bytes using WeasyPrint."""
    from fastapi.templating import Jinja2Templates
    from datetime import datetime
    try:
        from weasyprint import HTML
    except Exception:
        raise RuntimeError("WeasyPrint not available")

    result = get_profit_loss(db, from_date, to_date, page=1, page_size=1000000)
    templates = Jinja2Templates(directory="frontend/templates")
    template = templates.env.get_template('reports/profit_loss_pdf.html')
    context = {
        'rows': result['rows'],
        'total_revenue': result['total_revenue'],
        'total_expense': result['total_expense'],
        'net_profit': result['net_profit'],
        'from_date': from_date.isoformat(),
        'to_date': to_date.isoformat(),
        'generated_at': datetime.utcnow().isoformat(),
        'company_name': 'Company Name'
    }
    html_out = template.render(context)
    pdf_bytes = HTML(string=html_out).write_pdf()
    return pdf_bytes
