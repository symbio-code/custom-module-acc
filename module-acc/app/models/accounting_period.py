from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class AccountingPeriod(SQLModel, table=True):
    __tablename__ = "accounting_periods"

    id: Optional[int] = Field(default=None, primary_key=True)
    period_name: str
    start_date: date
    end_date: date
    is_closed: bool = False
