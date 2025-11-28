from datetime import date
import pytest
from sqlmodel import Session, select

from app.services.journal_service import create_journal_entry
from app.services.ledger_service import post_journal_entry, get_ledger_for_account


def test_post_journal_and_ledger_entries(db_session: Session):
    # Arrange - create a journal entry
    entry_data = {"date": date.today(), "description": "Post JE"}
    lines = [
        {"account_code": "100", "debit": 200.0, "credit": 0.0},
        {"account_code": "200", "debit": 0.0, "credit": 200.0}
    ]
    je = create_journal_entry(db_session, entry_data, lines)

    # Act - post to ledger
    res = post_journal_entry(db_session, je.id)
    assert res.get("status") == "posted"

    # Assert ledger rows exist for account 100
    ledger = get_ledger_for_account(db_session, "100")
    assert ledger["total"] >= 1
    assert ledger["closing_balance"] == pytest.approx(200.0)
