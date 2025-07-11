import pytest
import asyncio
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime
import os
import json

from api.main import app
from core.db import get_db, Base
from core.models import User, Article, Bookmark, UserEmbeddingUpdate
from core.auth import get_password_hash

# Test database URL - use same database as production for development testing
# For production environments, set TEST_DATABASE_URL to a separate test database
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

if not TEST_DATABASE_URL:
    raise ValueError("TEST_DATABASE_URL or DATABASE_URL must be set for testing")

# Create test engine with PostgreSQL
engine = create_engine(
    TEST_DATABASE_URL,
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
    
    yield session
    
    # Clean up: delete only test data from tables after each test
    try:
        session.rollback()
        # Delete in reverse dependency order to avoid foreign key conflicts
        # Only delete test data (users with @example.com emails) to avoid affecting real data
        session.execute(text("DELETE FROM user_embedding_updates WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        session.execute(text("DELETE FROM bookmarks WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        session.execute(text("DELETE FROM articles WHERE title LIKE 'Test %' OR url LIKE '%test%'"))
        session.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        session.commit()
    except Exception as e:
        # If targeted DELETE fails, try broader cleanup
        try:
            session.rollback()
            # Still be careful and only delete test data
            session.execute(text("DELETE FROM user_embedding_updates WHERE created_at > NOW() - INTERVAL '1 hour'"))
            session.execute(text("DELETE FROM bookmarks WHERE created_at > NOW() - INTERVAL '1 hour'"))
            session.execute(text("DELETE FROM articles WHERE title LIKE 'Test %'"))
            session.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
            session.commit()
        except Exception:
            session.rollback()
            # Last resort: just rollback and continue
            pass
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session) -> TestClient:
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user registration data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "username": "testuser",
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
    return {
        "email": "another@example.com",
        "password": "anotherpassword123",
        "username": "anotheruser",
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
    
    return user

@pytest.fixture
def auth_tokens(client, test_user_data) -> Dict[str, str]:
    """Register user and get authentication tokens."""
    # Register the user
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    data = response.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"]
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
    return {
        "title": "Test Article",
        "summary": "This is a test article summary",
        "url": "https://example.com/test-article",
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
    
    return article 