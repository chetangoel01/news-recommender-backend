import pytest
import uuid
from fastapi.testclient import TestClient
from typing import Dict, Any
from datetime import datetime

pytestmark = pytest.mark.articles


class TestGetArticles:
    """Test GET /articles endpoint for retrieving paginated articles."""

    def test_get_articles_success(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test successful retrieval of articles."""
        response = client.get("/articles", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "articles" in data
        assert "total" in data
        assert "page" in data
        assert "has_more" in data
        
        # Check we have articles
        assert len(data["articles"]) > 0
        assert data["total"] >= len(multiple_test_articles_in_db)
        assert data["page"] == 1
        
        # Check article structure
        article = data["articles"][0]
        assert "id" in article
        assert "title" in article
        assert "summary" in article
        assert "content_preview" in article
        assert "url" in article
        assert "source" in article
        assert "engagement" in article
        assert "category" in article
        assert "language" in article
        
        # Check source structure
        assert "name" in article["source"]
        
        # Check engagement structure
        engagement = article["engagement"]
        assert "views" in engagement
        assert "likes" in engagement
        assert "shares" in engagement
        assert "user_liked" in engagement
        assert "user_bookmarked" in engagement

    def test_get_articles_pagination(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test pagination functionality."""
        # Test first page with limit
        response = client.get("/articles?page=1&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["articles"]) <= 2
        assert data["page"] == 1
        
        # Test second page
        response = client.get("/articles?page=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2

    def test_get_articles_filter_by_category(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test filtering articles by category."""
        response = client.get("/articles?category=technology", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # All returned articles should be technology category
        for article in data["articles"]:
            assert article["category"] == "technology"

    def test_get_articles_filter_by_source(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test filtering articles by source."""
        response = client.get("/articles?source=TechNews", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # All returned articles should be from TechNews
        for article in data["articles"]:
            assert article["source"]["name"] == "TechNews"

    def test_get_articles_filter_by_language(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test filtering articles by language."""
        response = client.get("/articles?language=en", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # All returned articles should be in English
        for article in data["articles"]:
            assert article["language"] == "en"

    def test_get_articles_sort_recent(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test sorting articles by recent."""
        response = client.get("/articles?sort=recent", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should have articles in response
        assert len(data["articles"]) > 0

    def test_get_articles_sort_trending(self, client: TestClient, auth_headers: Dict[str, str], multiple_test_articles_in_db):
        """Test sorting articles by trending."""
        response = client.get("/articles?sort=trending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should have articles in response
        assert len(data["articles"]) > 0

    @pytest.mark.parametrize("query_params,description", [
        ("page=-1", "negative page number"),
        ("page=0", "zero page number"),
        ("limit=101", "limit too high"),
        ("sort=invalid", "invalid sort parameter"),
    ])
    def test_get_articles_invalid_parameters(self, client: TestClient, auth_headers: Dict[str, str], 
                                           query_params: str, description: str):
        """Test various invalid query parameters."""
        response = client.get(f"/articles?{query_params}", headers=auth_headers)
        assert response.status_code == 422

    def test_get_articles_unauthorized(self, client: TestClient, invalid_auth_headers: Dict[str, str]):
        """Test unauthorized access to articles."""
        response = client.get("/articles", headers=invalid_auth_headers)
        assert response.status_code == 401

    def test_get_articles_no_auth(self, client: TestClient):
        """Test accessing articles without authentication."""
        response = client.get("/articles")
        # FastAPI HTTPBearer returns 403 when no Authorization header is provided
        assert response.status_code == 403


class TestGetArticleDetail:
    """Test GET /articles/{article_id} endpoint for retrieving article details."""

    def test_get_article_detail_success(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test successful retrieval of article details."""
        response = client.get(f"/articles/{test_article_in_db.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["id"] == str(test_article_in_db.id)
        assert data["title"] == test_article_in_db.title
        assert data["summary"] == test_article_in_db.summary
        assert data["url"] == test_article_in_db.url
        assert "source" in data
        assert "engagement" in data
        assert "related_articles" in data
        
        # Check that view count was incremented
        # Note: This test will increment the view count, which is expected behavior

    def test_get_article_detail_invalid_uuid(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting article with invalid UUID format."""
        response = client.get("/articles/invalid-uuid", headers=auth_headers)
        assert response.status_code == 400
        assert "Invalid article ID format" in response.json()["detail"]

    def test_get_article_detail_not_found(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting non-existent article."""
        fake_uuid = str(uuid.uuid4())
        response = client.get(f"/articles/{fake_uuid}", headers=auth_headers)
        assert response.status_code == 404
        assert "Article not found" in response.json()["detail"]

    def test_get_article_detail_unauthorized(self, client: TestClient, invalid_auth_headers: Dict[str, str], test_article_in_db):
        """Test unauthorized access to article details."""
        response = client.get(f"/articles/{test_article_in_db.id}", headers=invalid_auth_headers)
        assert response.status_code == 401

    def test_get_article_detail_no_auth(self, client: TestClient, test_article_in_db):
        """Test accessing article details without authentication."""
        response = client.get(f"/articles/{test_article_in_db.id}")
        assert response.status_code == 403


class TestTrackArticleView:
    """Test POST /articles/{article_id}/view endpoint for tracking article views."""

    def test_track_article_view_success(self, client: TestClient, auth_headers: Dict[str, str], 
                                      test_article_in_db, article_view_data: Dict[str, Any]):
        """Test successful article view tracking."""
        response = client.post(
            f"/articles/{test_article_in_db.id}/view",
            headers=auth_headers,
            json=article_view_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tracked"] is True
        assert "updated_recommendations" in data

    def test_track_article_view_significant_engagement(self, client: TestClient, auth_headers: Dict[str, str], 
                                                     test_article_in_db):
        """Test view tracking with significant engagement triggers recommendation update."""
        significant_view_data = {
            "view_duration_seconds": 65.0,  # > 30 seconds
            "percentage_read": 85,  # > 70%
            "interaction_type": "swipe_up",
            "swipe_direction": "up"
        }
        
        response = client.post(
            f"/articles/{test_article_in_db.id}/view",
            headers=auth_headers,
            json=significant_view_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tracked"] is True
        assert data["updated_recommendations"] is True

    def test_track_article_view_minimal_engagement(self, client: TestClient, auth_headers: Dict[str, str], 
                                                  test_article_in_db):
        """Test view tracking with minimal engagement."""
        minimal_view_data = {
            "view_duration_seconds": 5.0,  # < 30 seconds
            "percentage_read": 20,  # < 70%
            "interaction_type": "swipe_left",
            "swipe_direction": "left"
        }
        
        response = client.post(
            f"/articles/{test_article_in_db.id}/view",
            headers=auth_headers,
            json=minimal_view_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tracked"] is True
        assert data["updated_recommendations"] is False

    def test_track_article_view_invalid_article_id(self, client: TestClient, auth_headers: Dict[str, str], 
                                                   article_view_data: Dict[str, Any]):
        """Test view tracking with invalid article ID."""
        response = client.post(
            "/articles/invalid-uuid/view",
            headers=auth_headers,
            json=article_view_data
        )
        assert response.status_code == 400

    def test_track_article_view_not_found(self, client: TestClient, auth_headers: Dict[str, str], 
                                         article_view_data: Dict[str, Any]):
        """Test view tracking for non-existent article."""
        fake_uuid = str(uuid.uuid4())
        response = client.post(
            f"/articles/{fake_uuid}/view",
            headers=auth_headers,
            json=article_view_data
        )
        assert response.status_code == 404

    def test_track_article_view_invalid_data(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test view tracking with invalid data."""
        invalid_data = {
            "view_duration_seconds": "invalid",  # Should be float
            "percentage_read": 150,  # Invalid percentage
        }
        
        response = client.post(
            f"/articles/{test_article_in_db.id}/view",
            headers=auth_headers,
            json=invalid_data
        )
        assert response.status_code == 422


class TestLikeArticle:
    """Test POST /articles/{article_id}/like and DELETE /articles/{article_id}/like endpoints."""

    def test_like_article_success(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test successful article liking."""
        initial_likes = test_article_in_db.likes or 0
        
        response = client.post(f"/articles/{test_article_in_db.id}/like", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["liked"] is True
        assert data["total_likes"] == initial_likes + 1
        assert data["user_engagement_updated"] is True

    def test_unlike_article_success(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test successful article unliking."""
        # First like the article
        client.post(f"/articles/{test_article_in_db.id}/like", headers=auth_headers)
        
        # Then unlike it
        response = client.delete(f"/articles/{test_article_in_db.id}/like", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["liked"] is False
        assert "total_likes" in data

    def test_like_article_invalid_id(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test liking article with invalid ID."""
        response = client.post("/articles/invalid-uuid/like", headers=auth_headers)
        assert response.status_code == 400

    def test_like_article_not_found(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test liking non-existent article."""
        fake_uuid = str(uuid.uuid4())
        response = client.post(f"/articles/{fake_uuid}/like", headers=auth_headers)
        assert response.status_code == 404

    def test_like_article_unauthorized(self, client: TestClient, invalid_auth_headers: Dict[str, str], test_article_in_db):
        """Test unauthorized article liking."""
        response = client.post(f"/articles/{test_article_in_db.id}/like", headers=invalid_auth_headers)
        assert response.status_code == 401

    def test_like_article_no_auth(self, client: TestClient, test_article_in_db):
        """Test liking article without authentication."""
        response = client.post(f"/articles/{test_article_in_db.id}/like")
        assert response.status_code == 403


class TestShareArticle:
    """Test POST /articles/{article_id}/share endpoint."""

    def test_share_article_success(self, client: TestClient, auth_headers: Dict[str, str], 
                                  test_article_in_db, article_share_data: Dict[str, Any]):
        """Test successful article sharing."""
        initial_shares = test_article_in_db.shares or 0
        
        response = client.post(
            f"/articles/{test_article_in_db.id}/share",
            headers=auth_headers,
            json=article_share_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["shared"] is True
        assert data["total_shares"] == initial_shares + 1
        assert "share_url" in data
        assert "share_id" in data
        assert data["share_url"].startswith("https://")

    def test_share_article_minimal_data(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test sharing article with minimal data."""
        minimal_share_data = {}
        
        response = client.post(
            f"/articles/{test_article_in_db.id}/share",
            headers=auth_headers,
            json=minimal_share_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["shared"] is True

    def test_share_article_invalid_id(self, client: TestClient, auth_headers: Dict[str, str], 
                                     article_share_data: Dict[str, Any]):
        """Test sharing article with invalid ID."""
        response = client.post(
            "/articles/invalid-uuid/share",
            headers=auth_headers,
            json=article_share_data
        )
        assert response.status_code == 400

    def test_share_article_not_found(self, client: TestClient, auth_headers: Dict[str, str], 
                                    article_share_data: Dict[str, Any]):
        """Test sharing non-existent article."""
        fake_uuid = str(uuid.uuid4())
        response = client.post(
            f"/articles/{fake_uuid}/share",
            headers=auth_headers,
            json=article_share_data
        )
        assert response.status_code == 404


class TestBookmarkArticle:
    """Test POST /articles/{article_id}/bookmark and DELETE /articles/{article_id}/bookmark endpoints."""

    def test_bookmark_article_success(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test successful article bookmarking."""
        response = client.post(f"/articles/{test_article_in_db.id}/bookmark", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["bookmarked"] is True
        assert "bookmark_id" in data
        assert "reading_list_count" in data
        assert data["reading_list_count"] >= 1

    def test_bookmark_article_duplicate(self, client: TestClient, authenticated_user, test_article_in_db):
        """Test bookmarking already bookmarked article."""
        # First, bookmark the article
        response1 = client.post(f"/articles/{test_article_in_db.id}/bookmark", headers=authenticated_user["auth_headers"])
        assert response1.status_code == 200
        
        # Try to bookmark the same article again
        response = client.post(f"/articles/{test_article_in_db.id}/bookmark", headers=authenticated_user["auth_headers"])
        
        assert response.status_code == 400
        assert "already bookmarked" in response.json()["detail"]

    def test_remove_bookmark_success(self, client: TestClient, auth_headers: Dict[str, str], test_bookmark_in_db):
        """Test successful bookmark removal."""
        response = client.delete(f"/articles/{test_bookmark_in_db.article_id}/bookmark", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["bookmarked"] is False
        assert "reading_list_count" in data

    def test_remove_bookmark_not_bookmarked(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test removing bookmark from non-bookmarked article."""
        response = client.delete(f"/articles/{test_article_in_db.id}/bookmark", headers=auth_headers)
        
        assert response.status_code == 404
        assert "Bookmark not found" in response.json()["detail"]

    def test_bookmark_article_invalid_id(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test bookmarking article with invalid ID."""
        response = client.post("/articles/invalid-uuid/bookmark", headers=auth_headers)
        assert response.status_code == 400

    def test_bookmark_article_not_found(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test bookmarking non-existent article."""
        fake_uuid = str(uuid.uuid4())
        response = client.post(f"/articles/{fake_uuid}/bookmark", headers=auth_headers)
        assert response.status_code == 404


class TestGetUserBookmarks:
    """Test GET /users/bookmarks endpoint."""

    def test_get_user_bookmarks_success(self, client: TestClient, auth_headers: Dict[str, str], test_bookmark_in_db):
        """Test successful retrieval of user bookmarks."""
        response = client.get("/users/bookmarks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "bookmarks" in data
        assert "total" in data
        assert "page" in data
        assert "has_more" in data
        
        # Should have at least one bookmark
        assert len(data["bookmarks"]) >= 1
        assert data["total"] >= 1
        
        # Check bookmark structure
        bookmark = data["bookmarks"][0]
        assert "bookmark_id" in bookmark
        assert "article" in bookmark
        assert "bookmarked_at" in bookmark
        
        # Check article structure within bookmark
        article = bookmark["article"]
        assert "id" in article
        assert "title" in article
        assert "source" in article
        assert "engagement" in article

    def test_get_user_bookmarks_pagination(self, client: TestClient, auth_headers: Dict[str, str], test_bookmark_in_db):
        """Test bookmark pagination."""
        response = client.get("/users/bookmarks?page=1&limit=1", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert len(data["bookmarks"]) <= 1

    def test_get_user_bookmarks_filter_category(self, client: TestClient, auth_headers: Dict[str, str], test_bookmark_in_db):
        """Test filtering bookmarks by category."""
        # Assume test_bookmark_in_db has a category
        category = test_bookmark_in_db.article.category
        
        response = client.get(f"/users/bookmarks?category={category}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All bookmarks should be from the specified category
        for bookmark in data["bookmarks"]:
            assert bookmark["article"]["category"] == category

    def test_get_user_bookmarks_empty(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting bookmarks when user has none."""
        # This test works because each test gets a fresh user
        response = client.get("/users/bookmarks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["bookmarks"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    def test_get_user_bookmarks_unauthorized(self, client: TestClient, invalid_auth_headers: Dict[str, str]):
        """Test unauthorized access to bookmarks."""
        response = client.get("/users/bookmarks", headers=invalid_auth_headers)
        assert response.status_code == 401

    def test_get_user_bookmarks_no_auth(self, client: TestClient):
        """Test accessing bookmarks without authentication."""
        response = client.get("/users/bookmarks")
        assert response.status_code == 403


class TestContentManagementIntegration:
    """Integration tests for content management workflows."""

    def test_complete_article_interaction_workflow(self, client: TestClient, auth_headers: Dict[str, str], 
                                                   test_article_in_db, article_view_data: Dict[str, Any], 
                                                   article_share_data: Dict[str, Any]):
        """Test complete article interaction workflow: view -> like -> share -> bookmark."""
        article_id = str(test_article_in_db.id)
        
        # 1. View the article
        response = client.post(f"/articles/{article_id}/view", headers=auth_headers, json=article_view_data)
        assert response.status_code == 200
        
        # 2. Get article details (increments view count)
        response = client.get(f"/articles/{article_id}", headers=auth_headers)
        assert response.status_code == 200
        article_data = response.json()
        
        # 3. Like the article
        response = client.post(f"/articles/{article_id}/like", headers=auth_headers)
        assert response.status_code == 200
        like_data = response.json()
        assert like_data["liked"] is True
        
        # 4. Share the article
        response = client.post(f"/articles/{article_id}/share", headers=auth_headers, json=article_share_data)
        assert response.status_code == 200
        share_data = response.json()
        assert share_data["shared"] is True
        
        # 5. Bookmark the article
        response = client.post(f"/articles/{article_id}/bookmark", headers=auth_headers)
        assert response.status_code == 200
        bookmark_data = response.json()
        assert bookmark_data["bookmarked"] is True
        
        # 6. Verify bookmark appears in user's bookmark list
        response = client.get("/users/bookmarks", headers=auth_headers)
        assert response.status_code == 200
        bookmarks_data = response.json()
        assert len(bookmarks_data["bookmarks"]) >= 1
        
        # Find our bookmarked article
        found_bookmark = False
        for bookmark in bookmarks_data["bookmarks"]:
            if bookmark["article"]["id"] == article_id:
                found_bookmark = True
                assert bookmark["article"]["engagement"]["user_bookmarked"] is True
                break
        assert found_bookmark is True
        
        # 7. Unlike the article
        response = client.delete(f"/articles/{article_id}/like", headers=auth_headers)
        assert response.status_code == 200
        unlike_data = response.json()
        assert unlike_data["liked"] is False
        
        # 8. Remove bookmark
        response = client.delete(f"/articles/{article_id}/bookmark", headers=auth_headers)
        assert response.status_code == 200
        remove_bookmark_data = response.json()
        assert remove_bookmark_data["bookmarked"] is False

    def test_article_engagement_metrics_update(self, client: TestClient, auth_headers: Dict[str, str], test_article_in_db):
        """Test that engagement metrics are properly updated."""
        article_id = str(test_article_in_db.id)
        
        # Get initial engagement metrics
        response = client.get(f"/articles/{article_id}", headers=auth_headers)
        assert response.status_code == 200
        initial_data = response.json()
        initial_views = initial_data["engagement"]["views"]
        initial_likes = initial_data["engagement"]["likes"]
        initial_shares = initial_data["engagement"]["shares"]
        
        # Perform interactions
        client.post(f"/articles/{article_id}/like", headers=auth_headers)
        client.post(f"/articles/{article_id}/share", headers=auth_headers, json={})
        
        # Get updated engagement metrics
        response = client.get(f"/articles/{article_id}", headers=auth_headers)
        assert response.status_code == 200
        updated_data = response.json()
        updated_views = updated_data["engagement"]["views"]
        updated_likes = updated_data["engagement"]["likes"]
        updated_shares = updated_data["engagement"]["shares"]
        
        # Verify metrics were incremented
        assert updated_views > initial_views  # View count incremented by GET request
        assert updated_likes == initial_likes + 1  # Like count incremented
        assert updated_shares == initial_shares + 1  # Share count incremented

    def test_multiple_users_same_article(self, client: TestClient, test_article_in_db, test_user_data: Dict[str, Any], 
                                        another_test_user_data: Dict[str, Any]):
        """Test multiple users interacting with the same article."""
        article_id = str(test_article_in_db.id)
        
        # Register and authenticate first user
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        user1_token = response.json()["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        # Register and authenticate second user
        response = client.post("/auth/register", json=another_test_user_data)
        assert response.status_code == 201
        user2_token = response.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        
        # Both users like the article
        response = client.post(f"/articles/{article_id}/like", headers=user1_headers)
        assert response.status_code == 200
        like1_data = response.json()
        
        response = client.post(f"/articles/{article_id}/like", headers=user2_headers)
        assert response.status_code == 200
        like2_data = response.json()
        
        # Verify like count incremented for both
        assert like2_data["total_likes"] == like1_data["total_likes"] + 1
        
        # Both users bookmark the article
        response = client.post(f"/articles/{article_id}/bookmark", headers=user1_headers)
        assert response.status_code == 200
        
        response = client.post(f"/articles/{article_id}/bookmark", headers=user2_headers)
        assert response.status_code == 200
        
        # Verify both users have the article in their bookmarks
        response = client.get("/users/bookmarks", headers=user1_headers)
        assert response.status_code == 200
        user1_bookmarks = response.json()
        assert len(user1_bookmarks["bookmarks"]) >= 1
        
        response = client.get("/users/bookmarks", headers=user2_headers)
        assert response.status_code == 200
        user2_bookmarks = response.json()
        assert len(user2_bookmarks["bookmarks"]) >= 1 