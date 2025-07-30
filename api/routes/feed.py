from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import base64
import json

from core.db import get_db
from core.auth import get_current_active_user
from core.models import User, Article, Like, Share, Bookmark
from core.schemas import (
    PersonalizedFeedResponse,
    TrendingFeedResponse,
    FeedArticle,
    FeedMetadata,
    TrendingTopic,
    EngagementPrediction
)
from services.recommendation import RecommendationService

router = APIRouter(tags=["feed"])

def _encode_cursor(score: float, article_id: str, published_at: Optional[datetime] = None) -> str:
    """Encode a composite cursor with score, article ID, and timestamp."""
    cursor_data = {
        "score": score,
        "article_id": article_id,
        "timestamp": published_at.isoformat() if published_at else datetime.now(timezone.utc).isoformat()
    }
    cursor_json = json.dumps(cursor_data, sort_keys=True)
    return base64.urlsafe_b64encode(cursor_json.encode()).decode()

def _decode_cursor(cursor: str) -> Optional[dict]:
    """Decode a composite cursor."""
    try:
        cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(cursor_json)
    except Exception:
        return None

def _build_feed_articles_batch(articles: List, user: User, db: Session, 
                              recommendation_reasons: List[str] = None, 
                              confidence_scores: List[float] = None,
                              position_scores: List[float] = None) -> List[FeedArticle]:
    """Helper function to build FeedArticle objects in batch to reduce database queries."""
    from sqlalchemy import and_
    
    if not articles:
        return []
    
    # OPTIMIZATION: Batch query all user interactions for these articles
    article_ids = [article.id for article in articles]
    
    # Get all user interactions in one query
    user_likes = set(
        db.query(Like.article_id).filter(
            and_(Like.user_id == user.id, Like.article_id.in_(article_ids))
        ).all()
    )
    user_shares = set(
        db.query(Share.article_id).filter(
            and_(Share.user_id == user.id, Share.article_id.in_(article_ids))
        ).all()
    )
    user_bookmarks = set(
        db.query(Bookmark.article_id).filter(
            and_(Bookmark.user_id == user.id, Bookmark.article_id.in_(article_ids))
        ).all()
    )
    
    # Convert to sets for O(1) lookup
    user_liked_ids = {str(like.article_id) for like in user_likes}
    user_shared_ids = {str(share.article_id) for share in user_shares}
    user_bookmarked_ids = {str(bookmark.article_id) for bookmark in user_bookmarks}
    
    feed_articles = []
    for i, article in enumerate(articles):
        # Check user engagement with this article (O(1) lookup)
        user_liked = str(article.id) in user_liked_ids
        user_shared = str(article.id) in user_shared_ids
        user_bookmarked = str(article.id) in user_bookmarked_ids
        
        # Calculate engagement prediction (simple heuristic)
        total_engagement = (article.views or 0) + (article.likes or 0) * 10 + (article.shares or 0) * 5
        engagement_rate = total_engagement / max(article.views or 1, 1)
        
        engagement_prediction = EngagementPrediction(
            likely_to_like=min(0.95, engagement_rate * 0.1),
            likely_to_share=min(0.8, engagement_rate * 0.05),
            likely_to_read_full=min(0.9, engagement_rate * 0.08)
        )
        
        feed_article = FeedArticle(
            id=article.id,
            title=article.title,
            summary=article.summary,
            image_url=article.url_to_image,
            source={
                "id": article.source_id,
                "name": article.source_name,
                "logo": None,  # TODO: Add source logo mapping
                "credibility_score": None  # TODO: Implement credibility scoring
            },
            recommendation_reason=recommendation_reasons[i] if recommendation_reasons else None,
            confidence_score=confidence_scores[i] if confidence_scores else None,
            position_score=position_scores[i] if position_scores else (1.0 - (i * 0.01)),
            content_type="article",
            estimated_read_time=f"{max(1, len((getattr(article, 'content', '') or '').split()) // 225)} min",
            engagement_prediction=engagement_prediction,
            published_at=article.published_at,
            category=article.category
        )
        feed_articles.append(feed_article)
    
    return feed_articles

