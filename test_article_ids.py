#!/usr/bin/env python3
"""
Test script to check article ID consistency between API and database.
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"

def test_article_ids_from_api():
    """Test getting articles from API and check their IDs"""
    print("🧪 Testing article IDs from API...")
    
    try:
        # Get articles from API (without auth, should work for public endpoints)
        response = requests.get(f"{BASE_URL}/articles?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            print(f"📋 Found {len(articles)} articles from API")
            for i, article in enumerate(articles):
                print(f"  {i+1}. ID: {article.get('id')} - Title: {article.get('title', 'No title')[:50]}...")
            
            return [article.get('id') for article in articles]
        else:
            print(f"❌ Failed to get articles: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting articles: {e}")
        return []

def test_article_ids_from_database():
    """Test getting article IDs directly from database"""
    print("\n🧪 Testing article IDs from database...")
    
    try:
        from core.models import Article
        from core.db import engine
        from sqlalchemy.orm import Session
        
        session = Session(engine)
        articles = session.query(Article).limit(5).all()
        
        print(f"📋 Found {len(articles)} articles from database")
        for i, article in enumerate(articles):
            print(f"  {i+1}. ID: {article.id} - Title: {article.title[:50] if article.title else 'No title'}...")
        
        session.close()
        return [str(article.id) for article in articles]
        
    except Exception as e:
        print(f"❌ Error getting articles from database: {e}")
        return []

def compare_article_ids():
    """Compare article IDs from API vs database"""
    print("\n🔍 Comparing article IDs...")
    
    api_ids = test_article_ids_from_api()
    db_ids = test_article_ids_from_database()
    
    print(f"\n📊 Summary:")
    print(f"  API article IDs: {len(api_ids)}")
    print(f"  DB article IDs: {len(db_ids)}")
    
    if api_ids and db_ids:
        # Check if any IDs match
        matches = set(api_ids) & set(db_ids)
        print(f"  Matching IDs: {len(matches)}")
        
        if matches:
            print(f"  ✅ Some IDs match between API and database")
        else:
            print(f"  ❌ No IDs match between API and database")
            print(f"  This could be the cause of the 500 errors!")

if __name__ == "__main__":
    print("🔧 Testing article ID consistency...")
    compare_article_ids() 