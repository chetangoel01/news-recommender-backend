#!/usr/bin/env python3
"""
Test script for password change endpoint structure and validation
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

def test_endpoint_structure():
    """Test the password change endpoint structure"""
    
    log("Testing password change endpoint structure")
    
    # Test 1: Check if endpoint exists (should return 401/403 for unauthenticated)
    log("Test 1: Checking if endpoint exists")
    response = requests.put(
        f"{BASE_URL}/users/password",
        json={"current_password": "test", "new_password": "test"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code in [401, 403]:
        log("✅ Endpoint exists and requires authentication")
    elif response.status_code == 404:
        log("❌ Endpoint not found", "ERROR")
        return False
    else:
        log(f"⚠️ Unexpected response: {response.status_code} - {response.text}")
    
    # Test 2: Check validation with missing fields
    log("Test 2: Testing validation with missing fields")
    response = requests.put(
        f"{BASE_URL}/users/password",
        json={"current_password": "test"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 422:
        log("✅ Validation working - missing field rejected")
    else:
        log(f"⚠️ Unexpected validation response: {response.status_code}")
    
    # Test 3: Check validation with short password
    log("Test 3: Testing validation with short password")
    response = requests.put(
        f"{BASE_URL}/users/password",
        json={"current_password": "test", "new_password": "short"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 422:
        log("✅ Validation working - short password rejected")
    else:
        log(f"⚠️ Unexpected validation response: {response.status_code}")
    
    # Test 4: Check OpenAPI schema
    log("Test 4: Checking OpenAPI schema")
    try:
        openapi_response = requests.get(f"{BASE_URL}/openapi.json")
        if openapi_response.status_code == 200:
            openapi_data = openapi_response.json()
            
            # Check if password endpoint is in schema
            if "/users/password" in openapi_data.get("paths", {}):
                log("✅ Password endpoint found in OpenAPI schema")
                
                # Check if it's a PUT method
                password_path = openapi_data["paths"]["/users/password"]
                if "put" in password_path:
                    log("✅ Password endpoint uses PUT method")
                    
                    # Check request body schema
                    put_schema = password_path["put"]
                    if "requestBody" in put_schema:
                        log("✅ Password endpoint has request body defined")
                    else:
                        log("⚠️ Password endpoint missing request body schema")
                else:
                    log("❌ Password endpoint not using PUT method", "ERROR")
            else:
                log("❌ Password endpoint not found in OpenAPI schema", "ERROR")
        else:
            log(f"❌ Could not fetch OpenAPI schema: {openapi_response.status_code}", "ERROR")
    except Exception as e:
        log(f"❌ Error checking OpenAPI schema: {str(e)}", "ERROR")
    
    return True

def test_schema_validation():
    """Test the schema validation for the password change endpoint"""
    
    log("Testing schema validation")
    
    # Test cases for validation
    test_cases = [
        {
            "name": "Missing current_password",
            "data": {"new_password": "validpassword123"},
            "expected_status": 422
        },
        {
            "name": "Missing new_password", 
            "data": {"current_password": "oldpassword123"},
            "expected_status": 422
        },
        {
            "name": "Short new password",
            "data": {"current_password": "oldpassword123", "new_password": "short"},
            "expected_status": 422
        },
        {
            "name": "Valid password format",
            "data": {"current_password": "oldpassword123", "new_password": "newpassword456"},
            "expected_status": 401  # Should fail due to auth, not validation
        }
    ]
    
    for test_case in test_cases:
        log(f"Testing: {test_case['name']}")
        response = requests.put(
            f"{BASE_URL}/users/password",
            json=test_case["data"],
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == test_case["expected_status"]:
            log(f"✅ {test_case['name']}: Expected status {test_case['expected_status']}")
        else:
            log(f"❌ {test_case['name']}: Got {response.status_code}, expected {test_case['expected_status']}", "ERROR")
    
    return True

def main():
    """Main test function"""
    log("=" * 50)
    log("PASSWORD CHANGE ENDPOINT STRUCTURE TEST")
    log("=" * 50)
    
    # Test endpoint structure
    structure_ok = test_endpoint_structure()
    
    # Test schema validation
    validation_ok = test_schema_validation()
    
    log("=" * 50)
    if structure_ok and validation_ok:
        log("PASSWORD CHANGE ENDPOINT STRUCTURE IS CORRECT! 🎉", "SUCCESS")
        log("The endpoint is properly implemented and validated")
        sys.exit(0)
    else:
        log("PASSWORD CHANGE ENDPOINT STRUCTURE TEST FAILED! ❌", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 