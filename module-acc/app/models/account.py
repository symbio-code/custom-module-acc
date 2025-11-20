from sqlmodel import SQLModel, Field
from typing import Optional

class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    name: str
    account_type: str   # Asset/Liability/Equity/Expense/Income
    parent_id: Optional[int] = Field(default=None, foreign_key="accounts.id")
