from sqlmodel import Session, select
from app.models.journal import JournalEntry, JournalEntryLine

def create_journal_entry(db: Session, entry_data: dict, lines: list):
    """Membuat entri jurnal baru dengan validasi debit=kredit"""
    # Step 1: Buat header journal entry
    je = JournalEntry(**entry_data)
    db.add(je)
    db.commit()
    db.refresh(je)

    # Step 2: Tambahkan line items
    total_debit = 0
    total_credit = 0

    for line in lines:
        jl = JournalEntryLine(journal_entry_id=je.id, **line)
        db.add(jl)
        total_debit += line.get("debit", 0)
        total_credit += line.get("credit", 0)

    # Validasi kesamaan debit dan kredit
    if total_debit != total_credit:
        db.rollback()
        raise ValueError("Total debit dan kredit harus sama")

    db.commit()
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