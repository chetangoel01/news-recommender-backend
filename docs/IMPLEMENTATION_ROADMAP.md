# Implementation Roadmap for News Recommender Backend

## Current State Analysis

Based on your existing codebase, you already have:
✅ **Article model with pgvector embeddings** (384-dimensional)  
✅ **ML pipeline for content processing** (fetch → summarize → embed)  
✅ **Basic FastAPI structure** with routing setup  
✅ **PostgreSQL database** with pgvector support  
✅ **Sentence transformers** for semantic embeddings  
✅ **News fetching pipeline** from NewsAPI  

## Phase 1: Core MVP (Weeks 1-4)

### Priority 1: Authentication & User Management
**Files to create/modify:**
- `api/routes/auth.py` - JWT authentication endpoints
- `api/routes/users.py` - User profile management (currently empty)
- `core/models.py` - Add User, UserPreferences models
- `core/auth.py` - JWT token handling utilities

**Key APIs to implement:**
```
POST /auth/register
POST /auth/login  
POST /auth/refresh
GET /users/profile
PUT /users/profile
```

### Priority 2: Article APIs & Basic Feed
**Files to create/modify:**
- `api/routes/articles.py` - Article CRUD operations
- `api/routes/feed.py` - Basic personalized feed
- `core/models.py` - Add UserEmbeddingUpdate model

**Key APIs to implement:**
```
GET /articles
GET /articles/{id}
POST /articles/{id}/view
GET /feed/personalized
GET /feed/trending
```

### Priority 3: Basic Recommendations
**Files to create/modify:**
- `services/recommendation.py` - Core recommendation logic
- `services/similarity.py` - Vector similarity search
- Update existing `pipeline/embed.py` for user embeddings

**Integration points:**
- Use existing article embeddings for content-based filtering
- Implement basic collaborative filtering using user embeddings
- Leverage pgvector for efficient similarity search

### Priority 4: Local Embedding Computation
**Files to create/modify:**
- `api/routes/embedding.py` - Embedding update endpoints
- `services/local_ml.py` - Client-side ML coordination
- `ml/embedding_sync.py` - Batch processing logic

**Key APIs to implement:**
```
POST /users/embedding/update
GET /users/embedding/status
```

## Phase 2: Enhanced Features (Weeks 5-8)

### Advanced Recommendation Engine
**Files to create:**
- `ml/collaborative_filtering.py` - Matrix factorization using embeddings
- `ml/content_filtering.py` - Enhanced content-based filtering
- `services/personalization.py` - Real-time personalization updates

### Engagement & Analytics
**Key APIs:**
```
POST /articles/{id}/like
POST /articles/{id}/share
POST /articles/{id}/bookmark
GET /users/bookmarks
GET /search/articles
GET /articles/{id}/similar
```

### Search & Discovery
**New components:**
- Semantic search with query expansion
- Trending detection algorithms
- Content diversity optimization
- Similar article recommendations

## Phase 3: Advanced ML & Analytics (Weeks 9-12)

### Local ML Integration
**Files to create:**
- `ml/embedding_models.py` - Local model management
- `ml/batch_processing.py` - Efficient batch updates
- `services/privacy_ml.py` - Privacy-first analytics

### Analytics & Performance
**New components:**
- Batched embedding update processing
- Performance monitoring for local computation
- Model evaluation and A/B testing framework
- Content performance analytics

### Advanced Features
- Cold start problem solutions for new users
- Real-time trend detection
- Content freshness optimization
- Personalization strength tuning

## Phase 4: Production Ready (Weeks 13-16)

### Admin & Moderation
**Files to create:**
- `api/routes/admin.py` - Admin dashboard APIs
- `services/moderation.py` - Content moderation logic
- `ml/content_safety.py` - Automated content filtering

### Performance & Scalability
**Optimizations:**
- Database indexing and query optimization
- Redis caching strategies for embeddings
- CDN integration for media content
- API rate limiting and throttling
- Edge computing for ML model distribution

### Monitoring & Deployment
**Infrastructure:**
- Health check endpoints
- Logging and error tracking
- Performance metrics collection
- Docker containerization
- ML model versioning system

## Technical Implementation Details

### Database Schema Extensions Needed

