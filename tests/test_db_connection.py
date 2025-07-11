#!/usr/bin/env python3
"""
Test file for database connection
Run this to verify your Supabase PostgreSQL connection is working
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Add the parent directory to Python path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import test_database_connection, get_database_connection
from core.db import SessionLocal
from sqlalchemy import text


def mask_database_url(database_url: str) -> str:
    if "@" in database_url and "://" in database_url:
        scheme, rest = database_url.split("://", 1)
        creds, host = rest.split("@", 1)
        user = creds.split(":")[0]
        return f"{scheme}://{user}:***@{host}"
    return database_url


def main():
    print("=== 🔌 Database Connection Test ===\n")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables.")
        return

    print(f"Database URL: {mask_database_url(database_url)}\n")

    # ---- psycopg2 test ----
    print("🔍 Testing raw connection with psycopg2...")
    if test_database_connection():
        print("✅ psycopg2 connection test PASSED!")

        print("\n=== 🧪 psycopg2 Query Test ===")
        connection = None
        try:
            connection = get_database_connection()
            cursor = connection.cursor()

            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"PostgreSQL Version: {version[0]}")

            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                LIMIT 5;
            """)
            tables = cursor.fetchall()
            print(f"Available tables: {[table[0] for table in tables] or 'No tables found'}")

        except Exception as e:
            print(f"❌ psycopg2 query test failed: {e}")
        finally:
            if connection:
                connection.close()
    else:
        print("❌ psycopg2 connection test FAILED!")

    # ---- SQLAlchemy test ----
    print("\n=== 🧪 SQLAlchemy Engine Test ===")
    db = None
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT version();"))
        version = result.fetchone()
        print(f"✅ SQLAlchemy connection successful!")
        print(f"PostgreSQL Version: {version[0]}")
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
