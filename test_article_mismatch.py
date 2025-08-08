#!/usr/bin/env python3
"""
Test to check if article IDs from API match database.
"""

import requests
import json
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User

def test_article_id_mismatch():
    """Test if API article IDs match database IDs."""
    print("🔍 Testing Article ID Mismatch")
    print("=" * 50)
    
    # Get articles from database
    session = Session(engine)
    db_articles = session.query(Article).limit(10).all()
    db_article_ids = [str(article.id) for article in db_articles]
    
    print(f"📊 Database has {len(db_articles)} articles")
    print(f"📋 Database article IDs: {db_article_ids[:5]}")
    
    # Get a test user for authentication
    test_user = session.query(User).first()
    if not test_user:
        print("❌ No users found in database")
        return
    
    print(f"👤 Using test user: {test_user.id}")
    
    # Try to get articles via API (this will require authentication)
    # For now, let's just check if the database articles are valid
    print("\n🔍 Checking if database articles are valid...")
    
    for i, article in enumerate(db_articles[:5]):
        print(f"  {i+1}. ID: {article.id}")
        print(f"     Title: {article.title[:50] if article.title else 'No title'}...")
        print(f"     Published: {article.published_at}")
        print(f"     Views: {article.views or 0}")
        print()
    
    # Check if any of the API-returned IDs exist in database
    api_returned_ids = [
        "ae7719ef-5c43-4e8c-aebd-087bd8472d1f",
        "e9ca25d0-5156-48c9-b0b3-ea0a0d258fc2", 
        "45e7ae2d-5265-456f-ac01-17441217add1",
        "410dc9d4-51c6-4827-b2b9-f220fd5cc206",
        "b3611faf-2cd1-4861-8710-2fb0c33d08eb"
    ]
    
    print(f"🔍 Checking if API-returned IDs exist in database...")
    print(f"📋 API-returned IDs: {api_returned_ids}")
    
    matches = []
    for api_id in api_returned_ids:
        try:
            import uuid
            api_uuid = uuid.UUID(api_id)
            article = session.query(Article).filter(Article.id == api_uuid).first()
            if article:
                matches.append(api_id)
                print(f"  ✅ Found: {api_id} -> {article.title[:30]}...")
            else:
                print(f"  ❌ Not found: {api_id}")
        except Exception as e:
            print(f"  ❌ Invalid UUID: {api_id} - {e}")
    
    print(f"\n📊 Summary:")
    print(f"  Database articles: {len(db_articles)}")
    print(f"  API-returned IDs: {len(api_returned_ids)}")
    print(f"  Matches: {len(matches)}")
    
    if len(matches) == 0:
        print(f"  ❌ NO MATCHES FOUND!")
        print(f"  This explains the 500 errors - the API is returning article IDs that don't exist in the database.")
        print(f"  Possible causes:")
        print(f"    1. Database was cleared/recreated")
        print(f"    2. Articles were recreated with new UUIDs")
        print(f"    3. Multiple database environments")
    else:
        print(f"  ✅ Found {len(matches)} matches")
    
    session.close()

if __name__ == "__main__":
    test_article_id_mismatch() 