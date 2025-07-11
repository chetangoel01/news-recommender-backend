# Database Schema Documentation

## Overview

This document describes the database schema for the News Recommender Backend system. The schema is designed to support a privacy-first recommendation system with local ML computation capabilities, user engagement tracking, and efficient vector similarity search using PostgreSQL with pgvector extension.

## Core Tables

### Articles Table

**Purpose**: Stores news articles with their content, metadata, and engagement metrics.

```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(100),
    category VARCHAR(50),
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    embedding VECTOR(384),
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    bookmarks INTEGER DEFAULT 0
);
```

**Columns**:
- `id`: UUID primary key for the article
- `title`: Article headline (up to 500 characters)
- `content`: Full article text content
- `summary`: AI-generated summary of the article
- `url`: Original article URL (must be unique)
- `source`: News source (e.g., "CNN", "BBC")
- `category`: Article category (e.g., "technology", "politics")
- `published_at`: When the article was originally published
- `created_at`: When the article was added to our system
- `updated_at`: When the article was last modified
- `embedding`: 384-dimensional vector embedding for semantic similarity
- `views`: Number of times the article has been viewed
- `likes`: Number of user likes
- `shares`: Number of times the article has been shared
- `bookmarks`: Number of times the article has been bookmarked

**Usage**: Central content repository for the recommendation system. Embeddings enable semantic search and content-based filtering.

---

### Users Table

**Purpose**: Stores user accounts, profiles, and personalization data.

```sql
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
    embedding VECTOR(384),
    articles_read INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0.0
);
```

**Columns**:
- `id`: UUID primary key for the user
- `username`: Unique username for login (3-50 characters)
- `email`: Unique email address for account recovery
- `password_hash`: Bcrypt-hashed password for secure authentication
- `display_name`: User's preferred display name (can be different from username)
- `profile_image`: URL or path to user's profile picture
- `bio`: User's self-description or biography
- `created_at`: Account creation timestamp
- `last_active`: Last time the user was active in the system
- `preferences`: JSON object storing user preferences (themes, notification settings, etc.)
- `embedding`: 384-dimensional vector representing user's interests and reading patterns
- `articles_read`: Total number of articles the user has read
- `engagement_score`: Calculated score representing user's overall engagement level

**Usage**: Core user management and personalization. The embedding vector is computed locally on the user's device and represents their reading interests for recommendation purposes.

**Example preferences JSON**:
```json
{
  "theme": "dark",
  "notifications": {
    "email": true,
    "push": false
  },
  "categories": {
    "technology": 0.8,
    "politics": 0.3,
    "sports": 0.1
  },
  "language": "en",
  "reading_speed": "normal"
}
```

---

### User Embedding Updates Table

**Purpose**: Tracks local ML computation sessions and embedding updates from user devices.

```sql
CREATE TABLE user_embedding_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    embedding_vector VECTOR(384),
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    articles_processed INTEGER,
    avg_read_time_seconds FLOAT,
    engagement_metrics JSONB,
    category_exposure JSONB,
    device_type VARCHAR(50),
    app_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_embedding_updates_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);
```

**Columns**:
- `id`: UUID primary key for the update record
- `user_id`: Reference to the user who generated this update
- `embedding_vector`: Updated 384-dimensional embedding computed locally
- `session_start`: When the local ML computation session began
- `session_end`: When the local ML computation session completed
- `articles_processed`: Number of articles processed in this session
- `avg_read_time_seconds`: Average time spent reading articles in this session
- `engagement_metrics`: JSON object with detailed engagement data
- `category_exposure`: JSON object tracking which categories were encountered
- `device_type`: Type of device ("mobile", "tablet", "desktop")
- `app_version`: Version of the client application
- `created_at`: When this update was received by the server

**Usage**: Enables privacy-first personalization by batching local ML computations. Reduces network traffic and keeps detailed user behavior on-device.

