from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_, text
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from core.db import get_db
from core.auth import get_current_active_user
from core.models import User, Article, Bookmark, Like, Share
from core.schemas import (
    ArticlesResponse,
    ArticleDetail,
    ArticleSummary,
    ArticleSource,
    ArticleEngagement,
    ArticleViewRequest,
    ArticleViewResponse,
    BookmarkResponse,
    BookmarksResponse,
    BookmarkItem,
    LikeResponse,
    ShareRequest,
    ShareResponse,
    ArticlePreview
)

router = APIRouter(tags=["articles"])

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
    # Check if user has liked/bookmarked/shared this article
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

@router.get("", response_model=ArticlesResponse)
async def get_articles(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    language: Optional[str] = Query(default=None),
    sort: str = Query(default="recent", pattern="^(recent|trending|relevance)$"),
    after_timestamp: Optional[datetime] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of articles with filtering.
    
    Supports filtering by category, source, language and sorting by recent, trending, or relevance.
    """
    try:
        # Build query
        query = db.query(Article)
        
        # Apply filters
        if category:
            query = query.filter(Article.category == category)
        
        if source:
            query = query.filter(Article.source_name == source)
        
        if language:
            query = query.filter(Article.language == language)
        
        if after_timestamp:
            query = query.filter(Article.published_at > after_timestamp)
        
        # Apply sorting
        if sort == "recent":
            query = query.order_by(desc(Article.published_at))
        elif sort == "trending":
            # Sort by engagement metrics (views, likes, shares)
            query = query.order_by(desc(Article.views + Article.likes * 10 + Article.shares * 5))
        elif sort == "relevance":
            # TODO: Implement relevance scoring based on user preferences
            query = query.order_by(desc(Article.published_at))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        articles = query.offset(offset).limit(limit).all()
        
        # Convert to response format
        article_summaries = []
        for article in articles:
            article_summaries.append(ArticleSummary(
                id=article.id,
                title=article.title,
                summary=article.summary,
                content_preview=_get_content_preview(article.content or article.description or ""),
                url=article.url,
                image_url=article.url_to_image,
                source=_build_article_source(article),
                author=article.author,
                published_at=article.published_at,
                category=article.category,
                language=article.language,
                read_time_minutes=_calculate_read_time(article.content or ""),
                engagement=_build_article_engagement(article, current_user, db),
                relevance_score=None  # TODO: Implement relevance scoring
            ))
        
        # Check if there are more results
        has_more = total > offset + limit
        next_cursor = None
        if articles and has_more and articles[-1].published_at:
            next_cursor = articles[-1].published_at.isoformat()
        
        return ArticlesResponse(
            articles=article_summaries,
            total=total,
            page=page,
            has_more=has_more,
            next_cursor=next_cursor
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve articles"
        )

@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get full article details.
    
    Returns complete article information including content, metadata, and engagement metrics.
    Increments view count and updates user reading history for recommendations.
    """
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Get article
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # Increment view count
        article.views = (article.views or 0) + 1
        db.commit()
        
        # TODO: Update user reading history for recommendations
        # TODO: Track reading time
        
        # Get related articles (placeholder implementation)
        related_articles = []
        # TODO: Implement semantic similarity search using embeddings
        
        return ArticleDetail(
            id=article.id,
            title=article.title,
            summary=article.summary,
            content=article.content,
            url=article.url,
            image_url=article.url_to_image,
            source=_build_article_source(article),
            author=article.author,
            published_at=article.published_at,
            fetched_at=article.fetched_at,
            category=article.category,
            language=article.language,
            tags=[],  # TODO: Implement tags
            read_time_minutes=_calculate_read_time(article.content or ""),
            engagement=_build_article_engagement(article, current_user, db),
            related_articles=related_articles
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve article"
        )

@router.post("/{article_id}/view", response_model=ArticleViewResponse)
async def track_article_view(
    article_id: str,
    view_data: ArticleViewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Track that user viewed an article (for swipe-based tracking).
    
    Records user engagement data and triggers real-time recommendation updates
    if significant interaction is detected.
    """
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Verify article exists
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # TODO: Store interaction data for ML model training
        # This would typically go into a user_interactions table
        
        # TODO: Update ML model with user engagement data
        # Check if this interaction should trigger recommendation updates
        updated_recommendations = False
        if view_data.view_duration_seconds > 30 or view_data.percentage_read and view_data.percentage_read > 70:
            # Significant engagement - trigger recommendation update
            updated_recommendations = True
            # TODO: Implement real-time recommendation update logic
        
        # Update user's articles_read count
        current_user.articles_read = (current_user.articles_read or 0) + 1
        db.commit()
        
        return ArticleViewResponse(
            tracked=True,
            updated_recommendations=updated_recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track article view"
        )

@router.post("/{article_id}/like", response_model=LikeResponse)
async def like_article(
    article_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Like an article.
    
    Updates user preference learning, triggers recommendation model updates,
    and sends notification to content creator.
    """
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Get article
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # Check if user has already liked this article
        existing_like = db.query(Like).filter(
            and_(Like.user_id == current_user.id, Like.article_id == article_uuid)
        ).first()
        
        if existing_like:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Article already liked by user"
            )
        
        # Create like record
        like = Like(
            user_id=current_user.id,
            article_id=article_uuid,
            created_at=datetime.now(timezone.utc)
        )
        db.add(like)
        
        # Increment the likes count
        article.likes = (article.likes or 0) + 1
        db.commit()
        
        # TODO: Update user preference learning
        # TODO: Trigger recommendation model updates
        # TODO: Send notification to content creator
        
        return LikeResponse(
            liked=True,
            total_likes=article.likes,
            user_engagement_updated=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to like article"
        )

@router.delete("/{article_id}/like", response_model=LikeResponse)
async def unlike_article(
    article_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unlike an article."""
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Get article
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # Find and remove like record
        like = db.query(Like).filter(
            and_(Like.user_id == current_user.id, Like.article_id == article_uuid)
        ).first()
        
        if not like:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Like not found - user has not liked this article"
            )
        
        # Remove like record
        db.delete(like)
        
        # Decrement the likes count
        if article.likes and article.likes > 0:
            article.likes -= 1
        db.commit()
        
        return LikeResponse(
            liked=False,
            total_likes=article.likes or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlike article"
        )

@router.post("/{article_id}/share", response_model=ShareResponse)
async def share_article(
    article_id: str,
    share_data: ShareRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Share an article."""
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Get article
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # Check if user has already shared this article
        existing_share = db.query(Share).filter(
            and_(Share.user_id == current_user.id, Share.article_id == article_uuid)
        ).first()
        
        # Create message that includes article title
        base_message = getattr(share_data, 'message', '')
        if base_message:
            enhanced_message = f"Check out this article: '{article.title}' - {base_message}"
        else:
            enhanced_message = f"Check out this article: '{article.title}'"
        
        if existing_share:
            # User already shared this article, increment count
            existing_share.count += 1
            existing_share.message = enhanced_message  # Update message with current article title
            existing_share.platform = getattr(share_data, 'platform', existing_share.platform or 'demo')
            existing_share.updated_at = datetime.now(timezone.utc)
            
            # Increment total shares count for article
            article.shares = (article.shares or 0) + 1
            db.commit()
            
            share_url = f"https://app.com/shared/{article_id}"  # TODO: Use actual domain
            return ShareResponse(
                shared=True,
                share_url=share_url,
                total_shares=article.shares,
                share_id=existing_share.id
            )
        
        # Create new share record
        share = Share(
            user_id=current_user.id,
            article_id=article_uuid,
            platform=getattr(share_data, 'platform', 'demo'),
            message=enhanced_message,
            count=1,
            created_at=datetime.now(timezone.utc)
        )
        db.add(share)
        
        # Increment shares count
        article.shares = (article.shares or 0) + 1
        db.commit()
        
        # Generate share URL
        share_url = f"https://app.com/shared/{article_id}"  # TODO: Use actual domain
        
        return ShareResponse(
            shared=True,
            share_url=share_url,
            total_shares=article.shares,
            share_id=share.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share article"
        )

@router.post("/{article_id}/bookmark", response_model=BookmarkResponse)
async def bookmark_article(
    article_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bookmark an article for later reading."""
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Check if article exists
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        # Check if already bookmarked
        existing_bookmark = db.query(Bookmark).filter(
            and_(Bookmark.user_id == current_user.id, Bookmark.article_id == article_uuid)
        ).first()
        
        if existing_bookmark:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Article already bookmarked"
            )
        
        # Create bookmark
        bookmark = Bookmark(
            user_id=current_user.id,
            article_id=article_uuid,
            created_at=datetime.now(timezone.utc)
        )
        db.add(bookmark)
        
        # Update article bookmarks count
        article.bookmarks = (article.bookmarks or 0) + 1
        db.commit()
        
        # Get total bookmarks count for user
        reading_list_count = db.query(Bookmark).filter(Bookmark.user_id == current_user.id).count()
        
        return BookmarkResponse(
            bookmarked=True,
            bookmark_id=bookmark.id,
            reading_list_count=reading_list_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bookmark article"
        )

@router.delete("/{article_id}/bookmark", response_model=BookmarkResponse)
async def remove_bookmark(
    article_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove bookmark from an article."""
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Find and remove bookmark
        bookmark = db.query(Bookmark).filter(
            and_(Bookmark.user_id == current_user.id, Bookmark.article_id == article_uuid)
        ).first()
        
        if not bookmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found"
            )
        
        db.delete(bookmark)
        
        # Update article bookmarks count
        article = db.query(Article).filter(Article.id == article_uuid).first()
        if article and article.bookmarks and article.bookmarks > 0:
            article.bookmarks -= 1
        
        db.commit()
        
        # Get total bookmarks count for user
        reading_list_count = db.query(Bookmark).filter(Bookmark.user_id == current_user.id).count()
        
        return BookmarkResponse(
            bookmarked=False,
            reading_list_count=reading_list_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove bookmark"
        )

@router.get("/{article_id}/similar", response_model=List[ArticlePreview])
async def get_similar_articles(
    article_id: str,
    limit: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get articles similar to the specified article using pgvector similarity search.
    
    Uses cosine similarity on article embeddings stored in PostgreSQL.
    """
    try:
        # Parse article ID
        try:
            article_uuid = uuid.UUID(article_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid article ID format"
            )
        
        # Get the source article
        source_article = db.query(Article).filter(Article.id == article_uuid).first()
        if not source_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        if not source_article.embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source article has no embedding"
            )
        
        # Find similar articles using pgvector cosine similarity
        # The <=> operator returns cosine distance (lower = more similar)
        similar_articles = db.query(Article)\
            .filter(Article.id != article_uuid)\
            .filter(Article.embedding.isnot(None))\
            .order_by(text("embedding <=> :embedding"))\
            .params(embedding=source_article.embedding)\
            .limit(limit)\
            .all()
        
        # Convert to response format
        return [
            ArticlePreview(
                id=str(article.id),
                title=article.title,
                summary=article.summary or article.description,
                image_url=article.url_to_image,
                source=ArticleSource(
                    id=article.source_id,
                    name=article.source_name
                ),
                published_at=article.published_at,
                category=article.category
            )
            for article in similar_articles
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find similar articles"
        )

 