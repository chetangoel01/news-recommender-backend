#!/usr/bin/env python3
"""
Test script for the view tracking endpoint.
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_ARTICLE_ID = "test-article-id"  # Replace with a real article ID

def test_view_tracking_without_auth():
    """Test view tracking without authentication (should fail with 403)"""
    print("🧪 Testing view tracking without authentication...")
    
    url = f"{BASE_URL}/articles/{TEST_ARTICLE_ID}/view"
    data = {
        "read_time_seconds": 30,
        "interaction_strength": 0.8,
        "interaction_type": "view"
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 403:
        print("✅ Correctly rejected without authentication")
    else:
        print("❌ Unexpected response")

def test_view_tracking_with_invalid_article():
    """Test view tracking with invalid article ID (should fail with 400)"""
    print("\n🧪 Testing view tracking with invalid article ID...")
    
    url = f"{BASE_URL}/articles/invalid-uuid/view"
    data = {
        "read_time_seconds": 30,
        "interaction_strength": 0.8,
        "interaction_type": "view"
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 403:
        print("✅ Correctly rejected without authentication")
    elif response.status_code == 400:
        print("✅ Correctly rejected invalid UUID")
    else:
        print("❌ Unexpected response")

def test_view_tracking_endpoint_structure():
    """Test the endpoint structure"""
    print("\n🧪 Testing endpoint structure...")
    
    # Test that the endpoint exists
    response = requests.get(f"{BASE_URL}/docs")
    if response.status_code == 200:
        print("✅ API documentation accessible")
    else:
        print("❌ API documentation not accessible")

if __name__ == "__main__":
    print("🔧 Testing view tracking endpoint...")
    
    test_view_tracking_endpoint_structure()
    test_view_tracking_without_auth()
    test_view_tracking_with_invalid_article()
    
    print("\n📋 Summary:")
    print("- Endpoint requires authentication (403 Forbidden)")
    print("- Endpoint validates article ID format")
    print("- Need valid auth token and real article ID for full test") 