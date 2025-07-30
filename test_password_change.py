#!/usr/bin/env python3
"""
Test script for password change endpoint
"""
import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "v1"

def log(message, level="INFO"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_password_change():
    """Test the password change functionality"""
    
    # Test data
    test_user = {
        "email": "test@example.com",
        "password": "testpassword123",
        "username": "testuser",
        "display_name": "Test User"
    }
    
    new_password = "newpassword456"
    
    log("Starting password change endpoint test")
    
    try:
        # Step 1: Register a test user
        log("Step 1: Registering test user")
        register_response = requests.post(
            f"{BASE_URL}/auth/register",
            json=test_user,
            headers={"Content-Type": "application/json"}
        )
        
        if register_response.status_code != 201:
            log(f"Registration failed: {register_response.status_code} - {register_response.text}", "ERROR")
            return False
            
        register_data = register_response.json()
        access_token = register_data["access_token"]
        log("User registered successfully")
        
        # Step 2: Test password change with correct current password
        log("Step 2: Testing password change with correct current password")
        password_change_data = {
            "current_password": test_user["password"],
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
        
        if change_response.status_code == 200:
            log("Password change successful with correct current password")
        else:
            log(f"Password change failed: {change_response.status_code} - {change_response.text}", "ERROR")
            return False
        
        # Step 3: Test login with new password
        log("Step 3: Testing login with new password")
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": test_user["email"],
                "password": new_password
            },
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code == 200:
            log("Login successful with new password")
        else:
            log(f"Login with new password failed: {login_response.status_code} - {login_response.text}", "ERROR")
            return False
        
        # Step 4: Test password change with incorrect current password
        log("Step 4: Testing password change with incorrect current password")
        wrong_password_data = {
            "current_password": "wrongpassword",
            "new_password": "anotherpassword789"
        }
        
        wrong_change_response = requests.put(
            f"{BASE_URL}/users/password",
            json=wrong_password_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if wrong_change_response.status_code == 400:
            log("Correctly rejected password change with wrong current password")
        else:
            log(f"Unexpected response for wrong password: {wrong_change_response.status_code} - {wrong_change_response.text}", "ERROR")
            return False
        
        # Step 5: Test password change with short new password
        log("Step 5: Testing password change with short new password")
        short_password_data = {
            "current_password": new_password,
            "new_password": "short"
        }
        
        short_change_response = requests.put(
            f"{BASE_URL}/users/password",
            json=short_password_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if short_change_response.status_code == 422:
            log("Correctly rejected password change with short new password")
        else:
            log(f"Unexpected response for short password: {short_change_response.status_code} - {short_change_response.text}", "ERROR")
            return False
        
        # Step 6: Test password change without authentication
        log("Step 6: Testing password change without authentication")
        no_auth_response = requests.put(
            f"{BASE_URL}/users/password",
            json=password_change_data,
            headers={"Content-Type": "application/json"}
        )
        
        if no_auth_response.status_code == 401:
            log("Correctly rejected password change without authentication")
        else:
            log(f"Unexpected response without auth: {no_auth_response.status_code} - {no_auth_response.text}", "ERROR")
            return False
        
        log("All password change tests passed! ✅", "SUCCESS")
        return True
        
    except requests.exceptions.ConnectionError:
        log("Connection error: Make sure the server is running on localhost:8000", "ERROR")
        return False
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "ERROR")
        return False

def test_endpoint_documentation():
    """Test if the endpoint is properly documented"""
    try:
        log("Testing endpoint documentation")
        docs_response = requests.get(f"{BASE_URL}/docs")
        
        if docs_response.status_code == 200:
            log("API documentation is accessible")
            
            # Check if password endpoint is mentioned in docs
            if "/users/password" in docs_response.text:
                log("Password change endpoint is documented")
            else:
                log("Password change endpoint not found in documentation", "WARNING")
        else:
            log(f"Could not access API documentation: {docs_response.status_code}", "WARNING")
            
    except Exception as e:
        log(f"Error checking documentation: {str(e)}", "WARNING")

def main():
    """Main test function"""
    log("=" * 50)
    log("PASSWORD CHANGE ENDPOINT TEST")
    log("=" * 50)
    
    # Test endpoint documentation
    test_endpoint_documentation()
    
    # Test password change functionality
    success = test_password_change()
    
    log("=" * 50)
    if success:
        log("ALL TESTS PASSED! 🎉", "SUCCESS")
        sys.exit(0)
    else:
        log("SOME TESTS FAILED! ❌", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 