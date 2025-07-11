from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any
from core.db import get_db
from core.auth import get_current_active_user
from core.models import User, UserEmbeddingUpdate
from core.schemas import (
    UserProfileResponse,
    UserProfileUpdate,
    UserEmbeddingUpdateRequest,
    UserEmbeddingUpdateResponse,
    EmbeddingStatusResponse
)

router = APIRouter(tags=["users"])

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information.
    
    Returns detailed user profile including preferences and statistics.
    """
    return UserProfileResponse(
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        email=current_user.email,
        profile_image=current_user.profile_image,
        bio=current_user.bio,
        created_at=current_user.created_at,
        articles_read=current_user.articles_read,
        preferences=current_user.preferences
    )

@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile information.
    
    Allows updating display name, bio, profile image, and preferences.
    """
    # Update only provided fields
    if profile_update.display_name is not None:
        current_user.display_name = profile_update.display_name
    
    if profile_update.bio is not None:
        current_user.bio = profile_update.bio
    
    if profile_update.profile_image is not None:
        current_user.profile_image = profile_update.profile_image
    
    if profile_update.preferences is not None:
        # Merge with existing preferences
        existing_prefs = current_user.preferences or {}
        updated_prefs = {**existing_prefs, **profile_update.preferences}
        current_user.preferences = updated_prefs
    
    # Update last active timestamp
    current_user.last_active = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(current_user)
        
        return UserProfileResponse(
            user_id=current_user.id,
            username=current_user.username,
            display_name=current_user.display_name,
            email=current_user.email,
            profile_image=current_user.profile_image,
            bio=current_user.bio,
            created_at=current_user.created_at,
            articles_read=current_user.articles_read,
            preferences=current_user.preferences
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.post("/embedding/update", response_model=UserEmbeddingUpdateResponse)
async def update_user_embedding(
    embedding_update: UserEmbeddingUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user embedding vector based on local device computation.
    
    Sent every ~10 articles to update server-side recommendations.
    """
    try:
        # Create embedding update record
        db_embedding_update = UserEmbeddingUpdate(
            user_id=current_user.id,
            embedding_vector=embedding_update.embedding_vector,
            interaction_summary=embedding_update.interaction_summary.dict(),
            session_start=embedding_update.session_start,
            session_end=embedding_update.session_end,
            articles_processed=embedding_update.articles_processed,
            device_type=embedding_update.device_type,
            app_version=embedding_update.app_version
        )
        
        # Update user's embedding vector (store as pgvector)
        current_user.embedding = embedding_update.embedding_vector
        
        # Update user statistics based on interaction summary
        engagement_metrics = embedding_update.interaction_summary.engagement_metrics
        current_user.articles_read += embedding_update.articles_processed
        
        # Calculate engagement score (simple heuristic)
        total_interactions = (
            engagement_metrics.liked_articles + 
            engagement_metrics.shared_articles + 
            engagement_metrics.bookmarked_articles
        )
        if embedding_update.articles_processed > 0:
            engagement_rate = total_interactions / embedding_update.articles_processed
            # Update engagement score with exponential moving average
            alpha = 0.3  # Learning rate
            current_user.engagement_score = (
                alpha * engagement_rate + 
                (1 - alpha) * current_user.engagement_score
            )
        
        # Update last active timestamp
        current_user.last_active = datetime.utcnow()
        
        # Save to database
        db.add(db_embedding_update)
        db.commit()
        db.refresh(current_user)
        
        # Calculate personalization metrics
        personalization_score = min(0.9, current_user.engagement_score + 0.1)
        diversity_adjustment = 0.2 if current_user.engagement_score > 0.5 else 0.1
        
        return UserEmbeddingUpdateResponse(
            embedding_updated=True,
            recommendations_refreshed=True,
            next_batch_ready=True,
            personalization_score=personalization_score,
            diversity_adjustment=diversity_adjustment
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user embedding"
        )

@router.get("/embedding/status", response_model=EmbeddingStatusResponse)
async def get_embedding_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user embedding status and sync requirements.
    """
    # Get latest embedding update
    latest_update = db.query(UserEmbeddingUpdate)\
        .filter(UserEmbeddingUpdate.user_id == current_user.id)\
        .order_by(UserEmbeddingUpdate.created_at.desc())\
        .first()
    
    last_updated = latest_update.created_at if latest_update else None
    
    # Calculate articles since last update (placeholder logic)
    articles_since_update = 5  # This would be calculated based on user activity
    sync_required = articles_since_update >= 10
    
    local_computation_config = {
        "model_name": "all-MiniLM-L6-v2",
        "update_frequency": 10,
        "batch_size_recommended": 50
    }
    
    return EmbeddingStatusResponse(
        last_updated=last_updated,
        articles_since_update=articles_since_update,
        sync_required=sync_required,
        embedding_version="v2.1",
        local_computation_config=local_computation_config
    )
