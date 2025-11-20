from fastapi import APIRouter, Depends
from sqlmodel import Session
from datetime import datetime

from app.database import get_session
from app.models import JournalEntry, JournalLine
from app.services.accounting_service import (
    create_journal_entry,
    add_journal_line,
    post_journal_to_gl
)

router = APIRouter(prefix="/journal", tags=["Journal Entries"])


@router.post("/entry")
def new_journal_entry(entry: JournalEntry, db: Session = Depends(get_session)):
    return create_journal_entry(
        db=db,
        date=entry.date,
        reference=entry.reference,
        memo=entry.memo,
    )


@router.post("/line")
def new_journal_line(line: JournalLine, db: Session = Depends(get_session)):
    return add_journal_line(
        db=db,
        journal_entry_id=line.journal_entry_id,
        account_id=line.account_id,
        debit=line.debit,
        credit=line.credit,
    )


@router.post("/post/{journal_id}")
def post_journal(journal_id: int, db: Session = Depends(get_session)):
    return post_journal_to_gl(db, journal_id)
