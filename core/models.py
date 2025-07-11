from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, FLOAT
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
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
    preferences = Column(JSON, nullable=True)
    embedding = Column(Vector(384), nullable=True)  # 384-dimensional user interest embedding
    articles_read = Column(Integer, nullable=True, default=0)
    engagement_score = Column(Float, nullable=True, default=0.0)
    
    # Relationships
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    embedding_updates = relationship("UserEmbeddingUpdate", back_populates="user", cascade="all, delete-orphan")

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String)
    source_name = Column(String, nullable=False)
    author = Column(String)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(Text)
    summary = Column(Text)  # AI-generated
    url = Column(Text, nullable=False, unique=True)
    url_to_image = Column(Text)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String(10), default="en")
    category = Column(String(50))
    tags = Column(ARRAY(String))
    
    # Content metadata
    read_time_minutes = Column(Integer)
    difficulty_level = Column(String(20))
    content_type = Column(String(20), default="article")  # article, video, podcast
    moderation_status = Column(String(20), default="approved")
    
    # Engagement metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    bookmarks = Column(Integer, default=0)
    read_time_avg_seconds = Column(Float, default=0.0)
    completion_rate = Column(Float, default=0.0)
    trending_score = Column(Float, default=0.0)
    
    # Semantic embedding for recommendations
    embedding = Column(Vector(384))  # 384-dimensional semantic embedding

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="bookmarks")
    article = relationship("Article")

class UserEmbeddingUpdate(Base):
    __tablename__ = "user_embedding_updates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    embedding_vector = Column(Vector(384))  # 384-dimensional vector
    interaction_summary = Column(JSON)  # Store interaction summary as JSON
    session_start = Column(DateTime, nullable=False)
    session_end = Column(DateTime, nullable=False)
    articles_processed = Column(Integer, nullable=False)
    device_type = Column(String(20))
    app_version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="embedding_updates")
