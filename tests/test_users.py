import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

pytestmark = pytest.mark.users


class TestUserProfile:
    """Test user profile endpoints."""

    def test_get_profile_success(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test successful profile retrieval."""
        response = client.get("/users/profile", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "user_id" in data
        assert "username" in data
        assert "display_name" in data
        assert "email" in data
        assert "profile_image" in data
        assert "bio" in data
        assert "created_at" in data
        assert "articles_read" in data
        assert "preferences" in data
        
        # Check data types and values
        assert isinstance(data["articles_read"], int)
        assert data["articles_read"] == 0  # New user should have 0 articles read
        assert isinstance(data["preferences"], dict)
        assert data["profile_image"] is None  # Should be None for new user
        assert data["bio"] is None  # Should be None for new user

    def test_get_profile_unauthorized(self, client: TestClient):
        """Test profile retrieval without authentication."""
        response = client.get("/users/profile")
        assert response.status_code == 403  # FastAPI returns 403 for missing auth

    def test_get_profile_invalid_token(self, client: TestClient, invalid_auth_headers: Dict[str, str]):
        """Test profile retrieval with invalid token."""
        response = client.get("/users/profile", headers=invalid_auth_headers)
        assert response.status_code == 401

    def test_update_profile_success(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test successful profile update."""
        update_data = {
            "display_name": "Updated Test User",
            "bio": "This is my updated bio",
            "profile_image": "https://example.com/profile.jpg",
            "preferences": {
                "categories": ["technology", "science", "health"],
                "notification_settings": {
                    "push_enabled": False,
                    "email_digest": True
                }
            }
        }
        
        response = client.put("/users/profile", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check updated values
        assert data["display_name"] == update_data["display_name"]
        assert data["bio"] == update_data["bio"]
        assert data["profile_image"] == update_data["profile_image"]
        assert "technology" in data["preferences"]["categories"]
        assert "science" in data["preferences"]["categories"]
        assert "health" in data["preferences"]["categories"]
        assert data["preferences"]["notification_settings"]["push_enabled"] == False

    def test_update_profile_partial(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test partial profile update (only some fields)."""
        update_data = {
            "display_name": "Partially Updated User",
            "profile_image": "https://example.com/new-profile.jpg"
        }
        
        response = client.put("/users/profile", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check updated values
        assert data["display_name"] == update_data["display_name"]
        assert data["profile_image"] == update_data["profile_image"]
        # Other fields should remain unchanged
        assert "user_id" in data
        assert "email" in data

    def test_update_profile_image_only(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test updating only profile image."""
        update_data = {
            "profile_image": "https://example.com/avatar.png"
        }
        
        response = client.put("/users/profile", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check updated value
        assert data["profile_image"] == update_data["profile_image"]

    def test_update_profile_preferences_merge(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test that preferences are merged properly."""
        # First update with some preferences
        initial_update = {
            "preferences": {
                "categories": ["technology"],
                "language": "en",
                "notification_settings": {
                    "push_enabled": True
                }
            }
        }
        
        response = client.put("/users/profile", json=initial_update, headers=auth_headers)
        assert response.status_code == 200
        
        # Then update with additional preferences
        second_update = {
            "preferences": {
                "categories": ["technology", "science"],  # Updated categories
                "content_type": "mixed"  # New field
                # notification_settings should remain from first update
            }
        }
        
        response = client.put("/users/profile", json=second_update, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check merged preferences
        prefs = data["preferences"]
        assert "technology" in prefs["categories"]
        assert "science" in prefs["categories"]
        assert prefs["content_type"] == "mixed"
        assert prefs["language"] == "en"  # Should remain from first update
        assert prefs["notification_settings"]["push_enabled"] == True

    def test_update_profile_unauthorized(self, client: TestClient):
        """Test profile update without authentication."""
        update_data = {"display_name": "Should Fail"}
        response = client.put("/users/profile", json=update_data)
        assert response.status_code == 403

    def test_update_profile_invalid_token(self, client: TestClient, invalid_auth_headers: Dict[str, str]):
        """Test profile update with invalid token."""
        update_data = {"display_name": "Should Fail"}
        response = client.put("/users/profile", json=update_data, headers=invalid_auth_headers)
        assert response.status_code == 401


class TestUserEmbeddingUpdate:
    """Test user embedding update endpoints."""

    def test_embedding_update_success(
        self, 
        client: TestClient, 
        auth_headers: Dict[str, str],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test successful embedding update."""
        response = client.post(
            "/users/embedding/update", 
            json=test_embedding_update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "embedding_updated" in data
        assert "recommendations_refreshed" in data
        assert "next_batch_ready" in data
        assert "personalization_score" in data
        assert "diversity_adjustment" in data
        
        # Check response values
        assert data["embedding_updated"] == True
        assert data["recommendations_refreshed"] == True
        assert data["next_batch_ready"] == True
        assert isinstance(data["personalization_score"], float)
        assert isinstance(data["diversity_adjustment"], float)
        assert 0 <= data["personalization_score"] <= 1
        assert 0 <= data["diversity_adjustment"] <= 1

    def test_embedding_update_invalid_vector_size(
        self, 
        client: TestClient, 
        auth_headers: Dict[str, str],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test embedding update with wrong vector size."""
        invalid_data = test_embedding_update_data.copy()
        invalid_data["embedding_vector"] = [0.1] * 100  # Wrong size (should be 384)
        
        response = client.post(
            "/users/embedding/update", 
            json=invalid_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 422

    def test_embedding_update_missing_fields(
        self, 
        client: TestClient, 
        auth_headers: Dict[str, str]
    ):
        """Test embedding update with missing required fields."""
        incomplete_data = {
            "embedding_vector": [0.1] * 384
            # Missing interaction_summary and other required fields
        }
        
        response = client.post(
            "/users/embedding/update", 
            json=incomplete_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 422

    def test_embedding_update_unauthorized(self, client: TestClient, test_embedding_update_data: Dict[str, Any]):
        """Test embedding update without authentication."""
        response = client.post("/users/embedding/update", json=test_embedding_update_data)
        assert response.status_code == 403

    def test_embedding_update_invalid_token(
        self, 
        client: TestClient, 
        invalid_auth_headers: Dict[str, str],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test embedding update with invalid token."""
        response = client.post(
            "/users/embedding/update", 
            json=test_embedding_update_data, 
            headers=invalid_auth_headers
        )
        assert response.status_code == 401

    def test_embedding_update_updates_user_stats(
        self, 
        client: TestClient, 
        auth_headers: Dict[str, str],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test that embedding update properly updates user statistics."""
        # Get initial profile
        profile_response = client.get("/users/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        initial_profile = profile_response.json()
        initial_articles_read = initial_profile["articles_read"]
        
        # Update embedding
        response = client.post(
            "/users/embedding/update", 
            json=test_embedding_update_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Check updated profile
        updated_profile_response = client.get("/users/profile", headers=auth_headers)
        assert updated_profile_response.status_code == 200
        updated_profile = updated_profile_response.json()
        
        # Articles read should be updated
        expected_articles_read = initial_articles_read + test_embedding_update_data["articles_processed"]
        assert updated_profile["articles_read"] == expected_articles_read


class TestEmbeddingStatus:
    """Test embedding status endpoint."""

    def test_embedding_status_success(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test successful embedding status retrieval."""
        response = client.get("/users/embedding/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "articles_since_update" in data
        assert "sync_required" in data
        assert "embedding_version" in data
        assert "local_computation_config" in data
        
        # Check data types
        assert isinstance(data["articles_since_update"], int)
        assert isinstance(data["sync_required"], bool)
        assert isinstance(data["embedding_version"], str)
        assert isinstance(data["local_computation_config"], dict)
        
        # Check local computation config structure
        config = data["local_computation_config"]
        assert "model_name" in config
        assert "update_frequency" in config
        assert "batch_size_recommended" in config

    def test_embedding_status_after_update(
        self, 
        client: TestClient, 
        auth_headers: Dict[str, str],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test embedding status after performing an update."""
        # First, update embedding
        update_response = client.post(
            "/users/embedding/update", 
            json=test_embedding_update_data, 
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # Then check status
        status_response = client.get("/users/embedding/status", headers=auth_headers)
        assert status_response.status_code == 200
        
        data = status_response.json()
        assert "last_updated" in data
        assert data["last_updated"] is not None  # Should have a timestamp now

    def test_embedding_status_unauthorized(self, client: TestClient):
        """Test embedding status without authentication."""
        response = client.get("/users/embedding/status")
        assert response.status_code == 403

    def test_embedding_status_invalid_token(self, client: TestClient, invalid_auth_headers: Dict[str, str]):
        """Test embedding status with invalid token."""
        response = client.get("/users/embedding/status", headers=invalid_auth_headers)
        assert response.status_code == 401


class TestUserProfileIntegration:
    """Test integration scenarios for user profile management."""

    def test_complete_user_lifecycle(
        self, 
        client: TestClient, 
        test_user_data: Dict[str, Any],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test complete user lifecycle: register -> profile -> update -> embedding."""
        # 1. Register user
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 201
        
        tokens = register_response.json()
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # 2. Get initial profile
        profile_response = client.get("/users/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        initial_profile = profile_response.json()
        
        # 3. Update profile
        profile_update = {
            "display_name": "Updated User",
            "bio": "Updated bio",
            "preferences": {
                "categories": ["technology", "science"]
            }
        }
        update_response = client.put("/users/profile", json=profile_update, headers=auth_headers)
        assert update_response.status_code == 200
        
        # 4. Update embedding
        embedding_response = client.post(
            "/users/embedding/update", 
            json=test_embedding_update_data, 
            headers=auth_headers
        )
        assert embedding_response.status_code == 200
        
        # 5. Check final profile state
        final_profile_response = client.get("/users/profile", headers=auth_headers)
        assert final_profile_response.status_code == 200
        final_profile = final_profile_response.json()
        
        # Verify all changes
        assert final_profile["display_name"] == "Updated User"
        assert final_profile["bio"] == "Updated bio"
        assert "technology" in final_profile["preferences"]["categories"]
        assert final_profile["articles_read"] == test_embedding_update_data["articles_processed"]

    def test_multiple_embedding_updates(
        self, 
        client: TestClient, 
        auth_headers: Dict[str, str],
        test_embedding_update_data: Dict[str, Any]
    ):
        """Test multiple embedding updates accumulate correctly."""
        # First update
        response1 = client.post(
            "/users/embedding/update", 
            json=test_embedding_update_data, 
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Second update with different data
        second_update = test_embedding_update_data.copy()
        second_update["articles_processed"] = 5
        second_update["interaction_summary"]["engagement_metrics"]["liked_articles"] = 2
        
        response2 = client.post(
            "/users/embedding/update", 
            json=second_update, 
            headers=auth_headers
        )
        assert response2.status_code == 200
        
        # Check final profile
        profile_response = client.get("/users/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        profile = profile_response.json()
        
        # Articles read should be sum of both updates
        expected_total = test_embedding_update_data["articles_processed"] + second_update["articles_processed"]
        assert profile["articles_read"] == expected_total 