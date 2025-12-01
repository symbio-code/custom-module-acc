# FastAPI Authentication Test Suite - Quick Start Guide

## Overview

This is a complete, production-ready test suite for FastAPI authentication with RBAC, JWT, and HTMX support.

- **60+ test methods** across 4 test files
- **1,845 lines** of comprehensive test code
- **18 test classes** organized by functionality
- **Full AAA pattern** (Arrange-Act-Assert)
- **Complete fixtures** for auth testing

## Files Created

```
tests/auth/
├── __init__.py
├── test_auth_login.py       (480 lines, 24 tests)
├── test_auth_logout.py      (307 lines, 9 tests)
├── test_auth_permissions.py (600 lines, 21 tests)
├── test_auth_htmx.py        (457 lines, 16 tests)
└── TEST_SUITE_SUMMARY.md    (this comprehensive guide)
```

## Updated conftest.py

Enhanced with 15+ new fixtures:
- User fixtures: `admin_user`, `accountant_user`, `viewer_user`
- Token fixtures: `admin_token`, `accountant_token`, `viewer_token`
- Auth headers: `admin_auth_headers`, `accountant_auth_headers`, `viewer_auth_headers`
- HTMX headers: `admin_htmx_headers`, `accountant_htmx_headers`, `viewer_htmx_headers`
- Helpers: `create_user_helper`

## Quick Run

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-cov

# Run all auth tests
cd /workspaces/custom-module-acc/module-acc
pytest tests/auth/ -v

# Run specific test file
pytest tests/auth/test_auth_login.py -v

# Run specific test class
pytest tests/auth/test_auth_login.py::TestValidLogin -v

# Run with coverage
pytest tests/auth/ --cov=app.security --cov=app.services.auth_service

# Run in parallel (install pytest-xdist)
pip install pytest-xdist
pytest tests/auth/ -n auto -v
```

## Test Categories

### 1. Login Tests (test_auth_login.py)
Tests for authentication and login functionality:
- ✓ Valid login with correct password
- ✓ Invalid login with wrong password
- ✓ Login with missing fields
- ✓ Password hashing and verification
- ✓ JWT token validation and expiration
- ✓ Protected route access

**Run:** `pytest tests/auth/test_auth_login.py -v`

### 2. Logout Tests (test_auth_logout.py)
Tests for logout and session management:
- ✓ Successful logout
- ✓ Cookie clearing
- ✓ Token invalidation behavior
- ✓ Logout flow cycles
- ✓ Multi-role logout

**Run:** `pytest tests/auth/test_auth_logout.py -v`

### 3. Permission Tests (test_auth_permissions.py)
Tests for role-based access control:
- ✓ Admin permissions (full CRUD)
- ✓ Accountant permissions (no delete)
- ✓ Viewer permissions (read-only)
- ✓ Journal RBAC
- ✓ Role hierarchy enforcement

**Run:** `pytest tests/auth/test_auth_permissions.py -v`

### 4. HTMX Tests (test_auth_htmx.py)
Tests for HTMX integration:
- ✓ HX-Redirect headers on login
- ✓ HX-Redirect headers on logout
- ✓ Request detection
- ✓ Error handling
- ✓ Multi-request flows

**Run:** `pytest tests/auth/test_auth_htmx.py -v`

## Seeded Test Users

Each test automatically gets these users:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| admin | admin_pass | admin | Full access |
| acct | acct_pass | accountant | Create, read, update (no delete) |
| viewer | viewer_pass | viewer | Read-only |

## Using Fixtures in Your Tests

### Example: Using auth fixtures

```python
def test_admin_access(self, client: TestClient, admin_auth_headers):
    """ARRANGE: Use admin_auth_headers fixture
    ACT: Call protected endpoint
    ASSERT: Admin has access
    """
    response = client.get("/accounts", headers=admin_auth_headers)
    assert response.status_code == 200
```

### Example: Creating a custom user

```python
def test_custom_user(self, client: TestClient, db_session):
    """Create a test user with specific permissions"""
    from app.utils.security import hash_password
    from app.models.user import User, UserRole
    
    user = User(
        username="custom_user",
        password_hash=hash_password("my_password"),
        role=UserRole.accountant
    )
    db_session.add(user)
    db_session.commit()
    
    # Now use in test
    response = client.post("/auth/login", json={"password": "my_password"})
    assert response.status_code == 200
```

### Example: HTMX request

```python
def test_htmx_login(self, client: TestClient, admin_htmx_headers):
    """Test HTMX login flow"""
    response = client.get("/accounts", headers=admin_htmx_headers)
    assert response.status_code == 200
