#!/usr/bin/env python3
"""
Direct test of database exclusion logic.
"""

import uuid
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User, UserArticleView
from datetime import datetime, timezone, timedelta

def test_direct_exclusion():
    """Test database exclusion directly."""
    print("🔍 Testing Database Exclusion Directly")
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
        
        # Check if user has any recent views
        recent_views = session.query(UserArticleView).filter(
            UserArticleView.user_id == str(test_user.id),
            UserArticleView.created_at >= datetime.now(timezone.utc) - timedelta(hours=12)
        ).all()
        
        print(f"📊 User has {len(recent_views)} recent views")
        for view in recent_views:
            print(f"   - Article {view.article_id} at {view.created_at}")
        
        # Get exclusion list
        exclude_ids = []
        for view in recent_views:
            exclude_ids.append(str(view.article_id))
        
        print(f"📊 Exclusion list: {exclude_ids}")
        
        # Test query without exclusion
        print("\n🔍 Testing query WITHOUT exclusion:")
        query_no_exclusion = session.query(Article).filter(
            Article.published_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).order_by(Article.published_at.desc()).limit(10)
        
        articles_no_exclusion = query_no_exclusion.all()
        article_ids_no_exclusion = [str(article.id) for article in articles_no_exclusion]
        print(f"📊 Got {len(articles_no_exclusion)} articles without exclusion")
        print(f"📋 Article IDs: {article_ids_no_exclusion[:5]}...")
        
        # Test query WITH exclusion
        print("\n🔍 Testing query WITH exclusion:")
        query_with_exclusion = session.query(Article).filter(
            Article.published_at >= datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        if exclude_ids:
            try:
                exclude_uuids = [uuid.UUID(article_id) for article_id in exclude_ids]
                query_with_exclusion = query_with_exclusion.filter(~Article.id.in_(exclude_uuids))
                print(f"✅ Applied exclusion filter with {len(exclude_uuids)} UUIDs")
            except Exception as e:
                print(f"❌ Error converting to UUIDs: {e}")
                query_with_exclusion = query_with_exclusion.filter(~Article.id.in_(exclude_ids))
        
        query_with_exclusion = query_with_exclusion.order_by(Article.published_at.desc()).limit(10)
        articles_with_exclusion = query_with_exclusion.all()
        article_ids_with_exclusion = [str(article.id) for article in articles_with_exclusion]
        
        print(f"📊 Got {len(articles_with_exclusion)} articles with exclusion")
        print(f"📋 Article IDs: {article_ids_with_exclusion[:5]}...")
        
        # Check for excluded articles in results
        excluded_in_results = set(article_ids_with_exclusion) & set(exclude_ids)
        if excluded_in_results:
            print(f"❌ Found {len(excluded_in_results)} excluded articles in results: {list(excluded_in_results)}")
        else:
            print("✅ No excluded articles found in results")
        
        # Compare results
        common_articles = set(article_ids_no_exclusion) & set(article_ids_with_exclusion)
        print(f"📊 Common articles between queries: {len(common_articles)}")
        
        if len(common_articles) == len(article_ids_no_exclusion):
            print("⚠️  WARNING: All articles are the same - exclusion might not be working")
        else:
            print("✅ Exclusion appears to be working - different articles returned")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_direct_exclusion() 