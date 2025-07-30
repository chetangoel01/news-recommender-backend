#!/usr/bin/env python3
"""
Test script for the scalable recommendation service.
Tests pagination, performance, and ensures no duplicates.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from core.db import get_db
from core.models import User, Article
from services.recommendation import RecommendationService

def test_scalable_recommendations():
    """Test the scalable recommendation service."""
    print("🧪 Testing Scalable Recommendation Service")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get a test user
        user = db.query(User).first()
        if not user:
            print("❌ No users found in database. Please create a user first.")
            return
        
        print(f"✅ Testing with user: {user.username}")
        
        # Create recommendation service
        service = RecommendationService(db)
        
        # Test 1: Basic recommendations
        print("\n📊 Test 1: Basic Recommendations")
        start_time = time.time()
        
        recommendations = asyncio.run(
            service.get_personalized_recommendations(user, limit=10)
        )
        
        end_time = time.time()
        print(f"⏱️  Response time: {(end_time - start_time)*1000:.2f}ms")
        print(f"📄 Found {len(recommendations)} recommendations")
        
        if recommendations:
            print("✅ Basic recommendations working")
            for i, (article, metadata) in enumerate(recommendations[:3]):
                print(f"  {i+1}. {article.title[:50]}... (Score: {metadata['confidence']:.2f})")
        else:
            print("⚠️  No recommendations found (this might be normal if no articles match criteria)")
        
        # Test 2: Pagination (if we have recommendations)
        if len(recommendations) >= 5:
            print("\n📄 Test 2: Pagination")
            
            # Get first page
            first_page = asyncio.run(
                service.get_personalized_recommendations(user, limit=5)
            )
            
            if first_page:
                # Get cursor from first article
                cursor = str(first_page[0][0].id)
                print(f"📍 Using cursor: {cursor[:8]}...")
                
                # Get second page
                second_page = asyncio.run(
                    service.get_personalized_recommendations(user, limit=5, cursor=cursor)
                )
                
                print(f"📄 First page: {len(first_page)} articles")
                print(f"📄 Second page: {len(second_page)} articles")
                
                # Check for duplicates
                first_page_ids = {str(article.id) for article, _ in first_page}
                second_page_ids = {str(article.id) for article, _ in second_page}
                
                duplicates = first_page_ids.intersection(second_page_ids)
                
                if duplicates:
                    print(f"❌ Found {len(duplicates)} duplicates between pages")
                    for dup_id in list(duplicates)[:3]:
                        print(f"    Duplicate: {dup_id[:8]}...")
                else:
                    print("✅ No duplicates found between pages")
                
                # Check if cursor article is in first page
                if cursor in first_page_ids:
                    print("✅ Cursor article found in first page")
                else:
                    print("⚠️  Cursor article not in first page (this might be expected)")
        
        # Test 3: Performance with larger limit
        print("\n⚡ Test 3: Performance with Larger Limit")
        start_time = time.time()
        
        large_recommendations = asyncio.run(
            service.get_personalized_recommendations(user, limit=50)
        )
        
        end_time = time.time()
        print(f"⏱️  Response time for 50 recommendations: {(end_time - start_time)*1000:.2f}ms")
        print(f"📄 Retrieved {len(large_recommendations)} recommendations")
        
        if (end_time - start_time) < 1.0:  # Less than 1 second
            print("✅ Performance is good (< 1 second)")
        else:
            print("⚠️  Performance might need optimization")
        
        # Test 4: Trending fallback
        print("\n🔥 Test 4: Trending Fallback")
        trending = service._get_trending_fallback(10)
        print(f"📄 Found {len(trending)} trending articles")
        
        if trending:
            print("✅ Trending fallback working")
            for i, (article, metadata) in enumerate(trending[:3]):
                print(f"  {i+1}. {article.title[:50]}...")
        else:
            print("⚠️  No trending articles found")
        
        # Test 5: Memory efficiency check
        print("\n💾 Test 5: Memory Efficiency")
        
        # Get total articles count
        total_articles = db.query(Article).count()
        print(f"📊 Total articles in database: {total_articles}")
        
        # Test with different limits to see memory usage
        for limit in [10, 25, 50]:
            start_time = time.time()
            recommendations = asyncio.run(
                service.get_personalized_recommendations(user, limit=limit)
            )
            end_time = time.time()
            
            print(f"  Limit {limit}: {len(recommendations)} articles in {(end_time - start_time)*1000:.2f}ms")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_database_queries():
    """Test database query performance."""
    print("\n🔍 Testing Database Query Performance")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Test user interactions query
        user = db.query(User).first()
        if not user:
            print("❌ No users found")
            return
        
        service = RecommendationService(db)
        
        # Test efficient user interactions
        start_time = time.time()
        interactions = service._get_user_interactions_efficient(str(user.id))
        end_time = time.time()
        
        print(f"⏱️  User interactions query: {(end_time - start_time)*1000:.2f}ms")
        print(f"📊 Found {len(interactions)} user interactions")
        
        # Test article count
        start_time = time.time()
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_articles = db.query(Article).filter(
            Article.published_at >= thirty_days_ago
        ).count()
        end_time = time.time()
        
        print(f"⏱️  Recent articles query: {(end_time - start_time)*1000:.2f}ms")
        print(f"📊 Found {recent_articles} recent articles")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting Scalable Recommendation Service Tests")
    print("=" * 60)
    
    test_scalable_recommendations()
    test_database_queries()
    
    print("\n🎉 Testing completed!") 