from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# User Preferences Schema
class UserPreferences(BaseModel):
    categories: Optional[List[str]] = []
    language: Optional[str] = "en"
    content_type: Optional[str] = "mixed"
    notification_settings: Optional[Dict[str, Any]] = {}

# Authentication Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    display_name: str
    preferences: Optional[UserPreferences] = None

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @field_validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.isalnum():
            raise ValueError('Username must contain only alphanumeric characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenRefresh(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    username: str
    display_name: str
    profile_image: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Response Schemas
class UserRegisterResponse(BaseModel):
    user_id: UUID
    email: str
    username: str
    access_token: str
    refresh_token: str
    expires_in: int

class UserLoginResponse(BaseModel):
    user_id: UUID
    access_token: str
    refresh_token: str
    expires_in: int
    user_profile: UserProfile

class TokenRefreshResponse(BaseModel):
    access_token: str
    expires_in: int

class UserProfileResponse(BaseModel):
    user_id: UUID
    username: str
    display_name: str
    email: str
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    articles_read: int
    preferences: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

# Interaction Summary Schemas
class EngagementMetrics(BaseModel):
    liked_articles: int
    shared_articles: int
    bookmarked_articles: int
    skipped_articles: int

class InteractionSummary(BaseModel):
    avg_read_time_seconds: float
    engagement_metrics: EngagementMetrics
    category_exposure: Dict[str, int]

class UserEmbeddingUpdateRequest(BaseModel):
    embedding_vector: List[float]
    interaction_summary: InteractionSummary
    session_start: datetime
    session_end: datetime
    articles_processed: int
    device_type: str
    app_version: str

    @field_validator('embedding_vector')
    def validate_embedding_vector(cls, v):
        if len(v) != 384:
            raise ValueError('Embedding vector must be 384-dimensional')
        return v

class UserEmbeddingUpdateResponse(BaseModel):
    embedding_updated: bool
    recommendations_refreshed: bool
    next_batch_ready: bool
    personalization_score: float
    diversity_adjustment: float

class EmbeddingStatusResponse(BaseModel):
    last_updated: Optional[datetime]
    articles_since_update: int
    sync_required: bool
    embedding_version: str
    local_computation_config: Dict[str, Any]

# Error Response Schema
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    reason: str

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[ErrorDetail] = None
    request_id: Optional[str] = None 