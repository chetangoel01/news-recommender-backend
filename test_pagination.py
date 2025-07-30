#!/usr/bin/env python3
"""
Test script to verify feed pagination is working correctly.
"""

import asyncio
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User
from services.recommendation import RecommendationService

async def test_personalized_pagination():
    """Test personalized feed pagination."""
    print("🧪 Testing Personalized Feed Pagination...")
    
    session = Session(engine)
    
    try:
        # Get a test user
        user = session.query(User).first()
        if not user:
            print("❌ No users found in database!")
            return
        
        print(f"👤 Testing with user: {user.username}")
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(session)
        
        # First page
        print("\n📄 First page (limit=10):")
        first_page = await recommendation_service.get_personalized_recommendations(
            user=user, limit=10, diversify=False
        )
        
        print(f"Found {len(first_page)} articles")
        for i, (article, metadata) in enumerate(first_page):
            print(f"  {i+1}. {article.title[:50]}... (ID: {article.id})")
        
        if not first_page:
            print("❌ No articles in first page!")
            return
        
        # Get cursor from last article
        cursor = str(first_page[-1][0].id)
        print(f"\n🔗 Cursor for next page: {cursor}")
        
        # Second page
        print("\n📄 Second page (with cursor):")
        second_page = await recommendation_service.get_personalized_recommendations(
            user=user, limit=10, diversify=False, cursor=cursor
        )
        
        print(f"Found {len(second_page)} articles")
        for i, (article, metadata) in enumerate(second_page):
            print(f"  {i+1}. {article.title[:50]}... (ID: {article.id})")
        
        # Check for duplicates
        first_ids = {str(article.id) for article, _ in first_page}
        second_ids = {str(article.id) for article, _ in second_page}
        duplicates = first_ids.intersection(second_ids)
        
        if duplicates:
            print(f"❌ Found {len(duplicates)} duplicate articles!")
            for dup_id in duplicates:
                print(f"  Duplicate ID: {dup_id}")
        else:
            print("✅ No duplicates found - pagination working correctly!")
            
    except Exception as e:
        print(f"❌ Error testing pagination: {e}")
    finally:
        session.close()

def test_trending_pagination():
    """Test trending feed pagination."""
    print("\n🔥 Testing Trending Feed Pagination...")
    
    session = Session(engine)
    
    try:
        # Get articles with some engagement
        articles = session.query(Article).filter(
            Article.views > 0
        ).order_by(Article.views.desc()).limit(20).all()
        
        if not articles:
            print("❌ No articles with engagement found!")
            return
        
        print(f"📊 Found {len(articles)} articles with engagement")
        
        # Show first 5 articles
        print("\n📄 First 5 trending articles:")
        for i, article in enumerate(articles[:5]):
            trend_score = (article.views or 0) + (article.likes or 0) * 10 + (article.shares or 0) * 5
            print(f"  {i+1}. {article.title[:50]}... (Score: {trend_score})")
        
        # Test cursor logic
        if len(articles) >= 2:
            cursor_score = (articles[1].views or 0) + (articles[1].likes or 0) * 10 + (articles[1].shares or 0) * 5
            print(f"\n🔗 Testing cursor with score: {cursor_score}")
            
            # Get articles with lower scores
            lower_score_articles = []
            for article in articles:
                score = (article.views or 0) + (article.likes or 0) * 10 + (article.shares or 0) * 5
                if score < cursor_score:
                    lower_score_articles.append(article)
            
            print(f"📄 Found {len(lower_score_articles)} articles with lower scores")
            for i, article in enumerate(lower_score_articles[:5]):
                score = (article.views or 0) + (article.likes or 0) * 10 + (article.shares or 0) * 5
                print(f"  {i+1}. {article.title[:50]}... (Score: {score})")
        
    except Exception as e:
        print(f"❌ Error testing trending pagination: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Testing Feed Pagination...")
    
    # Test personalized pagination
    asyncio.run(test_personalized_pagination())
    
    # Test trending pagination
    test_trending_pagination()
    
    print("\n✅ Pagination testing complete!") 