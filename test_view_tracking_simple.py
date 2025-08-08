#!/usr/bin/env python3
"""
Simple test for view tracking and duplicate prevention system.
"""

import asyncio
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import uuid

from core.db import engine
from core.models import User, Article, UserArticleInteraction, Like, Share, Bookmark
from services.recommendation import RecommendationService

def test_view_tracking_basic():
    """Test basic view tracking functionality."""
    print("\n🧪 Testing basic view tracking functionality...")
    
    session = Session(engine)
    
    try:
        # Create a test user
        test_user = User(
            username="test_user_view_tracking",
            email="test_view@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )
        session.add(test_user)
        session.commit()
        
        # Create a test article
        test_article = Article(
            title="Test Article for View Tracking",
            summary="This is a test article for view tracking",
            content="Full content of test article",
            url="https://example.com/test-article",
            source_name="TestSource",
            category="technology",
            published_at=datetime.now(timezone.utc),
            views=100,
            likes=10,
            shares=5
        )
        session.add(test_article)
        session.commit()
        
        # Track a view for the article
        interaction = UserArticleInteraction(
            user_id=test_user.id,
            article_id=test_article.id,
            interaction_type="view",
            read_time_seconds=45,
            interaction_strength=1.0,
            created_at=datetime.now(timezone.utc)
        )
        session.add(interaction)
        session.commit()
        
        # Verify the interaction was recorded
        recorded_interaction = session.query(UserArticleInteraction).filter(
            UserArticleInteraction.user_id == test_user.id,
            UserArticleInteraction.article_id == test_article.id,
            UserArticleInteraction.interaction_type == "view"
        ).first()
        
        assert recorded_interaction is not None
        assert recorded_interaction.read_time_seconds == 45
        assert recorded_interaction.interaction_strength == 1.0
        print("✅ Basic view tracking works correctly")
        
        # Test exclusion list
        recommendation_service = RecommendationService(session)
        exclude_ids = recommendation_service._get_smart_exclusion_list(str(test_user.id), force_fresh=False)
        
        # Verify viewed article is in exclusion list
        assert str(test_article.id) in exclude_ids, f"Viewed article {test_article.id} should be in exclusion list"
        print(f"✅ Exclusion list contains viewed article")
        print(f"✅ Total exclusion list size: {len(exclude_ids)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    finally:
        session.close()

def test_skip_tracking():
    """Test skip tracking functionality."""
    print("\n🧪 Testing skip tracking functionality...")
    
    session = Session(engine)
    
    try:
        # Create a test user
        test_user = User(
            username="test_user_skip_tracking",
            email="test_skip@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )
        session.add(test_user)
        session.commit()
        
        # Create a test article
        test_article = Article(
            title="Test Article for Skip Tracking",
            summary="This is a test article for skip tracking",
            content="Full content of test article",
            url="https://example.com/test-skip-article",
            source_name="TestSource",
            category="business",
            published_at=datetime.now(timezone.utc),
            views=50,
            likes=5,
            shares=2
        )
        session.add(test_article)
        session.commit()
        
        # Track a skip for the article
        interaction = UserArticleInteraction(
            user_id=test_user.id,
            article_id=test_article.id,
            interaction_type="skip",
            read_time_seconds=0,
            interaction_strength=0.5,
            created_at=datetime.now(timezone.utc)
        )
        session.add(interaction)
        session.commit()
        
        # Verify the skip was recorded
        recorded_interaction = session.query(UserArticleInteraction).filter(
            UserArticleInteraction.user_id == test_user.id,
            UserArticleInteraction.article_id == test_article.id,
            UserArticleInteraction.interaction_type == "skip"
        ).first()
        
        assert recorded_interaction is not None
        assert recorded_interaction.read_time_seconds == 0
        assert recorded_interaction.interaction_strength == 0.5
        print("✅ Skip tracking works correctly")
        
        # Test exclusion list
        recommendation_service = RecommendationService(session)
        exclude_ids = recommendation_service._get_smart_exclusion_list(str(test_user.id), force_fresh=False)
        
        # Verify skipped article is in exclusion list
        assert str(test_article.id) in exclude_ids, f"Skipped article {test_article.id} should be in exclusion list"
        print(f"✅ Exclusion list contains skipped article")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    finally:
        session.close()

def test_recommendations_exclude_viewed():
    """Test that recommendations exclude viewed articles."""
    print("\n🧪 Testing recommendations exclude viewed articles...")
    
    session = Session(engine)
    
    try:
        # Create a test user
        test_user = User(
            username="test_user_recommendations",
            email="test_rec@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )
        session.add(test_user)
        session.commit()
        
        # Create multiple test articles
        articles = []
        for i in range(5):
            article = Article(
                title=f"Test Article {i+1}",
                summary=f"This is test article {i+1}",
                content=f"Full content of test article {i+1}",
                url=f"https://example.com/test-article-{i+1}",
                source_name="TestSource",
                category="technology",
                published_at=datetime.now(timezone.utc) - timedelta(days=i),
                views=100 + i * 10,
                likes=10 + i,
                shares=5 + i
            )
            session.add(article)
            articles.append(article)
        session.commit()
        
        # Track views for some articles
        viewed_articles = articles[:3]
        for article in viewed_articles:
            interaction = UserArticleInteraction(
                user_id=test_user.id,
                article_id=article.id,
                interaction_type="view",
                read_time_seconds=30,
                interaction_strength=1.0,
                created_at=datetime.now(timezone.utc)
            )
            session.add(interaction)
        session.commit()
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(session)
        
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
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    finally:
        session.close()

def run_all_tests():
    """Run all view tracking tests."""
    print("🚀 Starting View Tracking and Duplicate Prevention Tests")
    print("=" * 60)
    
    tests = [
        test_view_tracking_basic,
        test_skip_tracking,
        test_recommendations_exclude_viewed
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! View tracking system is working correctly.")
        print("✅ Articles are properly excluded after being viewed")
        print("✅ No duplicates appear in recommendations")
        print("✅ Different interaction types are tracked appropriately")
    else:
        print(f"❌ {total - passed} tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests() 