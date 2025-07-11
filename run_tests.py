#!/usr/bin/env python3
"""
Test runner for News Recommender Backend

This script provides a convenient interface for running different test suites
with proper PostgreSQL database configuration and validation.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_database_config():
    """Check if database configuration is properly set up."""
    database_url = os.getenv("DATABASE_URL")
    test_database_url = os.getenv("TEST_DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        print("   Please set your PostgreSQL connection string:")
        print("   export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
        return False
    
    if not database_url.startswith("postgresql://"):
        print(f"❌ ERROR: DATABASE_URL must be a PostgreSQL connection string")
        print(f"   Current value starts with: {database_url.split('://')[0]}://")
        print("   Expected: postgresql://...")
        return False
    
    print(f"✅ Database configuration looks good")
    if test_database_url:
        print(f"✅ Separate test database configured")
    else:
        print(f"ℹ️  Using production database with '_test' suffix for testing")
    
    return True

def test_database_connection():
    """Test database connectivity before running tests."""
    print("🔍 Testing database connection...")
    
    try:
        # Import here to catch import errors
        from core.config import get_database_connection
        
        connection = get_database_connection()
        if connection:
            # Test pgvector extension
            cursor = connection.cursor()
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            result = cursor.fetchone()
            
            if result:
                print("✅ pgvector extension is available")
            else:
                print("⚠️  WARNING: pgvector extension not found")
                print("   Run: CREATE EXTENSION IF NOT EXISTS vector;")
            
            connection.close()
            return True
        else:
            print("❌ Failed to connect to database")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def run_command(command, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\n🚀 {description}")
    
    print(f"   Running: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {command[0]}")
        print("   Make sure pytest is installed: pip install pytest")
        return False

def show_help():
    """Show available commands."""
    print("""
🧪 News Recommender Backend Test Runner

USAGE:
    python run_tests.py <command>

COMMANDS:
    all          Run all tests (auth + users + integration)
    auth         Run authentication tests only  
    users        Run user profile tests only
    coverage     Run all tests with coverage report
    fast         Run tests without coverage (faster)
    verbose      Run tests with verbose output
    check        Check database configuration and connectivity
    help         Show this help message

EXAMPLES:
    python run_tests.py all         # Run all tests
    python run_tests.py auth        # Authentication tests only
    python run_tests.py coverage    # Generate coverage report
    python run_tests.py check       # Validate database setup

REQUIREMENTS:
    - PostgreSQL database with pgvector extension
    - DATABASE_URL environment variable set
    - All dependencies installed (pip install -r requirements.txt)

For more information, see TESTING_GUIDE.md
""")

def main():
    if len(sys.argv) != 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "help":
        show_help()
        return
    
    if command == "check":
        print("🔍 Checking database configuration...")
        if check_database_config() and test_database_connection():
            print("\n✅ All checks passed! Ready to run tests.")
        else:
            print("\n❌ Configuration issues found. Please fix before running tests.")
            sys.exit(1)
        return
    
    # Validate database configuration before running tests
    if not check_database_config():
        print("\n💡 Fix the database configuration and try again.")
        sys.exit(1)
    
    # Define test commands
    base_cmd = ["python", "-m", "pytest"]
    
    commands = {
        "all": {
            "cmd": base_cmd + ["tests/", "-v"],
            "desc": "Running all tests"
        },
        "auth": {
            "cmd": base_cmd + ["tests/test_auth.py", "-v", "-m", "auth"],
            "desc": "Running authentication tests"
        },
        "users": {
            "cmd": base_cmd + ["tests/test_users.py", "-v", "-m", "users"],
            "desc": "Running user profile tests"
        },
        "coverage": {
            "cmd": base_cmd + [
                "tests/", 
                "--cov=api", 
                "--cov=core", 
                "--cov-report=term-missing", 
                "--cov-report=html:htmlcov",
                "-v"
            ],
            "desc": "Running tests with coverage report"
        },
        "fast": {
            "cmd": base_cmd + ["tests/", "-v", "--disable-warnings"],
            "desc": "Running tests without coverage (faster)"
        },
        "verbose": {
            "cmd": base_cmd + ["tests/", "-vvv", "--tb=long"],
            "desc": "Running tests with verbose output"
        }
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)
    
    # Run the selected command
    test_config = commands[command]
    success = run_command(test_config["cmd"], test_config["desc"])
    
    if success:
        print(f"\n✅ {test_config['desc']} completed successfully!")
        
        if command == "coverage":
            print("\n📊 Coverage report generated:")
            print("   📄 Terminal: See output above")
            print("   🌐 HTML: Open htmlcov/index.html in your browser")
    else:
        print(f"\n❌ {test_config['desc']} failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 