**Example engagement_metrics JSON**:
```json
{
  "liked_articles": 3,
  "shared_articles": 1,
  "bookmarked_articles": 2,
  "skipped_articles": 4,
  "total_read_time": 452.3,
  "avg_scroll_depth": 0.75,
  "interaction_patterns": {
    "morning_reading": true,
    "weekend_binge": false
  }
}
```

**Example category_exposure JSON**:
```json
{
  "technology": 4,
  "business": 3,
  "politics": 2,
  "science": 1,
  "sports": 0
}
```

---

### Bookmarks Table

**Purpose**: Stores user's saved articles for later reading.

```sql
CREATE TABLE bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    article_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    
    CONSTRAINT uk_bookmarks_user_article UNIQUE(user_id, article_id),
    
    CONSTRAINT fk_bookmarks_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_bookmarks_article_id 
        FOREIGN KEY (article_id) 
        REFERENCES articles(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);
```

**Columns**:
- `id`: UUID primary key for the bookmark
- `user_id`: Reference to the user who created the bookmark
- `article_id`: Reference to the bookmarked article
- `created_at`: When the bookmark was created
- `notes`: Optional user notes about the bookmarked article

**Constraints**:
- `uk_bookmarks_user_article`: Ensures a user can't bookmark the same article twice
- Cascade deletes ensure bookmarks are removed when users or articles are deleted

**Usage**: Allows users to save articles for later reading. Used in recommendation algorithms to understand user interests.

---

### User Article Interactions Table

**Purpose**: Tracks detailed user interactions with articles for analytics and recommendation improvement.

```sql
CREATE TABLE user_article_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    article_id UUID NOT NULL,
    interaction_type VARCHAR(20) NOT NULL,
    read_time_seconds INTEGER,
    interaction_strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_interactions_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_interactions_article_id 
        FOREIGN KEY (article_id) 
        REFERENCES articles(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    CONSTRAINT chk_interaction_type 
        CHECK (interaction_type IN ('view', 'like', 'share', 'bookmark', 'skip'))
);
```

**Columns**:
- `id`: UUID primary key for the interaction
- `user_id`: Reference to the user who performed the interaction
- `article_id`: Reference to the article that was interacted with
- `interaction_type`: Type of interaction (view, like, share, bookmark, skip)
- `read_time_seconds`: How long the user spent reading (for 'view' interactions)
- `interaction_strength`: Weighted strength of the interaction (1.0 = normal, higher = stronger signal)
- `created_at`: When the interaction occurred

**Interaction Types**:
- `view`: User opened and read the article
- `like`: User explicitly liked the article
- `share`: User shared the article
- `bookmark`: User saved the article for later
- `skip`: User skipped the article without reading

**Usage**: Provides detailed analytics and training data for recommendation algorithms. Helps understand user preferences and engagement patterns.

---

### User Sessions Table

**Purpose**: Manages user authentication sessions and device information.

```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT fk_sessions_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);
```

**Columns**:
- `id`: UUID primary key for the session
- `user_id`: Reference to the authenticated user
- `session_token`: Unique JWT or session token for authentication
- `device_info`: JSON object with device details for security
- `ip_address`: IP address where the session was created
- `user_agent`: Browser/app user agent string
- `created_at`: When the session was created
- `expires_at`: When the session expires
- `last_activity`: Last time this session was used
- `is_active`: Whether the session is currently active

**Usage**: Secure session management, device tracking for security, and analytics about user access patterns.

**Example device_info JSON**:
```json
{
  "device_type": "mobile",
  "platform": "iOS",
  "app_version": "1.2.3",
  "screen_size": "1170x2532",
  "timezone": "America/New_York"
}
```

---

## Indexes and Performance

### Primary Indexes

