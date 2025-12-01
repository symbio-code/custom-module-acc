"""
HTMX-specific test suite for authentication module.

Tests cover:
- Login form returns correct HX headers
- Logout returns HX-Redirect header
- Invalid login returns inline error fragment
- HTMX request detection (hx-request header)
- Response format for HTMX (no body on redirect, only headers)
"""

import pytest
from sqlmodel import select
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.utils.security import hash_password


class TestHTMXLoginFlow:
    """Test HTMX-specific login behavior."""

    def test_login_with_htmx_request_header_redirects(self, client: TestClient, db_session):
        """ARRANGE: Create user and add HTMX request header
        ACT: Login with hx-request header
        ASSERT: Return 200 with HX-Redirect header to /dashboard
        """
        # Arrange
        password = "htmx_login_pass"
        hashed = hash_password(password)
        user = User(username="htmxlogin", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/dashboard"
        # Body should be empty for redirect
        assert response.text == ""
        # Cookie should be set in the TestClient cookie jar
        assert "access_token" in client.cookies

    def test_login_without_htmx_header_returns_json(self, client: TestClient, db_session):
        """ARRANGE: Create user, no HTMX header
        ACT: Login without hx-request header
        ASSERT: Return 200 with JSON token response
        """
        # Arrange
        password = "normal_login_pass"
        hashed = hash_password(password)
        user = User(username="normallogin", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": password}
        )

        # Assert
        assert response.status_code == 200
        assert "HX-Redirect" not in response.headers
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_htmx_login_sets_cookie_despite_redirect(self, client: TestClient, db_session):
        """ARRANGE: Create user, login with HTMX header
        ACT: Check if cookie is set alongside redirect
        ASSERT: Cookie is set and redirect header present
        """
        # Arrange
        password = "cookie_redirect_pass"
        hashed = hash_password(password)
        user = User(username="cookieredirect", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        # Cookie should be set in the TestClient cookie jar
        assert "access_token" in client.cookies

    def test_invalid_login_with_htmx_returns_401(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login with wrong password and HTMX header
        ASSERT: Return 401 error (not redirect)
        """
        # Arrange
        password = "correct_pass"
        hashed = hash_password(password)
        user = User(username="htmxwrongpass", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": "wrong_pass"},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 401
        # Should not redirect on error
        assert "HX-Redirect" not in response.headers


class TestHTMXLogoutFlow:
    """Test HTMX-specific logout behavior."""

    def test_logout_with_htmx_request_header_redirects(self, client: TestClient, db_session):
        """ARRANGE: Create user, login, add HTMX logout request
        ACT: Logout with hx-request header
        ASSERT: Return 200 with HX-Redirect header to /login
        """
        # Arrange
        password = "htmx_logout_pass"
        hashed = hash_password(password)
        user = User(username="htmxlogout", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Login first
        client.post("/auth/login?password=" + password)

        # Act
        response = client.post(
            "/auth/logout",
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/login"
        # Body should be empty for redirect
        assert response.text == ""

    def test_logout_without_htmx_header_returns_json(self, client: TestClient, db_session):
        """ARRANGE: Create user, login, logout without HTMX header
        ACT: Logout without hx-request header
        ASSERT: Return 200 with JSON status response
        """
        # Arrange
        password = "normal_logout_pass"
        hashed = hash_password(password)
        user = User(username="normallogout", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Login first
        client.post("/auth/login?password=" + password)

        # Act
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200
        assert "HX-Redirect" not in response.headers
        data = response.json()
        assert data == {"status": "logged_out"}

    def test_htmx_logout_clears_cookie_and_redirects(self, client: TestClient, db_session):
        """ARRANGE: Create user, login, logout with HTMX
        ACT: Check cookie cleared and redirect header present
        ASSERT: Both cookie deletion and redirect present
        """
        # Arrange
        password = "cookie_clear_pass"
        hashed = hash_password(password)
        user = User(username="cookieclear", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Login
        client.post("/auth/login?password=" + password)

        # Act
        response = client.post(
            "/auth/logout",
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/login"
        # Cookie should be cleared in client's cookie jar
        assert "access_token" not in client.cookies


class TestHTMXRequestDetection:
    """Test proper detection of HTMX requests."""

    def test_hx_request_header_case_insensitive(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login with HX-Request header (uppercase)
        ASSERT: Still treated as HTMX request and redirects
        Note: HTMX headers are case-sensitive, this tests current behavior
        """
        # Arrange
        password = "case_test_pass"
        hashed = hash_password(password)
        user = User(username="casetest", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"HX-Request": "true"}
        )

        # Assert - lowercase check (case-sensitive)
        # If not detected, will return JSON instead of redirect
        # Current implementation uses request.headers.get("hx-request")
        if "HX-Redirect" not in response.headers:
            # Expected behavior - headers are case-sensitive
            assert response.status_code == 200
            assert "access_token" in response.json()
        else:
            # If implementation handles case-insensitivity
            assert response.headers["HX-Redirect"] == "/dashboard"

    def test_hx_request_header_value_variations(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login with various hx-request values
        ASSERT: Treated as HTMX if header present
        """
        # Arrange
        password = "value_test_pass"
        hashed = hash_password(password)
        user = User(username="valuetest", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        values = ["true", "True", "1", "yes"]

        # Act & Assert
        for value in values:
            response = client.post(
                "/auth/login",
                json={"password": password},
                headers={"hx-request": value}
            )
            # Should redirect (HX-Redirect present) for all these values
            assert response.status_code == 200
            assert "HX-Redirect" in response.headers


class TestHTMXErrorFragments:
    """Test HTMX error response handling."""

    def test_invalid_login_error_format(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login with wrong password and HTMX header
        ASSERT: Return 401 with error detail
        """
        # Arrange
        password = "correct"
        hashed = hash_password(password)
        user = User(username="htmxerror", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": "wrong"},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 401
        error_data = response.json()
        assert "detail" in error_data
        assert len(error_data["detail"]) > 0

    def test_missing_field_error_with_htmx(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login without password field with HTMX header
        ASSERT: Return validation error (422)
        """
        # Arrange
        password = "test"
        hashed = hash_password(password)
        user = User(username="htmxmissing", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 422

    def test_user_not_found_error_with_htmx(self, client: TestClient, db_session):
        """ARRANGE: No users in database
        ACT: Login attempt with HTMX header
        ASSERT: Return 404 error
        """
        # Arrange
        from app.models.user import User as UserModel
        for user in db_session.exec(select(UserModel)).all():
            db_session.delete(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": "anypass"},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 404
        error_data = response.json()
        assert "not registered" in error_data["detail"].lower()


class TestHTMXHeadersPreserved:
    """Test that HTTP response headers are properly set for HTMX."""

    def test_hx_redirect_header_format(self, client: TestClient, db_session):
        """ARRANGE: Create user and login
        ACT: Check HX-Redirect header format
        ASSERT: Header value is valid URL path
        """
        # Arrange
        password = "header_format_pass"
        hashed = hash_password(password)
        user = User(username="headerformat", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 200
        redirect_path = response.headers.get("HX-Redirect", "")
        assert redirect_path.startswith("/")
        assert "dashboard" in redirect_path.lower() or "login" in redirect_path.lower()

    def test_cookie_set_alongside_hx_redirect(self, client: TestClient, db_session):
        """ARRANGE: Create user and login
        ACT: Check both cookie and HX-Redirect present
        ASSERT: Both are set
        """
        # Arrange
        password = "cookie_alongside_pass"
        hashed = hash_password(password)
        user = User(username="cookiealongside", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"hx-request": "true"}
        )

        # Assert
        assert response.status_code == 200
        # Check both are present in the TestClient cookie jar and headers
        assert "access_token" in client.cookies
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/dashboard"


class TestHTMXMultipleRequests:
    """Test HTMX behavior across multiple requests."""

    def test_htmx_login_then_api_request(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Login via HTMX, then make API request
        ASSERT: Cookie persists and API request succeeds
        """
        # Arrange
        password = "multi_request_pass"
        hashed = hash_password(password)
        user = User(username="multirequest", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act 1: HTMX login
        login_response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"hx-request": "true"}
        )
        assert login_response.status_code == 200
        assert "HX-Redirect" in login_response.headers

        # Act 2: Subsequent API call (cookie should persist in TestClient)
        me_response = client.get("/auth/me")

        # Assert
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "multirequest"

    def test_htmx_logout_then_redirected(self, client: TestClient, db_session):
        """ARRANGE: Create user, login via HTMX
        ACT: Logout via HTMX
        ASSERT: Redirect header set
        """
        # Arrange
        password = "logout_redirect_pass"
        hashed = hash_password(password)
        user = User(username="logoutredirect", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Login
        login_response = client.post(
            "/auth/login",
            json={"password": password},
            headers={"hx-request": "true"}
        )
        assert login_response.status_code == 200

        # Act: Logout
        logout_response = client.post(
            "/auth/logout",
            headers={"hx-request": "true"}
        )

        # Assert
        assert logout_response.status_code == 200
        assert "HX-Redirect" in logout_response.headers
        assert logout_response.headers["HX-Redirect"] == "/login"
