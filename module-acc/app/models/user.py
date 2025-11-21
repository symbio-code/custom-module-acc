from sqlmodel import SQLModel, Field
from typing import Optional

class AppUser(SQLModel, table=True):
    """Model untuk single user application"""
    __tablename__ = "app_user"

    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str  # Password yang sudah di-hash