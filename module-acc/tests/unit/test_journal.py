from datetime import date
import pytest
from sqlmodel import Session

from app.services.journal_service import create_journal_entry, get_journal_entry
from app.models.journal import JournalEntryLine


def test_create_journal_entry_balanced(db_session: Session):
    # Arrange
    entry_data = {"date": date.today(), "description": "Test JE"}
    lines = [
        {"account_code": "100", "debit": 100.0, "credit": 0.0},
        {"account_code": "400", "debit": 0.0, "credit": 100.0}
    ]

    # Act
    je = create_journal_entry(db_session, entry_data, lines)

    # Assert
    assert je is not None
    assert je.id is not None

    fetched = get_journal_entry(db_session, je.id)
    assert fetched["header"].id == je.id
    assert len(fetched["lines"]) == 2


def test_create_journal_unbalanced_raises(db_session: Session):
    entry_data = {"date": date.today(), "description": "Bad JE"}
    lines = [
        {"account_code": "100", "debit": 100.0, "credit": 0.0},
        {"account_code": "400", "debit": 0.0, "credit": 50.0}
    ]
    with pytest.raises(Exception):
        create_journal_entry(db_session, entry_data, lines)
