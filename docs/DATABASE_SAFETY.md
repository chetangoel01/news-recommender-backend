# 🚨 Database Safety Guide - CRITICAL READ

## ⚠️ URGENT: Prevent Data Loss During Testing

Your tests were **deleting production data** because they were using the same database for testing and production. This document explains how to fix this immediately.

## 🔥 What Happened

1. **Same Database Used**: Tests defaulted to using your production `DATABASE_URL`
2. **Dangerous Cleanup**: After each test, articles with URLs containing "test" were deleted
3. **Data Loss**: Legitimate articles with "test", "protest", "contest", etc. in URLs were deleted

## ✅ Immediate Fix Required

### 1. Set Up Separate Test Database

**Option A: Create a separate test database on same server**
```bash
# Create a test database (replace with your actual connection details)
createdb news_recommender_test

# Or via SQL:
# CREATE DATABASE news_recommender_test;
```

**Option B: Use Supabase with separate project**
- Create a separate Supabase project for testing
- Get the connection string for the test project

### 2. Configure Environment Variables

Create or update your `.env` file:

```bash
# Production/Development Database (your real data)
DATABASE_URL=postgresql://user:pass@host:5432/news_recommender

# Test Database (MUST be different! Data will be deleted!)
TEST_DATABASE_URL=postgresql://user:pass@host:5432/news_recommender_test
```

### 3. Enable pgvector on Test Database

```sql
-- Run this on your TEST database
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Verify Safety

Run this command to test the configuration:
```bash
python run_tests.py check
```

## 🛡️ Safety Features Now Enabled

### ✅ What's Fixed:

1. **Separate Database Requirement**: Tests now REQUIRE a separate `TEST_DATABASE_URL`
2. **Exact ID Tracking**: Tests now track the exact IDs of created records and delete ONLY those records
3. **No LIKE Patterns**: Completely removed all `LIKE` patterns from DELETE statements
4. **ID-Based Cleanup**: Only delete records using exact UUID matches: `WHERE id IN ('uuid1', 'uuid2', ...)`
5. **Registration System**: All test fixtures automatically register created record IDs for cleanup

### ✅ Safe Test Patterns:

Tests now use **exact ID tracking** instead of pattern matching:
- **Automatic Registration**: All test fixtures automatically register created record IDs
- **Exact Deletion**: Only delete records with IDs that were created during the test
- **Manual Registration**: Use `register_test_data(db_session, 'table_name', 'record_id')` for additional test data
- **Zero False Positives**: Impossible to accidentally delete production data

## 🔧 Running Tests Safely

```bash
# Check configuration first
python run_tests.py check

# Run tests (now safe!)
python run_tests.py all

# Run specific test suites
python run_tests.py auth
python run_tests.py users
```

## 📝 Writing Safe Tests

When creating test data in your test functions, use the registration helper:

```python
from tests.conftest import register_test_data

def test_create_article(db_session):
    # Create test data
    article = Article(title="My Test Article", ...)
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    
    # Register for cleanup (automatic in fixtures, manual in tests)
    register_test_data(db_session, 'articles', str(article.id))
    
    # Test logic here...
    # Article will be automatically deleted after test completes
```

**Supported table names for registration:**
- `'users'` - User records
- `'articles'` - Article records  
- `'bookmarks'` - Bookmark records
- `'user_embedding_updates'` - Embedding update records

## 🚫 What NOT to Do

### ❌ NEVER DO THIS:
```bash
# DON'T: Use same database for testing
TEST_DATABASE_URL=$DATABASE_URL  # This will delete your data!

# DON'T: Use production database for tests
export TEST_DATABASE_URL="$DATABASE_URL"
```

### ✅ ALWAYS DO THIS:
```bash
# DO: Use separate test database
export TEST_DATABASE_URL="postgresql://user:pass@host:5432/news_recommender_test"

# DO: Verify before running tests
python run_tests.py check
```

## 📊 Data Recovery (If Needed)

If you lost data and need to recover:

1. **Check if you have backups** (Supabase has automatic backups)
2. **Re-run your data pipeline** to fetch articles again:
   ```bash
   python -m pipeline.fetch
   python -m pipeline.embed
   python -m pipeline.build_faiss_index
   ```

## 🔄 Going Forward

### Development Workflow:
```bash
# 1. Set up environment (one time)
export TEST_DATABASE_URL="postgresql://..."

# 2. Verify safety
python run_tests.py check

# 3. Run tests safely
make test

# 4. Build FAISS index after adding real data
make index-build
```

### Production Deployment:
- Use completely separate databases for prod/staging/test
- Never set `TEST_DATABASE_URL` to production database
- Always verify configuration before running tests

## 📞 Emergency Checklist

If you suspect data loss:

1. ☐ **STOP** running tests immediately
2. ☐ Check if `TEST_DATABASE_URL` equals `DATABASE_URL`
3. ☐ Set up separate test database
4. ☐ Verify configuration with `python run_tests.py check`
5. ☐ Re-populate database if needed
6. ☐ Test with small dataset first

---

**Remember**: Tests should NEVER affect your production data. Always use separate databases for testing! 