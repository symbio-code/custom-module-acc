from sqlmodel import Session, select
from app.models.ledger import LedgerEntry
from app.models.journal import JournalEntry, JournalEntryLine
from app.models.account import Account
from datetime import date
from typing import Optional, List
from fastapi import HTTPException

def post_journal_entry(db: Session, journal_id: int):
    """Mem-posting journal entry ke ledger (core accounting logic)"""
    # Ambil journal entry header
    je = db.get(JournalEntry, journal_id)
    if not je:
        raise ValueError("Journal entry tidak ditemukan")

    # Validasi: tidak boleh posting dua kali
    if je.posted:
        return {"status": "already_posted"}

    # Ambil semua line items
    lines = db.exec(
        select(JournalEntryLine).where(
            JournalEntryLine.journal_entry_id == journal_id
        )
    ).all()

    # Generate ledger entries untuk setiap line
    for line in lines:
        entry = LedgerEntry(
            journal_entry_id=journal_id,
            date=je.date,
            account_code=line.account_code,
            debit=line.debit,
            credit=line.credit,
            description=je.description
        )
        db.add(entry)

    # Lock journal entry (tandai sudah diposting)
    je.posted = True
    db.commit()

    return {"status": "posted", "journal_id": journal_id}

def validate_account_code(db: Session, account_code: str) -> Account:
    """Validasi account_code exists di Chart of Accounts"""
    acc = db.exec(
        select(Account).where(Account.code == account_code)
    ).first()
    if not acc:
           raise HTTPException(status_code=404, detail=f"Account {account_code} not found in Chart of Accounts")
    return acc

def get_ledger_for_account(
    db: Session,
    account_code: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    opening_balance: float = 0.0,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """Mengambil ledger untuk akun tertentu dengan running balance"""
    # Validasi account exists
    validate_account_code(db, account_code)

    # Build query
    query = select(LedgerEntry).where(LedgerEntry.account_code == account_code)
    
    # Filter by date range
    if from_date:
        query = query.where(LedgerEntry.date >= from_date)
    if to_date:
        query = query.where(LedgerEntry.date <= to_date)
    
    query = query.order_by(LedgerEntry.date).offset(offset).limit(limit)
    rows = db.exec(query).all()

    # Hitung running balance
    running_balance = opening_balance
    ledger_with_balance = []
    
    for row in rows:
        running_balance += row.debit - row.credit
        ledger_with_balance.append({
                "date": row.date.isoformat() if row.date else "",
                "description": row.description or "",
                "reference": f"LE-{row.id:05d}",
                "debit": round(row.debit, 2),
                "credit": round(row.credit, 2),
                "running_balance": round(running_balance, 2)
        })
    
    # Total count (untuk pagination)
    total_query = select(LedgerEntry).where(LedgerEntry.account_code == account_code)
    if from_date:
        total_query = total_query.where(LedgerEntry.date >= from_date)
    if to_date:
        total_query = total_query.where(LedgerEntry.date <= to_date)
    total_count = len(db.exec(total_query).all())

    return {
        "account_code": account_code,
        "rows": ledger_with_balance,
        "total": total_count,
        "opening_balance": opening_balance,
        "closing_balance": running_balance,
        "page": (offset // limit) + 1 if limit > 0 else 1,
        "page_size": limit
    }

def get_ledger_for_account_simple(db: Session, account_code: str):
    """Mengambil ledger untuk akun tertentu (simple, tanpa running balance)"""
    rows = db.exec(
        select(LedgerEntry)
        .where(LedgerEntry.account_code == account_code)
        .order_by(LedgerEntry.date)
    ).all()
    return rows

def list_ledger(db: Session):
    """Mengambil semua ledger entries (semua akun)"""
    rows = db.exec(select(LedgerEntry).order_by(
        LedgerEntry.date, LedgerEntry.account_code
    )).all()
    return rows