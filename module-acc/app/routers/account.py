from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.models.account import Account
from app.services.account_service import (
    create_account, list_accounts, update_account,
    delete_account, get_account
)

router = APIRouter(prefix="/accounts")

@router.post("/")
def create(data: Account, db: Session = Depends(get_session)):
    return create_account(db, data)

@router.get("/")
def list_all(
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    sort_by: str = "code",
    sort_dir: str = "asc",
    db: Session = Depends(get_session)
):
    return list_accounts(
        db, page, page_size, search, sort_by, sort_dir
    )

@router.get("/{id}")
def detail(id: int, db: Session = Depends(get_session)):
    return get_account(db, id)

@router.put("/{id}")
def update(id: int, data: dict, db: Session = Depends(get_session)):
    return update_account(db, id, data)

@router.delete("/{id}")
def delete(id: int, db: Session = Depends(get_session)):
    return delete_account(db, id)