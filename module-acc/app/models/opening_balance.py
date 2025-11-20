from sqlmodel import SQLModel, Field
from typing import Optional

class OpeningBalance(SQLModel, table=True):
    __tablename__ = "opening_balances"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    debit: float = 0
    credit: float = 0
