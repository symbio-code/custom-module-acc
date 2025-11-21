from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class LedgerEntry(SQLModel, table=True):
    """Tabel utama untuk ledger entries (buku besar)"""
    __tablename__ = "ledger_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_entry_id: int = Field(index=True)
    date: date
    account_code: str = Field(index=True)
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None