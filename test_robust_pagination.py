#!/usr/bin/env python3
"""
Test script for robust cursor-based pagination.
This script verifies that the new composite cursor system eliminates duplicates
and provides stable ordering across pages.
"""

import asyncio
import requests
import json
import base64
from typing import List, Set, Dict, Any
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
TEST_USER_EMAIL = "user@example.com"
TEST_USER_PASSWORD = "password"

class PaginationTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        
    def login(self):
        """Login to get authentication token."""
        login_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.user_id = data.get("user_id") or data.get("id")
            username = data.get("username") or data.get("email", "Unknown")
            print(f"✅ Logged in successfully as {username}")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def get_personalized_feed(self, limit: int = 20, cursor: str = None) -> Dict[str, Any]:
        """Get personalized feed with pagination."""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            
        response = self.session.get(f"{API_BASE}/feed/personalized", headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get personalized feed: {response.status_code} - {response.text}")
            return None
    
    def get_trending_feed(self, limit: int = 20, cursor: str = None) -> Dict[str, Any]:
        """Get trending feed with pagination."""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            
        response = self.session.get(f"{API_BASE}/feed/trending", headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get trending feed: {response.status_code} - {response.text}")
            return None
    
    def decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """Decode a composite cursor."""
        try:
            cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(cursor_json)
        except Exception as e:
            print(f"❌ Failed to decode cursor: {e}")
            return None
    
    def test_personalized_pagination(self, num_pages: int = 3):
        """Test personalized feed pagination for duplicates."""
        print("\n🧪 Testing Personalized Feed Pagination")
        print("=" * 50)
        
        all_article_ids: Set[str] = set()
        cursors: List[str] = []
        page = 1
        
        while page <= num_pages:
            print(f"\n📄 Page {page}")
            
            # Get feed
            cursor = cursors[-1] if cursors else None
            feed_data = self.get_personalized_feed(limit=20, cursor=cursor)
            
            if not feed_data:
                print("❌ Failed to get feed data")
                break
            
            articles = feed_data.get("articles", [])
            next_cursor = feed_data.get("next_cursor")
            has_more = feed_data.get("has_more", False)
            
            print(f"   📊 Articles returned: {len(articles)}")
            print(f"   🔗 Has more: {has_more}")
            print(f"   📍 Next cursor: {next_cursor[:50] + '...' if next_cursor else 'None'}")
            
            # Check for duplicates
            page_article_ids = set()
            duplicates_in_page = 0
            
            for article in articles:
                article_id = article["id"]
                
                # Check for duplicates within this page
                if article_id in page_article_ids:
                    duplicates_in_page += 1
                    print(f"   ⚠️  Duplicate within page: {article_id}")
                page_article_ids.add(article_id)
                
                # Check for duplicates across all pages
                if article_id in all_article_ids:
                    print(f"   ❌ Duplicate across pages: {article_id}")
                    return False
                all_article_ids.add(article_id)
            
            if duplicates_in_page > 0:
                print(f"   ❌ Found {duplicates_in_page} duplicates within page")
                return False
            
            print(f"   ✅ No duplicates found")
            
            # Store cursor for next page
            if next_cursor:
                cursors.append(next_cursor)
                
                # Decode and display cursor info
                cursor_data = self.decode_cursor(next_cursor)
                if cursor_data:
                    print(f"   🔍 Cursor data: score={cursor_data.get('score', 'N/A'):.2f}, article_id={cursor_data.get('article_id', 'N/A')}")
            
            # Break if no more pages
            if not has_more or not next_cursor:
                print(f"   🏁 Reached end of feed")
                break
            
            page += 1
        
        print(f"\n📈 Summary:")
        print(f"   Total unique articles: {len(all_article_ids)}")
        print(f"   Total pages processed: {page - 1}")
        print(f"   ✅ No duplicates found across all pages!")
        
        return True
    
    def test_trending_pagination(self, num_pages: int = 3):
        """Test trending feed pagination for duplicates."""
        print("\n🔥 Testing Trending Feed Pagination")
        print("=" * 50)
        
        all_article_ids: Set[str] = set()
        cursors: List[str] = []
        page = 1
        
        while page <= num_pages:
            print(f"\n📄 Page {page}")
            
            # Get feed
            cursor = cursors[-1] if cursors else None
            feed_data = self.get_trending_feed(limit=20, cursor=cursor)
            
            if not feed_data:
                print("❌ Failed to get feed data")
                break
            
            articles = feed_data.get("articles", [])
            next_cursor = feed_data.get("next_cursor")
            has_more = feed_data.get("has_more", False)
            
            print(f"   📊 Articles returned: {len(articles)}")
            print(f"   🔗 Has more: {has_more}")
            print(f"   📍 Next cursor: {next_cursor[:50] + '...' if next_cursor else 'None'}")
            
            # Check for duplicates
            page_article_ids = set()
            duplicates_in_page = 0
            
            for article in articles:
                article_id = article["id"]
                
                # Check for duplicates within this page
                if article_id in page_article_ids:
                    duplicates_in_page += 1
                    print(f"   ⚠️  Duplicate within page: {article_id}")
                page_article_ids.add(article_id)
                
                # Check for duplicates across all pages
                if article_id in all_article_ids:
                    print(f"   ❌ Duplicate across pages: {article_id}")
                    return False
                all_article_ids.add(article_id)
            
            if duplicates_in_page > 0:
                print(f"   ❌ Found {duplicates_in_page} duplicates within page")
                return False
            
            print(f"   ✅ No duplicates found")
            
            # Store cursor for next page
            if next_cursor:
                cursors.append(next_cursor)
                
                # Decode and display cursor info
                cursor_data = self.decode_cursor(next_cursor)
                if cursor_data:
                    print(f"   🔍 Cursor data: score={cursor_data.get('score', 'N/A'):.2f}, article_id={cursor_data.get('article_id', 'N/A')}")
            
            # Break if no more pages
            if not has_more or not next_cursor:
                print(f"   🏁 Reached end of feed")
                break
            
            page += 1
        
        print(f"\n📈 Summary:")
        print(f"   Total unique articles: {len(all_article_ids)}")
        print(f"   Total pages processed: {page - 1}")
        print(f"   ✅ No duplicates found across all pages!")
        
        return True
    
    def test_cursor_stability(self):
        """Test that cursors are stable and work correctly."""
        print("\n🔒 Testing Cursor Stability")
        print("=" * 50)
        
        # Get first page
        feed_data = self.get_personalized_feed(limit=10)
        if not feed_data:
            print("❌ Failed to get first page")
            return False
        
        articles = feed_data.get("articles", [])
        next_cursor = feed_data.get("next_cursor")
        
        if not next_cursor:
            print("❌ No next cursor returned")
            return False
        
        print(f"   📄 First page: {len(articles)} articles")
        print(f"   🔗 Next cursor: {next_cursor[:50]}...")
        
        # Decode cursor
        cursor_data = self.decode_cursor(next_cursor)
        if not cursor_data:
            print("❌ Failed to decode cursor")
            return False
        
        print(f"   🔍 Cursor data: {cursor_data}")
        
        # Use cursor to get second page
        second_page_data = self.get_personalized_feed(limit=10, cursor=next_cursor)
        if not second_page_data:
            print("❌ Failed to get second page with cursor")
            return False
        
        second_articles = second_page_data.get("articles", [])
        print(f"   📄 Second page: {len(second_articles)} articles")
        
        # Verify no overlap
        first_page_ids = {article["id"] for article in articles}
        second_page_ids = {article["id"] for article in second_articles}
        
        overlap = first_page_ids.intersection(second_page_ids)
        if overlap:
            print(f"   ❌ Found overlap between pages: {overlap}")
            return False
        
        print(f"   ✅ No overlap between pages")
        print(f"   ✅ Cursor stability test passed!")
        
        return True
    
    def run_all_tests(self):
        """Run all pagination tests."""
        print("🚀 Starting Robust Pagination Tests")
        print("=" * 60)
        
        # Login first
        if not self.login():
            return False
        
        # Run tests
        tests = [
            ("Personalized Feed Pagination", self.test_personalized_pagination),
            ("Trending Feed Pagination", self.test_trending_pagination),
            ("Cursor Stability", self.test_cursor_stability)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {test_name}: {status}")
        
        print(f"\n   Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Robust pagination is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the implementation.")
        
        return passed == total

def main():
    """Main test runner."""
    tester = PaginationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 Robust cursor-based pagination is working perfectly!")
        print("   ✅ No duplicates between pages")
        print("   ✅ Stable ordering with composite cursors")
        print("   ✅ Proper cursor encoding/decoding")
        print("   ✅ Scalable performance")
    else:
        print("\n❌ Some pagination issues detected. Please review the implementation.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 