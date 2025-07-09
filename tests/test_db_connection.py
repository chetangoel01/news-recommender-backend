#!/usr/bin/env python3
"""
Test file for database connection
Run this to verify your Supabase PostgreSQL connection is working
"""

from core.config import test_database_connection, get_database_connection, DatabaseConfig

def main():
    print("=== Database Connection Test ===")
    print()
    
    # Display current configuration (without password)
    print("Current Database Configuration:")
    print(f"Host: {DatabaseConfig.HOST}")
    print(f"Port: {DatabaseConfig.PORT}")
    print(f"Database: {DatabaseConfig.DBNAME}")
    print(f"User: {DatabaseConfig.USER}")
    print(f"Password: {'*' * len(DatabaseConfig.PASSWORD) if DatabaseConfig.PASSWORD else 'Not set'}")
    print()
    
    # Test the connection
    print("Testing database connection...")
    success = test_database_connection()
    
    if success:
        print("\n✅ Database connection test PASSED!")
        
        # Additional test: try to get a connection and run a simple query
        print("\n=== Additional Connection Test ===")
        connection = get_database_connection()
        if connection:
            try:
                cursor = connection.cursor()
                
                # Test basic query
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                print(f"PostgreSQL Version: {version[0]}")
                
                # Test if we can list tables (optional)
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    LIMIT 5;
                """)
                tables = cursor.fetchall()
                print(f"Available tables: {[table[0] for table in tables] if tables else 'No tables found'}")
                
                cursor.close()
                connection.close()
                print("✅ Additional tests completed successfully!")
                
            except Exception as e:
                print(f"❌ Additional test failed: {e}")
                connection.close()
    else:
        print("\n❌ Database connection test FAILED!")

if __name__ == "__main__":
    main() 