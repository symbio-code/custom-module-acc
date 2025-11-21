from sqlmodel import SQLModel, Field
from typing import Optional

class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    account_type: str  # asset, liability, equity, revenue, expense
    level: int = 0     # indent level (0-3)
    parent_code: Optional[str] = Field(default=None)
    is_group: bool = False
    is_active: bool = True