```sql
-- Add to your existing Article table
ALTER TABLE articles ADD COLUMN views INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN likes INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN shares INTEGER DEFAULT 0;
ALTER TABLE articles ADD COLUMN bookmarks INTEGER DEFAULT 0;

-- New tables to create
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    profile_image TEXT,
    bio TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    preferences JSONB,
    embedding VECTOR(384),  -- User interest embedding
    articles_read INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0.0
);

CREATE TABLE user_embedding_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    embedding_vector VECTOR(384),
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    articles_processed INTEGER,
    avg_read_time_seconds FLOAT,
    engagement_metrics JSONB,
    category_exposure JSONB,
    device_type VARCHAR(50),
    app_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    article_id UUID REFERENCES articles(id),
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    UNIQUE(user_id, article_id)
);

-- Indexes for performance
CREATE INDEX idx_users_embedding ON users USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_user_embedding_updates_user_id ON user_embedding_updates(user_id);
CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);
```

### Local Embedding Computation Architecture

1. **Client-Side Processing (Week 4)**
   - Download all-MiniLM-L6-v2 model (~22MB)
   - Local interaction buffering and aggregation
   - Privacy-first approach with minimal data sharing

2. **Batch Updates (Week 5)**
   - Every 10 articles trigger embedding computation
   - Send aggregated embedding + interaction summary
   - Server-side recommendation refresh

3. **Hybrid Approach (Week 7)**
   - Combine local embeddings with server-side collaborative filtering
   - Real-time personalization with offline capability
   - Edge computing optimizations

4. **Advanced ML (Week 10)**
   - Federated learning principles
   - On-device model fine-tuning
   - Privacy-preserving analytics

### Recommendation Algorithm Priority

1. **Content-Based (Week 1)**
   - Use existing article embeddings
   - Cosine similarity with user's reading history
   - Simple but effective for cold start

2. **Embedding-Based Collaborative Filtering (Week 3)**
   - User embedding similarity
   - Collaborative signals without individual tracking
   - Privacy-preserving recommendations

3. **Hybrid Local-Server Approach (Week 6)**
   - Local embedding computation + server optimization
   - Real-time learning from aggregated feedback
   - Diversity and novelty optimization

4. **Advanced Personalization (Week 9)**
   - Multi-objective optimization
   - Context-aware recommendations
   - Temporal pattern recognition

### API Performance Targets

- **Feed generation**: < 200ms
- **Embedding similarity**: < 100ms  
- **Search queries**: < 300ms
- **Embedding updates**: < 500ms
- **Local ML computation**: < 100ms per batch

### Swipe Navigation Optimization

**Preloading Strategy:**
- Load next 10 articles when user reaches article 5
- Cache article images and metadata
- Background embedding computation
- Prefetch similarity recommendations

**Local Interaction Tracking:**
```python
# Local device buffer (sent every 10 articles)
{
    "embedding_vector": [0.1, -0.2, 0.3, ...],
    "interaction_summary": {
        "articles_processed": 10,
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
    }
}
```

## Key Integrations

### Existing Components to Leverage
- **`pipeline/embed.py`**: Extend for user embedding computation
- **`pipeline/run_pipeline.py`**: Add embedding update processing
- **`core/models.py`**: Add embedding and analytics models
- **`core/db.py`**: Add connection pooling for batch processing

### External Services Integration
- **Redis**: Embedding caching, session management
- **CDN**: ML model distribution, image optimization
- **Edge Computing**: Local ML model hosting
- **Analytics**: Privacy-first metrics collection

## Success Metrics

### Week 4 (MVP):
- User registration and authentication working
- Basic article feed with 10+ articles
- Simple like/bookmark functionality
- Local embedding computation functional

### Week 8 (Enhanced):
- Batched embedding updates working
- Advanced recommendation accuracy > 70%
- Search and discovery features
- Performance targets met

### Week 12 (Advanced):
- Privacy-first ML pipeline
- A/B testing framework
- Advanced analytics dashboard
- Recommendation accuracy > 80%

### Week 16 (Production):
- Full admin panel
- Content moderation
- Edge computing optimizations
- 99.9% uptime target

## Privacy & Efficiency Benefits

### Local Computation Advantages
- **95% Network Reduction**: Batched vs real-time updates
- **90% Server Load Reduction**: Client-side processing
- **Enhanced Privacy**: User data stays on device
- **Offline Capability**: Works without constant connectivity
- **Battery Efficiency**: Optimized batch processing

### Technical Specifications
- **Model Size**: 22MB initial download
- **Memory Usage**: <50MB additional RAM
- **Processing Time**: <100ms per batch update
- **Network Efficiency**: 1 API call per 10 articles vs 50+ calls

## Next Immediate Steps

1. **Start with authentication** - Create `api/routes/auth.py`
2. **Extend user models** - Add User table to `core/models.py`
3. **Create article routes** - Build on existing Article model
4. **Implement local ML coordination** - Plan client-side embedding computation
5. **Test with existing data** - Use your current article pipeline

The focus is now on building a privacy-first, efficient system that reduces server load while maintaining high-quality personalization through local machine learning computation. 