```sql
-- Vector similarity indexes (requires pgvector extension)
CREATE INDEX idx_users_embedding ON users USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops);

-- Article indexes
CREATE INDEX idx_articles_url ON articles(url);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_created_at ON articles(created_at);
CREATE INDEX idx_articles_views ON articles(views);

-- User lookup indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_active ON users(last_active);

-- Foreign key indexes for efficient joins
CREATE INDEX idx_user_embedding_updates_user_id ON user_embedding_updates(user_id);
CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);
CREATE INDEX idx_bookmarks_article_id ON bookmarks(article_id);
CREATE INDEX idx_interactions_user_id ON user_article_interactions(user_id);
CREATE INDEX idx_interactions_article_id ON user_article_interactions(article_id);
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);

-- Temporal indexes for time-based queries
CREATE INDEX idx_user_embedding_updates_created_at ON user_embedding_updates(created_at);
CREATE INDEX idx_bookmarks_created_at ON bookmarks(created_at);
CREATE INDEX idx_interactions_created_at ON user_article_interactions(created_at);

-- Composite indexes for common query patterns
CREATE INDEX idx_interactions_user_article ON user_article_interactions(user_id, article_id);
CREATE INDEX idx_interactions_type ON user_article_interactions(interaction_type);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
```

### Index Usage Patterns

- **Vector Indexes**: Enable fast cosine similarity searches for recommendations
- **Foreign Key Indexes**: Speed up JOIN operations and maintain referential integrity
- **Temporal Indexes**: Support time-based queries (recent articles, session cleanup)
- **Composite Indexes**: Optimize complex queries involving multiple columns

---

## Relationships and Data Flow

### Entity Relationship Diagram

```
Users (1) ←→ (M) UserEmbeddingUpdates
Users (1) ←→ (M) Bookmarks ←→ (M) Articles
Users (1) ←→ (M) UserArticleInteractions ←→ (M) Articles  
Users (1) ←→ (M) UserSessions
```

### Data Flow Patterns

1. **User Registration Flow**:
   ```
   User registers → users table created → Initial embedding computed locally
   ```

2. **Reading Session Flow**:
   ```
   User reads articles → interactions logged → Local ML processes batch → 
   embedding_vector updated → Server receives embedding update
   ```

3. **Recommendation Flow**:
   ```
   User requests feed → User embedding retrieved → Vector similarity search → 
   Articles ranked by relevance → Personalized feed returned
   ```

4. **Engagement Tracking**:
   ```
   User interacts with article → user_article_interactions logged → 
   Article engagement counters updated → User engagement_score updated
   ```

---

## Security Considerations

### Data Protection

1. **Password Security**: All passwords are bcrypt-hashed with salt
2. **Session Management**: JWTs with expiration and device tracking
3. **Privacy-First ML**: Embeddings computed locally, only aggregated data shared
4. **Cascade Deletes**: Automatic cleanup prevents orphaned sensitive data

### Access Patterns

- **User Data**: Users can only access their own data
- **Public Data**: Articles are publicly readable but interaction data is private
- **Admin Access**: Limited to system maintenance and anonymized analytics

---

## Maintenance Procedures

### Regular Cleanup

```sql
-- Clean up expired sessions (run daily)
DELETE FROM user_sessions 
WHERE expires_at < NOW() AND is_active = false;

-- Archive old embedding updates (run monthly)
DELETE FROM user_embedding_updates 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Update engagement scores (run weekly)
UPDATE users SET engagement_score = (
    SELECT AVG(interaction_strength) 
    FROM user_article_interactions 
    WHERE user_id = users.id 
    AND created_at > NOW() - INTERVAL '30 days'
);
```

### Performance Monitoring

```sql
-- Monitor vector index performance
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%embedding%';

-- Check table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public';
```

---

## Migration Scripts

### Initial Setup

1. Ensure pgvector extension is installed
2. Run the main table creation script
3. Create indexes for performance
4. Set up regular maintenance jobs

### Future Schema Changes

- Use `ALTER TABLE` with `IF NOT EXISTS` for safe migrations
- Always test migrations on development data first
- Consider downtime requirements for large table modifications
- Plan index rebuilding for vector similarity indexes

---

## Usage Examples

### Common Queries

