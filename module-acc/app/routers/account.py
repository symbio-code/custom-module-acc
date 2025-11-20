from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.database import get_session
from app.models import Account
from app.services.accounting_service import create_account, list_accounts

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/")
def create_new_account(account: Account, db: Session = Depends(get_session)):
    return create_account(
        db=db,
        code=account.code,
        name=account.name,
        account_type=account.account_type,
        parent_id=account.parent_id
    )


@router.get("/")
def get_all_accounts(db: Session = Depends(get_session)):
    return list_accounts(db)
