from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from core.db import get_db
from core.auth import get_current_active_user
from core.models import User, Article
from core.schemas import ArticleSummary, SearchResponse, SearchMetadata

router = APIRouter(tags=["search"])


@router.get("/articles", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., description="Search query"),
    semantic: bool = Query(default=True, description="Use semantic search"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    date_range: str = Query(default="all", pattern="^(24h|7d|30d|all)$", description="Date range filter"),
    sort: str = Query(default="relevance", pattern="^(relevance|recent|popular)$", description="Sort order"),
    limit: int = Query(default=20, le=100, description="Number of results"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search articles using keyword and semantic search.
    
    Supports filtering by category, date range, and sorting by relevance, recent, or popularity.
    """
    try:
        if not q.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query cannot be empty"
            )
        
        # Build base query
        query = db.query(Article)
        
        # Apply date range filter
        if date_range != "all":
            now = datetime.utcnow()
            if date_range == "24h":
                start_date = now - timedelta(hours=24)
            elif date_range == "7d":
                start_date = now - timedelta(days=7)
            elif date_range == "30d":
                start_date = now - timedelta(days=30)
            
            query = query.filter(Article.published_at >= start_date)
        
        # Apply category filter
        if category:
            query = query.filter(Article.category == category)
        
        # Apply search filters
        search_terms = q.lower().split()
        search_conditions = []
        
        for term in search_terms:
            # Search in title, summary, and content
            term_condition = or_(
                Article.title.ilike(f"%{term}%"),
                Article.summary.ilike(f"%{term}%"),
                Article.content.ilike(f"%{term}%"),
                Article.description.ilike(f"%{term}%")
            )
            search_conditions.append(term_condition)
        
        # Combine search conditions with AND logic
        if search_conditions:
            query = query.filter(and_(*search_conditions))
        
        # Apply sorting
        if sort == "recent":
            query = query.order_by(desc(Article.published_at))
        elif sort == "popular":
            # Sort by engagement metrics
            query = query.order_by(desc(Article.views + Article.likes * 10 + Article.shares * 5))
        elif sort == "relevance":
            # For now, sort by published date (most recent first)
            # TODO: Implement proper relevance scoring using embeddings
            query = query.order_by(desc(Article.published_at))
        
        # Get total count
        total = query.count()
        
        # Apply limit
        articles = query.limit(limit).all()
        
        # Convert to response format using the same functions as the articles endpoint
        from api.routes.articles import _get_content_preview, _build_article_source, _build_article_engagement, _calculate_read_time
        
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
                relevance_score=None  # Will be calculated based on search
            ))
        
        # Build search metadata
        search_metadata = SearchMetadata(
            query=q,
            total_results=total,
            search_time_ms=0,  # TODO: Add timing
            semantic_expansion=[],  # TODO: Implement semantic expansion
            suggested_filters=[]  # TODO: Implement filter suggestions
        )
        
        return SearchResponse(
            articles=article_summaries,
            search_metadata=search_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform search"
        ) 