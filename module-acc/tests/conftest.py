import sys
from pathlib import Path
import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi.testclient import TestClient

# Ensure project package is importable (module-acc folder)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.account import Account
from app.models.user import User, UserRole
from app.models.journal import JournalEntry, JournalEntryLine
from app.models.ledger import LedgerEntry
from app.models.opening_balance import OpeningBalance
from app.security import create_access_token

# Import the FastAPI app and original get_session (we will override per-test)
from app.main import app
from app.database import get_session as original_get_session




@pytest.fixture()
def db_session(tmp_path):
    """Create a fresh SQLite DB file for each test and return a Session.

    This gives maximal isolation: each test gets its own database file,
    tables are created and required seed data inserted. The TestClient is
    overridden to use the same `Session` for requests.
    """
    db_file = tmp_path / "test.db"
    database_url = f"sqlite:///{db_file}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    # Create all tables for this test DB
    SQLModel.metadata.create_all(engine)

    # Seed minimal data required for tests (accounts + users)
    with Session(engine) as session:
        accounts = [
            Account(code="100", name="Cash", account_type="asset", level=0, is_group=False),
            Account(code="200", name="Accounts Payable", account_type="liability", level=0, is_group=False),
            Account(code="300", name="Equity", account_type="equity", level=0, is_group=False),
            Account(code="400", name="Sales", account_type="revenue", level=0, is_group=False),
            Account(code="500", name="Rent Expense", account_type="expense", level=0, is_group=False),
        ]
        for a in accounts:
            exists = session.exec(select(Account).where(Account.code == a.code)).first()
            if not exists:
                session.add(a)

        admin = session.exec(select(User).where(User.username == 'admin')).first()
        if not admin:
            admin = User(username="admin", password_hash="x", role=UserRole.admin)
            session.add(admin)
        acct = session.exec(select(User).where(User.username == 'acct')).first()
        if not acct:
            acct = User(username="acct", password_hash="x", role=UserRole.accountant)
            session.add(acct)
        viewer = session.exec(select(User).where(User.username == 'viewer')).first()
        if not viewer:
            viewer = User(username="viewer", password_hash="x", role=UserRole.viewer)
            session.add(viewer)

        session.commit()

    # Provide a Session bound to this engine for the test
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        try:
            engine.dispose()
        except Exception:
            pass


# Override the FastAPI dependency to use our test session

@pytest.fixture()
def client(db_session):
    # Override get_session to yield the per-test session
    def _override_get_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[original_get_session] = _override_get_session
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(original_get_session, None)


# (Seeding happens per-test in `db_session` to guarantee isolation)


# Helper fixtures for auth headers
@pytest.fixture
def admin_headers(db_session):
    u = db_session.exec(select(User).where(User.username == 'admin')).first()
    token = create_access_token(u)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def accountant_headers(db_session):
    u = db_session.exec(select(User).where(User.username == 'acct')).first()
    token = create_access_token(u)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(db_session):
    u = db_session.exec(select(User).where(User.username == 'viewer')).first()
    token = create_access_token(u)
    return {"Authorization": f"Bearer {token}"}
