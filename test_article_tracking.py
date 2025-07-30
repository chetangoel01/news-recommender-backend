#!/usr/bin/env python3
"""
Test script to verify article tracking and exclusion system.
This test ensures that users don't see the same articles on refresh.
"""

import asyncio
import requests
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User, UserArticleView, Like, Share, Bookmark
from services.recommendation import RecommendationService

class ArticleTrackingTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.auth_token = None
        self.test_user = None
        self.session = Session(engine)
    
    def setup_test_user(self):
        """Create or get a test user for testing."""
        # Try to get existing test user
        self.test_user = self.session.query(User).filter(
            User.email == "test_article_tracking@example.com"
        ).first()
        
        if not self.test_user:
            # Create test user
            from core.auth import get_password_hash
            self.test_user = User(
                username="test_article_tracking",
                email="test_article_tracking@example.com",
                password_hash=get_password_hash("testpassword123"),
                display_name="Article Tracking Test User"
            )
            self.session.add(self.test_user)
            self.session.commit()
            print(f"✅ Created test user: {self.test_user.id}")
        else:
            print(f"✅ Using existing test user: {self.test_user.id}")
        
        return self.test_user
    
    def login_test_user(self):
        """Login the test user and get auth token."""
        login_data = {
            "email": "test_article_tracking@example.com",
            "password": "testpassword123"
        }
        
        response = requests.post(f"{self.base_url}/auth/login", json=login_data)
        if response.status_code == 200:
            self.auth_token = response.json()["access_token"]
            print("✅ Successfully logged in test user")
            return True
        else:
            print(f"❌ Failed to login: {response.status_code} - {response.text}")
            return False
    
    def track_article_interaction(self, article_id, interaction_type="swipe_up", duration=5.0, percentage=20):
        """Track an article interaction."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        view_data = {
            "view_duration_seconds": duration,
            "percentage_read": percentage,
            "interaction_type": interaction_type,
            "swipe_direction": "up"
        }
        
        response = requests.post(
            f"{self.base_url}/articles/{article_id}/view",
            headers=headers,
            json=view_data
        )
        
        if response.status_code == 200:
            print(f"✅ Tracked {interaction_type} for article {article_id}")
            return True
        else:
            print(f"❌ Failed to track interaction: {response.status_code} - {response.text}")
            return False
    
    def get_personalized_feed(self, force_fresh=False):
        """Get personalized feed."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        params = {
            "limit": 10,
            "force_fresh": str(force_fresh).lower()
        }
        
        response = requests.get(f"{self.base_url}/feed/personalized", headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Got {len(data['articles'])} articles (force_fresh: {force_fresh})")
            return data
        else:
            print(f"❌ Failed to get feed: {response.status_code} - {response.text}")
            return None
    
    def test_article_exclusion(self):
        """Test that articles are properly excluded after interaction."""
        print("\n🧪 Testing Article Exclusion System")
        print("=" * 50)
        
        # Get initial feed
        print("\n📄 Step 1: Get initial feed")
        initial_feed = self.get_personalized_feed()
        if not initial_feed or not initial_feed['articles']:
            print("❌ No articles in initial feed")
            return False
        
        initial_articles = initial_feed['articles']
        initial_article_ids = [article['id'] for article in initial_articles]
        print(f"📊 Initial feed has {len(initial_articles)} articles")
        print(f"📋 Article IDs: {initial_article_ids[:5]}...")
        
        # Track interactions with first 3 articles
        print("\n📝 Step 2: Track interactions with articles")
        tracked_articles = []
        for i, article in enumerate(initial_articles[:3]):
            article_id = article['id']
            interaction_type = f"swipe_up_{i}"
            
            success = self.track_article_interaction(article_id, interaction_type)
            if success:
                tracked_articles.append(article_id)
        
        print(f"📊 Tracked {len(tracked_articles)} articles")
        
        # Wait a moment for database to update
        import time
        print("⏳ Waiting for database to update...")
        time.sleep(2)
        
        # Check database state immediately after tracking
        print("\n🔍 Checking database state after tracking:")
        session = Session(engine)
        try:
            recent_views = session.query(UserArticleView).filter(
                UserArticleView.user_id == str(self.test_user.id),
                UserArticleView.created_at >= datetime.now(timezone.utc) - timedelta(hours=12)
            ).all()
            print(f"📊 Database shows {len(recent_views)} recent views")
            for view in recent_views:
                print(f"   - Article {view.article_id} at {view.created_at}")
        except Exception as e:
            print(f"❌ Error checking database: {e}")
        finally:
            session.close()
        
        # Get feed again (should exclude tracked articles)
        print("\n🔄 Step 3: Get feed after tracking (should exclude tracked articles)")
        second_feed = self.get_personalized_feed()
        if not second_feed:
            return False
        
        second_articles = second_feed['articles']
        second_article_ids = [article['id'] for article in second_articles]
        
        # Check for duplicates
        duplicates = set(initial_article_ids) & set(second_article_ids)
        tracked_duplicates = set(tracked_articles) & set(second_article_ids)
        
        print(f"📊 Second feed has {len(second_articles)} articles")
        print(f"📋 Second feed article IDs: {second_article_ids[:5]}...")
        print(f"🔍 Found {len(duplicates)} total duplicates")
        print(f"🔍 Found {len(tracked_duplicates)} duplicates from tracked articles")
        
        if tracked_duplicates:
            print(f"❌ FAILED: Found tracked articles in second feed: {tracked_duplicates}")
            return False
        else:
            print("✅ SUCCESS: No tracked articles found in second feed")
        
        # Test force fresh mode
        print("\n🆕 Step 4: Test force fresh mode")
        fresh_feed = self.get_personalized_feed(force_fresh=True)
        if not fresh_feed:
            return False
        
        fresh_articles = fresh_feed['articles']
        fresh_article_ids = [article['id'] for article in fresh_articles]
        
        # Check for any duplicates with initial feed
        fresh_duplicates = set(initial_article_ids) & set(fresh_article_ids)
        print(f"📊 Fresh feed has {len(fresh_articles)} articles")
        print(f"🔍 Found {len(fresh_duplicates)} duplicates with initial feed")
        
        if fresh_duplicates:
            print(f"⚠️  WARNING: Found {len(fresh_duplicates)} duplicates in fresh feed")
            print(f"   Duplicate IDs: {list(fresh_duplicates)[:3]}")
        else:
            print("✅ SUCCESS: Fresh feed has no duplicates with initial feed")
        
        return True
    
    def test_database_exclusion_logic(self):
        """Test the database exclusion logic directly."""
        print("\n🧪 Testing Database Exclusion Logic")
        print("=" * 50)
        
        # Get user's exclusion list
        recommendation_service = RecommendationService(self.session)
        exclude_ids = recommendation_service._get_smart_exclusion_list(str(self.test_user.id))
        
        print(f"📊 User has {len(exclude_ids)} articles in exclusion list")
        
        # Check what types of interactions are being excluded
        recent_views = self.session.query(UserArticleView).filter(
            UserArticleView.user_id == self.test_user.id,
            UserArticleView.created_at >= datetime.now(timezone.utc) - timedelta(hours=12)
        ).count()
        
        recent_likes = self.session.query(Like).filter(
            Like.user_id == self.test_user.id,
            Like.created_at >= datetime.now(timezone.utc) - timedelta(days=14)
        ).count()
        
        print(f"📊 Recent views (last 12h): {recent_views}")
        print(f"📊 Recent likes (last 14d): {recent_likes}")
        
        # Test force fresh exclusion
        force_fresh_exclude_ids = recommendation_service._get_smart_exclusion_list(
            str(self.test_user.id), force_fresh=True
        )
        
        print(f"📊 Force fresh exclusion list: {len(force_fresh_exclude_ids)} articles")
        print(f"📊 Difference: {len(force_fresh_exclude_ids) - len(exclude_ids)} additional articles excluded")
        
        return len(force_fresh_exclude_ids) >= len(exclude_ids)
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        # Remove test user's interactions
        self.session.query(UserArticleView).filter(
            UserArticleView.user_id == self.test_user.id
        ).delete()
        
        self.session.query(Like).filter(
            Like.user_id == self.test_user.id
        ).delete()
        
        self.session.query(Share).filter(
            Share.user_id == self.test_user.id
        ).delete()
        
        self.session.query(Bookmark).filter(
            Bookmark.user_id == self.test_user.id
        ).delete()
        
        self.session.commit()
        print("✅ Test data cleaned up")
    
    def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting Article Tracking Tests")
        print("=" * 50)
        
        try:
            # Setup
            self.setup_test_user()
            if not self.login_test_user():
                return False
            
            # Run tests
            test1_success = self.test_article_exclusion()
            test2_success = self.test_database_exclusion_logic()
            
            # Results
            print("\n📊 Test Results")
            print("=" * 30)
            print(f"Article Exclusion Test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
            print(f"Database Logic Test: {'✅ PASSED' if test2_success else '❌ FAILED'}")
            
            if test1_success and test2_success:
                print("\n🎉 ALL TESTS PASSED! Article tracking system is working correctly.")
                return True
            else:
                print("\n⚠️  Some tests failed. Article tracking system needs attention.")
                return False
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup_test_data()
            self.session.close()

def main():
    """Run the article tracking tests."""
    print("🚀 Starting Article Tracking Tests")
    print("=" * 50)
    
    tester = ArticleTrackingTester()
    
    try:
        # Setup test user
        if not tester.setup_test_user():
            print("❌ Failed to setup test user")
            return False
        
        # Login test user
        if not tester.login_test_user():
            print("❌ Failed to login test user")
            return False
        
        # Run tests
        test_results = []
        
        # Test 1: Article exclusion
        print("\n🧪 Testing Article Exclusion System")
        print("=" * 50)
        exclusion_result = tester.test_article_exclusion()
        test_results.append(("Article Exclusion Test", exclusion_result))
        
        # Test 2: Database logic
        print("\n🧪 Testing Database Exclusion Logic")
        print("=" * 50)
        db_result = tester.test_database_exclusion_logic()
        test_results.append(("Database Logic Test", db_result))
        
        # Print results
        print("\n📊 Test Results")
        print("=" * 30)
        all_passed = True
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
            if not result:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All tests passed! Article tracking system is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Article tracking system needs attention.")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up at the very end
        print("\n🧹 Cleaning up test data...")
        tester.cleanup_test_data()
        print("✅ Test data cleaned up")

if __name__ == "__main__":
    main() 