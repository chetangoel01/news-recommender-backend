#!/usr/bin/env python3
"""
Database table creation script for News Recommender Backend

This script creates all the necessary tables for the authentication
and user management system.
"""

import sys
import os
from sqlalchemy import create_engine, text
from core.db import Base, DATABASE_URL
from core.models import User, Article, Bookmark, UserEmbeddingUpdate

def create_tables():
    """Create all database tables."""
    if not DATABASE_URL:
        print("Error: DATABASE_URL is not set in environment variables")
        sys.exit(1)
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create pgvector extension if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create additional indexes as specified in the schema
        with engine.connect() as conn:
            # Create vector index for embedding
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_embedding 
                ON public.users USING ivfflat (embedding vector_cosine_ops)
            """))
            
            # Create btree indexes (username and email already indexed in model)
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON public.users USING btree (username)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON public.users USING btree (email)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_last_active 
                ON public.users USING btree (last_active)
            """))
            
            conn.commit()
        
        print("✅ Database tables created successfully!")
        print("\nCreated tables:")
        print("- users")
        print("- articles") 
        print("- bookmarks")
        print("- user_embedding_updates")
        
        print("\nCreated indexes:")
        print("- idx_users_embedding (ivfflat)")
        print("- idx_users_username (btree)")
        print("- idx_users_email (btree)")
        print("- idx_users_last_active (btree)")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            print(f"\nVerified {len(tables)} tables in database:")
            for table in tables:
                print(f"  - {table}")
                
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

def drop_tables():
    """Drop all database tables (use with caution!)."""
    if not DATABASE_URL:
        print("Error: DATABASE_URL is not set in environment variables")
        sys.exit(1)
    
    response = input("⚠️  This will DELETE ALL DATA. Are you sure? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    try:
        engine = create_engine(DATABASE_URL)
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully!")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_tables()
    else:
        create_tables() 