from sqlmodel import SQLModel, Field
from typing import Optional

class GLEntry(SQLModel, table=True):
    __tablename__ = "gl_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_entry_id: int = Field(foreign_key="journal_entries.id")
    account_id: int = Field(foreign_key="accounts.id")
    debit: float = 0
    credit: float = 0
    balance_after: float = 0
