#!/usr/bin/env python3
"""
Comprehensive test suite for view tracking and duplicate prevention system.

This test file verifies that:
1. View tracking works correctly
2. Articles are properly excluded from recommendations after being viewed
3. Different interaction types are tracked appropriately
4. The recommendation system prevents duplicates
5. Pagination works without showing previously seen articles
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from core.db import engine
from core.models import User, Article, UserArticleInteraction, Like, Share, Bookmark
from services.recommendation import RecommendationService
from api.routes.feed import get_personalized_feed


class TestViewTrackingSystem:
    """Test the complete view tracking and duplicate prevention system."""
    
    @pytest.fixture
    def db_session(self):
        """Create a database session for testing."""
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()
    
    @pytest.fixture
    def test_user(self, db_session: Session) -> User:
        """Create a test user."""
        user = User(
            username="test_user_view_tracking",
            email="test_view@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def test_articles(self, db_session: Session) -> List[Article]:
        """Create multiple test articles."""
        articles = []
        categories = ["technology", "business", "politics", "science"]
        sources = ["TechNews", "BusinessDaily", "PoliticsNow", "ScienceWeekly"]
        
        for i in range(20):
            article = Article(
                title=f"Test Article {i+1} - {categories[i % 4]}",
                summary=f"This is test article {i+1} about {categories[i % 4]}",
                content=f"Full content of test article {i+1}",
                url=f"https://example.com/article-{i+1}",
                source_name=sources[i % 4],
                category=categories[i % 4],
                published_at=datetime.now(timezone.utc) - timedelta(days=i),
                views=100 + i * 10,
                likes=10 + i,
                shares=5 + i // 2
            )
            db_session.add(article)
            articles.append(article)
        
        db_session.commit()
        return articles
    
    def test_view_tracking_basic_functionality(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test basic view tracking functionality."""
        print("\n�� Testing basic view tracking functionality...")
        
        # Track a view for the first article
        article = test_articles[0]
        interaction = UserArticleInteraction(
            user_id=test_user.id,
            article_id=article.id,
            interaction_type="view",
            read_time_seconds=45,
            interaction_strength=1.0,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(interaction)
        db_session.commit()
        
        # Verify the interaction was recorded
        recorded_interaction = db_session.query(UserArticleInteraction).filter(
            UserArticleInteraction.user_id == test_user.id,
            UserArticleInteraction.article_id == article.id,
            UserArticleInteraction.interaction_type == "view"
        ).first()
        
        assert recorded_interaction is not None
        assert recorded_interaction.read_time_seconds == 45
        assert recorded_interaction.interaction_strength == 1.0
        print("✅ Basic view tracking works correctly")
    
    def test_skip_tracking_functionality(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test skip tracking functionality."""
        print("\n🧪 Testing skip tracking functionality...")
        
        # Track a skip for the second article
        article = test_articles[1]
        interaction = UserArticleInteraction(
            user_id=test_user.id,
            article_id=article.id,
            interaction_type="skip",
            read_time_seconds=0,
            interaction_strength=0.5,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(interaction)
        db_session.commit()
        
        # Verify the skip was recorded
        recorded_interaction = db_session.query(UserArticleInteraction).filter(
            UserArticleInteraction.user_id == test_user.id,
            UserArticleInteraction.article_id == article.id,
            UserArticleInteraction.interaction_type == "skip"
        ).first()
        
        assert recorded_interaction is not None
        assert recorded_interaction.read_time_seconds == 0
        assert recorded_interaction.interaction_strength == 0.5
        print("✅ Skip tracking works correctly")
    
    def test_exclusion_list_includes_views(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that the exclusion list includes viewed articles."""
        print("\n🧪 Testing exclusion list includes viewed articles...")
        
        # Track views for multiple articles
        viewed_articles = test_articles[:5]
        for article in viewed_articles:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="view",
                read_time_seconds=30,
                interaction_strength=1.0,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(interaction)
        db_session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db_session)
        
        # Get exclusion list
        exclude_ids = recommendation_service._get_smart_exclusion_list(test_user.id, force_fresh=False)
        
        # Verify viewed articles are in exclusion list
        viewed_article_ids = [str(article.id) for article in viewed_articles]
        for article_id in viewed_article_ids:
            assert article_id in exclude_ids, f"Viewed article {article_id} should be in exclusion list"
        
        print(f"✅ Exclusion list contains {len(viewed_article_ids)} viewed articles")
        print(f"✅ Total exclusion list size: {len(exclude_ids)}")
    
    def test_exclusion_list_includes_skips(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that the exclusion list includes skipped articles."""
        print("\n🧪 Testing exclusion list includes skipped articles...")
        
        # Track skips for multiple articles
        skipped_articles = test_articles[5:10]
        for article in skipped_articles:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="skip",
                read_time_seconds=0,
                interaction_strength=0.5,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(interaction)
        db_session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db_session)
        
        # Get exclusion list
        exclude_ids = recommendation_service._get_smart_exclusion_list(test_user.id, force_fresh=False)
        
        # Verify skipped articles are in exclusion list
        skipped_article_ids = [str(article.id) for article in skipped_articles]
        for article_id in skipped_article_ids:
            assert article_id in exclude_ids, f"Skipped article {article_id} should be in exclusion list"
        
        print(f"✅ Exclusion list contains {len(skipped_article_ids)} skipped articles")
    
    def test_recommendations_exclude_viewed_articles(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that recommendations exclude viewed articles."""
        print("\n🧪 Testing recommendations exclude viewed articles...")
        
        # Track views for some articles
        viewed_articles = test_articles[:3]
        for article in viewed_articles:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="view",
                read_time_seconds=30,
                interaction_strength=1.0,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(interaction)
        db_session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db_session)
        
        # Get recommendations
        recommendations = asyncio.run(
            recommendation_service.get_personalized_recommendations(
                user=test_user,
                limit=10,
                diversify=False
            )
        )
        
        # Get recommended article IDs
        recommended_article_ids = [str(article.id) for article, _ in recommendations]
        
        # Verify viewed articles are not in recommendations
        viewed_article_ids = [str(article.id) for article in viewed_articles]
        for viewed_id in viewed_article_ids:
            assert viewed_id not in recommended_article_ids, f"Viewed article {viewed_id} should not be recommended"
        
        print(f"✅ Recommendations exclude {len(viewed_articles)} viewed articles")
        print(f"✅ Got {len(recommendations)} recommendations")
    
    def test_pagination_without_duplicates(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that pagination doesn't show duplicate articles."""
        print("\n�� Testing pagination without duplicates...")
        
        # Track views for some articles
        viewed_articles = test_articles[:5]
        for article in viewed_articles:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="view",
                read_time_seconds=30,
                interaction_strength=1.0,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(interaction)
        db_session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db_session)
        
        # Get first page
        first_page = asyncio.run(
            recommendation_service.get_personalized_recommendations(
                user=test_user,
                limit=5,
                diversify=False
            )
        )
        
        # Get second page
        second_page = asyncio.run(
            recommendation_service.get_personalized_recommendations(
                user=test_user,
                limit=5,
                diversify=False
            )
        )
        
        # Get article IDs from both pages
        first_page_ids = [str(article.id) for article, _ in first_page]
        second_page_ids = [str(article.id) for article, _ in second_page]
        
        # Check for duplicates between pages
        duplicates = set(first_page_ids) & set(second_page_ids)
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicates between pages: {duplicates}"
        
        # Check that viewed articles don't appear in either page
        viewed_article_ids = [str(article.id) for article in viewed_articles]
        for viewed_id in viewed_article_ids:
            assert viewed_id not in first_page_ids, f"Viewed article {viewed_id} in first page"
            assert viewed_id not in second_page_ids, f"Viewed article {viewed_id} in second page"
        
        print(f"✅ No duplicates between pages")
        print(f"✅ First page: {len(first_page)} articles")
        print(f"✅ Second page: {len(second_page)} articles")
    
    def test_mixed_interaction_types(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that different interaction types are all excluded."""
        print("\n🧪 Testing mixed interaction types...")
        
        # Create different types of interactions
        interactions = [
            (test_articles[0], "view", 45, 1.0),
            (test_articles[1], "skip", 0, 0.5),
            (test_articles[2], "like", None, 1.0),
            (test_articles[3], "share", None, 1.0),
            (test_articles[4], "bookmark", None, 1.0),
        ]
        
        for article, interaction_type, read_time, strength in interactions:
            if interaction_type in ["view", "skip"]:
                # Use UserArticleInteraction table
                interaction = UserArticleInteraction(
                    user_id=test_user.id,
                    article_id=article.id,
                    interaction_type=interaction_type,
                    read_time_seconds=read_time,
                    interaction_strength=strength,
                    created_at=datetime.now(timezone.utc)
                )
                db_session.add(interaction)
            elif interaction_type == "like":
                # Use Like table
                like = Like(
                    user_id=test_user.id,
                    article_id=article.id,
                    created_at=datetime.now(timezone.utc)
                )
                db_session.add(like)
            elif interaction_type == "share":
                # Use Share table
                share = Share(
                    user_id=test_user.id,
                    article_id=article.id,
                    platform="test",
                    created_at=datetime.now(timezone.utc)
                )
                db_session.add(share)
            elif interaction_type == "bookmark":
                # Use Bookmark table
                bookmark = Bookmark(
                    user_id=test_user.id,
                    article_id=article.id,
                    created_at=datetime.now(timezone.utc)
                )
                db_session.add(bookmark)
        
        db_session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db_session)
        
        # Get exclusion list
        exclude_ids = recommendation_service._get_smart_exclusion_list(test_user.id, force_fresh=False)
        
        # Verify all interacted articles are excluded
        interacted_article_ids = [str(article.id) for article, _, _, _ in interactions]
        for article_id in interacted_article_ids:
            assert article_id in exclude_ids, f"Interacted article {article_id} should be in exclusion list"
        
        print(f"✅ All {len(interactions)} interaction types are properly excluded")
    
    def test_force_fresh_exclusion(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that force_fresh uses more aggressive exclusion."""
        print("\n🧪 Testing force_fresh exclusion...")
        
        # Create some old interactions (30+ days ago)
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        for article in test_articles[:3]:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="view",
                read_time_seconds=30,
                interaction_strength=1.0,
                created_at=old_date
            )
            db_session.add(interaction)
        
        # Create some recent interactions
        recent_date = datetime.now(timezone.utc) - timedelta(days=5)
        for article in test_articles[3:6]:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="view",
                read_time_seconds=30,
                interaction_strength=1.0,
                created_at=recent_date
            )
            db_session.add(interaction)
        
        db_session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db_session)
        
        # Get standard exclusion list
        standard_exclude_ids = recommendation_service._get_smart_exclusion_list(test_user.id, force_fresh=False)
        
        # Get force_fresh exclusion list
        fresh_exclude_ids = recommendation_service._get_smart_exclusion_list(test_user.id, force_fresh=True)
        
        # Force fresh should exclude more articles (including older ones)
        assert len(fresh_exclude_ids) >= len(standard_exclude_ids), "Force fresh should exclude more articles"
        
        print(f"✅ Standard exclusion: {len(standard_exclude_ids)} articles")
        print(f"✅ Force fresh exclusion: {len(fresh_exclude_ids)} articles")
    
    def test_interaction_strength_tracking(self, db_session: Session, test_user: User, test_articles: List[Article]):
        """Test that interaction strength is properly tracked."""
        print("\n🧪 Testing interaction strength tracking...")
        
        # Create interactions with different strengths
        interactions = [
            (test_articles[0], "view", 10, 0.3),   # Quick view
            (test_articles[1], "view", 60, 1.0),   # Long read
            (test_articles[2], "view", 120, 1.5),  # Very long read
            (test_articles[3], "skip", 0, 0.1),    # Quick skip
        ]
        
        for article, interaction_type, read_time, strength in interactions:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type=interaction_type,
                read_time_seconds=read_time,
                interaction_strength=strength,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(interaction)
        
        db_session.commit()
        
        # Verify interactions were recorded with correct strengths
        for article, interaction_type, read_time, expected_strength in interactions:
            recorded = db_session.query(UserArticleInteraction).filter(
                UserArticleInteraction.user_id == test_user.id,
                UserArticleInteraction.article_id == article.id,
                UserArticleInteraction.interaction_type == interaction_type
            ).first()
            
            assert recorded is not None
            assert recorded.interaction_strength == expected_strength
            assert recorded.read_time_seconds == read_time
        
        print("✅ Interaction strength tracking works correctly")
    
    def test_concurrent_user_interactions(self, db_session: Session, test_articles: List[Article]):
        """Test that multiple users can interact with the same articles."""
        print("\n�� Testing concurrent user interactions...")
        
        # Create two test users
        user1 = User(
            username="user1_view_test",
            email="user1@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )
        user2 = User(
            username="user2_view_test",
            email="user2@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        
        # Both users view the same article
        article = test_articles[0]
        interaction1 = UserArticleInteraction(
            user_id=user1.id,
            article_id=article.id,
            interaction_type="view",
            read_time_seconds=30,
            interaction_strength=1.0,
            created_at=datetime.now(timezone.utc)
        )
        interaction2 = UserArticleInteraction(
            user_id=user2.id,
            article_id=article.id,
            interaction_type="view",
            read_time_seconds=45,
            interaction_strength=1.0,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(interaction1)
        db_session.add(interaction2)
        db_session.commit()
        
        # Verify both interactions were recorded
        user1_interaction = db_session.query(UserArticleInteraction).filter(
            UserArticleInteraction.user_id == user1.id,
            UserArticleInteraction.article_id == article.id
        ).first()
        
        user2_interaction = db_session.query(UserArticleInteraction).filter(
            UserArticleInteraction.user_id == user2.id,
            UserArticleInteraction.article_id == article.id
        ).first()
        
        assert user1_interaction is not None
        assert user2_interaction is not None
        assert user1_interaction.read_time_seconds == 30
        assert user2_interaction.read_time_seconds == 45
        
        print("✅ Concurrent user interactions work correctly")


def run_view_tracking_tests():
    """Run all view tracking tests."""
    print("🚀 Starting View Tracking and Duplicate Prevention Tests")
    print("=" * 60)
    
    # Create test instance
    test_instance = TestViewTrackingSystem()
    
    # Get database session
    db_session = Session(engine)
    
    try:
        # Create test user
        test_user = test_instance.test_user.__call__(db_session)
        
        # Create test articles
        test_articles = test_instance.test_articles.__call__(db_session)
        
        print(f"✅ Created test user: {test_user.username}")
        print(f"✅ Created {len(test_articles)} test articles")
        
        # Run all tests
        test_instance.test_view_tracking_basic_functionality(db_session, test_user, test_articles)
        test_instance.test_skip_tracking_functionality(db_session, test_user, test_articles)
        test_instance.test_exclusion_list_includes_views(db_session, test_user, test_articles)
        test_instance.test_exclusion_list_includes_skips(db_session, test_user, test_articles)
        test_instance.test_recommendations_exclude_viewed_articles(db_session, test_user, test_articles)
        test_instance.test_pagination_without_duplicates(db_session, test_user, test_articles)
        test_instance.test_mixed_interaction_types(db_session, test_user, test_articles)
        test_instance.test_force_fresh_exclusion(db_session, test_user, test_articles)
        test_instance.test_interaction_strength_tracking(db_session, test_user, test_articles)
        test_instance.test_concurrent_user_interactions(db_session, test_articles)
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! View tracking system is working correctly.")
        print("✅ Articles are properly excluded after being viewed")
        print("✅ No duplicates appear in recommendations")
        print("✅ Pagination works without showing previously seen articles")
        print("✅ Different interaction types are tracked appropriately")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    run_view_tracking_tests() 