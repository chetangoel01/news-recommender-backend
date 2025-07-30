# Testing Guide - News Recommender Backend

## 🧪 Testing Philosophy

This project uses **production-grade testing** with the same PostgreSQL database and models that run in production. This ensures our tests validate the actual system behavior rather than testing against simplified mock implementations.

## 🏗️ Test Architecture

### PostgreSQL-First Testing

**Why PostgreSQL Instead of SQLite?**
- ✅ **Schema Compatibility**: Tests use the exact same models as production (Supabase)
- ✅ **pgvector Support**: Vector operations and similarity search are properly tested
- ✅ **UUID Handling**: Native PostgreSQL UUID support matches production behavior  
- ✅ **Data Type Validation**: ARRAY, JSONB, and VECTOR columns work exactly as in production
- ✅ **Foreign Key Constraints**: Proper referential integrity testing
- ✅ **Extension Testing**: pgvector and other PostgreSQL extensions are validated

**Previous SQLite Issues:**
- ❌ Models stored embeddings as JSON strings instead of vectors
- ❌ UUIDs were stored as strings instead of native UUID types
- ❌ ARRAY columns were converted to TEXT fields
- ❌ pgvector similarity search was impossible to test
- ❌ Schema mismatch led to production bugs not caught in tests

### Test Database Setup

Tests use a **separate PostgreSQL test database** to ensure isolation:

```bash
# Production database
DATABASE_URL=postgresql://user:pass@host:5432/production_db

# Test database (automatically created)
TEST_DATABASE_URL=postgresql://user:pass@host:5432/test_db
```

## 🚀 Quick Start

### 1. Prerequisites

You need access to a PostgreSQL database with pgvector extension:

**Option A: Supabase (Recommended)**
```bash
# Use your Supabase connection string
export DATABASE_URL="postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:5432/postgres"
```

**Option B: Local PostgreSQL**
```bash
# Install PostgreSQL and pgvector locally
createdb news_recommender_test
psql news_recommender_test -c "CREATE EXTENSION vector"
export TEST_DATABASE_URL="postgresql://localhost:5432/news_recommender_test"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Tests

```bash
# Quick test run
make test

# Or using pytest directly
pytest tests/ -v

# Run specific test suites
pytest tests/test_auth.py -v -m auth
pytest tests/test_users.py -v -m users
```

## 📋 Test Organization

### Test Markers

Tests are organized using pytest markers:

```python
@pytest.mark.auth          # Authentication tests
@pytest.mark.users         # User profile tests  
@pytest.mark.integration   # Cross-module integration tests
@pytest.mark.slow          # Tests that might take longer
@pytest.mark.db           # Database-dependent tests
```

### Test Structure

```
tests/
├── conftest.py           # PostgreSQL fixtures and test configuration
├── test_auth.py          # Authentication & authorization tests (including OAuth)
├── test_users.py         # User profile & embedding tests
├── test_db_connection.py # Database connectivity validation
└── test_*.py            # Additional test modules
```

## 🔧 Test Configuration

### Environment Variables

```bash
# Required: Database connection for testing
DATABASE_URL="postgresql://user:pass@host:5432/production_db"

# Optional: Separate test database (recommended)
TEST_DATABASE_URL="postgresql://user:pass@host:5432/test_db" 

# Authentication secrets (for JWT testing)
SECRET_KEY="test-secret-key-for-jwt-signing"
```

### Test Database Isolation

Each test gets a **fresh database state**:

1. **Session Setup**: Creates tables with pgvector extension
2. **Test Isolation**: Each test cleans all table data after execution
3. **Session Teardown**: Drops all tables after test session

This ensures:
- ✅ Tests don't interfere with each other
- ✅ No leftover data between test runs
- ✅ Full schema validation on each run
- ✅ Production-identical database state

## 📊 Coverage Reporting

Tests include comprehensive coverage tracking:

```bash
# Run tests with coverage
python run_tests.py coverage

# Generate HTML coverage report
pytest tests/ --cov=api --cov=core --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Coverage Targets:**
- **Minimum**: 80% overall coverage
- **Authentication**: 95%+ coverage
- **User Management**: 90%+ coverage
- **Core Models**: 85%+ coverage

## 🧪 Test Categories

### Authentication Tests (`test_auth.py`)

**Test Classes:**
- `TestUserRegistration`: Account creation, validation, duplicates
- `TestUserLogin`: Login success/failure, credential validation  
- `TestTokenRefresh`: JWT token refresh flow
- `TestAuthenticationFlow`: End-to-end auth scenarios

