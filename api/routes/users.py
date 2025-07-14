from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from core.db import get_db
from core.auth import get_current_active_user
from core.models import User, UserEmbeddingUpdate, Bookmark, Article, Like, Share
from core.schemas import (
    UserProfileResponse,
    UserProfileUpdate,
    UserEmbeddingUpdateRequest,
    UserEmbeddingUpdateResponse,
    EmbeddingStatusResponse,
    BookmarksResponse,
    BookmarkItem,
    ArticleSummary,
    ArticleSource,
    ArticleEngagement
)

router = APIRouter(tags=["users"])

def _build_article_source(article: Article) -> ArticleSource:
    """Helper function to build ArticleSource from Article model."""
    return ArticleSource(
        id=article.source_id,
        name=article.source_name,
        logo=None,  # TODO: Add source logo mapping
        credibility_score=None  # TODO: Implement credibility scoring
    )

def _build_article_engagement(article: Article, user: User, db: Session) -> ArticleEngagement:
    """Helper function to build ArticleEngagement from Article model."""
    from sqlalchemy import and_
    # Check if user has liked/shared/bookmarked this article
    user_liked = bool(
        db.query(Like).filter(
            and_(Like.user_id == user.id, Like.article_id == article.id)
        ).first()
    ) if user else False
    
    user_shared = bool(
        db.query(Share).filter(
            and_(Share.user_id == user.id, Share.article_id == article.id)
        ).first()
    ) if user else False
    
    user_bookmarked = bool(
        db.query(Bookmark).filter(
            and_(Bookmark.user_id == user.id, Bookmark.article_id == article.id)
        ).first()
    ) if user else False
    
    return ArticleEngagement(
        views=article.views or 0,
        likes=article.likes or 0,
        shares=article.shares or 0,
        user_liked=user_liked,
        user_shared=user_shared,
        user_bookmarked=user_bookmarked
    )

def _get_content_preview(content: str, max_length: int = 200) -> str:
    """Generate content preview with specified max length."""
    if not content:
        return ""
    if len(content) <= max_length:
        return content
    return content[:max_length].rsplit(' ', 1)[0] + "..."

def _calculate_read_time(content: str) -> int:
    """Calculate estimated read time in minutes based on content length."""
    if not content:
        return 0
    words = len(content.split())
    # Average reading speed is 200-250 words per minute
    return max(1, round(words / 225))

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
    current_user.last_active = datetime.now(timezone.utc)
    
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
            interaction_summary=embedding_update.interaction_summary.model_dump(),
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
        current_user.last_active = datetime.now(timezone.utc)
        
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

@router.get("/bookmarks", response_model=BookmarksResponse)
async def get_user_bookmarks(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's bookmarked articles."""
    try:
        # Build query for user's bookmarks
        query = db.query(Bookmark).filter(Bookmark.user_id == current_user.id)
        
        # Join with articles for filtering
        query = query.join(Article, Bookmark.article_id == Article.id)
        
        # Apply category filter if provided
        if category:
            query = query.filter(Article.category == category)
        
        # Order by bookmark creation date (most recent first)
        query = query.order_by(desc(Bookmark.created_at))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        bookmarks = query.offset(offset).limit(limit).all()
        
        # Convert to response format
        bookmark_items = []
        for bookmark in bookmarks:
            article_summary = ArticleSummary(
                id=bookmark.article.id,
                title=bookmark.article.title,
                summary=bookmark.article.summary,
                content_preview=_get_content_preview(bookmark.article.content or bookmark.article.description or ""),
                url=bookmark.article.url,
                image_url=bookmark.article.url_to_image,
                source=_build_article_source(bookmark.article),
                author=bookmark.article.author,
                published_at=bookmark.article.published_at,
                category=bookmark.article.category,
                language=bookmark.article.language,
                read_time_minutes=_calculate_read_time(bookmark.article.content or ""),
                engagement=_build_article_engagement(bookmark.article, current_user, db),
                relevance_score=None
            )
            
            bookmark_items.append(BookmarkItem(
                bookmark_id=bookmark.id,
                article=article_summary,
                bookmarked_at=bookmark.created_at
            ))
        
        # Check if there are more results
        has_more = total > offset + limit
        
        return BookmarksResponse(
            bookmarks=bookmark_items,
            total=total,
            page=page,
            has_more=has_more
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bookmarks"
        )
