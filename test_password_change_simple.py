#!/usr/bin/env python3
"""
Simple test script for password change endpoint
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

def test_password_change_simple():
    """Test the password change functionality with existing user"""
    
    # Test with existing user credentials
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    new_password = "newpassword456"
    
    log("Starting simple password change test")
    
    try:
        # Step 1: Try to login with existing user
        log("Step 1: Attempting to login with existing user")
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code != 200:
            log(f"Login failed: {login_response.status_code} - {login_response.text}", "ERROR")
            log("Trying to register a new user instead...")
            
            # Try registration
            register_data = {
                "email": "test@example.com",
                "password": "testpassword123",
                "username": "testuser",
                "display_name": "Test User"
            }
            
            register_response = requests.post(
                f"{BASE_URL}/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"}
            )
            
            if register_response.status_code != 201:
                log(f"Registration also failed: {register_response.status_code} - {register_response.text}", "ERROR")
                return False
            
            register_data = register_response.json()
            access_token = register_data["access_token"]
            log("User registered successfully")
        else:
            login_data = login_response.json()
            access_token = login_data["access_token"]
            log("Login successful")
        
        # Step 2: Test password change endpoint
        log("Step 2: Testing password change endpoint")
        password_change_data = {
            "current_password": login_data["password"],
            "new_password": new_password
        }
        
        change_response = requests.put(
            f"{BASE_URL}/users/password",
            json=password_change_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        log(f"Password change response: {change_response.status_code}")
        log(f"Response body: {change_response.text}")
        
        if change_response.status_code == 200:
            log("Password change successful! ✅")
            return True
        else:
            log(f"Password change failed: {change_response.status_code} - {change_response.text}", "ERROR")
            return False
        
    except requests.exceptions.ConnectionError:
        log("Connection error: Make sure the server is running on localhost:8000", "ERROR")
        return False
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "ERROR")
        return False

def test_endpoint_exists():
    """Test if the password change endpoint exists"""
    try:
        log("Testing if password change endpoint exists")
        
        # Test with invalid data to see if endpoint responds
        test_data = {
            "current_password": "test",
            "new_password": "test"
        }
        
        response = requests.put(
            f"{BASE_URL}/users/password",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should get 401 (unauthorized) not 404 (not found)
        if response.status_code == 401:
            log("Password change endpoint exists and requires authentication ✅")
            return True
        elif response.status_code == 404:
            log("Password change endpoint not found ❌", "ERROR")
            return False
        else:
            log(f"Unexpected response: {response.status_code} - {response.text}")
            return True
            
    except Exception as e:
        log(f"Error testing endpoint: {str(e)}", "ERROR")
        return False

def main():
    """Main test function"""
    log("=" * 50)
    log("SIMPLE PASSWORD CHANGE ENDPOINT TEST")
    log("=" * 50)
    
    # Test if endpoint exists
    endpoint_exists = test_endpoint_exists()
    
    if endpoint_exists:
        # Test password change functionality
        success = test_password_change_simple()
    else:
        success = False
    
    log("=" * 50)
    if success:
        log("PASSWORD CHANGE ENDPOINT IS WORKING! 🎉", "SUCCESS")
        sys.exit(0)
    else:
        log("PASSWORD CHANGE ENDPOINT TEST FAILED! ❌", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 