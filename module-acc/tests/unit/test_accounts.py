from datetime import date
from sqlmodel import Session, select
import pytest

from app.models.account import Account
from app.services.account_service import create_account, list_accounts


def test_create_account_and_hierarchy(db_session: Session):
    # Arrange
    data = Account(code="110", name="Bank", account_type="asset")

    # Act
    acc = create_account(db_session, data)

    # Assert
    assert acc.id is not None
    assert acc.code == "110"
    assert acc.name == "Bank"

    # Ensure list_accounts returns this account
    res = list_accounts(db_session, page=1, page_size=100)
    codes = [r.code for r in res['rows']]
    assert "110" in codes


def test_create_account_invalid_code(db_session: Session):
    data = Account(code="ABC", name="Invalid", account_type="asset")
    with pytest.raises(Exception):
        create_account(db_session, data)
