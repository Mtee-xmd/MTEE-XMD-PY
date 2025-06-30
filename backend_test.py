#!/usr/bin/env python3
import requests
import json
import os
import time
import tempfile
from pathlib import Path

# Backend URL from frontend/.env
BACKEND_URL = "https://6a2ccdb7-9aa2-4a75-a5cd-6ebb915ef16d.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": []
}

def log_test_result(test_name, passed, message=""):
    """Log test result and print to console"""
    status = "PASSED" if passed else "FAILED"
    result = {"test": test_name, "status": status}
    
    if message:
        result["message"] = message
    
    if passed:
        test_results["passed"].append(result)
    else:
        test_results["failed"].append(result)
    
    print(f"[{status}] {test_name}")
    if message:
        print(f"  {message}")
    print()

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "healthy":
            log_test_result("Health Check Endpoint", True, f"Response: {data}")
            return True
        else:
            log_test_result("Health Check Endpoint", False, f"Unexpected response: {data}")
            return False
    except Exception as e:
        log_test_result("Health Check Endpoint", False, f"Error: {str(e)}")
        return False

def test_bot_status():
    """Test the bot status endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/bot/status")
        response.raise_for_status()
        data = response.json()
        
        # Check if the response contains expected fields
        required_fields = ["id", "is_connected", "last_seen"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            log_test_result("Bot Status Endpoint", True, f"Response: {data}")
            return True
        else:
            log_test_result("Bot Status Endpoint", False, 
                           f"Missing fields: {missing_fields}. Response: {data}")
            return False
    except Exception as e:
        log_test_result("Bot Status Endpoint", False, f"Error: {str(e)}")
        return False

def test_generate_qr():
    """Test the generate QR code endpoint"""
    try:
        response = requests.post(f"{API_BASE_URL}/bot/generate-qr")
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") and "qr_code" in data:
            log_test_result("Generate QR Code Endpoint", True, f"QR Code: {data['qr_code']}")
            return True, data.get("qr_code")
        else:
            log_test_result("Generate QR Code Endpoint", False, f"Unexpected response: {data}")
            return False, None
    except Exception as e:
        log_test_result("Generate QR Code Endpoint", False, f"Error: {str(e)}")
        return False, None

def test_connect_bot():
    """Test the connect bot endpoint"""
    try:
        response = requests.post(f"{API_BASE_URL}/bot/connect")
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            log_test_result("Connect Bot Endpoint", True, f"Response: {data}")
            return True
        else:
            log_test_result("Connect Bot Endpoint", False, f"Unexpected response: {data}")
            return False
    except Exception as e:
        log_test_result("Connect Bot Endpoint", False, f"Error: {str(e)}")
        return False

def test_list_sessions():
    """Test the list sessions endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/sessions")
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") and "sessions" in data:
            log_test_result("List Sessions Endpoint", True, 
                           f"Found {data.get('count', 0)} sessions")
            return True, data.get("sessions", [])
        else:
            log_test_result("List Sessions Endpoint", False, f"Unexpected response: {data}")
            return False, []
    except Exception as e:
        log_test_result("List Sessions Endpoint", False, f"Error: {str(e)}")
        return False, []

def test_upload_session_file():
    """Test uploading a session file"""
    try:
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False, suffix="_test_session.json") as temp_file:
            # Create mock WhatsApp session data
            mock_session = {
                "clientID": "test-client-id",
                "serverToken": "test-server-token",
                "clientToken": "test-client-token",
                "encKey": "test-enc-key",
                "macKey": "test-mac-key"
            }
            temp_file.write(json.dumps(mock_session).encode('utf-8'))
            temp_file_path = temp_file.name
        
        # Upload the file
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('test_session.json', f, 'application/json')}
            response = requests.post(f"{API_BASE_URL}/sessions/upload", files=files)
            response.raise_for_status()
            data = response.json()
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        if data.get("success") and "file_id" in data:
            log_test_result("Upload Session File", True, 
                           f"File ID: {data['file_id']}, Link: {data.get('public_link', 'N/A')}")
            return True, data.get("file_id")
        else:
            log_test_result("Upload Session File", False, f"Unexpected response: {data}")
            return False, None
    except Exception as e:
        log_test_result("Upload Session File", False, f"Error: {str(e)}")
        try:
            # Clean up the temporary file if it exists
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except:
            pass
        return False, None

def test_restore_session():
    """Test restoring a session"""
    try:
        response = requests.post(f"{API_BASE_URL}/bot/restore-session")
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            log_test_result("Restore Session Endpoint", True, f"Response: {data}")
            return True
        else:
            # This might be a valid response if no sessions exist
            if "No session files found" in data.get("message", ""):
                log_test_result("Restore Session Endpoint", True, 
                               "No sessions to restore (expected behavior)")
                return True
            else:
                log_test_result("Restore Session Endpoint", False, f"Unexpected response: {data}")
                return False
    except Exception as e:
        log_test_result("Restore Session Endpoint", False, f"Error: {str(e)}")
        return False

def verify_mega_connection():
    """Verify Mega.nz connection through health check"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        
        if data.get("mega_connected"):
            log_test_result("Mega.nz Connection", True, "Successfully connected to Mega.nz")
            return True
        else:
            log_test_result("Mega.nz Connection", False, "Not connected to Mega.nz")
            return False
    except Exception as e:
        log_test_result("Mega.nz Connection", False, f"Error: {str(e)}")
        return False

def verify_mongodb_connection():
    """Verify MongoDB connection indirectly through bot status endpoint"""
    try:
        # If we can get bot status, MongoDB is working
        response = requests.get(f"{API_BASE_URL}/bot/status")
        response.raise_for_status()
        
        log_test_result("MongoDB Connection", True, "Successfully connected to MongoDB")
        return True
    except Exception as e:
        log_test_result("MongoDB Connection", False, f"Error: {str(e)}")
        return False

def run_all_tests():
    """Run all tests in sequence"""
    print("=" * 50)
    print("STARTING BACKEND API TESTS")
    print("=" * 50)
    print(f"Backend URL: {API_BASE_URL}")
    print("=" * 50)
    
    # Test basic health and connections
    test_health_check()
    verify_mega_connection()
    verify_mongodb_connection()
    
    # Test bot status and control
    test_bot_status()
    qr_success, _ = test_generate_qr()
    if qr_success:
        # Wait a moment to ensure QR code is processed
        time.sleep(1)
        test_connect_bot()
    
    # Test session management
    sessions_success, sessions = test_list_sessions()
    upload_success, file_id = test_upload_session_file()
    
    # If upload succeeded, verify by listing sessions again
    if upload_success:
        time.sleep(2)  # Give some time for the upload to process
        test_list_sessions()
    
    # Test session restoration
    test_restore_session()
    
    # Print summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Total tests: {len(test_results['passed']) + len(test_results['failed'])}")
    print(f"Passed: {len(test_results['passed'])}")
    print(f"Failed: {len(test_results['failed'])}")
    
    if test_results['failed']:
        print("\nFailed Tests:")
        for test in test_results['failed']:
            print(f"- {test['test']}: {test.get('message', 'No details')}")
    
    print("=" * 50)

if __name__ == "__main__":
    run_all_tests()