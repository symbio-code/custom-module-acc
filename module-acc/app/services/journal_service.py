from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.journal import JournalEntry, JournalEntryLine


def create_journal_entry(db: Session, entry_data: dict, lines: list):
    """Create journal entry with lines. Validate total debit == total credit before committing."""
    if not lines or len(lines) == 0:
        raise HTTPException(status_code=400, detail="Journal must have at least one line")

    total_debit = 0
    total_credit = 0

    # Compute totals first and validate structure
    for line in lines:
        try:
            d = float(line.get("debit", 0) or 0)
            c = float(line.get("credit", 0) or 0)
        except Exception:
            raise HTTPException(status_code=400, detail="Debit and credit must be numeric")
        total_debit += d
        total_credit += c

    if round(total_debit, 2) != round(total_credit, 2):
        raise HTTPException(status_code=400, detail="Total debit and credit must be equal")

    # Create header and lines in a single transaction
    je = JournalEntry(**entry_data)
    db.add(je)
    db.commit()
    db.refresh(je)

    for line in lines:
        jl = JournalEntryLine(journal_entry_id=je.id, **line)
        db.add(jl)

    db.commit()
    db.refresh(je)
    return je

def get_journal_entry(db: Session, id: int):
    """Mengambil satu entri jurnal lengkap dengan line items"""
    je = db.get(JournalEntry, id)
    if not je:
        return None

    lines = db.exec(
        select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == id)
    ).all()

    return {"header": je, "lines": lines}

def list_journal_entries(db: Session, page=1, page_size=20):
    """Daftar entri jurnal dengan pagination"""
    offset = (page - 1) * page_size

    rows = db.exec(
        select(JournalEntry)
        .order_by(JournalEntry.date.desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    total = db.exec(select(JournalEntry)).all()
    return {
        "rows": rows,
        "total": len(total),
        "page": page,
        "page_size": page_size
    }

def delete_journal_entry(db: Session, id: int):
    """Menghapus entri jurnal beserta line items"""
    je = db.get(JournalEntry, id)
    if not je:
        return False

    # Hapus semua line items terlebih dahulu
    lines = db.exec(
        select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == id)
    ).all()

    for line in lines:
        db.delete(line)

    db.delete(je)
    db.commit()
    return True