```sql
-- Get user's recent bookmarks
SELECT a.title, a.summary, b.created_at, b.notes
FROM bookmarks b
JOIN articles a ON b.article_id = a.id
WHERE b.user_id = $1
ORDER BY b.created_at DESC
LIMIT 20;

-- Find similar articles using vector similarity
SELECT title, url, embedding <=> $1 as similarity
FROM articles
WHERE embedding <=> $1 < 0.5
ORDER BY embedding <=> $1
LIMIT 10;

-- Get user engagement analytics
SELECT 
    COUNT(*) as total_interactions,
    COUNT(*) FILTER (WHERE interaction_type = 'like') as likes,
    COUNT(*) FILTER (WHERE interaction_type = 'share') as shares,
    AVG(read_time_seconds) as avg_read_time
FROM user_article_interactions
WHERE user_id = $1
AND created_at > NOW() - INTERVAL '30 days';

-- Find trending articles
SELECT title, views, likes, shares, 
       (views + likes * 2 + shares * 3) as trend_score
FROM articles
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY trend_score DESC
LIMIT 20;
```

---

## Complete Database Setup Script

Here's the complete SQL script to create the entire database schema from scratch:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create articles table
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(100),
    category VARCHAR(50),
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    embedding VECTOR(384),
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    bookmarks INTEGER DEFAULT 0
);

-- Create users table
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
    embedding VECTOR(384),
    articles_read INTEGER DEFAULT 0,
    engagement_score FLOAT DEFAULT 0.0
);

-- Create user_embedding_updates table
CREATE TABLE user_embedding_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    embedding_vector VECTOR(384),
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    articles_processed INTEGER,
    avg_read_time_seconds FLOAT,
    engagement_metrics JSONB,
    category_exposure JSONB,
    device_type VARCHAR(50),
    app_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_embedding_updates_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);

-- Create bookmarks table
CREATE TABLE bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    article_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    
    CONSTRAINT uk_bookmarks_user_article UNIQUE(user_id, article_id),
    
    CONSTRAINT fk_bookmarks_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_bookmarks_article_id 
        FOREIGN KEY (article_id) 
        REFERENCES articles(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);

-- Create user_article_interactions table
CREATE TABLE user_article_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    article_id UUID NOT NULL,
    interaction_type VARCHAR(20) NOT NULL,
    read_time_seconds INTEGER,
    interaction_strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_interactions_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_interactions_article_id 
        FOREIGN KEY (article_id) 
        REFERENCES articles(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    CONSTRAINT chk_interaction_type 
        CHECK (interaction_type IN ('view', 'like', 'share', 'bookmark', 'skip'))
);

-- Create user_sessions table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT fk_sessions_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
);

-- Create all indexes
-- Vector similarity indexes
CREATE INDEX idx_users_embedding ON users USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops);

-- Article indexes
CREATE INDEX idx_articles_url ON articles(url);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_created_at ON articles(created_at);
CREATE INDEX idx_articles_views ON articles(views);

-- User lookup indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_active ON users(last_active);

-- Foreign key indexes for efficient joins
CREATE INDEX idx_user_embedding_updates_user_id ON user_embedding_updates(user_id);
CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);
CREATE INDEX idx_bookmarks_article_id ON bookmarks(article_id);
CREATE INDEX idx_interactions_user_id ON user_article_interactions(user_id);
CREATE INDEX idx_interactions_article_id ON user_article_interactions(article_id);
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);

-- Temporal indexes for time-based queries
CREATE INDEX idx_user_embedding_updates_created_at ON user_embedding_updates(created_at);
CREATE INDEX idx_bookmarks_created_at ON bookmarks(created_at);
CREATE INDEX idx_interactions_created_at ON user_article_interactions(created_at);

-- Composite indexes for common query patterns
CREATE INDEX idx_interactions_user_article ON user_article_interactions(user_id, article_id);
CREATE INDEX idx_interactions_type ON user_article_interactions(interaction_type);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
```

This schema is designed to support a modern, privacy-first news recommendation system with efficient vector similarity search and comprehensive user engagement tracking. 