@router.get("/personalized", response_model=PersonalizedFeedResponse)
async def get_personalized_feed(
    limit: int = Query(default=50, ge=10, le=100),
    refresh: Optional[str] = Query(default="false", description="Force refresh recommendations"),
    content_type: str = Query(default="mixed", pattern="^(articles|videos|mixed)$"),
    diversify: bool = Query(default=True),
    cursor: Optional[str] = Query(default=None, description="Composite cursor for pagination (score + article ID)"),
    force_fresh: Optional[bool] = Query(default=False, description="Force fresh content (exclude more articles)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized article feed optimized for swipe navigation.
    
    Uses collaborative filtering + content-based recommendations with diversity constraints.
    Supports robust cursor-based pagination with composite cursors for no duplicates.
    """
    try:
        # FIX: Handle refresh parameter that might be sent as [object Object] or other invalid values
        try:
            refresh_bool = refresh.lower() == "true" if isinstance(refresh, str) else False
        except (AttributeError, ValueError):
            refresh_bool = False
        
        # Initialize recommendation service
        recommendation_service = RecommendationService(db)
        
        print(f"🔍 API: Getting recommendations for user {current_user.id}")
        print(f"🔍 API: Parameters - limit: {limit}, diversify: {diversify}, content_type: {content_type}, force_fresh: {force_fresh or refresh_bool}")
        
        # Get personalized recommendations with pagination
        recommended_articles = await recommendation_service.get_personalized_recommendations(
            user=current_user,
            limit=limit,
            diversify=diversify,
            content_type=content_type,
            cursor=cursor,
            force_fresh=force_fresh or refresh_bool
        )
        
        print(f"🔍 API: Got {len(recommended_articles)} recommended articles")
        if recommended_articles:
            article_ids = [str(article.id) for article, _ in recommended_articles]
            print(f"🔍 API: Article IDs: {article_ids[:5]}...")
        
        # OPTIMIZATION: Extract articles and metadata for batch processing
        articles = [article for article, _ in recommended_articles]
        recommendation_reasons = [metadata.get("reason") for _, metadata in recommended_articles]
        confidence_scores = [metadata.get("confidence") for _, metadata in recommended_articles]
        position_scores = [metadata.get("position_score", 1.0 - (i * 0.01)) for i, (_, metadata) in enumerate(recommended_articles)]
        
        # Build feed articles in batch (much more efficient)
        feed_articles = _build_feed_articles_batch(
            articles=articles,
            user=current_user,
            db=db,
            recommendation_reasons=recommendation_reasons,
            confidence_scores=confidence_scores,
            position_scores=position_scores
        )
        
        # Calculate feed metadata
        personalization_strength = min(0.9, current_user.engagement_score + 0.1) if current_user.engagement_score else 0.5
        diversity_score = 0.7 if diversify else 0.3
        
        feed_metadata = FeedMetadata(
            generated_at=datetime.now(timezone.utc),
            algorithm_version="v1.0",
            personalization_strength=personalization_strength,
            diversity_score=diversity_score,
            cache_ttl_minutes=30
        )
        
        # Generate next cursor for pagination using composite cursor
        next_cursor = None
        if feed_articles and len(feed_articles) == limit:
            last_article = feed_articles[-1]
            last_tuple = recommended_articles[-1] if recommended_articles else None
            if last_tuple:
                _, last_metadata = last_tuple
                print(f"🔍 Feed: Last metadata: {last_metadata}")
                score = 0.0
                
                # Extract score from the nested metadata structure
                if 'scores' in last_metadata and 'total_score' in last_metadata['scores']:
                    score = last_metadata['scores']['total_score']
                    print(f"🔍 Feed: Using score from metadata.scores.total_score: {score}")
                elif 'total_score' in last_metadata:
                    score = last_metadata['total_score']
                    print(f"🔍 Feed: Using score from metadata.total_score: {score}")
                else:
                    print(f"🔍 Feed: No scores found in metadata, using default: {score}")
                    print(f"🔍 Feed: Available metadata keys: {list(last_metadata.keys())}")
                    if 'scores' in last_metadata:
                        print(f"🔍 Feed: Scores keys: {list(last_metadata['scores'].keys())}")
                
                # Get the article's published_at timestamp for better pagination
                published_at = None
                if hasattr(last_article, 'published_at') and last_article.published_at:
                    published_at = last_article.published_at
                
                next_cursor = _encode_cursor(score, str(last_article.id), published_at)
                print(f"🔍 Feed: Generated cursor with score: {score} for article: {last_article.id}")
        
        return PersonalizedFeedResponse(
            articles=feed_articles,
            feed_metadata=feed_metadata,
            preload_next_batch=True,
            next_cursor=next_cursor,
            has_more=next_cursor is not None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate personalized feed: {str(e)}"
        )

@router.get("/trending", response_model=TrendingFeedResponse)
async def get_trending_feed(
    timeframe: str = Query(default="24h", pattern="^(1h|6h|24h|7d)$"),
    category: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=10, le=100),
    cursor: Optional[str] = Query(default=None, description="Composite cursor for pagination (trending score + article ID)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get trending articles across the platform.
    
    Calculates trending scores based on engagement velocity and virality.
    Supports robust cursor-based pagination with composite cursors for no duplicates.
    """
    try:
        # Calculate time window
        now = datetime.now(timezone.utc)
        if timeframe == "1h":
            start_time = now - timedelta(hours=1)
        elif timeframe == "6h":
            start_time = now - timedelta(hours=6)
        elif timeframe == "24h":
            start_time = now - timedelta(days=1)
        else:  # 7d
            start_time = now - timedelta(days=7)
        
        # Build trending query with stable ordering
        query = db.query(Article)
        
        # Filter by time window
        query = query.filter(Article.published_at >= start_time)
        
        # Filter by category if specified
        if category:
            query = query.filter(Article.category == category)
        
        # Calculate trending score (views + likes*10 + shares*5) / hours_since_published
        trending_score_expr = func.coalesce(
            (Article.views + func.coalesce(Article.likes, 0) * 10 + func.coalesce(Article.shares, 0) * 5) / 
            func.greatest(1, func.extract('epoch', now - Article.published_at) / 3600), 0
        )
        
        # Apply cursor filter if provided
        if cursor:
            cursor_data = _decode_cursor(cursor)
            if cursor_data:
                cursor_score = cursor_data.get("score", 0.0)
                cursor_article_id = cursor_data.get("article_id")
                
                if cursor_article_id:
                    # Apply robust cursor filter: (score, id) < (cursor_score, cursor_article_id)
                    query = query.filter(
                        or_(
                            trending_score_expr < cursor_score,
                            and_(
                                trending_score_expr == cursor_score,
                                Article.id < cursor_article_id
                            )
                        )
                    )
        
        # Order by trending score with stable ordering
        trending_articles = query.order_by(desc(trending_score_expr), Article.id).limit(limit).all()
        
        # Build feed articles with trending metadata
        feed_articles = []
        for i, article in enumerate(trending_articles):
            # Calculate trend score
            hours_since_published = max(1, (now - article.published_at).total_seconds() / 3600)
            trend_score = (article.views or 0) + (article.likes or 0) * 10 + (article.shares or 0) * 5
            trend_score = trend_score / hours_since_published
            
            # Determine velocity
            if trend_score > 1000:
                velocity = "fast_rising"
            elif trend_score > 500:
                velocity = "rising"
            else:
                velocity = "steady"
            
            feed_article = _build_feed_articles_batch(
                articles=[article],
                user=current_user,
                db=db,
                recommendation_reasons=[f"Trending in {article.category or 'general'}"],
                confidence_scores=[min(0.95, trend_score / 1000)],
                position_scores=[1.0 - (i * 0.02)]
            )[0]
            
            # Add trending-specific fields
            feed_article.trend_score = trend_score
            feed_article.trending_rank = i + 1
            feed_article.velocity = velocity
            feed_article.engagement_metrics = {
                "views_last_hour": article.views or 0,
                "shares_per_minute": (article.shares or 0) / max(1, hours_since_published * 60)
            }
            
            feed_articles.append(feed_article)
        
        # Calculate trending topics (simplified)
        trending_topics = []
        category_counts = {}
        for article in trending_articles:
            if article.category:
                category_counts[article.category] = category_counts.get(article.category, 0) + 1
        
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            trending_topics.append(TrendingTopic(
                topic=category,
                mention_count=count,
                sentiment="positive",  # TODO: Implement sentiment analysis
                trending_articles_count=count
            ))
        
        # Generate next cursor for pagination using composite cursor
        next_cursor = None
        if feed_articles and len(feed_articles) == limit:
            last_article = feed_articles[-1]
            next_cursor = _encode_cursor(last_article.trend_score, str(last_article.id))
        
        return TrendingFeedResponse(
            articles=feed_articles,
            trending_topics=trending_topics,
            next_cursor=next_cursor,
            has_more=next_cursor is not None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate trending feed: {str(e)}"
        ) 