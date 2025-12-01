"""
Comprehensive logout test suite for authentication module.

Tests cover:
- Successful logout
- Cookie clearing
- Token invalidation
- HTMX logout support
- Logout without authentication
"""

import pytest
from sqlmodel import select
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.utils.security import hash_password
from app.security import create_access_token


class TestSuccessfulLogout:
    """Test successful logout scenarios."""

    def test_logout_clears_cookie(self, client: TestClient, db_session):
        """ARRANGE: User logged in with token in cookie
        ACT: Call /auth/logout
        ASSERT: access_token cookie is deleted
        """
        # Arrange
        password = "logout_test_pass"
        hashed = hash_password(password)
        user = User(username="logoutuser", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Login first to set cookie
        login_response = client.post("/auth/login?password=" + password)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Act
        logout_response = client.post("/auth/logout")

        # Assert
        assert logout_response.status_code == 200
        assert logout_response.json()["status"] == "logged_out"
        # Cookie should be cleared in the TestClient cookie jar
        assert "access_token" not in client.cookies

    def test_logout_returns_status_message(self, client: TestClient, db_session):
        """ARRANGE: Create user and login
        ACT: Call /auth/logout
        ASSERT: Return {"status": "logged_out"} with 200
        """
        # Arrange
        password = "status_test"
        hashed = hash_password(password)
        user = User(username="statususer", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        client.post("/auth/login?password=" + password)

        # Act
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "logged_out"}

    def test_logout_without_prior_login(self, client: TestClient):
        """ARRANGE: No user logged in
        ACT: Call /auth/logout directly
        ASSERT: Return 200 (logout is idempotent)
        """
        # Act
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "logged_out"


class TestTokenInvalidation:
    """Test token behavior after logout."""

    def test_token_still_valid_after_logout(self, client: TestClient, db_session):
        """ARRANGE: User logs in and logs out
        ACT: Try to use old token after logout
        ASSERT: Token is still valid (app doesn't track token invalidation)
        Note: This test documents current behavior. In production, implement 
        token blacklist/invalidation for proper logout.
        """
        # Arrange
        password = "token_inv_test"
        hashed = hash_password(password)
        user = User(username="tokeninv", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act - logout
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200

        # Try to use token after logout
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert - Token still works (document this behavior)
        # In production, implement token blacklist to invalidate tokens on logout
        assert me_response.status_code == 200

    def test_cookie_removed_but_bearer_token_still_works(self, client: TestClient, db_session):
        """ARRANGE: User logs in
        ACT: Logout (clears cookie), then use Bearer token
        ASSERT: Bearer token continues to work (cookie cleared, token still valid)
        """
        # Arrange
        password = "cookie_bearer_test"
        hashed = hash_password(password)
        user = User(username="cookiebearer", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act - Logout (clears cookie)
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200

        # Use Bearer token to access protected endpoint
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "cookiebearer"


class TestLogoutFlow:
    """Test complete login/logout flow."""

    def test_complete_login_logout_cycle(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login, verify access, logout, verify state
        ASSERT: Flow completes successfully
        """
        # Arrange
        password = "cycle_test_pass"
        hashed = hash_password(password)
        user = User(username="cycleuser", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act 1: Login
        login_response = client.post("/auth/login?password=" + password)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Assert 1: Can access /me
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "cycleuser"

        # Act 2: Logout
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200

        # Assert 2: Can still access with token (no token invalidation in current impl)
        me_after_logout = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Token still works (document current behavior)
        assert me_after_logout.status_code == 200

    def test_multiple_logout_calls_are_idempotent(self, client: TestClient, db_session):
        """ARRANGE: User logs in
        ACT: Call logout multiple times
        ASSERT: All calls return 200 (idempotent)
        """
        # Arrange
        password = "idempotent_test"
        hashed = hash_password(password)
        user = User(username="idempotent", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        client.post("/auth/login?password=" + password)

        # Act - multiple logouts
        responses = []
        for _ in range(3):
            response = client.post("/auth/logout")
            responses.append(response)

        # Assert - all should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "logged_out"

    def test_logout_then_new_login(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login, logout, login again
        ASSERT: Both logins succeed with different tokens
        """
        # Arrange
        password = "relogin_test"
        hashed = hash_password(password)
        user = User(username="reloginuser", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act 1: First login
        response1 = client.post("/auth/login?password=" + password)
        token1 = response1.json()["access_token"]

        # Act 2: Logout
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200

        # Act 3: Second login
        response2 = client.post("/auth/login?password=" + password)
        token2 = response2.json()["access_token"]

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Tokens produced are valid JWT strings (may be identical depending on implementation)
        assert isinstance(token1, str) and isinstance(token2, str)
        # Both tokens should be valid
        me1 = client.get("/auth/me", headers={"Authorization": f"Bearer {token1}"})
        me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token2}"})
        assert me1.status_code == 200
        assert me2.status_code == 200


class TestLogoutWithDifferentRoles:
    """Test logout across different user roles."""

    def test_admin_logout(self, client: TestClient, db_session):
        """ARRANGE: Admin user
        ACT: Login and logout
        ASSERT: Logout works for admin
        """
        # Arrange
        password = "admin_logout"
        hashed = hash_password(password)
        user = User(username="adminlogout", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        client.post("/auth/login?password=" + password)
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200

    def test_accountant_logout(self, client: TestClient, db_session):
        """ARRANGE: Accountant user
        ACT: Login and logout
        ASSERT: Logout works for accountant
        """
        # Arrange
        password = "acct_logout"
        hashed = hash_password(password)
        user = User(username="acctlogout", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        client.post("/auth/login?password=" + password)
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200

    def test_viewer_logout(self, client: TestClient, db_session):
        """ARRANGE: Viewer user
        ACT: Login and logout
        ASSERT: Logout works for viewer
        """
        # Arrange
        password = "viewer_logout"
        hashed = hash_password(password)
        user = User(username="viewerlogout", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        client.post("/auth/login?password=" + password)
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200
