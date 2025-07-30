from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON, func, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

def create_indexes():
    """Create performance indexes for the recommendation system."""
    try:
        # Create indexes for personalized feed optimization
        with engine.connect() as conn:
            # Index for article filtering and scoring
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_articles_published_at 
                ON articles(published_at DESC);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_articles_category 
                ON articles(category);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_articles_engagement 
                ON articles(views DESC, likes DESC, shares DESC);
            """))
            
            # Composite index for the main feed query
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_articles_feed_query 
                ON articles(published_at DESC, category, views DESC, likes DESC, shares DESC);
            """))
            
            # Indexes for user interactions
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_likes_user_article 
                ON likes(user_id, article_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_shares_user_article 
                ON shares(user_id, article_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_bookmarks_user_article 
                ON bookmarks(user_id, article_id);
            """))
            
            # Index for user preferences
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_preferences 
                ON users USING GIN(preferences);
            """))
            
            conn.commit()
            logger.info("Database indexes created successfully")
            
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise

def init_db():
    """Initialize database with tables and indexes."""
    create_tables()
    create_indexes()
    logger.info("Database initialization completed")
