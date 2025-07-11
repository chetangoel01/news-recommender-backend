import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

pytestmark = pytest.mark.auth


class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_user_success(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test successful user registration."""
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check response structure
        assert "user_id" in data
        assert "email" in data
        assert "username" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data
        
        # Check response values
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["expires_in"] == 3600  # 1 hour in seconds
        assert len(data["access_token"]) > 20
        assert len(data["refresh_token"]) > 20

    def test_register_duplicate_email(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test registration with duplicate email."""
        # Register first user
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        
        # Try to register with same email but different username
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "differentuser"
        
        response = client.post("/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "email" in response.text.lower()

    def test_register_duplicate_username(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test registration with duplicate username."""
        # Register first user
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        
        # Try to register with same username but different email
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        
        response = client.post("/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "username" in response.text.lower()

    def test_register_invalid_email(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test registration with invalid email."""
        invalid_data = test_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test registration with short password."""
        invalid_data = test_user_data.copy()
        invalid_data["password"] = "short"
        
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422

    def test_register_short_username(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test registration with short username."""
        invalid_data = test_user_data.copy()
        invalid_data["username"] = "ab"
        
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422

    def test_register_missing_fields(self, client: TestClient):
        """Test registration with missing required fields."""
        incomplete_data = {
            "email": "test@example.com"
            # Missing password, username, display_name
        }
        
        response = client.post("/auth/register", json=incomplete_data)
        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test successful user login."""
        # First register the user
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 201
        
        # Now login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check response structure
        assert "user_id" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data
        assert "user_profile" in data
        
        # Check user profile structure
        profile = data["user_profile"]
        assert "username" in profile
        assert "display_name" in profile
        assert profile["username"] == test_user_data["username"]
        assert profile["display_name"] == test_user_data["display_name"]
        
        # Check token values
        assert data["expires_in"] == 3600
        assert len(data["access_token"]) > 20
        assert len(data["refresh_token"]) > 20

    def test_login_invalid_email(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test login with invalid email."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": test_user_data["password"]
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "incorrect" in response.text.lower()

    def test_login_invalid_password(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test login with invalid password."""
        # First register the user
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 201
        
        # Try login with wrong password
        login_data = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "incorrect" in response.text.lower()

    def test_login_invalid_email_format(self, client: TestClient):
        """Test login with invalid email format."""
        login_data = {
            "email": "invalid-email",
            "password": "somepassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 422

    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing fields."""
        # Missing password
        login_data = {
            "email": "test@example.com"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 422


class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test successful token refresh."""
        # Register and get initial tokens
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 201
        
        initial_data = register_response.json()
        refresh_token = initial_data["refresh_token"]
        
        # Refresh the token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "access_token" in data
        assert "expires_in" in data
        
        # Check values
        assert data["expires_in"] == 3600
        assert len(data["access_token"]) > 20
        
        # Access token should be valid JWT format (contains 3 parts separated by dots)
        assert len(data["access_token"].split(".")) == 3

    def test_refresh_invalid_token(self, client: TestClient):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        assert "invalid" in response.text.lower()

    def test_refresh_missing_token(self, client: TestClient):
        """Test refresh with missing token."""
        response = client.post("/auth/refresh", json={})
        assert response.status_code == 422

    def test_refresh_access_token_as_refresh(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test using access token as refresh token (should fail)."""
        # Register and get tokens
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 201
        
        initial_data = register_response.json()
        access_token = initial_data["access_token"]
        
        # Try to use access token as refresh token
        refresh_data = {"refresh_token": access_token}
        response = client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401


class TestAuthenticationFlow:
    """Test complete authentication flow scenarios."""

    def test_complete_auth_flow(self, client: TestClient, test_user_data: Dict[str, Any]):
        """Test complete authentication flow: register -> login -> refresh."""
        # 1. Register
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 201
        register_data = register_response.json()
        
        # 2. Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login_response = client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        # 3. Refresh token
        refresh_data = {"refresh_token": login_data["refresh_token"]}
        refresh_response = client.post("/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200
        
        # All should succeed
        assert len(register_data["access_token"]) > 20
        assert len(login_data["access_token"]) > 20
        assert len(refresh_response.json()["access_token"]) > 20

    def test_register_then_login_different_users(
        self, 
        client: TestClient, 
        test_user_data: Dict[str, Any],
        another_test_user_data: Dict[str, Any]
    ):
        """Test registering multiple users and login with each."""
        # Register first user
        response1 = client.post("/auth/register", json=test_user_data)
        assert response1.status_code == 201
        
        # Register second user
        response2 = client.post("/auth/register", json=another_test_user_data)
        assert response2.status_code == 201
        
        # Login as first user
        login1_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        login1_response = client.post("/auth/login", json=login1_data)
        assert login1_response.status_code == 200
        
        # Login as second user
        login2_data = {
            "email": another_test_user_data["email"],
            "password": another_test_user_data["password"]
        }
        login2_response = client.post("/auth/login", json=login2_data)
        assert login2_response.status_code == 200
        
        # Both should have different user IDs
        user1_id = login1_response.json()["user_id"]
        user2_id = login2_response.json()["user_id"]
        assert user1_id != user2_id 