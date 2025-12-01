# FastAPI Auth Test Suite - Examples & Patterns

This document provides practical examples of how to use the test suite and common patterns.

## Table of Contents

1. [Basic Test Structure](#basic-test-structure)
2. [Using Fixtures](#using-fixtures)
3. [Common Test Patterns](#common-test-patterns)
4. [Edge Cases](#edge-cases)
5. [Integration Examples](#integration-examples)

---

## Basic Test Structure

### Example 1: Simple Login Test

```python
def test_user_can_login(self, client: TestClient, db_session):
    """ARRANGE: Create user with known password
    ACT: Login with that password
    ASSERT: Receive valid token
    """
    # ARRANGE
    from app.utils.security import hash_password
    from app.models.user import User, UserRole
    
    password = "my_secure_password"
    user = User(
        username="testuser",
        password_hash=hash_password(password),
        role=UserRole.viewer
    )
    db_session.add(user)
    db_session.commit()
    
    # ACT
    response = client.post("/auth/login", json={"password": password})
    
    # ASSERT
    assert response.status_code == 200
    assert "access_token" in response.json()
```

---

## Using Fixtures

### Pre-built User Fixtures

```python
from sqlmodel import select
from app.models.user import User

class TestWithFixtures:
    def test_with_admin_user(self, admin_user: User):
        """Use the pre-created admin user"""
        assert admin_user.username == "admin"
        assert admin_user.role.value == "admin"
    
    def test_with_accountant_user(self, accountant_user: User):
        """Use the pre-created accountant user"""
        assert accountant_user.username == "acct"
        assert accountant_user.role.value == "accountant"
    
    def test_with_viewer_user(self, viewer_user: User):
        """Use the pre-created viewer user"""
        assert viewer_user.username == "viewer"
        assert viewer_user.role.value == "viewer"
```

### Pre-built Token Fixtures

```python
class TestWithTokens:
    def test_with_admin_token(self, admin_token: str, client: TestClient):
        """Use the pre-generated admin token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_with_accountant_token(self, accountant_token: str, client: TestClient):
        """Use the pre-generated accountant token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {accountant_token}"}
        )
        assert response.status_code == 200
```

### Pre-built Headers Fixtures

```python
class TestWithHeaders:
    def test_with_admin_headers(self, client: TestClient, admin_auth_headers: dict):
        """Use pre-built admin authorization headers"""
        response = client.get("/accounts", headers=admin_auth_headers)
        assert response.status_code == 200
    
    def test_with_accountant_headers(self, client: TestClient, accountant_auth_headers: dict):
        """Use pre-built accountant authorization headers"""
        response = client.get("/accounts", headers=accountant_auth_headers)
        assert response.status_code == 200
    
    def test_with_viewer_headers(self, client: TestClient, viewer_auth_headers: dict):
        """Use pre-built viewer authorization headers"""
        response = client.get("/accounts", headers=viewer_auth_headers)
        assert response.status_code == 200
```

### Create Custom Users

```python
class TestWithCustomUsers:
    def test_create_custom_user_with_helper(self, client: TestClient, create_user_helper):
        """Use helper fixture to create custom test users"""
        # Create a new user with specific role
        user = create_user_helper(
            username="special_user",
            password="special_password",
            role=UserRole.accountant
        )
        
        # Now test with this user
        response = client.post(
            "/auth/login",
            json={"password": "special_password"}
        )
        assert response.status_code == 200
    
    def test_create_multiple_custom_users(self, db_session, create_user_helper):
        """Create multiple users for complex scenarios"""
        from app.models.user import UserRole
        
        users = []
        for i in range(3):
            user = create_user_helper(
                username=f"user_{i}",
                password=f"pass_{i}",
                role=UserRole.viewer
            )
            users.append(user)
        
        assert len(users) == 3
        assert all(u.role.value == "viewer" for u in users)
```

---

## Common Test Patterns

### Pattern 1: Test Protected Endpoints

```python
class TestProtectedEndpoints:
    def test_protected_endpoint_without_auth(self, client: TestClient):
        """ARRANGE: No authentication
        ACT: Call protected endpoint
        ASSERT: Return 401
        """
        response = client.get("/accounts")
        assert response.status_code == 401
        assert "token" in response.json()["detail"].lower()
    
    def test_protected_endpoint_with_valid_token(self, client: TestClient, admin_auth_headers: dict):
        """ARRANGE: Valid admin token
        ACT: Call protected endpoint with token
        ASSERT: Return 200
        """
        response = client.get("/accounts", headers=admin_auth_headers)
        assert response.status_code == 200
    
    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """ARRANGE: Invalid token
        ACT: Call protected endpoint
        ASSERT: Return 401
        """
        response = client.get(
            "/accounts",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401
```

### Pattern 2: Test RBAC (Role-Based Access Control)

```python
class TestRBACPatterns:
    def test_admin_can_delete(self, client: TestClient, admin_auth_headers: dict, db_session):
        """ARRANGE: Admin user, existing account
        ACT: Try to delete
        ASSERT: Success (204 or 200)
        """
        # Create an account
        account = Account(
            code="999", name="Test", account_type="asset",
            level=0, is_group=False
        )
        db_session.add(account)
        db_session.commit()
        
        # Admin deletes it
        response = client.delete(
            f"/accounts/{account.id}",
            headers=admin_auth_headers
        )
        assert response.status_code in [200, 204]
    
    def test_viewer_cannot_delete(self, client: TestClient, viewer_auth_headers: dict, db_session):
        """ARRANGE: Viewer user, existing account
        ACT: Try to delete
        ASSERT: 403 Forbidden
        """
        # Create an account
        account = Account(
            code="998", name="Test", account_type="asset",
            level=0, is_group=False
        )
        db_session.add(account)
        db_session.commit()
        
        # Viewer tries to delete
        response = client.delete(
            f"/accounts/{account.id}",
            headers=viewer_auth_headers
        )
        assert response.status_code == 403
    
    def test_role_hierarchy(self, client: TestClient, db_session):
        """ARRANGE: Users with different roles
        ACT: Test each role's permissions
        ASSERT: Hierarchy enforced
        """
        from app.utils.security import hash_password
        from app.models.user import User, UserRole
        
        # Create users
        admin = create_test_user(db_session, "admin_test", "pass", UserRole.admin)
        acct = create_test_user(db_session, "acct_test", "pass", UserRole.accountant)
        viewer = create_test_user(db_session, "viewer_test", "pass", UserRole.viewer)
        
        # Admin can create
        response = client.post(
            "/accounts",
            json={"code": "997", "name": "Admin Created", "account_type": "asset", 
                  "level": 0, "is_group": False},
            headers={"Authorization": f"Bearer {create_access_token(admin)}"}
        )
        assert response.status_code in [200, 201]
        
        # Accountant can create
        response = client.post(
            "/accounts",
            json={"code": "996", "name": "Acct Created", "account_type": "asset",
                  "level": 0, "is_group": False},
            headers={"Authorization": f"Bearer {create_access_token(acct)}"}
        )
        assert response.status_code in [200, 201]
        
        # Viewer cannot create
        response = client.post(
            "/accounts",
            json={"code": "995", "name": "Viewer Created", "account_type": "asset",
                  "level": 0, "is_group": False},
            headers={"Authorization": f"Bearer {create_access_token(viewer)}"}
        )
        assert response.status_code == 403
```

### Pattern 3: Test Login/Logout Cycle

```python
class TestLoginLogoutPatterns:
    def test_complete_session_lifecycle(self, client: TestClient, create_user_helper):
        """ARRANGE: Create user
        ACT: Login, use token, logout
        ASSERT: All steps succeed
        """
        user = create_user_helper("lifecycle_user", "password123")
        
        # Step 1: Login
        login_response = client.post("/auth/login", json={"password": "password123"})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Step 2: Use token
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "lifecycle_user"
        
        # Step 3: Logout
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200
        
        # Step 4: Verify cookie cleared
        assert logout_response.cookies.get("access_token") is not None
    
    def test_multiple_users_logged_in(self, client: TestClient, admin_user, viewer_user):
        """ARRANGE: Multiple users
        ACT: Login each, use tokens independently
        ASSERT: Each user's token works independently
        """
        from app.security import create_access_token
        
        admin_token = create_access_token(admin_user)
        viewer_token = create_access_token(viewer_user)
        
        # Admin accesses /me
        admin_me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_me.json()["role"] == "admin"
        
        # Viewer accesses /me
        viewer_me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert viewer_me.json()["role"] == "viewer"
```

### Pattern 4: Test HTMX Requests

```python
class TestHTMXPatterns:
    def test_htmx_login_flow(self, client: TestClient, create_user_helper):
        """ARRANGE: User and HTMX headers
        ACT: Login with HTMX request
        ASSERT: Redirect header present
        """
        user = create_user_helper("htmx_user", "password")
        
        response = client.post(
            "/auth/login",
            json={"password": "password"},
            headers={"hx-request": "true"}
        )
        
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/dashboard"
    
    def test_htmx_vs_api_responses(self, client: TestClient, create_user_helper):
        """ARRANGE: User
        ACT: Login twice - once with HTMX, once without
        ASSERT: Different responses
        """
        user = create_user_helper("response_user", "password")
        
        # API request (no HTMX header)
        api_response = client.post(
            "/auth/login",
            json={"password": "password"}
        )
        assert "access_token" in api_response.json()
        assert "HX-Redirect" not in api_response.headers
        
        # HTMX request
        htmx_response = client.post(
            "/auth/login",
            json={"password": "password"},
            headers={"hx-request": "true"}
        )
        assert "HX-Redirect" in htmx_response.headers
        assert htmx_response.text == ""  # No body for redirect
```

---

## Edge Cases

### Edge Case 1: Invalid Credentials

```python
class TestInvalidCredentials:
    def test_wrong_password_rejected(self, client: TestClient, db_session):
        """ARRANGE: User with password 'correct'
        ACT: Login with 'wrong'
        ASSERT: 401 error
        """
        from app.utils.security import hash_password
        from app.models.user import User, UserRole
        
        user = User(
            username="edge_user1",
            password_hash=hash_password("correct"),
            role=UserRole.viewer
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post("/auth/login", json={"password": "wrong"})
        assert response.status_code == 401
    
    def test_empty_password_rejected(self, client: TestClient, db_session):
        """ARRANGE: User with actual password
        ACT: Login with empty string
        ASSERT: 401 error
        """
        from app.utils.security import hash_password
        from app.models.user import User, UserRole
        
        user = User(
            username="edge_user2",
            password_hash=hash_password("actual_password"),
            role=UserRole.viewer
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post("/auth/login", json={"password": ""})
        assert response.status_code == 401
    
    def test_missing_password_field(self, client: TestClient):
        """ARRANGE: Login request
        ACT: Missing password field
        ASSERT: 422 validation error
        """
        response = client.post("/auth/login", json={})
        assert response.status_code == 422
```

### Edge Case 2: Token Expiration

```python
class TestTokenExpiration:
    def test_expired_token_rejected(self, client: TestClient):
        """ARRANGE: Create expired token
        ACT: Use it on protected endpoint
        ASSERT: 401 error
        """
        from datetime import datetime, timedelta
        from app.security import SECRET, ALGORITHM
        import jwt
        
        past_exp = datetime.utcnow() - timedelta(hours=1)
        payload = {"sub": "test", "role": "viewer", "exp": past_exp}
        expired_token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
```

---

## Integration Examples

### Full Test Suite Example

```python
import pytest
from sqlmodel import Session, select
from fastapi.testclient import TestClient

class TestFullAuthFlow:
    """Integration test demonstrating complete auth flow"""
    
    def test_admin_workflow(self, client: TestClient, admin_auth_headers: dict):
        """ARRANGE: Admin user
        ACT: Complete workflow - login, create, read, update, delete
        ASSERT: All succeed
        """
        # 1. Check current user
        me_response = client.get("/auth/me", headers=admin_auth_headers)
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "admin"
        
        # 2. Create account
        create_response = client.post(
            "/accounts",
            json={
                "code": "901",
                "name": "Integration Test Account",
                "account_type": "asset",
                "level": 0,
                "is_group": False
            },
            headers=admin_auth_headers
        )
        assert create_response.status_code in [200, 201]
        account_id = create_response.json()["id"]
        
        # 3. Read account
        read_response = client.get(
            f"/accounts/{account_id}",
            headers=admin_auth_headers
        )
        assert read_response.status_code == 200
        
        # 4. Update account
        update_response = client.put(
            f"/accounts/{account_id}",
            json={"name": "Updated Name"},
            headers=admin_auth_headers
        )
        assert update_response.status_code in [200, 204]
        
        # 5. Delete account
        delete_response = client.delete(
            f"/accounts/{account_id}",
            headers=admin_auth_headers
        )
        assert delete_response.status_code in [200, 204]
    
    def test_viewer_limited_workflow(self, client: TestClient, viewer_auth_headers: dict):
        """ARRANGE: Viewer user
        ACT: Try to do actions
        ASSERT: Only read succeeds, write fails
        """
        # 1. Can read
        read_response = client.get("/accounts", headers=viewer_auth_headers)
        assert read_response.status_code == 200
        
        # 2. Cannot create
        create_response = client.post(
            "/accounts",
            json={
                "code": "902",
                "name": "Viewer Test",
                "account_type": "asset",
                "level": 0,
                "is_group": False
            },
            headers=viewer_auth_headers
        )
        assert create_response.status_code == 403
```

---

## Tips & Best Practices

1. **Use Fixtures**: Leverage pre-built fixtures to reduce boilerplate
2. **Follow AAA**: Always use Arrange-Act-Assert pattern
3. **Clear Names**: Test names should describe what they test
4. **DRY**: Create helper functions for repeated patterns
5. **Isolation**: Each test should be independent
6. **Coverage**: Test both success and failure cases
7. **Documentation**: Comment non-obvious test logic

---

**Ready to write amazing tests! 🎯**
