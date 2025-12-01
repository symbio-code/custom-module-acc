"""
Comprehensive login test suite for authentication module.

Tests cover:
- Valid login with correct credentials
- Invalid login with wrong password
- Login with missing fields
- Password hashing verification
- JWT token validation and expiration
- Protected route access
"""

import pytest
import jwt
import os
from datetime import datetime, timedelta
from sqlmodel import select
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.utils.security import hash_password, verify_password
from app.security import create_access_token, decode_token


class TestValidLogin:
    """Test successful login scenarios."""

    def test_login_with_correct_password(self, client: TestClient, db_session):
        """ARRANGE: Create user with known password
        ACT: Login with correct password
        ASSERT: Return 200 with access_token
        """
        # Arrange
        password = "correct_password_123"
        hashed = hash_password(password)
        user = User(username="testuser", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + password)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_sets_httponly_cookie(self, client: TestClient, db_session):
        """ARRANGE: Create user with known password
        ACT: Login with correct password
        ASSERT: Response includes httponly access_token cookie
        """
        # Arrange
        password = "secure_pass_456"
        hashed = hash_password(password)
        user = User(username="cookieuser", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + password)

        # Assert
        assert response.status_code == 200
        cookies = response.cookies
        assert "access_token" in cookies
        # TestClient automatically handles cookies, verify it was set
        assert cookies["access_token"] is not None

    def test_token_contains_user_info(self, client: TestClient, db_session):
        """ARRANGE: Create user with specific role
        ACT: Login and decode the JWT token
        ASSERT: Token contains correct username and role
        """
        # Arrange
        password = "token_test_789"
        hashed = hash_password(password)
        user = User(username="roleuser", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + password)
        token = response.json()["access_token"]

        # Assert
        payload = decode_token(token)
        assert payload["sub"] == "roleuser"
        assert payload["role"] == "viewer"
        assert "exp" in payload

    def test_token_expiration_claim(self, client: TestClient, db_session):
        """ARRANGE: Create user and login
        ACT: Decode token and check expiration
        ASSERT: Token has valid exp claim within 12 hours
        """
        # Arrange
        password = "exp_test_pass"
        hashed = hash_password(password)
        user = User(username="expuser", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + password)
        token = response.json()["access_token"]
        payload = decode_token(token)

        # Assert
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = exp_time - now
        # Token should expire in approximately 12 hours (with 1 hour buffer for test execution)
        assert 11 * 3600 < time_diff.total_seconds() < 13 * 3600


