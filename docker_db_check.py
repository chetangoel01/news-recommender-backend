#!/usr/bin/env python3
"""
Database health check script for Docker container
Run this inside the Docker container to diagnose database issues
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def check_environment():
    """Check environment variables"""
    print("🔍 Checking environment variables...")
    env_vars = ['host', 'port', 'dbname', 'user', 'password', 'DATABASE_URL']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'password' in var.lower():
                print(f"  ✅ {var}: {'*' * len(value)}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")

def test_database_connection():
    """Test database connection"""
    print("\n🔌 Testing database connection...")
    
    try:
        # Try DATABASE_URL first
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            print("  📡 Using DATABASE_URL...")
            conn = psycopg2.connect(database_url)
        else:
            print("  📡 Using individual connection parameters...")
            conn = psycopg2.connect(
                host=os.getenv("host", "localhost"),
                port=os.getenv("port", "5432"),
                database=os.getenv("dbname", "postgres"),
                user=os.getenv("user", ""),
                password=os.getenv("password", "")
            )
        
        print("  ✅ Database connection successful!")
        
        # Test basic query
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT version();")
            result = cur.fetchone()
            print(f"  📊 Database version: {result['version']}")
            
            # Check current database
            cur.execute("SELECT current_database();")
            db_name = cur.fetchone()['current_database']
            print(f"  🗄️  Current database: {db_name}")
            
            # Check current user
            cur.execute("SELECT current_user;")
            user = cur.fetchone()['current_user']
            print(f"  👤 Current user: {user}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def check_tables():
    """Check if required tables exist"""
    print("\n📋 Checking database tables...")
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            conn = psycopg2.connect(
                host=os.getenv("host", "localhost"),
                port=os.getenv("port", "5432"),
                database=os.getenv("dbname", "postgres"),
                user=os.getenv("user", ""),
                password=os.getenv("password", "")
            )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check all tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            
            print(f"  📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"    - {table['table_name']}")
            
            # Check if users table exists
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users';
            """)
            result = cur.fetchone()
            if result:
                print("  ✅ Users table exists")
                
                # Check users table structure
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()
                print("  📋 Users table structure:")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    default = f" (default: {col['column_default']})" if col['column_default'] else ""
                    print(f"    - {col['column_name']}: {col['data_type']} {nullable}{default}")
            else:
                print("  ❌ Users table does not exist")
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Table check failed: {e}")
        return False

def check_extensions():
    """Check if required extensions are installed"""
    print("\n🔧 Checking database extensions...")
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            conn = psycopg2.connect(
                host=os.getenv("host", "localhost"),
                port=os.getenv("port", "5432"),
                database=os.getenv("dbname", "postgres"),
                user=os.getenv("user", ""),
                password=os.getenv("password", "")
            )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check all extensions
            cur.execute("""
                SELECT extname, extversion 
                FROM pg_extension 
                ORDER BY extname;
            """)
            extensions = cur.fetchall()
            
            print(f"  📦 Found {len(extensions)} extensions:")
            for ext in extensions:
                print(f"    - {ext['extname']} (v{ext['extversion']})")
            
            # Check specifically for vector extension
            cur.execute("""
                SELECT extname FROM pg_extension WHERE extname = 'vector';
            """)
            result = cur.fetchone()
            if result:
                print("  ✅ pgvector extension is installed")
            else:
                print("  ❌ pgvector extension is NOT installed")
                print("  ⚠️  This might cause issues with Vector columns")
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Extension check failed: {e}")
        return False

def test_user_creation():
    """Test creating a user to see what fails"""
    print("\n🧪 Testing user creation...")
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            conn = psycopg2.connect(
                host=os.getenv("host", "localhost"),
                port=os.getenv("port", "5432"),
                database=os.getenv("dbname", "postgres"),
                user=os.getenv("user", ""),
                password=os.getenv("password", "")
            )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Try to insert a test user
            test_user_data = {
                'username': 'testuser123',
                'email': 'test@example.com',
                'password_hash': 'hashed_password_here',
                'display_name': 'Test User',
                'preferences': json.dumps({
                    "categories": ["technology"],
                    "language": "en",
                    "content_type": "mixed",
                    "notification_settings": {
                        "push_enabled": True,
                        "email_digest": True,
                        "breaking_news": True
                    }
                })
            }
            
            try:
                print("  🔄 Attempting to create test user...")
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, display_name, preferences)
                    VALUES (%(username)s, %(email)s, %(password_hash)s, %(display_name)s, %(preferences)s)
                    RETURNING id;
                """, test_user_data)
                
                user_id = cur.fetchone()['id']
                print(f"  ✅ Test user created successfully with ID: {user_id}")
                
                # Clean up
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                print("  ✅ Test user cleaned up")
                return True
                
            except Exception as e:
                print(f"  ❌ User creation failed: {e}")
                print(f"  🔍 Error type: {type(e).__name__}")
                conn.rollback()
                return False
                
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def check_logs():
    """Check for recent database errors"""
    print("\n📝 Checking for recent database errors...")
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            conn = psycopg2.connect(
                host=os.getenv("host", "localhost"),
                port=os.getenv("port", "5432"),
                database=os.getenv("dbname", "postgres"),
                user=os.getenv("user", ""),
                password=os.getenv("password", "")
            )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if log_statement is enabled
            cur.execute("SHOW log_statement;")
            log_statement = cur.fetchone()['log_statement']
            print(f"  📊 Log statement setting: {log_statement}")
            
            # Check if log_min_duration_statement is set
            cur.execute("SHOW log_min_duration_statement;")
            log_min_duration = cur.fetchone()['log_min_duration_statement']
            print(f"  ⏱️  Log min duration: {log_min_duration}")
            
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Log check failed: {e}")

def main():
    """Run all health checks"""
    print("🏥 Database Health Check")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now()}")
    
    # Run all checks
    check_environment()
    
    if test_database_connection():
        check_tables()
        check_extensions()
        test_user_creation()
        check_logs()
    
    print("\n" + "=" * 50)
    print("🏁 Health check completed!")
    print("\n💡 If you see any ❌ errors above, those are likely the cause of the 500 error.")
    print("   Common issues:")
    print("   - Missing pgvector extension")
    print("   - Incorrect table schema")
    print("   - Missing required columns")
    print("   - Database permission issues")

if __name__ == "__main__":
    main() 