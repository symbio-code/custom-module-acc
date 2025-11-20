from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime
    reference: Optional[str] = None
    memo: Optional[str] = None
    posted: bool = False
