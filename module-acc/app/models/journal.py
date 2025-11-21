from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class JournalEntry(SQLModel, table=True):
    """Tabel header untuk entri jurnal"""
    __tablename__ = "journal_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    description: Optional[str] = None
    posted: bool = False  # Terkunci setelah masuk ledger

class JournalEntryLine(SQLModel, table=True):
    """Tabel detail line items untuk entri jurnal"""
    __tablename__ = "journal_entry_lines"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_entry_id: int = Field(foreign_key="journal_entries.id")
    account_code: str = Field(index=True)
    debit: float = 0.0
    credit: float = 0.0