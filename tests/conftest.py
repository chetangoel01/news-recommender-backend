import pytest
import asyncio
import logging
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime
import os
import json

# Configure logging for tests
logger = logging.getLogger(__name__)

def register_test_data(db_session, table_name: str, record_id: str):
    """Register a test data ID for safe cleanup. 
    
    Call this function whenever you create test data in your tests:
    register_test_data(db_session, 'users', str(user.id))
    register_test_data(db_session, 'articles', str(article.id))
    
    SAFETY: Only records registered here will be deleted during cleanup.
    """
    if hasattr(db_session, '_test_data_tracker'):
        db_session._test_data_tracker[table_name].add(record_id)
        logger.info(f"🔒 REGISTERED for cleanup: {table_name} ID {record_id}")

def verify_safe_cleanup(session, test_data_tracker):
    """Verify that we're only deleting test-created records."""
    logger.info("🔍 SAFETY CHECK: Verifying cleanup targets...")
    
    # Check for dry-run mode
    dry_run = os.getenv("TEST_DRY_RUN", "false").lower() == "true"
    if dry_run:
        logger.warning("🧪 DRY RUN MODE: Will show deletions but not execute them")
    
    total_records = 0
    for table_name, ids in test_data_tracker.items():
        if ids:
            action = "Would delete" if dry_run else "Will delete"
            logger.info(f"📋 {action} {len(ids)} {table_name} records created during this test")
            for record_id in ids:
                logger.debug(f"   - {table_name}: {record_id}")
            total_records += len(ids)
    
    if total_records == 0:
        logger.info("✅ No test records to clean up")
    else:
        action = "Would clean up" if dry_run else "Total cleanup"
        logger.info(f"🧹 {action}: {total_records} test-created records")
        logger.info("🔒 SAFETY: Will only delete records created during this test session")
    
    return total_records

from api.main import app
from core.db import get_db, Base
from core.models import User, Article, Bookmark, UserEmbeddingUpdate
from core.auth import get_password_hash

# Database URL for testing
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set!")

logger.info("🔒 SAFETY: Only test-created records (tracked by UUID) will be deleted")

# Create test engine with PostgreSQL
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "connect_timeout": 15,
        "application_name": "news-recommender-test",
        "sslmode": "require",
    },
    pool_pre_ping=True,
    pool_recycle=300
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def setup_test_db():
    """Create test database tables."""
    try:
        # Create pgvector extension if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        
        # Create all tables using the same models as production
        # This is safe because it only creates tables that don't already exist
        Base.metadata.create_all(bind=engine)
        yield
        
        # NOTE: We don't drop tables in development to avoid accidents
        # Tables will be reused between test sessions
        # Individual test cleanup handles data removal
        
    except Exception as e:
        pytest.fail(f"Failed to setup test database: {e}")

