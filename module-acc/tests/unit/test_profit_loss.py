from datetime import date, timedelta
import pytest

from app.services.profit_loss_service import get_profit_loss
from app.services.journal_service import create_journal_entry


def test_profit_loss_basic(db_session):
    today = date.today()
    # create revenue and expense entries
    entry1 = {"date": today, "description": "Sale"}
    lines1 = [{"account_code": "400", "debit": 0.0, "credit": 1000.0}, {"account_code": "100", "debit": 1000.0, "credit": 0.0}]
    create_journal_entry(db_session, entry1, lines1)

    entry2 = {"date": today, "description": "Rent"}
    lines2 = [{"account_code": "500", "debit": 200.0, "credit": 0.0}, {"account_code": "100", "debit": 0.0, "credit": 200.0}]
    create_journal_entry(db_session, entry2, lines2)

    res = get_profit_loss(db_session, from_date=today - timedelta(days=1), to_date=today + timedelta(days=1))

    assert res["total_revenue"] == pytest.approx(1000.0)
    assert res["total_expense"] == pytest.approx(200.0)
    assert res["net_profit"] == pytest.approx(800.0)
