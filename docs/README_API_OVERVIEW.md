# News Recommender Backend - API Documentation Overview

## 📚 Documentation Files

1. **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - Complete API specification with all endpoints
2. **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** - Phased development plan and priorities
3. **README_API_OVERVIEW.md** (this file) - Quick reference and summary

## 🎯 Key Features Covered

### Core Functionality
- **Swipe-based navigation** optimized for mobile consumption
- **ML-powered recommendations** using semantic embeddings
- **Local embedding computation** for privacy and efficiency
- **Batched analytics** with client-side processing
- **Content moderation** and admin controls

### Technical Highlights
- **FastAPI** backend with automatic API documentation
- **PostgreSQL + pgvector** for semantic similarity search
- **Sentence Transformers** for 384-dimensional embeddings
- **Redis caching** for performance optimization
- **JWT authentication** with refresh token support
- **Privacy-first ML** with local computation and batched updates

## 🔧 API Categories

| Category | Endpoints | Purpose |
|----------|-----------|---------|
| **Authentication** | `/auth/*` | User registration, login, token management |
| **User Management** | `/users/*` | Profiles, preferences, embedding updates |
| **Content** | `/articles/*` | Article CRUD, viewing, metadata |
| **Discovery** | `/feed/*`, `/search/*` | Personalized feeds, trending, search |
| **Engagement** | `/articles/{id}/like`, `/bookmarks/*` | Likes, shares, bookmarks |
| **Analytics** | `/users/embedding/*` | Local ML coordination, batched updates |
| **Admin** | `/admin/*` | Content moderation, user management |

## 📱 Swipe Navigation API Pattern

```javascript
// Core swipe interactions
POST /articles/{id}/view           // Track article view
POST /users/embedding/update       // Batched embedding updates (every 10 articles)
GET /feed/personalized            // Get next articles for swiping
GET /articles/{id}/similar        // Related content suggestions
GET /users/embedding/status       // Check sync requirements
```

**Swipe Actions:**
- **Up**: Next article (positive engagement)
- **Down**: Previous article (navigation)
- **Left**: Skip/dislike (negative feedback)
- **Right**: Like/save (strong positive signal)

## 🤖 Recommendation System APIs

### Content Discovery
```
GET /feed/personalized          # ML-powered personal feed
GET /feed/trending             # Platform-wide trending content
GET /articles/{id}/similar     # Vector similarity search
GET /search/articles           # Semantic + keyword search
```

### Local ML Data Collection
```
POST /users/embedding/update   # Batched user embedding updates
GET /users/embedding/status    # Sync status and configuration
POST /articles/{id}/view       # Reading behavior tracking
POST /articles/{id}/like       # Explicit feedback
```

## 🔄 Privacy-First Architecture

### Local Embedding Computation
```
Client Device Processing       # User interactions → Local ML model
Every 10 Articles             # Trigger embedding computation
Batch Update                  # Send aggregated data to server
Server Refresh               # Update recommendations
```

### Benefits of Local Processing
- **95% Network Reduction**: Batched vs real-time updates
- **Enhanced Privacy**: User data stays on device until aggregated
- **Offline Capability**: Works without constant connectivity
- **Battery Efficiency**: Optimized batch processing
- **90% Server Load Reduction**: Client-side computation

## 📊 Data Models Overview

### Core Entities
```python
User                          # User profiles and preferences
Article                      # News content with embeddings
UserEmbeddingUpdate          # Batched embedding updates with interaction summaries
Bookmark                     # User bookmarked articles
```

### ML Components
```python
# 384-dimensional vectors for similarity
article.embedding            # Content semantic representation
user.embedding              # User interest profile (updated via batches)
embedding_update.vector     # Client-computed embedding updates
```

## 🚀 Implementation Priority

### Phase 1: MVP (Weeks 1-4)
1. ✅ **Authentication APIs** - Register, login, profile management
2. ✅ **Basic Article APIs** - CRUD operations, viewing
3. ✅ **Simple Feed** - Basic personalized recommendations
4. ✅ **Core Interactions** - Like, bookmark, view tracking
5. ✅ **Local ML Setup** - Client-side embedding computation

### Phase 2: Enhanced Features (Weeks 5-8)
1. **Batched Analytics** - Local embedding updates every 10 articles
2. **Advanced Recommendations** - Hybrid local-server approach
3. **Search & Discovery** - Semantic search with similarity
4. **Performance Optimization** - Caching and efficiency improvements