@pytest.fixture(scope="function")
def db_session(setup_test_db):
    """Create a fresh database session for each test."""
    session = TestingSessionLocal()
    
    # Track test data IDs for safe cleanup
    test_data_tracker = {
        'users': set(),
        'articles': set(),
        'bookmarks': set(),
        'user_embedding_updates': set()
    }
    
    # Make tracker available to the session
    session._test_data_tracker = test_data_tracker
    
    yield session
    
    # Clean up: delete ONLY the exact records created during this test
    try:
        session.rollback()
        
        # Safety verification before any deletions
        total_to_delete = verify_safe_cleanup(session, test_data_tracker)
        
        if total_to_delete == 0:
            logger.info("✅ No cleanup needed - no test records created")
            return
        
        # Check for dry-run mode
        dry_run = os.getenv("TEST_DRY_RUN", "false").lower() == "true"
        if dry_run:
            logger.warning("🧪 DRY RUN: Skipping actual deletions")
            logger.info(f"🔍 Would have deleted {total_to_delete} test records")
            return
        
        # Delete in reverse dependency order using exact IDs only
        deleted_counts = {}
        
        if test_data_tracker['user_embedding_updates']:
            ids = list(test_data_tracker['user_embedding_updates'])
            ids_str = "'" + "','".join(ids) + "'"
            logger.info(f"🗑️  Deleting {len(ids)} user_embedding_updates records: {ids}")
            result = session.execute(text(f"DELETE FROM user_embedding_updates WHERE id IN ({ids_str})"))
            deleted_counts['user_embedding_updates'] = result.rowcount
        
        if test_data_tracker['bookmarks']:
            ids = list(test_data_tracker['bookmarks'])
            ids_str = "'" + "','".join(ids) + "'"
            logger.info(f"🗑️  Deleting {len(ids)} bookmarks records: {ids}")
            result = session.execute(text(f"DELETE FROM bookmarks WHERE id IN ({ids_str})"))
            deleted_counts['bookmarks'] = result.rowcount
        
        if test_data_tracker['articles']:
            ids = list(test_data_tracker['articles'])
            ids_str = "'" + "','".join(ids) + "'"
            logger.info(f"🗑️  Deleting {len(ids)} articles records: {ids}")
            result = session.execute(text(f"DELETE FROM articles WHERE id IN ({ids_str})"))
            deleted_counts['articles'] = result.rowcount
        
        if test_data_tracker['users']:
            ids = list(test_data_tracker['users'])
            ids_str = "'" + "','".join(ids) + "'"
            logger.info(f"🗑️  Deleting {len(ids)} users records: {ids}")
            result = session.execute(text(f"DELETE FROM users WHERE id IN ({ids_str})"))
            deleted_counts['users'] = result.rowcount
        
        session.commit()
        
        # Verify cleanup success
        total_deleted = sum(deleted_counts.values())
        logger.info(f"✅ CLEANUP SUCCESS: Deleted {total_deleted} test records by exact UUID")
        
        for table, count in deleted_counts.items():
            if count > 0:
                logger.info(f"   - {table}: {count} records")
        
        # Double-check: verify expected vs actual deletions
        expected_total = sum(len(ids) for ids in test_data_tracker.values())
        if total_deleted != expected_total:
            logger.warning(f"⚠️  Deletion mismatch: expected {expected_total}, deleted {total_deleted}")
        else:
            logger.info("🔒 SAFETY VERIFIED: All test records cleaned up successfully")
            
    except Exception as e:
        # If cleanup fails, log the error but don't attempt any other cleanup
        session.rollback()
        logger.error(f"❌ Test cleanup failed: {e}")
        logger.error("🚨 CRITICAL: Test data may not have been cleaned up properly")
        
        # Log what we were trying to delete for debugging
        for table_name, ids in test_data_tracker.items():
            if ids:
                logger.error(f"   Failed to clean: {table_name} - {list(ids)}")
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session) -> TestClient:
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def authenticated_user(client, db_session) -> Dict[str, Any]:
    """Create ONE authenticated user per test with unique credentials."""
    # Generate unique user data for this specific test
    unique_id = str(uuid.uuid4()).replace('-', '')[:16]
    
    user_data = {
        "email": f"testuser{unique_id}@example.com",
        "password": "testpassword123",
        "username": f"testuser{unique_id}",
        "display_name": "Test User",
        "preferences": {
            "categories": ["technology", "business"],
            "language": "en",
            "content_type": "mixed"
        }
    }
    
    # Register user via API (most realistic)
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    
    auth_data = response.json()
    user_id = auth_data["user_id"]
    
    # Register for cleanup
    register_test_data(db_session, 'users', user_id)
    
    return {
        "user_id": user_id,
        "user_data": user_data,
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data["refresh_token"],
        "auth_headers": {"Authorization": f"Bearer {auth_data['access_token']}"}
    }

