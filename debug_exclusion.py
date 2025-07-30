#!/usr/bin/env python3
"""
Debug script to test article exclusion logic directly.
"""

import uuid
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User, UserArticleView
from services.recommendation import RecommendationService

def debug_exclusion():
    """Debug the article exclusion logic."""
    print("🔍 Debugging Article Exclusion Logic")
    print("=" * 50)
    
    session = Session(engine)
    
    try:
        # Get test user
        test_user = session.query(User).filter(
            User.email == "test_article_tracking@example.com"
        ).first()
        
        if not test_user:
            print("❌ Test user not found")
            return
        
        print(f"✅ Using test user: {test_user.id}")
        
        # Get recommendation service
        recommendation_service = RecommendationService(session)
        
        # Get exclusion list
        exclude_ids = recommendation_service._get_smart_exclusion_list(str(test_user.id))
        print(f"📊 Exclusion list has {len(exclude_ids)} articles: {exclude_ids}")
        
        # Test candidate selection with exclusion
        candidates = recommendation_service._get_candidate_articles_improved(
            exclude_article_ids=exclude_ids,
            limit=10
        )
        
        candidate_ids = [str(article.id) for article in candidates]
        print(f"📊 Got {len(candidates)} candidates: {candidate_ids[:5]}...")
        
        # Check for excluded articles in candidates
        excluded_in_candidates = set(candidate_ids) & set(exclude_ids)
        if excluded_in_candidates:
            print(f"❌ Found {len(excluded_in_candidates)} excluded articles in candidates: {list(excluded_in_candidates)}")
        else:
            print("✅ No excluded articles found in candidates")
        
        # Test the database query directly
        print("\n🔍 Testing Database Query Directly")
        query = session.query(Article)
        
        if exclude_ids:
            try:
                exclude_uuids = [uuid.UUID(article_id) for article_id in exclude_ids]
                query = query.filter(~Article.id.in_(exclude_uuids))
                print(f"✅ Applied exclusion filter with {len(exclude_uuids)} UUIDs")
            except Exception as e:
                print(f"❌ Error converting to UUIDs: {e}")
        
        # Add time filter
        from datetime import datetime, timezone, timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.filter(Article.published_at >= cutoff_date)
        
        # Get results
        results = query.limit(10).all()
        result_ids = [str(article.id) for article in results]
        print(f"📊 Direct query returned {len(results)} articles: {result_ids[:5]}...")
        
        # Check for excluded articles in direct query results
        excluded_in_results = set(result_ids) & set(exclude_ids)
        if excluded_in_results:
            print(f"❌ Found {len(excluded_in_results)} excluded articles in direct query: {list(excluded_in_results)}")
        else:
            print("✅ No excluded articles found in direct query")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_exclusion() 