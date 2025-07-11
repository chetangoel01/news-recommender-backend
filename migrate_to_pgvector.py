#!/usr/bin/env python3
"""
Migration script to convert embedding column from ARRAY to pgvector
"""

import psycopg2
from core.config import DatabaseConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_to_pgvector():
    """Migrate embedding column to use pgvector"""
    
    # Connect to database
    try:
        params = DatabaseConfig.get_connection_params()
        if 'dsn' in params:
            conn = psycopg2.connect(params['dsn'])
        else:
            conn = psycopg2.connect(**params)
        
        conn.autocommit = False
        cursor = conn.cursor()
        
        logger.info("✅ Connected to database")
        
        # Check if pgvector extension is enabled
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if not cursor.fetchone():
            logger.info("📦 Enabling pgvector extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("✅ pgvector extension enabled")
        
        # Check current column type
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'articles' AND column_name = 'embedding';
        """)
        current_type = cursor.fetchone()[0]
        logger.info(f"📊 Current embedding column type: {current_type}")
        
        if current_type == 'USER-DEFINED' or current_type == 'vector':
            logger.info("✅ Embedding column is already pgvector type")
            return
        
        # Create new column with pgvector type
        logger.info("🔄 Creating new embedding column with pgvector type...")
        cursor.execute("ALTER TABLE articles ADD COLUMN embedding_vector vector(384);")
        
        # Copy data from old column to new column
        logger.info("📋 Copying embedding data...")
        cursor.execute("""
            UPDATE articles 
            SET embedding_vector = embedding::vector 
            WHERE embedding IS NOT NULL;
        """)
        
        # Drop old column and rename new column
        logger.info("🗑️ Dropping old embedding column...")
        cursor.execute("ALTER TABLE articles DROP COLUMN embedding;")
        
        logger.info("🔄 Renaming new column...")
        cursor.execute("ALTER TABLE articles RENAME COLUMN embedding_vector TO embedding;")
        
        # Create index for better performance
        logger.info("📈 Creating vector index...")
        cursor.execute("CREATE INDEX ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
        
        # Commit changes
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Verify the change
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'articles' AND column_name = 'embedding';
        """)
        new_type = cursor.fetchone()[0]
        logger.info(f"📊 New embedding column type: {new_type}")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting migration to pgvector...")
    migrate_to_pgvector()
    print("✅ Migration script completed!") 