#!/usr/bin/env python3
"""
Test the recommendation service directly with the same database session as the API.
"""

import uuid
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User, UserArticleView
from services.recommendation import RecommendationService
from datetime import datetime, timezone, timedelta

async def test_recommendation_service():
    """Test recommendation service directly."""
    print("🔍 Testing Recommendation Service Directly")
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
        
        # Check recent views
        recent_views = session.query(UserArticleView).filter(
            UserArticleView.user_id == str(test_user.id),
            UserArticleView.created_at >= datetime.now(timezone.utc) - timedelta(hours=12)
        ).all()
        
        print(f"📊 User has {len(recent_views)} recent views")
        for view in recent_views:
            print(f"   - Article {view.article_id} at {view.created_at}")
        
        # Get recommendation service with same session
        recommendation_service = RecommendationService(session)
        
        # Get exclusion list
        exclude_ids = recommendation_service._get_smart_exclusion_list(str(test_user.id))
        print(f"📊 Exclusion list has {len(exclude_ids)} articles: {exclude_ids}")
        
        # Get recommendations
        print("\n🔍 Getting recommendations...")
        recommendations = await recommendation_service.get_personalized_recommendations(
            user=test_user,
            limit=10,
            force_fresh=False
        )
        
        print(f"📊 Got {len(recommendations)} recommendations")
        if recommendations:
            article_ids = [str(article.id) for article, _ in recommendations]
            print(f"📋 Article IDs: {article_ids[:5]}...")
            
            # Check for excluded articles in recommendations
            excluded_in_recommendations = set(article_ids) & set(exclude_ids)
            if excluded_in_recommendations:
                print(f"❌ Found {len(excluded_in_recommendations)} excluded articles in recommendations: {list(excluded_in_recommendations)}")
            else:
                print("✅ No excluded articles found in recommendations")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_recommendation_service()) 