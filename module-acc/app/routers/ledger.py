from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.database import get_session
from app.services.ledger_service import (
    post_journal_entry, 
    get_ledger_for_account, 
    list_ledger
)

router = APIRouter(prefix="/ledger")

@router.post("/post/{journal_id}")
def post_journal(journal_id: int, db: Session = Depends(get_session)):
    """Endpoint untuk mem-posting journal entry ke ledger"""
    return post_journal_entry(db, journal_id)

@router.get("/")
def ledger_all(db: Session = Depends(get_session)):
    """Endpoint untuk mengambil semua ledger entries"""
    return list_ledger(db)

@router.get("/{account_code}")
def ledger_account(account_code: str, db: Session = Depends(get_session)):
    """Endpoint untuk mengambil ledger per akun tertentu"""
    return get_ledger_for_account(db, account_code)