```

## Test Structure (AAA Pattern)

Every test follows Arrange-Act-Assert:

```python
class TestSomething:
    def test_something(self, client: TestClient, db_session):
        # ARRANGE: Set up test data
        password = "test_password"
        hashed = hash_password(password)
        user = User(username="testuser", password_hash=hashed)
        db_session.add(user)
        db_session.commit()
        
        # ACT: Execute the code being tested
        response = client.post("/auth/login", json={"password": password})
        
        # ASSERT: Verify the results
        assert response.status_code == 200
        assert "access_token" in response.json()
```

## Common Test Patterns

### Testing protected endpoints

```python
# Without auth - should fail
response = client.get("/accounts")
assert response.status_code == 401

# With auth - should succeed
response = client.get("/accounts", headers=admin_auth_headers)
assert response.status_code == 200
```

### Testing role-based access

```python
# Viewer trying to delete (should fail)
response = client.delete(f"/accounts/{account_id}", headers=viewer_auth_headers)
assert response.status_code == 403

# Admin deleting (should succeed)
response = client.delete(f"/accounts/{account_id}", headers=admin_auth_headers)
assert response.status_code in [200, 204]
```

### Testing HTMX requests

```python
# HTMX login (should redirect)
response = client.post(
    "/auth/login",
    json={"password": password},
    headers={"hx-request": "true"}
)
assert response.status_code == 200
assert "HX-Redirect" in response.headers
assert response.headers["HX-Redirect"] == "/dashboard"

# Regular login (should return JSON)
response = client.post("/auth/login", json={"password": password})
assert response.status_code == 200
assert "access_token" in response.json()
```

## Coverage Areas

✓ **Authentication**: Login, token generation, validation
✓ **Password Security**: Hashing, verification, salt
✓ **Authorization**: Role-based access control
✓ **Tokens**: Generation, validation, expiration
✓ **Sessions**: Logout, cookie management
✓ **Error Handling**: 401, 403, 422, 404
✓ **HTMX**: Request detection, redirects, headers
✓ **Edge Cases**: Expired tokens, invalid format, empty values

## Running Specific Tests

```bash
# Run all login tests
pytest tests/auth/test_auth_login.py -v

# Run all RBAC tests
pytest tests/auth/test_auth_permissions.py -v

# Run all HTMX tests
pytest tests/auth/test_auth_htmx.py -v

# Run all logout tests
pytest tests/auth/test_auth_logout.py -v

# Run a specific test class
pytest tests/auth/test_auth_login.py::TestValidLogin -v

# Run a specific test
pytest tests/auth/test_auth_login.py::TestValidLogin::test_login_with_correct_password -v

# Run with verbose output and stop on first failure
pytest tests/auth/ -v -x

# Run with coverage report
pytest tests/auth/ --cov=app --cov-report=html

# Run in parallel
pytest tests/auth/ -n auto
```

## Key Features

- ✓ **Comprehensive**: 60+ tests covering all auth scenarios
- ✓ **Isolated**: Each test uses fresh database
- ✓ **Secure**: Passwords hashed with bcrypt
- ✓ **Standard Patterns**: AAA (Arrange-Act-Assert)
- ✓ **Fixtures**: Pre-built fixtures for common scenarios
- ✓ **RBAC**: Full role-based access control testing
- ✓ **HTMX**: Complete HTMX integration testing
- ✓ **Edge Cases**: Tests for error conditions

## Troubleshooting

### Tests fail with "User not found"
Make sure conftest.py `_seed_base_data()` function is called. It should be automatic for each test.

### Import errors
Ensure you're running from the module-acc directory:
```bash
cd /workspaces/custom-module-acc/module-acc
pytest tests/auth/ -v
```

### Database locked (SQLite)
If using SQLite, this shouldn't happen - each test gets fresh temp file. If it does:
```bash
pytest tests/auth/ --tb=short
```

### Token validation fails
Ensure `SECRET_KEY` is set in `.env`. Default is "secret123" in security.py if not set.

## Next Steps

1. **Run the tests**: `pytest tests/auth/ -v`
2. **Check coverage**: `pytest tests/auth/ --cov=app.security --cov-report=html`
3. **Integrate with CI/CD**: Add to GitHub Actions or similar
4. **Extend tests**: Add more edge cases or features
5. **Production**: Implement token blacklist, rate limiting, 2FA

## Production Recommendations

1. **Token Invalidation**: Implement token blacklist on logout
2. **Rate Limiting**: Limit login attempts (prevent brute force)
3. **Account Lockout**: Lock account after N failed attempts
4. **Audit Logging**: Log all auth events
5. **2FA**: Add two-factor authentication for admins
6. **Password Policy**: Enforce strong passwords
7. **Session Timeout**: Implement session timeouts
8. **HTTPS Only**: Use HTTPS with secure cookies

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Passlib](https://passlib.readthedocs.io/)
- [HTMX](https://htmx.org/)

---

**Happy Testing! 🚀**
