from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.services.accounting_service import (
    get_trial_balance,
    get_general_ledger,
    get_simple_balance_sheet
)

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get("/trial-balance")
def trial_balance(db: Session = Depends(get_session)):
    return get_trial_balance(db)


@router.get("/gl/{account_id}")
def general_ledger(account_id: int, db: Session = Depends(get_session)):
    return get_general_ledger(db, account_id)


@router.get("/balance-sheet")
def simple_balance_sheet(db: Session = Depends(get_session)):
    return get_simple_balance_sheet(db)
