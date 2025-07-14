from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, FLOAT
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from core.db import Base

# Import pgvector vector type
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    # Fallback to ARRAY if pgvector not available
    Vector = lambda dim: ARRAY(FLOAT)

class User(Base):
    __tablename__ = "users"
    
    # Core fields matching the PostgreSQL schema
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    profile_image = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True, server_default=func.now())
    last_active = Column(DateTime, nullable=True, server_default=func.now(), index=True)
    
    # App-specific fields
    preferences = Column(JSON, nullable=True)  # JSONB in actual database
    embedding = Column(Vector(384), nullable=True)  # 384-dimensional user interest embedding (USER-DEFINED type)
    articles_read = Column(Integer, nullable=True, default=0)
    engagement_score = Column(Float, nullable=True, default=0.0)
    
    # Relationships
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    shares = relationship("Share", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    embedding_updates = relationship("UserEmbeddingUpdate", back_populates="user", cascade="all, delete-orphan")

class Article(Base):
    __tablename__ = "articles"
    
    # Match the actual database schema provided by the user
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    source_id = Column(Text)
    source_name = Column(Text, nullable=False)
    author = Column(Text)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(Text)
    summary = Column(Text)  # AI-generated
    url = Column(Text, nullable=False, unique=True)
    url_to_image = Column(Text)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, server_default=func.current_timestamp())
    language = Column(Text)
    category = Column(Text)
    
    # Engagement metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    bookmarks = Column(Integer, default=0)
    
    # Semantic embedding for recommendations
    embedding = Column(Vector(384))  # 384-dimensional semantic embedding (USER-DEFINED type in DB)
    
    # These columns don't exist in the actual database yet
    # tags = Column(ARRAY(String))
    # read_time_minutes = Column(Integer)
    # difficulty_level = Column(String(20))
    # content_type = Column(String(20), default="article")
    # moderation_status = Column(String(20), default="approved")
    # read_time_avg_seconds = Column(Float, default=0.0)
    # completion_rate = Column(Float, default=0.0)
    # trending_score = Column(Float, default=0.0)

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="likes")
    article = relationship("Article")

class Share(Base):
    __tablename__ = "shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    platform = Column(String, nullable=True)  # e.g., 'twitter', 'facebook', 'email', 'copy_link'
    message = Column(Text, nullable=True)  # Optional user message with the share
    count = Column(Integer, default=1, nullable=False)  # Number of times this user shared this article
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="shares")
    article = relationship("Article")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="bookmarks")
    article = relationship("Article")

class UserEmbeddingUpdate(Base):
    __tablename__ = "user_embedding_updates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    embedding_vector = Column(Vector(384))  # 384-dimensional vector (USER-DEFINED type)
    interaction_summary = Column(JSON)  # Store interaction summary as JSON
    session_start = Column(DateTime, nullable=False)
    session_end = Column(DateTime, nullable=False)
    articles_processed = Column(Integer, nullable=False)
    device_type = Column(String)  # character varying in DB
    app_version = Column(String)  # character varying in DB
    created_at = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="embedding_updates")
