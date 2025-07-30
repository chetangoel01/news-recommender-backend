# News Recommender Backend

A privacy-first news recommendation system with local ML computation, user authentication, and personalized content delivery. Built with FastAPI, PostgreSQL, and pgvector for scalable semantic search.

## 🚀 Features

- **Privacy-First Architecture**: ML computations run locally on user devices
- **User Authentication**: JWT-based auth with Google & Apple OAuth support  
- **Personalized Recommendations**: Vector-based content matching with user embeddings
- **Semantic Search**: pgvector-powered similarity search across news articles
- **Real-time Sync**: Efficient embedding updates from local device computation
- **Production Ready**: Comprehensive test suite with PostgreSQL integration

## 🏗️ Technology Stack

- **Backend**: FastAPI with async support
- **Database**: PostgreSQL with pgvector extension (Supabase)
- **Authentication**: JWT tokens with bcrypt password hashing & OAuth integration
- **ML/Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **Testing**: pytest with production database testing
- **Deployment**: Containerized with Docker support

## 📁 Project Structure

```
news-recommender-backend/
├── 📂 api/                    # FastAPI routes & endpoints
│   ├── 📄 main.py            # FastAPI app configuration  
│   └── 📂 routes/
│       ├── 📄 auth.py        # Authentication endpoints
│       └── 📄 users.py       # User profile & embedding endpoints
│
├── 📂 core/                   # Core business logic
│   ├── 📄 auth.py            # Authentication & JWT handling
│   ├── 📄 db.py              # Database connection & session management
│   ├── 📄 models.py          # SQLAlchemy models
│   ├── 📄 schemas.py         # Pydantic schemas for API
│   └── 📄 config.py          # Configuration & settings
│
├── 📂 tests/                  # Comprehensive test suite
│   ├── 📄 test_auth.py       # Authentication tests
│   ├── 📄 test_users.py      # User profile & embedding tests
│   └── 📄 conftest.py        # Test configuration & fixtures
│
├── 📂 docs/                   # Comprehensive documentation
├── 📂 scripts/                # Utility scripts (currently empty)
├── 📂 pipeline/               # News processing pipeline
└── 📂 assets/                 # Architecture diagrams
```

## 📚 Documentation

This project has comprehensive documentation organized in the [`docs/`](./docs/) folder:

- **[📖 Documentation Index](./docs/README.md)** - Start here for complete documentation overview
- **[🔐 Authentication Guide](./docs/README_AUTH.md)** - Setup JWT auth, user management  
- **[📊 API Documentation](./docs/API_DOCUMENTATION.md)** - Complete API reference with examples
- **[🗄️ Database Schema](./docs/DATABASE_SCHEMA.md)** - PostgreSQL schema with pgvector setup
- **[🧪 Testing Guide](./docs/TESTING_GUIDE.md)** - Production-grade testing with PostgreSQL
- **[🛣️ Implementation Roadmap](./docs/IMPLEMENTATION_ROADMAP.md)** - Project timeline & features

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.12+
- PostgreSQL with pgvector extension (or Supabase account)
- Virtual environment tool

### 2. Installation
```bash
# Clone and setup
git clone <repository>
cd news-recommender-backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 3. Environment Setup
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your database credentials and secret key
```

### 4. Database Setup
```bash
# Database tables are created automatically by the application
# Verify setup by running tests
python run_tests.py check
```

### 5. Run Development Server
```bash
# Start the API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 6. Run Tests
```bash
# Run full test suite
make test

# Or run specific test categories
python run_tests.py auth     # Authentication tests
python run_tests.py users    # User profile tests  
python run_tests.py all      # All tests
```

## 🏛️ Architecture

This system implements a **privacy-first recommendation architecture**:

1. **Local ML Computation**: User devices compute embeddings locally
2. **Selective Sync**: Only aggregated embeddings sent to server (~every 10 articles)
3. **Server-Side Matching**: Fast vector similarity search with pgvector
4. **Personalized Delivery**: Recommendations based on user interest vectors

```
[User Device]     [API Backend]      [Database]
     │                  │                 │
     ├─ Local ML ────── ├─ Auth/Users ─── ├─ PostgreSQL
     ├─ Reading ─────── ├─ Embeddings ─── ├─ pgvector
     └─ Privacy ─────── └─ Recommendations └─ Vector Search
```

## 🧪 Testing

The project features **production-grade testing** with 43 comprehensive tests:

- ✅ **Authentication Flow**: Registration, login, OAuth (Google/Apple), token management
- ✅ **User Profiles**: Profile management and preferences  
- ✅ **Embedding Updates**: Local ML computation workflow
- ✅ **Database Integration**: Real PostgreSQL with pgvector
- ✅ **API Endpoints**: Complete request/response testing

```bash
# Check current test status
make test
# Expected: 43 passed, minimal warnings
```

## 🚢 Deployment

Ready for production deployment with:
- Docker containerization support
- Environment-based configuration
- Production database compatibility
- Comprehensive monitoring endpoints
- Security best practices implemented

## 📄 License

[Add your license here]

---

**Next Steps**: Check the [📖 Documentation Index](./docs/README.md) for detailed guides on authentication, API usage, database setup, and testing workflows.
