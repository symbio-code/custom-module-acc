from sqlmodel import Session, select
from app.models.ledger import LedgerEntry
from app.models.journal import JournalEntry, JournalEntryLine

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

def get_ledger_for_account(db: Session, account_code: str):
    """Mengambil ledger untuk akun tertentu"""
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