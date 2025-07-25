# Authentication & User Profile APIs

This document explains how to set up and use the authentication and user profile APIs for the News Recommender Backend.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/dbname

# Authentication Configuration
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=true
```

### 3. Start the Server

Database tables are created automatically by the application.

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the APIs

```bash
# Run all tests
python run_tests.py all

# Or use pytest directly
pytest tests/ -v
```

## 📋 API Endpoints

### Authentication Endpoints

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "username": "johndoe",
  "display_name": "John Doe",
  "preferences": {
    "categories": ["technology", "business"],
    "language": "en",
    "content_type": "mixed"
  }
}
```

#### Login User
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token_here"
}
```

### User Profile Endpoints

#### Get User Profile
```http
GET /users/profile
Authorization: Bearer your_access_token_here
```

#### Update User Profile
```http
PUT /users/profile
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
  "display_name": "Updated Name",
  "bio": "My bio",
  "preferences": {
    "categories": ["technology", "science"],
    "notification_settings": {
      "push_enabled": false
    }
  }
}
```

#### Update User Embedding
```http
POST /users/embedding/update
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
  "embedding_vector": [0.1, -0.2, 0.3, ...],  // 384-dimensional vector
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
      "politics": 2
    }
  },
  "session_start": "2024-01-20T16:00:00Z",
  "session_end": "2024-01-20T16:30:00Z",
  "articles_processed": 10,
  "device_type": "mobile",
  "app_version": "1.2.3"
}
```

#### Get Embedding Status
```http
GET /users/embedding/status
Authorization: Bearer your_access_token_here
```

## 🔒 Authentication Flow

### 1. User Registration
- User provides email, password, username, and preferences
- Password is hashed using bcrypt
- User record is created in database
- Access token (1 hour) and refresh token (30 days) are returned

### 2. User Login
- User provides email and password
- Credentials are verified against database
- New access and refresh tokens are generated
- User profile information is returned

### 3. Token Usage
- Include access token in Authorization header: `Bearer <token>`
- Access tokens expire after 1 hour
- Use refresh token to get new access token when needed
- Refresh tokens expire after 30 days

### 4. Protected Endpoints
- All user profile endpoints require valid access token
- Invalid or expired tokens return 401 Unauthorized
- Inactive users are rejected with 400 Bad Request

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    profile_image TEXT,
    bio TEXT,
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    email_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',
    role VARCHAR(20) DEFAULT 'user',
    articles_read INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0.0,
    embedding VECTOR(384),  -- pgvector extension
    preferences JSONB
);
```

### User Embedding Updates Table
```sql
CREATE TABLE user_embedding_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    embedding_vector VECTOR(384),
    interaction_summary JSONB,
    session_start TIMESTAMP NOT NULL,
    session_end TIMESTAMP NOT NULL,
    articles_processed INTEGER NOT NULL,
    device_type VARCHAR(20),
    app_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🧪 Testing

The project uses **production-grade PostgreSQL testing** with the same database and models as Supabase production:

### Prerequisites

**Database Setup Required:**
```bash
# Set your PostgreSQL connection (Supabase recommended)
export DATABASE_URL="postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres"

# Optional: Use separate test database for isolation
export TEST_DATABASE_URL="postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres_test"

# Ensure pgvector extension is enabled in your database
# Run in Supabase SQL Editor: CREATE EXTENSION IF NOT EXISTS vector;
```

### Running Tests

```bash
# Check database configuration first
python run_tests.py check

# Run all tests
python run_tests.py all

# Run specific test modules
python run_tests.py auth      # Authentication tests only
python run_tests.py users     # User profile tests only

# Run with coverage report
python run_tests.py coverage

# Run tests without coverage (faster)
python run_tests.py fast

# Direct pytest usage
pytest tests/ -v
pytest tests/test_auth.py -v -m auth
pytest tests/test_users.py -v -m users
```

### Test Coverage

The test suite includes:

**Authentication Tests (`tests/test_auth.py`):**
- ✅ User registration (success, validation, duplicates)
- ✅ User login (success, invalid credentials)
- ✅ Token refresh (success, invalid tokens)
- ✅ Complete authentication flows

**User Profile Tests (`tests/test_users.py`):**
- ✅ Get user profile (authenticated/unauthenticated)
- ✅ Update user profile (full/partial updates)
- ✅ User embedding updates (validation, statistics)
- ✅ Embedding status tracking
- ✅ Integration scenarios

### Test Features

- **PostgreSQL Native**: Tests use the same database as production (Supabase)
- **pgvector Integration**: Vector operations and similarity search fully tested
- **Schema Validation**: UUID, ARRAY, JSONB, and VECTOR types validated
- **Isolated Tests**: Each test gets fresh database state with proper cleanup
- **Fixtures**: Reusable test data and authentication tokens
- **Markers**: Organized by functionality (@pytest.mark.auth, @pytest.mark.users)
- **Coverage Reports**: HTML and terminal coverage reports
- **Production Confidence**: Tests validate actual production behavior

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing secret (change in production!)
- `DEBUG`: Enable/disable debug mode
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifetime (default: 60)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifetime (default: 30)

### Security Features
- ✅ Password hashing with bcrypt
- ✅ JWT tokens with expiration
- ✅ Bearer token authentication
- ✅ Input validation with Pydantic
- ✅ SQL injection protection with SQLAlchemy
- ✅ Rate limiting ready (add middleware)
- ✅ CORS configuration

## 📚 API Documentation

Once the server is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 Next Steps

This authentication system provides the foundation for:
1. **Content Management APIs** - Article CRUD operations
2. **Discovery & Recommendation APIs** - Personalized feeds
3. **Analytics & ML APIs** - User behavior tracking
4. **Admin & Moderation APIs** - Content moderation

All future endpoints can use the `get_current_active_user` dependency for authentication.

## 🚨 Production Considerations

Before deploying to production:

1. **Change the SECRET_KEY** to a strong, random value
2. **Configure CORS** properly for your frontend domain
3. **Add rate limiting** middleware
4. **Set up HTTPS** for secure token transmission
5. **Configure proper logging** for security events
6. **Add input sanitization** for XSS prevention
7. **Set up monitoring** for authentication failures

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check `DATABASE_URL` environment variable
   - Ensure PostgreSQL is running
   - Verify pgvector extension is installed

2. **Token Validation Error**
   - Check if `SECRET_KEY` is consistent
   - Verify token hasn't expired
   - Ensure Bearer token format: `Bearer <token>`

3. **User Registration Failed**
   - Check for duplicate email/username
   - Verify password meets requirements (8+ characters)
   - Check database constraints

For more detailed troubleshooting, check the FastAPI logs and error responses.

## 📖 Additional Documentation

- **[Complete Testing Guide](TESTING_GUIDE.md)** - Comprehensive pytest setup and usage
- **[API Documentation](API_DOCUMENTATION.md)** - Full API specification
- **[Makefile Commands](Makefile)** - Development workflow commands 