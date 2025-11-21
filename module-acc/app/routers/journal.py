from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.database import get_session
from app.services.journal_service import (
    create_journal_entry, list_journal_entries,
    get_journal_entry, delete_journal_entry
)

router = APIRouter(prefix="/journal")

@router.post("/")
def create_journal(payload: dict, db: Session = Depends(get_session)):
    """Endpoint untuk membuat entri jurnal baru"""
    entry_data = payload.get("entry")
    lines = payload.get("lines", [])
    return create_journal_entry(db, entry_data, lines)

@router.get("/")
def list_journals(page: int = 1, page_size: int = 20, db: Session = Depends(get_session)):
    """Endpoint untuk daftar entri jurnal"""
    return list_journal_entries(db, page, page_size)

@router.get("/{id}")
def journal_detail(id: int, db: Session = Depends(get_session)):
    """Endpoint untuk detail entri jurnal"""
    return get_journal_entry(db, id)

@router.delete("/{id}")
def delete_journal(id: int, db: Session = Depends(get_session)):
    """Endpoint untuk menghapus entri jurnal"""
    return delete_journal_entry(db, id)