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




import uuid
from sqlalchemy import text, event
from sqlalchemy.pool import NullPool

def _get_test_schema_name():
    """Generate a unique schema name for this test (per-test isolation)."""
    return f"test_{uuid.uuid4().hex[:12]}"


def _create_test_schema(engine, schema_name: str):
    """Create a test schema and all tables within it.
    
    Uses explicit schema qualification to ensure tables are created in the
    test schema, not the public schema.
    """
    # Create schema
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.commit()
    
    # Set the schema on all tables temporarily for creation
    for table in SQLModel.metadata.tables.values():
        table.schema = schema_name
    
    try:
        # Create all tables in the test schema
        SQLModel.metadata.create_all(engine)
    finally:
        # Reset schemas back to None (public)
        for table in SQLModel.metadata.tables.values():
            table.schema = None


def _drop_test_schema(engine, schema_name: str):
    """Drop the test schema and all tables within it."""
    with engine.connect() as conn:
        try:
            conn.execute(text(f"DROP SCHEMA {schema_name} CASCADE"))
            conn.commit()
        except Exception:
            pass


@pytest.fixture()
def db_session(tmp_path):
    """Create a test Session with per-test isolation.

    For SQLite: creates a fresh temp file per test (full isolation).
    For Postgres (TEST_USE_POSTGRES=1): creates a fresh schema per test with all tables,
    seed data, and transaction handling. This ensures complete isolation like SQLite.
    """
    load_dotenv(dotenv_path=ROOT / ".env")
    use_postgres = os.getenv("TEST_USE_POSTGRES", "0") == "1"
    env_db = os.getenv("DATABASE_URL")
    
    if use_postgres and env_db and not env_db.count("${{") > 0:
        # Postgres with per-test schema isolation
        database_url = env_db
        
        # Generate unique schema name for this test
        schema_name = _get_test_schema_name()
        
        # Create engine with NullPool to avoid connection pooling issues
        # Each connection is fresh and not reused, ensuring no cross-test schema contamination
        engine = create_engine(database_url, echo=False, poolclass=NullPool)
        # Ensure the application's module-level engine is replaced with our test engine
        try:
            import app.database as app_database
            app_database.engine = engine
        except Exception:
            pass
        
        try:
            # Create test schema with all tables
            _create_test_schema(engine, schema_name)
            
            # Register event listener AFTER creating schema, to ensure it's set on every connection
            def set_search_path(dbapi_conn, connection_record):
                with dbapi_conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}, public")
            
            listener = event.listens_for(engine, "connect")(set_search_path)
            
            # Seed base data in test schema
            with Session(engine) as session:
                _seed_base_data(session)
            
            # Provide a Session for the test
            session = Session(engine)
            
            try:
                yield session
            finally:
                session.close()
        finally:
            # Clean up: remove listener, drop schema, dispose engine
            try:
                event.remove(engine, "connect", set_search_path)
            except Exception:
                pass
            
            # Drop schema (will also drop all tables within it)
            try:
                _drop_test_schema(engine, schema_name)
            except Exception as e:
                print(f"Warning: Failed to drop test schema {schema_name}: {e}")
            
            try:
                engine.dispose()
            except Exception:
                pass
    else:
        # SQLite: use per-test temp file (RECOMMENDED for CI/automated tests)
        db_file = tmp_path / "test.db"
        database_url = f"sqlite:///{db_file}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        
        # Create all tables
        # Ensure the application's module-level engine is replaced with our test engine
        try:
            import app.database as app_database
            app_database.engine = engine
        except Exception:
            pass
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
    from app.utils.security import hash_password
    
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
        admin = User(username="admin", password_hash=hash_password("admin"), role=UserRole.admin)
        session.add(admin)
    acct = session.exec(select(User).where(User.username == 'acct')).first()
    if not acct:
        acct = User(username="acct", password_hash=hash_password("acct"), role=UserRole.accountant)
        session.add(acct)
    viewer = session.exec(select(User).where(User.username == 'viewer')).first()
    if not viewer:
        viewer = User(username="viewer", password_hash=hash_password("viewer"), role=UserRole.viewer)
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


# ============================================================================
# AUTH-SPECIFIC FIXTURES FOR TESTING
# ============================================================================

@pytest.fixture
def admin_user(db_session) -> User:
    """Get the seeded admin user."""
    u = db_session.exec(select(User).where(User.username == 'admin')).first()
    assert u is not None, "Admin user not found in database"
    return u


@pytest.fixture
def accountant_user(db_session) -> User:
    """Get the seeded accountant user."""
    u = db_session.exec(select(User).where(User.username == 'acct')).first()
    assert u is not None, "Accountant user not found in database"
    return u


@pytest.fixture
def viewer_user(db_session) -> User:
    """Get the seeded viewer user."""
    u = db_session.exec(select(User).where(User.username == 'viewer')).first()
    assert u is not None, "Viewer user not found in database"
    return u


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate a valid JWT token for admin user."""
    return create_access_token(admin_user)


@pytest.fixture
def accountant_token(accountant_user: User) -> str:
    """Generate a valid JWT token for accountant user."""
    return create_access_token(accountant_user)


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    """Generate a valid JWT token for viewer user."""
    return create_access_token(viewer_user)


@pytest.fixture
def admin_auth_headers(admin_token: str) -> dict:
    """Authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def accountant_auth_headers(accountant_token: str) -> dict:
    """Authorization headers with accountant token."""
    return {"Authorization": f"Bearer {accountant_token}"}


@pytest.fixture
def viewer_auth_headers(viewer_token: str) -> dict:
    """Authorization headers with viewer token."""
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def htmx_headers() -> dict:
    """HTMX request headers."""
    return {"hx-request": "true"}


@pytest.fixture
def admin_htmx_headers(admin_token: str) -> dict:
    """HTMX request headers with admin authorization."""
    return {
        "hx-request": "true",
        "Authorization": f"Bearer {admin_token}"
    }


@pytest.fixture
def accountant_htmx_headers(accountant_token: str) -> dict:
    """HTMX request headers with accountant authorization."""
    return {
        "hx-request": "true",
        "Authorization": f"Bearer {accountant_token}"
    }


@pytest.fixture
def viewer_htmx_headers(viewer_token: str) -> dict:
    """HTMX request headers with viewer authorization."""
    return {
        "hx-request": "true",
        "Authorization": f"Bearer {viewer_token}"
    }


# ============================================================================
# HELPER FUNCTIONS FOR AUTH TESTING
# ============================================================================

def create_test_user(
    db_session: Session,
    username: str,
    password: str,
    role: UserRole = UserRole.viewer
) -> User:
    """Create a test user with hashed password.
    
    Args:
        db_session: Database session
        username: Username for the new user
        password: Plaintext password (will be hashed)
        role: User role (default: viewer)
    
    Returns:
        Created User object
    """
    from app.utils.security import hash_password
    
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def create_user_helper(db_session):
    """Fixture to create test users during a test."""
    return lambda username, password, role=UserRole.viewer: create_test_user(
        db_session, username, password, role
    )
