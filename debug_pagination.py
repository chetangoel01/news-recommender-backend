#!/usr/bin/env python3
"""
Debug script to test pagination and score calculation.
"""

import asyncio
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User
from services.recommendation import RecommendationService

async def debug_pagination():
    """Debug pagination issues."""
    print("🔍 Debugging Pagination Issues...")
    
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
        
        # Test first page
        print("\n📄 Testing First Page:")
        first_page = await recommendation_service.get_personalized_recommendations(
            user=user, limit=5, diversify=False
        )
        
        print(f"Found {len(first_page)} articles")
        for i, (article, metadata) in enumerate(first_page):
            print(f"  {i+1}. {article.title[:50]}... (ID: {article.id})")
            print(f"      Reason: {metadata.get('reason', 'N/A')}")
            print(f"      Confidence: {metadata.get('confidence', 'N/A')}")
            if 'scores' in metadata:
                scores = metadata['scores']
                print(f"      Scores: {scores}")
        
        if not first_page:
            print("❌ No articles in first page!")
            return
        
        # Test cursor generation
        print("\n🔗 Testing Cursor Generation:")
        last_article, last_metadata = first_page[-1]
        print(f"Last article: {last_article.id}")
        print(f"Last metadata: {last_metadata}")
        
        if 'scores' in last_metadata and 'total_score' in last_metadata['scores']:
            score = last_metadata['scores']['total_score']
            print(f"Total score: {score}")
            
            # Generate cursor
            cursor = recommendation_service._encode_cursor(score, str(last_article.id))
            print(f"Generated cursor: {cursor[:50]}...")
            
            # Test second page
            print("\n📄 Testing Second Page:")
            second_page = await recommendation_service.get_personalized_recommendations(
                user=user, limit=5, diversify=False, cursor=cursor
            )
            
            print(f"Found {len(second_page)} articles")
            for i, (article, metadata) in enumerate(second_page):
                print(f"  {i+1}. {article.title[:50]}... (ID: {article.id})")
                print(f"      Reason: {metadata.get('reason', 'N/A')}")
                print(f"      Confidence: {metadata.get('confidence', 'N/A')}")
                if 'scores' in metadata:
                    scores = metadata['scores']
                    print(f"      Scores: {scores}")
            
            # Check for duplicates
            first_ids = {str(article.id) for article, _ in first_page}
            second_ids = {str(article.id) for article, _ in second_page}
            duplicates = first_ids.intersection(second_ids)
            
            if duplicates:
                print(f"❌ Found {len(duplicates)} duplicates: {duplicates}")
            else:
                print("✅ No duplicates found!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(debug_pagination()) 