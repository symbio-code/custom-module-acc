from datetime import date, timedelta
import pytest
from sqlmodel import Session

from app.services.trial_balance_service import get_trial_balance
from app.services.journal_service import create_journal_entry


def test_trial_balance_balances(db_session: Session):
    # Arrange: create matching journal entries across accounts
    today = date.today()
    entry_data = {"date": today, "description": "TB JE"}
    lines = [
        {"account_code": "100", "debit": 500.0, "credit": 0.0},
        {"account_code": "200", "debit": 0.0, "credit": 500.0}
    ]
    je = create_journal_entry(db_session, entry_data, lines)

    # Act
    res = get_trial_balance(db_session, from_date=today - timedelta(days=1), to_date=today + timedelta(days=1))

    # Assert: totals equal
    assert res["total_debit"] == pytest.approx(res["total_credit"])
    assert res["balanced"] is True
