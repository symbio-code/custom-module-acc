from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class OpeningBalance(SQLModel, table=True):
    __tablename__ = "opening_balances"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_code: str = Field(index=True)
    fiscal_year: int
    opening_amount: float = 0.0
    created_at: Optional[date] = None
