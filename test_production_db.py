#!/usr/bin/env python3
"""
Test script to check production database connection and user creation
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test basic database connection"""
    try:
        # Try to connect using environment variables
        conn = psycopg2.connect(
            host=os.getenv("host", "localhost"),
            port=os.getenv("port", "5432"),
            database=os.getenv("dbname", "postgres"),
            user=os.getenv("user", ""),
            password=os.getenv("password", "")
        )
        
        print("✅ Database connection successful!")
        
        # Test basic query
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT version();")
            result = cur.fetchone()
            print(f"📊 Database version: {result['version']}")
            
            # Check if users table exists
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users';
            """)
            result = cur.fetchone()
            if result:
                print("✅ Users table exists")
            else:
                print("❌ Users table does not exist")
            
            # Check table structure
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            print("📋 Users table structure:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
            
            # Check if pgvector extension is installed
            cur.execute("""
                SELECT extname FROM pg_extension WHERE extname = 'vector';
            """)
            result = cur.fetchone()
            if result:
                print("✅ pgvector extension is installed")
            else:
                print("❌ pgvector extension is NOT installed")
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_user_creation():
    """Test creating a user directly in the database"""
    try:
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
                'display_name': 'Test User'
            }
            
            try:
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, display_name, preferences)
                    VALUES (%(username)s, %(email)s, %(password_hash)s, %(display_name)s, %(preferences)s)
                    RETURNING id;
                """, {
                    **test_user_data,
                    'preferences': '{"categories": ["technology"], "language": "en", "content_type": "mixed"}'
                })
                
                user_id = cur.fetchone()['id']
                print(f"✅ Test user created successfully with ID: {user_id}")
                
                # Clean up
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                print("✅ Test user cleaned up")
                
            except Exception as e:
                print(f"❌ User creation failed: {e}")
                conn.rollback()
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing production database connection...")
    print("=" * 50)
    
    # Test connection
    if test_database_connection():
        print("\n" + "=" * 50)
        print("🧪 Testing user creation...")
        test_user_creation()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!") 