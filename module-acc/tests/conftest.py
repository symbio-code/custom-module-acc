import sys
from pathlib import Path
import pytest
import os
from dotenv import load_dotenv
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




def _truncate_all_tables(engine):
    """Truncate all tables in the database (for per-test cleanup when using Postgres)."""
    with engine.connect() as conn:
        # Disable foreign key constraints temporarily
        try:
            conn.execute("SET session_replication_role = 'replica';")
        except Exception:
            pass  # SQLite does not support this; it will just fail silently
        
        # Truncate all tables
        for table in reversed(SQLModel.metadata.sorted_tables):
            try:
                conn.execute(f"TRUNCATE TABLE {table.name} CASCADE;")
            except Exception:
                # Fallback to DELETE for SQLite compatibility
                try:
                    conn.execute(f"DELETE FROM {table.name};")
                except Exception:
                    pass
        
        # Re-enable foreign key constraints
        try:
            conn.execute("SET session_replication_role = 'origin';")
        except Exception:
            pass
        
        conn.commit()


@pytest.fixture()
def db_session(tmp_path):
    """Create a fresh SQLite DB file for each test and return a Session.

    This gives maximal isolation: each test gets its own database file,
    tables are created and required seed data inserted. The TestClient is
    overridden to use the same `Session` for requests.
    
    NOTE: TEST_USE_POSTGRES=1 is NOT recommended for automated tests due to
    transaction isolation challenges. Use only for manual integration testing
    against a real Postgres instance (e.g., for dev or QA). Automated tests
    should use the default SQLite per-test approach for full isolation.
    """
    load_dotenv(dotenv_path=ROOT / ".env")
    use_postgres = os.getenv("TEST_USE_POSTGRES", "0") == "1"
    env_db = os.getenv("DATABASE_URL")
    
    if use_postgres and env_db and not env_db.count("${{") > 0:
        # Only use Postgres if explicitly enabled AND env_db has no placeholders
        # (to prevent misconfiguration against unresolved Railway template strings)
        database_url = env_db
        engine = create_engine(database_url)
        
        # Create all tables if needed
        SQLModel.metadata.create_all(engine)
        
        # For Postgres tests, truncate all data at start of each test
        # (transaction rollback approach does not fully isolate seed data)
        _truncate_all_tables(engine)
        
        # Seed base data
        with Session(engine) as session:
            _seed_base_data(session)
        
        # Provide a Session for the test
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()
            try:
                engine.dispose()
            except Exception:
                pass
    else:
        # SQLite: use per-test temp file with full isolation (RECOMMENDED)
        db_file = tmp_path / "test.db"
        database_url = f"sqlite:///{db_file}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        
        # Create all tables
        SQLModel.metadata.create_all(engine)
        
        # Seed base data
        with Session(engine) as session:
            _seed_base_data(session)
        
        # Provide a Session for the test
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()
            try:
                engine.dispose()
            except Exception:
                pass


def _seed_base_data(session: Session):
    """Seed common test data into a session."""
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