**Key Features Tested:**
- ✅ Password hashing with bcrypt
- ✅ JWT token generation and validation
- ✅ Refresh token rotation
- ✅ Google OAuth authentication (token verification, user creation)
- ✅ Apple OAuth authentication (token verification, user creation)
- ✅ Input validation with Pydantic
- ✅ Duplicate email/username handling
- ✅ Authentication required endpoints

### OAuth Authentication Tests (`test_auth.py`)

**Test Classes:**
- `TestGoogleAuthentication`: Google OAuth flow testing
- `TestAppleAuthentication`: Apple OAuth flow testing

**Key Features Tested:**
- ✅ Google ID token verification with public keys
- ✅ Apple ID token verification with public keys
- ✅ Automatic user creation for new OAuth users
- ✅ Error handling for invalid/missing tokens
- ✅ Client ID configuration validation
- ✅ OAuth user profile integration

### User Profile Tests (`test_users.py`)

**Test Classes:**
- `TestUserProfile`: Profile CRUD operations
- `TestUserEmbeddingUpdate`: ML embedding updates  
- `TestEmbeddingStatus`: Embedding sync status tracking
- `TestUserProfileIntegration`: Complete user lifecycle

**Key Features Tested:**
- ✅ Profile retrieval and updates
- ✅ Preference merging and validation
- ✅ 384-dimensional vector embedding storage
- ✅ Embedding update batching (every 10 articles)
- ✅ Personalization score calculation
- ✅ User statistics tracking

### Vector Operations Testing

**pgvector Integration:**
```python
# Test embedding storage (384-dimensional vectors)
user.embedding = [0.1, -0.2, 0.3] + [0.0] * 381

# Test embedding updates
update = UserEmbeddingUpdate(
    user_id=user.id,
    embedding_vector=[0.5] * 384,  # Native vector storage
    interaction_summary={...}      # JSONB field
)
```

## 🚨 Common Issues & Solutions

### Database Connection Errors

**Problem**: `psycopg2.OperationalError: could not connect`
```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# Test connection manually
python tests/test_db_connection.py
```

**Problem**: `pgvector extension not found`
```sql
-- Enable pgvector in your PostgreSQL database
CREATE EXTENSION IF NOT EXISTS vector;
```

### Test Isolation Issues

**Problem**: Tests interfere with each other
```python
# Check that cleanup is working in conftest.py
session.execute(text("DELETE FROM user_embedding_updates"))
session.execute(text("DELETE FROM bookmarks"))  
session.execute(text("DELETE FROM articles"))
session.execute(text("DELETE FROM users"))
```

### Vector Dimension Errors

**Problem**: `Invalid vector dimension`
```python
# Ensure all embeddings are exactly 384-dimensional
embedding = [0.1] * 384  # ✅ Correct
embedding = [0.1] * 128  # ❌ Wrong dimension
```

## 🎯 Best Practices

### Writing New Tests

1. **Use Production Models**: Import from `core.models`, not test-specific models
2. **Test Vector Operations**: Include embedding storage and retrieval  
3. **Validate Schema**: Test UUID, ARRAY, and JSONB field handling
4. **Clean Test Data**: Use fixtures for consistent test data
5. **Mark Tests**: Add appropriate pytest markers

```python
import pytest
from core.models import User, Article, UserEmbeddingUpdate

@pytest.mark.users
@pytest.mark.db
def test_user_embedding_update(db_session, test_user_in_db):
    """Test vector embedding storage and retrieval."""
    embedding = [0.1] * 384
    
    # Store embedding 
    test_user_in_db.embedding = embedding
    db_session.commit()
    
    # Retrieve and validate
    user = db_session.query(User).first()
    assert len(user.embedding) == 384
    assert user.embedding[0] == 0.1
```

### Performance Testing

```bash
# Fast tests (skip slow integration tests)
python run_tests.py fast

# Parallel test execution
pytest tests/ -n auto

# Profile test performance
pytest tests/ --durations=10
```

## 📈 Continuous Integration

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  env:
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
  run: |
    python run_tests.py coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## 🎉 Benefits of This Approach

**Development Benefits:**
- 🔍 **Early Bug Detection**: Catch schema issues before production
- 🚀 **Faster Development**: Tests match production behavior exactly
- 🛡️ **Data Integrity**: Test foreign keys, constraints, and indexes
- 📊 **ML Validation**: Test vector operations and similarity search

**Production Benefits:**
- ✅ **Zero Schema Drift**: Test and production schemas are identical
- 🔒 **Database Confidence**: Know that PostgreSQL features work correctly
- 📈 **Performance Validation**: Test query performance with realistic data
- 🎯 **Feature Parity**: pgvector and extension features are validated

This testing approach provides **production confidence** that was impossible with the previous SQLite-based testing system. 