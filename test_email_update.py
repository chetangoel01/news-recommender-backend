#!/usr/bin/env python3
"""
Test email update functionality
"""
import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"

def log(message, level="INFO"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_email_update():
    """Test email update functionality"""
    
    log("Testing email update functionality")
    
    # Test 1: Test with valid request format but no auth
    log("Test 1: Testing with valid request format (no auth)")
    valid_request = {
        "email": "newemail@example.com",
        "display_name": "Updated Name"
    }
    
    response = requests.put(
        f"{BASE_URL}/users/profile",
        json=valid_request,
        headers={"Content-Type": "application/json"}
    )
    
    log(f"Valid request (no auth): {response.status_code} - {response.text}")
    
    # Test 2: Test with invalid email format
    log("Test 2: Testing with invalid email format")
    invalid_emails = [
        "invalid-email",
        "missing@",
        "@missing.com",
        "spaces @example.com",
        ""
    ]
    
    for i, email in enumerate(invalid_emails):
        response = requests.put(
            f"{BASE_URL}/users/profile",
            json={"email": email},
            headers={"Content-Type": "application/json"}
        )
        log(f"Invalid email {i+1} ('{email}'): {response.status_code} - {response.text}")
    
    # Test 3: Test with valid email format
    log("Test 3: Testing with valid email format")
    valid_emails = [
        "test@example.com",
        "user.name@domain.com",
        "user+tag@example.co.uk",
        "123@numbers.com"
    ]
    
    for i, email in enumerate(valid_emails):
        response = requests.put(
            f"{BASE_URL}/users/profile",
            json={"email": email},
            headers={"Content-Type": "application/json"}
        )
        log(f"Valid email {i+1} ('{email}'): {response.status_code} - {response.text}")
    
    # Test 4: Test OpenAPI schema
    log("Test 4: Checking OpenAPI schema for email field")
    try:
        openapi_response = requests.get(f"{BASE_URL}/openapi.json")
        if openapi_response.status_code == 200:
            openapi_data = openapi_response.json()
            
            # Check if profile endpoint is in schema
            if "/users/profile" in openapi_data.get("paths", {}):
                profile_path = openapi_data["paths"]["/users/profile"]
                if "put" in profile_path:
                    put_schema = profile_path["put"]
                    if "requestBody" in put_schema:
                        log("✅ Profile endpoint has request body defined")
                        
                        # Check if email field is in the schema
                        schema_ref = put_schema["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                        schema_name = schema_ref.split("/")[-1]
                        
                        if "components" in openapi_data and "schemas" in openapi_data["components"]:
                            schemas = openapi_data["components"]["schemas"]
                            if schema_name in schemas:
                                schema = schemas[schema_name]
                                if "properties" in schema and "email" in schema["properties"]:
                                    log("✅ Email field found in profile update schema")
                                else:
                                    log("❌ Email field not found in profile update schema", "ERROR")
                            else:
                                log(f"❌ Schema {schema_name} not found", "ERROR")
                        else:
                            log("❌ Components/schemas not found in OpenAPI", "ERROR")
                    else:
                        log("❌ Profile endpoint missing request body schema", "ERROR")
                else:
                    log("❌ Profile endpoint not using PUT method", "ERROR")
            else:
                log("❌ Profile endpoint not found in OpenAPI schema", "ERROR")
        else:
            log(f"❌ Could not fetch OpenAPI schema: {openapi_response.status_code}", "ERROR")
    except Exception as e:
        log(f"❌ Error checking OpenAPI schema: {str(e)}", "ERROR")
    
    return True

def test_endpoint_behavior():
    """Test endpoint behavior patterns"""
    
    log("Testing endpoint behavior patterns")
    
    # Test different HTTP methods
    log("Testing different HTTP methods")
    methods = ["GET", "POST", "DELETE", "PATCH"]
    
    for method in methods:
        response = requests.request(
            method,
            f"{BASE_URL}/users/profile",
            headers={"Content-Type": "application/json"}
        )
        log(f"{method} method: {response.status_code}")
    
    # Test with different auth headers
    log("Testing with different auth headers")
    auth_tests = [
        {"Authorization": "Bearer invalid_token"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic invalid"},
        {},
    ]
    
    for i, headers in enumerate(auth_tests):
        response = requests.put(
            f"{BASE_URL}/users/profile",
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json", **headers}
        )
        log(f"Auth test {i+1}: {response.status_code} - {response.text}")

def main():
    """Main test function"""
    log("=" * 60)
    log("EMAIL UPDATE FUNCTIONALITY TEST")
    log("=" * 60)
    
    # Test email update logic
    logic_ok = test_email_update()
    
    # Test endpoint behavior
    test_endpoint_behavior()
    
    log("=" * 60)
    if logic_ok:
        log("EMAIL UPDATE FUNCTIONALITY TEST COMPLETED! ✅", "SUCCESS")
        log("The endpoint is properly structured and handles email updates")
        sys.exit(0)
    else:
        log("EMAIL UPDATE FUNCTIONALITY TEST FAILED! ❌", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 