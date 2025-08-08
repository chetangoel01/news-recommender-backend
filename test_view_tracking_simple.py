#!/usr/bin/env python3
"""
Simple test for view tracking endpoint with valid article ID.
"""

import requests
import json
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article, User

def test_view_tracking_with_valid_article():
    """Test view tracking with a valid article ID from database."""
    print("🔍 Testing View Tracking with Valid Article")
    print("=" * 50)
    
    # Get a valid article from database
    session = Session(engine)
    article = session.query(Article).first()
    
    if not article:
        print("❌ No articles found in database")
        return
    
    print(f"📄 Using article: {article.id}")
    print(f"   Title: {article.title[:50] if article.title else 'No title'}...")
    
    # Test the view tracking endpoint
    url = f"http://localhost:8000/articles/{article.id}/view"
    data = {
        "read_time_seconds": 30,
        "interaction_strength": 0.8,
        "interaction_type": "view"
    }
    
    print(f"\n🌐 Testing view tracking endpoint...")
    print(f"   URL: {url}")
    print(f"   Data: {data}")
    
    try:
        response = requests.post(url, json=data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 403:
            print("   ✅ Correctly rejected without authentication")
        elif response.status_code == 200:
            print("   ✅ View tracking successful!")
        elif response.status_code == 404:
            print("   ❌ Article not found")
        elif response.status_code == 500:
            print("   ❌ Internal server error")
            print("   This suggests an issue with the view tracking logic")
        else:
            print(f"   ❓ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    session.close()

if __name__ == "__main__":
    test_view_tracking_with_valid_article() 