### Phase 3: Advanced Features (Weeks 9-12)
1. **Advanced ML** - Personalization algorithms, A/B testing
2. **Analytics Dashboard** - Privacy-first performance metrics
3. **Content Discovery** - Enhanced search and trending
4. **Edge Computing** - Optimized ML model distribution

### Phase 4: Production Ready (Weeks 13-16)
1. **Admin Panel** - Content moderation and user management
2. **Performance Optimization** - Caching, CDN, scaling
3. **Monitoring** - Health checks, logging, alerts
4. **Security Hardening** - Rate limiting, input validation

## 🏗️ Architecture Patterns

### Microservices Ready
- **Auth Service**: User authentication and authorization
- **Content Service**: Article management and storage
- **Recommendation Engine**: ML-powered personalization
- **Analytics Service**: Batched embedding processing
- **Admin Service**: Moderation and management

### Caching Strategy
- **L1 (In-Memory)**: Hot recommendations, user sessions
- **L2 (Redis)**: Article metadata, embedding similarity scores
- **L3 (CDN)**: Images, ML models, static assets
- **Local Cache**: Client-side embeddings and interaction buffer

### Performance Targets
- Feed generation: **< 200ms**
- Embedding similarity: **< 100ms**
- Search queries: **< 300ms**
- Local ML computation: **< 100ms per batch**
- Embedding updates: **< 500ms**

## 🔐 Security & Compliance

### Authentication
- **JWT tokens** with 1-hour expiration
- **Refresh tokens** for seamless re-authentication
- **Role-based access** (user, creator, moderator, admin)

### Privacy-First Design
- **Local ML Processing**: User behavior stays on device
- **Aggregated Updates**: Only computed embeddings sent to server
- **GDPR compliance** for EU users
- **COPPA compliance** for users under 13
- **Content sanitization** for XSS prevention
- **Rate limiting** on all endpoints

### Technical Privacy Features
- **Model Download**: ML model cached locally (~22MB)
- **Interaction Buffering**: Local storage until batch threshold
- **Aggregated Analytics**: Summary statistics instead of raw events
- **Embedding Vectors**: Abstract representations vs detailed behavior

## 📈 Success Metrics

### User Engagement
- **Session duration** - Time spent in app
- **Swipe velocity** - Articles consumed per session
- **Return rate** - Daily/weekly active users
- **Content completion** - Percentage of articles read fully

### Recommendation Quality
- **Click-through rate** - Articles opened from feed
- **Dwell time** - Time spent reading recommended content
- **Like rate** - Positive feedback on recommendations
- **Diversity score** - Topic variety in personal feeds

### Privacy & Efficiency Metrics
- **Network efficiency** - API calls reduced vs traditional tracking
- **Local computation time** - On-device ML processing speed
- **Battery impact** - Power usage optimization
- **Offline functionality** - App usage without connectivity

### Business Metrics
- **User growth** - Registration and retention rates
- **Content velocity** - New articles processed daily
- **Engagement rate** - Individual interactions per user
- **Platform health** - Uptime and performance metrics

## 🛠️ Development Tools

### API Documentation
- **FastAPI automatic docs** at `/docs` and `/redoc`
- **OpenAPI specification** for client generation
- **Postman collections** for testing

### Local ML Development
- **Model versioning** for client-side updates
- **Embedding validation** tools
- **Privacy compliance** testing
- **Performance profiling** for local computation

### Testing Strategy
- **Unit tests** for core business logic
- **Integration tests** for API endpoints
- **Load testing** for performance validation
- **A/B testing** for recommendation algorithms
- **Privacy testing** for data handling compliance

## 📞 Quick Start

1. **Review the full API documentation** in `API_DOCUMENTATION.md`
2. **Follow the implementation roadmap** in `IMPLEMENTATION_ROADMAP.md`
3. **Start with Phase 1 APIs** for immediate value
4. **Plan client-side ML integration** early in development
5. **Build incrementally** following the phased approach

---

This documentation provides a complete foundation for building a modern, privacy-first news application with sophisticated recommendation capabilities and optimized swipe-based navigation. The local ML computation approach ensures user privacy while reducing server costs and improving performance through efficient batched processing. 