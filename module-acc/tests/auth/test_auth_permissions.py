"""
Comprehensive RBAC (Role-Based Access Control) test suite for authentication module.

Tests cover:
- Admin permissions: can create, read, update, delete accounts and journals
- Accountant permissions: can create and read, cannot delete
- Viewer permissions: can only read, cannot create/update/delete
- Role-based endpoint access
- Protected route enforcement by role
"""

import pytest
from sqlmodel import select
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.models.account import Account
from app.utils.security import hash_password
from app.security import create_access_token


class TestAdminPermissions:
    """Test admin role can perform all actions."""

    def test_admin_can_create_account(self, client: TestClient, db_session):
        """ARRANGE: Admin user logged in
        ACT: Create new account via POST /accounts/new
        ASSERT: Account created successfully (200 or 201)
        """
        # Arrange
        password = "admin_create_pass"
        hashed = hash_password(password)
        user = User(username="admin_create", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        account_data = {
            "code": "110",
            "name": "Savings Account",
            "account_type": "asset",
            "level": 1,
            "is_group": False,
            "is_active": True
        }

        # Act
        response = client.post(
            "/accounts",
            json=account_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 201]

    def test_admin_can_update_account(self, client: TestClient, db_session):
        """ARRANGE: Admin user and existing account
        ACT: Update account via PUT /accounts/{id}
        ASSERT: Account updated successfully
        """
        # Arrange
        password = "admin_update_pass"
        hashed = hash_password(password)
        user = User(username="admin_update", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)

        account = Account(
            code="120",
            name="Old Name",
            account_type="asset",
            level=1,
            is_group=False
        )
        db_session.add(account)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.put(
            f"/accounts/{account.id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 204]

    def test_admin_can_delete_account(self, client: TestClient, db_session):
        """ARRANGE: Admin user and existing account
        ACT: Delete account via DELETE /accounts/{id}
        ASSERT: Account deleted successfully
        """
        # Arrange
        password = "admin_delete_pass"
        hashed = hash_password(password)
        user = User(username="admin_delete", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)

        account = Account(
            code="130",
            name="To Delete",
            account_type="asset",
            level=1,
            is_group=False
        )
        db_session.add(account)
        db_session.commit()
        account_id = account.id

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.delete(
            f"/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 204]

    def test_admin_can_read_accounts(self, client: TestClient, db_session):
        """ARRANGE: Admin user and existing accounts
        ACT: Read accounts via GET /accounts
        ASSERT: Accounts list returned
        """
        # Arrange
        password = "admin_read_pass"
        hashed = hash_password(password)
        user = User(username="admin_read", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.get(
            "/accounts",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200


class TestAccountantPermissions:
    """Test accountant role can create/read but not delete."""

    def test_accountant_can_create_account(self, client: TestClient, db_session):
        """ARRANGE: Accountant user logged in
        ACT: Create new account
        ASSERT: Account created successfully
        """
        # Arrange
        password = "acct_create_pass"
        hashed = hash_password(password)
        user = User(username="acct_create", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        account_data = {
            "code": "140",
            "name": "Accountant Created Account",
            "account_type": "asset",
            "level": 1,
            "is_group": False,
            "is_active": True
        }

        # Act
        response = client.post(
            "/accounts",
            json=account_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 201]

    def test_accountant_can_update_account(self, client: TestClient, db_session):
        """ARRANGE: Accountant user and existing account
        ACT: Update account
        ASSERT: Account updated successfully
        """
        # Arrange
        password = "acct_update_pass"
        hashed = hash_password(password)
        user = User(username="acct_update", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)

        account = Account(
            code="150",
            name="Acct Update Test",
            account_type="asset",
            level=1,
            is_group=False
        )
        db_session.add(account)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.put(
            f"/accounts/{account.id}",
            json={"name": "Updated by Accountant"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 204]

    def test_accountant_cannot_delete_account(self, client: TestClient, db_session):
        """ARRANGE: Accountant user and existing account
        ACT: Attempt to delete account
        ASSERT: Return 403 Insufficient privileges
        """
        # Arrange
        password = "acct_delete_pass"
        hashed = hash_password(password)
        user = User(username="acct_delete", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)

        account = Account(
            code="160",
            name="Cannot Delete",
            account_type="asset",
            level=1,
            is_group=False
        )
        db_session.add(account)
        db_session.commit()
        account_id = account.id

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.delete(
            f"/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403

    def test_accountant_can_read_accounts(self, client: TestClient, db_session):
        """ARRANGE: Accountant user
        ACT: Read accounts
        ASSERT: Accounts list returned
        """
        # Arrange
        password = "acct_read_pass"
        hashed = hash_password(password)
        user = User(username="acct_read", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.get(
            "/accounts",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200


class TestViewerPermissions:
    """Test viewer role can only read."""

    def test_viewer_cannot_create_account(self, client: TestClient, db_session):
        """ARRANGE: Viewer user
        ACT: Attempt to create account
        ASSERT: Return 403 Insufficient privileges
        """
        # Arrange
        password = "viewer_create_pass"
        hashed = hash_password(password)
        user = User(username="viewer_create", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        account_data = {
            "code": "170",
            "name": "Viewer Try Create",
            "account_type": "asset",
            "level": 1,
            "is_group": False,
            "is_active": True
        }

        # Act
        response = client.post(
            "/accounts",
            json=account_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403

    def test_viewer_cannot_update_account(self, client: TestClient, db_session):
        """ARRANGE: Viewer user and existing account
        ACT: Attempt to update account
        ASSERT: Return 403 Insufficient privileges
        """
        # Arrange
        password = "viewer_update_pass"
        hashed = hash_password(password)
        user = User(username="viewer_update", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)

        account = Account(
            code="180",
            name="Viewer Update Test",
            account_type="asset",
            level=1,
            is_group=False
        )
        db_session.add(account)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.put(
            f"/accounts/{account.id}",
            json={"name": "Viewer Try Update"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403

    def test_viewer_cannot_delete_account(self, client: TestClient, db_session):
        """ARRANGE: Viewer user and existing account
        ACT: Attempt to delete account
        ASSERT: Return 403 Insufficient privileges
        """
        # Arrange
        password = "viewer_delete_pass"
        hashed = hash_password(password)
        user = User(username="viewer_delete", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)

        account = Account(
            code="190",
            name="Viewer Cannot Delete",
            account_type="asset",
            level=1,
            is_group=False
        )
        db_session.add(account)
        db_session.commit()
        account_id = account.id

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.delete(
            f"/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403

    def test_viewer_can_read_accounts(self, client: TestClient, db_session):
        """ARRANGE: Viewer user
        ACT: Read accounts
        ASSERT: Accounts list returned
        """
        # Arrange
        password = "viewer_read_pass"
        hashed = hash_password(password)
        user = User(username="viewer_read", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        # Act
        response = client.get(
            "/accounts",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 200


class TestJournalRBAC:
    """Test RBAC for journal endpoints."""

    def test_admin_can_create_journal(self, client: TestClient, db_session):
        """ARRANGE: Admin user
        ACT: Create journal entry
        ASSERT: Journal created successfully
        """
        # Arrange
        password = "admin_journal_create"
        hashed = hash_password(password)
        user = User(username="admin_jcreate", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        journal_data = {
            "entry": {
                "date": "2025-11-28",
                "description": "Admin Journal Entry",
            },
            "lines": [
                {"account_code": "100", "debit": 100.0, "credit": 0.0},
                {"account_code": "200", "debit": 0.0, "credit": 100.0},
            ]
        }

        # Act
        response = client.post(
            "/journal/",
            json=journal_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 201]

    def test_accountant_can_create_journal(self, client: TestClient, db_session):
        """ARRANGE: Accountant user
        ACT: Create journal entry
        ASSERT: Journal created successfully
        """
        # Arrange
        password = "acct_journal_create"
        hashed = hash_password(password)
        user = User(username="acct_jcreate", password_hash=hashed, role=UserRole.accountant)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        journal_data = {
            "entry": {
                "date": "2025-11-28",
                "description": "Accountant Journal Entry",
            },
            "lines": [
                {"account_code": "100", "debit": 50.0, "credit": 0.0},
                {"account_code": "200", "debit": 0.0, "credit": 50.0},
            ]
        }

        # Act
        response = client.post(
            "/journal/",
            json=journal_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code in [200, 201]

    def test_viewer_cannot_create_journal(self, client: TestClient, db_session):
        """ARRANGE: Viewer user
        ACT: Attempt to create journal entry
        ASSERT: Return 403 Insufficient privileges
        """
        # Arrange
        password = "viewer_journal_create"
        hashed = hash_password(password)
        user = User(username="viewer_jcreate", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        journal_data = {
            "entry": {
                "date": "2025-11-28",
                "description": "Viewer Try Journal",
            },
            "lines": [
                {"account_code": "100", "debit": 20.0, "credit": 0.0},
                {"account_code": "200", "debit": 0.0, "credit": 20.0},
            ]
        }

        # Act
        response = client.post(
            "/journal/",
            json=journal_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403


class TestRoleHierarchy:
    """Test role hierarchy and access control edge cases."""

    def test_admin_always_has_access(self, client: TestClient, db_session):
        """ARRANGE: Admin user
        ACT: Access multiple protected endpoints
        ASSERT: All return 200 (not 403)
        """
        # Arrange
        password = "admin_hierarchy"
        hashed = hash_password(password)
        user = User(username="admin_hier", password_hash=hashed, role=UserRole.admin)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        endpoints = ["/accounts", "/journal"]

        # Act & Assert
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code != 403, f"Admin blocked at {endpoint}"

    def test_incorrect_role_denied_access(self, client: TestClient, db_session):
        """ARRANGE: Create user with viewer role
        ACT: Call endpoint requiring admin/accountant
        ASSERT: Return 403 Insufficient privileges
        """
        # Arrange
        password = "viewer_denied"
        hashed = hash_password(password)
        user = User(username="viewer_denied", password_hash=hashed, role=UserRole.viewer)
        db_session.add(user)
        db_session.commit()

        login_response = client.post("/auth/login?password=" + password)
        token = login_response.json()["access_token"]

        account_data = {
            "code": "200",
            "name": "Should Fail",
            "account_type": "asset",
            "level": 1,
            "is_group": False,
            "is_active": True
        }

        # Act
        response = client.post(
            "/accounts",
            json=account_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == 403

    def test_no_token_returns_401_not_403(self, client: TestClient):
        """ARRANGE: No authentication
        ACT: Call protected endpoint without token
        ASSERT: Return 401 (not 403)
        """
        # Act
        response = client.get("/accounts")

        # Assert
        assert response.status_code == 401

    def test_invalid_token_returns_401_not_403(self, client: TestClient):
        """ARRANGE: Invalid token
        ACT: Call protected endpoint with invalid token
        ASSERT: Return 401 (not 403)
        """
        # Act
        response = client.get(
            "/accounts",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        # Assert
        assert response.status_code == 401
