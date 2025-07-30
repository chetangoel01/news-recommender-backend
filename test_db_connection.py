#!/usr/bin/env python3
"""
Test database connection and basic operations
"""
import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"

def log(message, level="INFO"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_basic_endpoints():
    """Test basic endpoints to see what's working"""
    
    log("Testing basic endpoints")
    
    # Test health endpoint
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        log(f"Health endpoint: {health_response.status_code} - {health_response.text}")
    except Exception as e:
        log(f"Health endpoint error: {str(e)}", "ERROR")
    
    # Test OpenAPI schema
    try:
        openapi_response = requests.get(f"{BASE_URL}/openapi.json")
        log(f"OpenAPI endpoint: {openapi_response.status_code}")
        if openapi_response.status_code == 200:
            openapi_data = openapi_response.json()
            log(f"Available paths: {list(openapi_data.get('paths', {}).keys())}")
    except Exception as e:
        log(f"OpenAPI endpoint error: {str(e)}", "ERROR")
    
    # Test registration with detailed error
    try:
        test_user = {
            "email": "debug@example.com",
            "password": "testpassword123",
            "username": "debuguser",
            "display_name": "Debug User"
        }
        
        log("Testing registration with detailed logging...")
        register_response = requests.post(
            f"{BASE_URL}/auth/register",
            json=test_user,
            headers={"Content-Type": "application/json"}
        )
        
        log(f"Registration response: {register_response.status_code}")
        log(f"Registration headers: {dict(register_response.headers)}")
        log(f"Registration body: {register_response.text}")
        
        if register_response.status_code != 201:
            log("Registration failed - checking if it's a database issue", "ERROR")
            
            # Try a simpler request to see if it's a general server issue
            simple_response = requests.get(f"{BASE_URL}/docs")
            log(f"Docs endpoint: {simple_response.status_code}")
            
    except Exception as e:
        log(f"Registration test error: {str(e)}", "ERROR")

def test_auth_endpoints():
    """Test authentication endpoints"""
    
    log("Testing authentication endpoints")
    
    # Test login with non-existent user
    try:
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"},
            headers={"Content-Type": "application/json"}
        )
        log(f"Login with non-existent user: {login_response.status_code} - {login_response.text}")
    except Exception as e:
        log(f"Login test error: {str(e)}", "ERROR")

def main():
    """Main test function"""
    log("=" * 50)
    log("DATABASE CONNECTION TEST")
    log("=" * 50)
    
    test_basic_endpoints()
    test_auth_endpoints()
    
    log("=" * 50)
    log("Database connection test completed")

if __name__ == "__main__":
    main() 