@pytest.fixture(scope="function") 
def second_user(client, db_session) -> Dict[str, Any]:
    """Create a SECOND authenticated user for multi-user tests only."""
    unique_id = str(uuid.uuid4()).replace('-', '')[:16]
    
    user_data = {
        "email": f"seconduser{unique_id}@example.com",
        "password": "testpassword123",
        "username": f"seconduser{unique_id}",
        "display_name": "Second User", 
        "preferences": {
            "categories": ["science", "politics"],
            "language": "en",
            "content_type": "articles"
        }
    }
    
    # Register user via API
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    
    auth_data = response.json()
    user_id = auth_data["user_id"]
    
    # Register for cleanup
    register_test_data(db_session, 'users', user_id)
    
    return {
        "user_id": user_id,
        "user_data": user_data, 
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data["refresh_token"],
        "auth_headers": {"Authorization": f"Bearer {auth_data['access_token']}"}
    }

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Primary test user data for general testing."""
    # Generate unique data to avoid conflicts
    import time
    import random
    
    unique_id = uuid.uuid4().hex[:20]
    
    return {
        "email": f"testuser{unique_id}@example.com",
        "password": "testpassword123",
        "username": f"testuser{unique_id}",
        "display_name": "Test User",
        "preferences": {
            "categories": ["technology", "business"],
            "language": "en",
            "content_type": "mixed"
        }
    }

@pytest.fixture
def another_test_user_data() -> Dict[str, Any]:
    """Another test user for testing conflicts."""
    # Generate highly unique data to avoid any conflicts
    import time
    import random
    
    unique_id = uuid.uuid4().hex[:20]
    
    return {
        "email": f"another{unique_id}@example.com",
        "password": "anotherpassword123",
        "username": f"anotheruser{unique_id}",
        "display_name": "Another User",
        "preferences": {
            "categories": ["science", "politics"],
            "language": "en",
            "content_type": "articles"
        }
    }

@pytest.fixture
def test_user_in_db(db_session, test_user_data) -> User:
    """Create a test user directly in the database."""
    hashed_password = get_password_hash(test_user_data["password"])
    
    user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        password_hash=hashed_password,
        display_name=test_user_data["display_name"],
        preferences=test_user_data["preferences"],
        # Initialize with a sample 384-dimensional embedding vector
        embedding=[0.1] * 384
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Register this user ID for exact cleanup
    if hasattr(db_session, '_test_data_tracker'):
        db_session._test_data_tracker['users'].add(str(user.id))
    
    return user

@pytest.fixture
def auth_tokens(client, test_user_data, db_session) -> Dict[str, str]:
    """Register user and get authentication tokens."""
    # Register the user
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    data = response.json()
    
    # CRITICAL: Register this user for cleanup since it was created via API
    # We need to find the user in the database and register its ID
    user_id = data["user_id"]
    register_test_data(db_session, 'users', user_id)
    
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": user_id  # Include user_id for reference
    }

@pytest.fixture
def auth_headers(auth_tokens) -> Dict[str, str]:
    """Get authentication headers with access token."""
    return {
        "Authorization": f"Bearer {auth_tokens['access_token']}"
    }

@pytest.fixture
def test_embedding_update_data() -> Dict[str, Any]:
    """Test data for embedding updates."""
    return {
        "embedding_vector": [0.1, -0.2, 0.3] + [0.0] * 381,  # 384-dimensional vector
        "interaction_summary": {
            "avg_read_time_seconds": 45.2,
            "engagement_metrics": {
                "liked_articles": 3,
                "shared_articles": 1,
                "bookmarked_articles": 2,
                "skipped_articles": 4
            },
            "category_exposure": {
                "technology": 4,
                "business": 3,
                "politics": 2,
                "science": 1
            }
        },
        "session_start": "2024-01-20T16:00:00Z",
        "session_end": "2024-01-20T16:30:00Z",
        "articles_processed": 10,
        "device_type": "mobile",
        "app_version": "1.2.3"
    }

@pytest.fixture
def invalid_auth_headers() -> Dict[str, str]:
    """Get invalid authentication headers for testing unauthorized access."""
    return {
        "Authorization": "Bearer invalid_token_here"
    }

@pytest.fixture
def test_article_data() -> Dict[str, Any]:
    """Test article data for testing."""
    # Generate unique URL for each test to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    return {
        "title": "Test Article for Unit Testing",  # Matches safer cleanup pattern
        "summary": "This is a test article summary",
        "url": f"https://test-example.com/article-{unique_id}",  # Unique URL for each test
        "source_name": "Test Source",
        "category": "technology",
        "embedding": [0.5] * 384  # 384-dimensional vector
    }

@pytest.fixture
def test_article_in_db(db_session, test_article_data) -> Article:
    """Create a test article in the database."""
    article = Article(
        title=test_article_data["title"],
        summary=test_article_data["summary"],
        url=test_article_data["url"],
        source_name=test_article_data["source_name"],
        category=test_article_data["category"],
        embedding=test_article_data["embedding"]
    )
    
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    
    # Register this article ID for exact cleanup
    if hasattr(db_session, '_test_data_tracker'):
        db_session._test_data_tracker['articles'].add(str(article.id))
    
    return article

@pytest.fixture(scope="function")
def multiple_test_articles_in_db(db_session) -> list[Article]:
    """Create multiple test articles with different categories and sources."""
    # Generate unique identifiers for URLs to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    
    articles_data = [
        {
            "title": "Tech Article Test 1",
            "summary": "Technology summary 1",
            "content": "This is a technology article about AI and machine learning. " * 20,
            "url": f"https://test-tech.com/article-1-{unique_id}",
            "source_name": "TechNews",
            "source_id": "tech_source_1",
            "author": "Tech Author 1",
            "category": "technology",
            "language": "en",
            "views": 100,
            "likes": 10,
            "shares": 5,
            "bookmarks": 3,
            "embedding": [0.1 * i for i in range(384)]
        },
        {
            "title": "Business Article Test 2",
            "summary": "Business summary 2",
            "content": "This is a business article about market trends and economics. " * 15,
            "url": f"https://test-business.com/article-2-{unique_id}",
            "source_name": "BusinessDaily",
            "source_id": "business_source_1",
            "author": "Business Author 1",
            "category": "business",
            "language": "en",
            "views": 200,
            "likes": 20,
            "shares": 8,
            "bookmarks": 12,
            "embedding": [0.2 * i for i in range(384)]
        },
        {
            "title": "Science Article Test 3",
            "summary": "Science summary 3",
            "content": "This is a science article about space exploration and discoveries. " * 25,
            "url": f"https://test-science.com/article-3-{unique_id}",
            "source_name": "ScienceToday",
            "source_id": "science_source_1",
            "author": "Science Author 1",
            "category": "science",
            "language": "en",
            "views": 300,
            "likes": 30,
            "shares": 15,
            "bookmarks": 8,
            "embedding": [0.3 * i for i in range(384)]
        },
        {
            "title": "Politics Article Test 4",
            "summary": "Politics summary 4",
            "content": "This is a politics article about current events and policy. " * 10,
            "url": f"https://test-politics.com/article-4-{unique_id}",
            "source_name": "PoliticsWeekly",
            "source_id": "politics_source_1",
            "author": "Politics Author 1",
            "category": "politics",
            "language": "en",
            "views": 150,
            "likes": 8,
            "shares": 12,
            "bookmarks": 5,
            "embedding": [0.4 * i for i in range(384)]
        },
        {
            "title": "Technology Article Test 5",
            "summary": "Another tech summary",
            "content": "This is another technology article about software development. " * 30,
            "url": f"https://test-tech.com/article-5-{unique_id}",
            "source_name": "TechNews",
            "source_id": "tech_source_1",
            "author": "Tech Author 2",
            "category": "technology",
            "language": "en",
            "views": 400,
            "likes": 45,
            "shares": 20,
            "bookmarks": 18,
            "embedding": [0.5 * i for i in range(384)]
        }
    ]
    
    created_articles = []
    for article_data in articles_data:
        article = Article(**article_data)
        db_session.add(article)
        created_articles.append(article)
    
    db_session.commit()
    
    # Refresh all articles to get their IDs
    for article in created_articles:
        db_session.refresh(article)
        # Register for cleanup
        if hasattr(db_session, '_test_data_tracker'):
            db_session._test_data_tracker['articles'].add(str(article.id))
    
    return created_articles

@pytest.fixture
def test_bookmark_in_db(db_session, test_user_in_db, test_article_in_db) -> Bookmark:
    """Create a test bookmark in the database."""
    bookmark = Bookmark(
        user_id=test_user_in_db.id,
        article_id=test_article_in_db.id,
        notes="Test bookmark note"
    )
    
    db_session.add(bookmark)
    db_session.commit()
    db_session.refresh(bookmark)
    
    # Register for cleanup
    if hasattr(db_session, '_test_data_tracker'):
        db_session._test_data_tracker['bookmarks'].add(str(bookmark.id))
    
    return bookmark

@pytest.fixture
def article_view_data() -> Dict[str, Any]:
    """Test data for article view tracking."""
    return {
        "view_duration_seconds": 45.5,
        "percentage_read": 75,
        "interaction_type": "swipe_up",
        "swipe_direction": "up"
    }

@pytest.fixture
def article_share_data() -> Dict[str, Any]:
    """Test data for article sharing."""
    return {
        "platform": "twitter",
        "message": "Check out this amazing article!",
        "include_summary": True
    } 