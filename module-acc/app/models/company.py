from sqlmodel import SQLModel, Field
from typing import Optional

class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    currency: str = "IDR"