class TestInvalidLogin:
    """Test failed login scenarios."""

    def test_login_with_wrong_password(self, client: TestClient, db_session):
        """ARRANGE: Create user with password 'correct'
        ACT: Login with password 'wrong'
        ASSERT: Return 401 unauthorized
        """
        # Arrange
        correct_password = "correct_password"
        hashed = hash_password(correct_password)
        user = User(username="wrongpass", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + "wrong_password")

        # Assert
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "password" in response.json()["detail"].lower()

    def test_login_with_no_user_in_db(self, client: TestClient, db_session):
        """ARRANGE: Delete all users from database
        ACT: Attempt login
        ASSERT: Return 404 user not registered
        """
        # Arrange - ensure no users exist
        from app.database import get_session
        for user in db_session.exec(select(User)).all():
            db_session.delete(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + "anypass")

        # Assert
        assert response.status_code == 404
        assert "not registered" in response.json()["detail"].lower()

    def test_login_multiple_attempts_different_passwords(self, client: TestClient, db_session):
        """ARRANGE: Create user
        ACT: Attempt login with multiple wrong passwords
        ASSERT: All attempts fail with 401
        """
        # Arrange
        password = "correct_one"
        hashed = hash_password(password)
        user = User(username="multitest", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        wrong_passwords = ["wrong1", "wrong2", "wrong3", "wrong4"]

        # Act & Assert
        for wrong_pass in wrong_passwords:
            response = client.post("/auth/login?password=" + wrong_pass)
            assert response.status_code == 401


class TestLoginMissingFields:
    """Test login validation with missing or incomplete data."""

    def test_login_missing_password_field(self, client: TestClient, db_session):
        """ARRANGE: User exists in database
        ACT: Send login request without password field
        ASSERT: Return validation error
        """
        # Arrange
        password = "test_pass"
        hashed = hash_password(password)
        user = User(username="nopass", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login", json={})

        # Assert
        assert response.status_code == 422  # Validation error

    def test_login_with_null_password(self, client: TestClient, db_session):
        """ARRANGE: User exists
        ACT: Send null/None password
        ASSERT: Return validation error
        """
        # Arrange
        password = "test_pass"
        hashed = hash_password(password)
        user = User(username="nullpass", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        # Act
        # No password parameter at all -> validation error
        response = client.post("/auth/login")

        # Assert
        assert response.status_code == 422

    def test_login_with_empty_password(self, client: TestClient, db_session):
        """ARRANGE: User exists
        ACT: Send empty string password
        ASSERT: Return 401 invalid password
        """
        # Arrange
        password = "actualpass"
        hashed = hash_password(password)
        user = User(username="emptypass", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        # Act
        response = client.post("/auth/login?password=" + "")

        # Assert
        assert response.status_code == 401


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hashing_creates_different_hashes(self):
        """ARRANGE: Same password
        ACT: Hash it twice
        ASSERT: Resulting hashes are different (bcrypt uses random salt)
        """
        # Arrange
        password = "same_password_123"

        # Act
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Assert
        assert hash1 != hash2
        assert len(hash1) > 0
        assert len(hash2) > 0

    def test_password_verification_succeeds(self):
        """ARRANGE: Password and its hash
        ACT: Verify password against hash
        ASSERT: Verification succeeds
        """
        # Arrange
        password = "verify_me_456"
        hashed = hash_password(password)

        # Act
        is_valid = verify_password(password, hashed)

        # Assert
        assert is_valid is True

    def test_password_verification_fails_wrong_password(self):
        """ARRANGE: Password and hash of different password
        ACT: Verify wrong password against hash
        ASSERT: Verification fails
        """
        # Arrange
        password = "correct_pass"
        wrong_password = "wrong_pass"
        hashed = hash_password(password)

        # Act
        is_valid = verify_password(wrong_password, hashed)

        # Assert
        assert is_valid is False

    def test_hash_stored_in_database(self, db_session):
        """ARRANGE: Create user with hashed password
        ACT: Retrieve from database
        ASSERT: Stored hash matches and is not plaintext
        """
        # Arrange
        password = "db_test_pass"
        hashed = hash_password(password)
        user = User(username="hashtest", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        # Act
        retrieved_user = db_session.exec(select(User).where(User.username == "hashtest")).first()

        # Assert
        assert retrieved_user is not None
        assert retrieved_user.password_hash == hashed
        assert retrieved_user.password_hash != password
        assert verify_password(password, retrieved_user.password_hash)


class TestTokenValidation:
    """Test JWT token validation and decoding."""

    def test_decode_valid_token(self, client: TestClient, db_session):
        """ARRANGE: Create user and login
        ACT: Decode the returned token
        ASSERT: Token decodes successfully with correct claims
        """
        # Arrange
        password = "valid_token_test"
        hashed = hash_password(password)
        user = User(username="tokenuser", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        response = client.post("/auth/login?password=" + password)
        token = response.json()["access_token"]

        # Act
        payload = decode_token(token)

        # Assert
        assert payload["sub"] == "tokenuser"
        assert payload["role"] == "accountant"
        assert "exp" in payload

    def test_decode_expired_token_raises_error(self):
        """ARRANGE: Create token with past expiration
        ACT: Attempt to decode expired token
        ASSERT: Raises HTTPException 401 Token expired
        """
        # Arrange
        from app.security import SECRET, ALGORITHM
        past_exp = datetime.utcnow() - timedelta(hours=1)
        payload = {"sub": "testuser", "role": "admin", "exp": past_exp}
        expired_token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

        # Act & Assert
        with pytest.raises(Exception):  # HTTPException
            decode_token(expired_token)

    def test_decode_invalid_token_format(self):
        """ARRANGE: Malformed token string
        ACT: Attempt to decode
        ASSERT: Raises HTTPException 401 Invalid token
        """
        # Arrange
        invalid_token = "not.a.valid.jwt.token"

        # Act & Assert
        with pytest.raises(Exception):  # HTTPException
            decode_token(invalid_token)

    def test_decode_empty_token(self):
        """ARRANGE: Empty token string
        ACT: Attempt to decode
        ASSERT: Raises HTTPException 401 Invalid token
        """
        # Arrange
        empty_token = ""

        # Act & Assert
        with pytest.raises(Exception):  # HTTPException
            decode_token(empty_token)

    def test_token_with_wrong_secret(self):
        """ARRANGE: Create token with different secret
        ACT: Attempt to decode with app secret
        ASSERT: Raises HTTPException 401 Invalid token
        """
        # Arrange
        from app.security import ALGORITHM
        wrong_secret = "wrong_secret_key_xyz"
        exp = datetime.utcnow() + timedelta(hours=12)
        payload = {"sub": "testuser", "role": "admin", "exp": exp}
        wrong_token = jwt.encode(payload, wrong_secret, algorithm=ALGORITHM)

        # Act & Assert
        with pytest.raises(Exception):  # HTTPException
            decode_token(wrong_token)


class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    def test_me_endpoint_requires_authentication(self, client: TestClient):
        """ARRANGE: No authentication
        ACT: Call /auth/me without token
        ASSERT: Return 401 unauthorized
        """
        # Act
        response = client.get("/auth/me")

        # Assert
        assert response.status_code == 401
        assert "token" in response.json()["detail"].lower()

    def test_me_endpoint_with_valid_token(self, client: TestClient, db_session):
        """ARRANGE: Create user and obtain token
        ACT: Call /auth/me with valid token
        ASSERT: Return user info with 200
        """
        # Arrange
        password = "me_test_pass"
        hashed = hash_password(password)
        user = User(username="me_user", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        response = client.post("/auth/login?password=" + password)
        token = response.json()["access_token"]

        # Act
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "me_user"
        assert data["role"] == "viewer"

    def test_me_endpoint_with_expired_token(self, client: TestClient):
        """ARRANGE: Create expired token
        ACT: Call /auth/me with expired token
        ASSERT: Return 401 token expired
        """
        # Arrange
        from app.security import SECRET, ALGORITHM
        past_exp = datetime.utcnow() - timedelta(hours=1)
        payload = {"sub": "testuser", "role": "admin", "exp": past_exp}
        expired_token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

        # Act
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        # Assert
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_me_endpoint_returns_correct_role(self, client: TestClient, db_session):
        """ARRANGE: Create admin user and login
        ACT: Call /auth/me
        ASSERT: Returns admin role
        """
        # Arrange
        password = "admin_role_pass"
        hashed = hash_password(password)
        user = User(username="admin_me", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        response = client.post("/auth/login?password=" + password)
        token = response.json()["access_token"]

        # Act
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["role"] == "admin"
