import base64
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text, case, literal_column, String, Integer
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import numpy as np
import random
import hashlib
import json
from functools import lru_cache

from core.models import User, Article, Like, Share, Bookmark, UserEmbeddingUpdate, UserArticleInteraction

class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    class LightweightArticle:
        """Lightweight Article object for optimized queries."""
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    def _encode_cursor(self, score: float, article_id: str, published_at: datetime = None) -> str:
        """Encode a composite cursor with score, article ID, and timestamp."""
        cursor_data = {
            "score": score,
            "article_id": article_id,
            "timestamp": published_at.isoformat() if published_at else datetime.now(timezone.utc).isoformat()
        }
        cursor_json = json.dumps(cursor_data, sort_keys=True)
        return base64.urlsafe_b64encode(cursor_json.encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> Optional[Dict[str, Any]]:
        """Decode a composite cursor."""
        try:
            cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(cursor_json)
        except Exception:
            return None
    
    async def get_personalized_recommendations(
        self, 
        user: User, 
        limit: int = 50, 
        diversify: bool = True,
        content_type: str = "mixed",
        cursor: Optional[str] = None,
        force_fresh: bool = False
    ) -> List[Tuple[Article, Dict[str, Any]]]:
        """
        Get personalized article recommendations for a user.
        
        Improved implementation with:
        1. Smart handling of sparse data
        2. Content-based fallbacks
        3. Adaptive weighting
        4. Proper pagination with randomization
        5. Cold start solutions
        6. Force fresh content when requested
        """
        try:
            # Generate cache key with randomization component
            cache_key = self._generate_cache_key(user.id, limit, diversify, content_type, cursor, force_fresh)
            
            # Check cache first (disabled for now to ensure fresh results)
            # cached_result = self._get_cached_recommendations(cache_key)
            # if cached_result:
            #     return cached_result
            
            # Get smart exclusion list (more aggressive if force_fresh is True)
            exclude_ids = self._get_smart_exclusion_list(user.id, force_fresh)
            
            # Debug logging
            print(f"🔍 RecommendationService: User {user.id} has {len(exclude_ids)} recent interactions to exclude")
            print(f"🔍 RecommendationService: Requesting {limit} recommendations (force_fresh: {force_fresh})")
            
            # Check if this is a cold start scenario
            is_cold_start = self._is_cold_start_user(user)
            
            if is_cold_start:
                print(f"🔍 RecommendationService: Cold start user detected")
                recommendations = self._get_cold_start_recommendations(user, limit, exclude_ids, cursor)
            else:
                # Get scored recommendations with improved algorithm
                recommendations = self._get_improved_recommendations(
                    user, exclude_ids, limit, diversify, content_type, cursor
                )
            
            print(f"🔍 RecommendationService: Found {len(recommendations)} recommendations")
            
            if not recommendations:
                print(f"🔍 RecommendationService: No recommendations found, falling back to diverse trending")
                return self._get_diverse_trending_fallback(limit, cursor, exclude_ids)
            
            # Cache the result (disabled for now)
            # self._cache_recommendations(cache_key, recommendations)
            
            return recommendations
            
        except Exception as e:
            print(f"🔍 RecommendationService: Error in get_personalized_recommendations: {e}")
            # Fallback to diverse trending articles on error
            return self._get_diverse_trending_fallback(limit, cursor, exclude_ids)
    
    def _is_cold_start_user(self, user: User) -> bool:
        """Check if user is in cold start scenario."""
        interaction_count = self._get_user_interaction_count(user.id)
        has_preferences = bool(user.preferences and user.preferences.get("categories"))
        has_embedding = bool(user.embedding)
        
        # Cold start if very few interactions and no rich profile data
        return interaction_count < 5 and not (has_preferences or has_embedding)
    
    def _get_user_interaction_count(self, user_id: str) -> int:
        """Get total interaction count for user."""
        try:
            like_count = self.db.query(func.count(Like.id)).filter(Like.user_id == user_id).scalar() or 0
            share_count = self.db.query(func.count(Share.id)).filter(Share.user_id == user_id).scalar() or 0
            bookmark_count = self.db.query(func.count(Bookmark.id)).filter(Bookmark.user_id == user_id).scalar() or 0
            
            return like_count + share_count + bookmark_count
        except Exception:
            return 0
    
    def _get_cold_start_recommendations(
        self, 
        user: User, 
        limit: int, 
        exclude_ids: List[str],
        cursor: Optional[str] = None
    ) -> List[Tuple[Article, Dict[str, Any]]]:
        """Handle new users with no interaction history."""
        
        # Strategy 1: Use explicit preferences if available
        if user.preferences and user.preferences.get("categories"):
            categories = user.preferences["categories"]
            articles = self._get_category_based_recommendations(categories, limit, exclude_ids, cursor)
            if articles:
                return self._format_recommendations(articles, "Based on your interests")
        
        # Strategy 2: Get diverse trending articles with randomization
        return self._get_diverse_trending_fallback(limit, cursor, exclude_ids)
    
    def _get_category_based_recommendations(
        self, 
        categories: List[str], 
        limit: int, 
        exclude_ids: List[str],
        cursor: Optional[str] = None
    ) -> List[Article]:
        """Get recommendations based on preferred categories."""
        query = self.db.query(Article).filter(
            Article.category.in_(categories),
            Article.published_at >= datetime.now(timezone.utc) - timedelta(days=90)  # Extended from 14 to 90 days
        )
        
        if exclude_ids:
            query = query.filter(~Article.id.in_(exclude_ids))
        
        # Apply cursor pagination
        if cursor:
            query = self._apply_simple_cursor_pagination(query, cursor)
        
        # Add randomization to prevent same results
        query = query.order_by(
            desc(Article.views + func.coalesce(Article.likes, 0) * 10),
            func.random(),  # Add randomization
            Article.id
        )
        
        return query.limit(limit).all()
    
    def _get_improved_recommendations(
        self,
        user: User,
        exclude_ids: List[str],
        limit: int,
        diversify: bool,
        content_type: str,
        cursor: Optional[str] = None
    ) -> List[Tuple[Article, Dict[str, Any]]]:
        """Get recommendations with improved scoring algorithm."""
        
        # Get candidate articles with wider time window for sparse data
        candidates = self._get_candidate_articles_improved(exclude_ids, content_type, limit * 3, cursor)
        
        if not candidates:
            return []
        
        # Calculate hybrid scores for all candidates
        scored_articles = []
        for article in candidates:
            score, score_breakdown = self._calculate_hybrid_score(user, article)
            scored_articles.append((article, score, score_breakdown))
        
        # Sort by score with randomization for ties
        scored_articles.sort(key=lambda x: (x[1], random.random()), reverse=True)
        
        # Apply diversity filtering if requested
        if diversify:
            scored_articles = self._apply_improved_diversity_filter(scored_articles, limit)
        else:
            scored_articles = scored_articles[:limit]
        
        # Format recommendations
        recommendations = []
        for i, (article, score, metadata) in enumerate(scored_articles):
            reason = self._generate_recommendation_reason(metadata, article)
            confidence = min(0.95, score)
            
            recommendation_metadata = {
                "reason": reason,
                "confidence": confidence,
                "position_score": 1.0 - (i * 0.01),
                "scores": metadata
            }
            
            recommendations.append((article, recommendation_metadata))
        
        return recommendations
    
    def _get_candidate_articles_improved(
        self, 
        exclude_article_ids: List[str], 
        content_type: str = "mixed",
        limit: int = 150,
        cursor: Optional[str] = None
    ) -> List[Article]:
        """Get candidate articles with improved strategy for sparse data."""
        query = self.db.query(Article)
        
        # Exclude articles - convert string IDs to UUID objects
        if exclude_article_ids:
            try:
                import uuid
                exclude_uuids = [uuid.UUID(article_id) for article_id in exclude_article_ids]
                query = query.filter(~Article.id.in_(exclude_uuids))
                print(f"🔍 RecommendationService: Excluding {len(exclude_uuids)} articles from candidate query")
                print(f"🔍 RecommendationService: Exclusion IDs: {exclude_article_ids[:3]}...")
            except Exception as e:
                print(f"🔍 Error converting exclusion IDs to UUIDs: {e}")
                # Fallback: exclude as strings (may not work with all DB setups)
                query = query.filter(~Article.id.in_(exclude_article_ids))
        
        # Filter by content type
        if content_type == "videos":
            # TODO: Implement video filtering when video content is added
            return []
        
        # Wider time window for sparse data environments
        days_back = 90 if self._is_sparse_data_environment() else 30
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        query = query.filter(Article.published_at >= cutoff_date)
        
        # Apply cursor pagination if provided
        if cursor:
            query = self._apply_simple_cursor_pagination(query, cursor)
        
        # Order with randomization to prevent same results
        query = query.order_by(
            desc(Article.published_at),
            desc(Article.views + func.coalesce(Article.likes, 0) * 10),
            func.random(),  # Add randomization
            Article.id
        )
        
        candidates = query.limit(limit).all()
        candidate_ids = [str(article.id) for article in candidates]
        
        print(f"🔍 RecommendationService: Got {len(candidates)} candidate articles")
        print(f"🔍 RecommendationService: Candidate IDs: {candidate_ids[:5]}...")
        
        # Check for excluded articles in candidates
        if exclude_article_ids:
            excluded_in_candidates = set(candidate_ids) & set(exclude_article_ids)
            if excluded_in_candidates:
                print(f"❌ WARNING: Found {len(excluded_in_candidates)} excluded articles in candidates: {list(excluded_in_candidates)[:3]}")
            else:
                print("✅ SUCCESS: No excluded articles found in candidates")
        
        return candidates
    
    def _apply_simple_cursor_pagination(self, query, cursor: str):
        """Apply simple cursor pagination to avoid showing same articles."""
        cursor_data = self._decode_cursor(cursor)
        if cursor_data and cursor_data.get("article_id"):
            cursor_article_id = cursor_data["article_id"]
            # Simple exclusion: don't show articles we've seen before
            return query.filter(Article.id > cursor_article_id)
        return query
    
    def _calculate_hybrid_score(self, user: User, article: Article) -> Tuple[float, Dict[str, Any]]:
        """Calculate score with multiple fallback strategies and adaptive weighting."""
        
        scores = {
            "content_score": 0.0,
            "collab_score": 0.0,
            "popularity_score": 0.0,
            "freshness_score": 0.0,
            "preference_score": 0.0,
            "diversity_score": 0.0
        }
        
        # Content similarity (primary signal when available)
        if user.embedding and hasattr(article, 'embedding') and article.embedding:
            scores["content_score"] = self._calculate_embedding_similarity(
                user.embedding, article.embedding
            )
        else:
            # Fallback to metadata-based similarity
            scores["content_score"] = self._calculate_content_similarity_fallback(user, article)
        
        # Collaborative filtering (with fallbacks)
        collab_score = self._calculate_collaborative_score(user, article)
        if collab_score == 0.0:
            # Fallback: Use category popularity among similar users
            scores["collab_score"] = self._calculate_category_popularity_fallback(article.category)
        else:
            scores["collab_score"] = collab_score
        
        # Always calculate these (they don't depend on sparse interaction data)
        scores["popularity_score"] = self._calculate_popularity_score(article)
        scores["freshness_score"] = self._calculate_freshness_score(article)
        scores["preference_score"] = self._calculate_preference_score(user, article)
        scores["diversity_score"] = self._calculate_diversity_score(article)
        
        # Adaptive weighting based on data availability
        weights = self._get_adaptive_weights(user, scores)
        
        total_score = sum(scores[key] * weights[key] for key in scores.keys())
        
        # Add small random component to prevent identical rankings
        total_score += random.uniform(0, 0.05)
        
        return total_score, scores
    
    def _calculate_content_similarity_fallback(self, user: User, article: Article) -> float:
        """Calculate content similarity using available metadata when embeddings are missing."""
        score = 0.0
        
        # Category matching (most reliable signal)
        if user.preferences and article.category:
            user_categories = user.preferences.get("categories", [])
            if article.category.lower() in [cat.lower() for cat in user_categories]:
                score += 0.6
            elif any(keyword.lower() in article.title.lower() for keyword in user_categories):
                score += 0.3
        
        # Keyword matching in title/summary
        if user.preferences and 'keywords' in user.preferences:
            keywords = user.preferences['keywords']
            title_text = (article.title + ' ' + (article.summary or '')).lower()
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in title_text)
            score += min(0.3, keyword_matches * 0.1)
        
        # Source preference (if we track this)
        if hasattr(user, 'preferred_sources') and article.source_name:
            if article.source_name in user.preferred_sources:
                score += 0.2
        
        return min(1.0, score)
    
    def _calculate_category_popularity_fallback(self, category: str) -> float:
        """Calculate category popularity as collaborative filtering fallback."""
        if not category:
            return 0.2
        
        try:
            # Get average engagement for this category
            avg_engagement = self.db.query(
                func.avg(Article.views + func.coalesce(Article.likes, 0) * 10)
            ).filter(
                Article.category == category,
                Article.published_at >= datetime.now(timezone.utc) - timedelta(days=30)
            ).scalar()
            
            if avg_engagement:
                # Normalize to 0-1 range
                return min(1.0, np.log10(avg_engagement + 1) / 5.0)
            
        except Exception:
            pass
        
        return 0.3  # Default moderate score
    
    def _calculate_diversity_score(self, article: Article) -> float:
        """Calculate diversity score to promote variety."""
        score = 0.0
        
        # Bonus for articles from different sources
        if article.source_name:
            score += 0.3
        
        # Bonus for articles with categories
        if article.category:
            score += 0.2
        
        # Bonus for articles with images
        if article.url_to_image:
            score += 0.1
        
        return min(1.0, score)
    
    def _get_adaptive_weights(self, user: User, scores: Dict[str, float]) -> Dict[str, float]:
        """Adjust weights based on data availability and user maturity."""
        
        # Default weights
        weights = {
            "content_score": 0.25,
            "collab_score": 0.15,
            "popularity_score": 0.25,
            "freshness_score": 0.15,
            "preference_score": 0.15,
            "diversity_score": 0.05
        }
        
        # Adjust based on user interaction history
        interaction_count = self._get_user_interaction_count(user.id)
        
        if interaction_count < 5:  # New user
            weights.update({
                "content_score": 0.1,      # Less reliable
                "collab_score": 0.05,      # Less reliable
                "popularity_score": 0.4,   # More reliable
                "freshness_score": 0.2,
                "preference_score": 0.15,
                "diversity_score": 0.1
            })
        elif interaction_count < 20:  # Moderate user
            weights.update({
                "content_score": 0.2,
                "collab_score": 0.1,
                "popularity_score": 0.3,
                "freshness_score": 0.15,
                "preference_score": 0.15,
                "diversity_score": 0.1
            })
        
        # Boost content score if embeddings are available
        if user.embedding and scores["content_score"] > 0.1:
            weights["content_score"] += 0.1
            weights["popularity_score"] -= 0.1
        
        # Boost preference score if user has explicit preferences
        if user.preferences and user.preferences.get("categories"):
            weights["preference_score"] += 0.05
            weights["popularity_score"] -= 0.05
        
        return weights
    
    def _apply_improved_diversity_filter(
        self, 
        scored_articles: List[Tuple[Article, float, Dict]], 
        limit: int
    ) -> List[Tuple[Article, float, Dict]]:
        """Apply improved diversity filtering to ensure variety."""
        if len(scored_articles) <= limit:
            return scored_articles
        
        selected = []
        category_counts = {}
        source_counts = {}
        
        # Sort by score first
        scored_articles.sort(key=lambda x: x[1], reverse=True)
        
        for article, score, metadata in scored_articles:
            category = article.category or "general"
            source = article.source_name or "unknown"
            
            # Diversity constraints
            max_per_category = max(2, limit // 4)  # At most 25% from one category
            max_per_source = max(1, limit // 8)    # At most 12.5% from one source
            
            category_count = category_counts.get(category, 0)
            source_count = source_counts.get(source, 0)
            
            # Apply diversity constraints
            if category_count < max_per_category and source_count < max_per_source:
                selected.append((article, score, metadata))
                category_counts[category] = category_count + 1
                source_counts[source] = source_count + 1
                
                if len(selected) >= limit:
                    break
        
        # If we haven't filled the limit, add remaining articles (relaxing constraints)
        if len(selected) < limit:
            remaining = [item for item in scored_articles if item not in selected]
            selected.extend(remaining[:limit - len(selected)])
        
        return selected
    
    def _get_smart_exclusion_list(self, user_id: str, force_fresh: bool = False) -> List[str]:
        """Get comprehensive exclusion list to prevent showing same articles on refresh."""
        try:
            # Adjust exclusion windows based on force_fresh parameter
            if force_fresh:
                # More aggressive exclusion for fresh content requests
                interaction_cutoff = datetime.now(timezone.utc) - timedelta(days=30)    # Last 30 days
                all_time_cutoff = datetime.now(timezone.utc) - timedelta(days=180)      # Last 180 days
            else:
                # Standard exclusion windows
                interaction_cutoff = datetime.now(timezone.utc) - timedelta(days=14)    # Last 14 days
                all_time_cutoff = datetime.now(timezone.utc) - timedelta(days=90)       # Last 90 days
            
            exclude_ids = []
            
            # 1. Recent likes/shares/bookmarks
            recent_likes = self.db.query(Like.article_id).filter(
                Like.user_id == user_id,
                Like.created_at >= interaction_cutoff
            ).all()
            exclude_ids.extend([str(like.article_id) for like in recent_likes])
            
            recent_shares = self.db.query(Share.article_id).filter(
                Share.user_id == user_id,
                Share.created_at >= interaction_cutoff
            ).all()
            exclude_ids.extend([str(share.article_id) for share in recent_shares])
            
            recent_bookmarks = self.db.query(Bookmark.article_id).filter(
                Bookmark.user_id == user_id,
                Bookmark.created_at >= interaction_cutoff
            ).all()
            exclude_ids.extend([str(bookmark.article_id) for bookmark in recent_bookmarks])
            
            # 2. NEW: Recent article views and interactions
            recent_views = self.db.query(UserArticleInteraction.article_id).filter(
                and_(
                    UserArticleInteraction.user_id == user_id,
                    UserArticleInteraction.interaction_type.in_(['view', 'skip']),
                    UserArticleInteraction.created_at >= interaction_cutoff
                )
            ).all()
            exclude_ids.extend([str(view.article_id) for view in recent_views])
            
            # 3. Articles with explicit positive feedback (longer window)
            positive_interactions = self.db.query(Like.article_id).filter(
                and_(
                    Like.user_id == user_id,
                    Like.created_at >= all_time_cutoff
                )
            ).all()
            exclude_ids.extend([str(like.article_id) for like in positive_interactions])
            
            # 4. NEW: All-time viewed articles (prevent showing articles user has seen)
            all_time_views = self.db.query(UserArticleInteraction.article_id).filter(
                and_(
                    UserArticleInteraction.user_id == user_id,
                    UserArticleInteraction.interaction_type == 'view',
                    UserArticleInteraction.created_at >= all_time_cutoff
                )
            ).all()
            exclude_ids.extend([str(view.article_id) for view in all_time_views])
            
            # Remove duplicates and return
            unique_exclude_ids = list(set(exclude_ids))
            
            print(f"🔍 RecommendationService: Excluding {len(unique_exclude_ids)} articles for user {user_id} (force_fresh: {force_fresh})")
            print(f"🔍 RecommendationService: Breakdown - Recent interactions: {len(recent_likes) + len(recent_shares) + len(recent_bookmarks)}, Recent views: {len(recent_views)}, All-time views: {len(all_time_views)}")
            
            return unique_exclude_ids
            
        except Exception as e:
            print(f"🔍 Error getting exclusion list: {e}")
            return []
    
    def _is_sparse_data_environment(self) -> bool:
        """Check if we're in a sparse data environment."""
        try:
            # Quick check: if less than 100 total interactions in last week, consider sparse
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            interaction_count = self.db.query(func.count(Like.id)).filter(
                Like.created_at >= week_ago
            ).scalar()
            
            return (interaction_count or 0) < 100
        except Exception:
            return True  # Assume sparse if we can't check
    
    def _get_diverse_trending_fallback(self, limit: int, cursor: Optional[str] = None, exclude_ids: List[str] = None) -> List[Tuple[Article, Dict[str, Any]]]:
        """Get diverse trending articles as fallback with proper pagination."""
        try:
            # Get articles from different categories - extended time window for sparse data
            categories_query = self.db.query(func.distinct(Article.category)).filter(
                Article.category.isnot(None),
                Article.published_at >= datetime.now(timezone.utc) - timedelta(days=90)  # Extended from 14 to 90 days
            ).all()
            
            categories = [cat[0] for cat in categories_query if cat[0]]
            
            diverse_articles = []
            
            # First try to get articles from each category
            if categories:
                articles_per_category = max(1, limit // len(categories))
                
                for category in categories:
                    query = self.db.query(Article).filter(
                        Article.category == category,
                        Article.published_at >= datetime.now(timezone.utc) - timedelta(days=90)  # Extended from 14 to 90 days
                    )
                    
                    # Apply exclusion filter
                    if exclude_ids:
                        try:
                            import uuid
                            exclude_uuids = [uuid.UUID(article_id) for article_id in exclude_ids]
                            query = query.filter(~Article.id.in_(exclude_uuids))
                            print(f"🔍 RecommendationService: Excluding {len(exclude_uuids)} articles from diverse trending fallback")
                        except Exception as e:
                            print(f"🔍 Error converting exclusion IDs to UUIDs in diverse trending: {e}")
                            query = query.filter(~Article.id.in_(exclude_ids))
                    
                    # Apply cursor pagination
                    if cursor:
                        query = self._apply_simple_cursor_pagination(query, cursor)
                    
                    cat_articles = query.order_by(
                        desc(Article.views + func.coalesce(Article.likes, 0) * 10),
                        func.random(),  # Add randomization
                        Article.id
                    ).limit(articles_per_category).all()
                    
                    diverse_articles.extend(cat_articles)
            
            # If we don't have enough articles from categories, add uncategorized articles
            if len(diverse_articles) < limit:
                remaining_needed = limit - len(diverse_articles)
                print(f"🔍 RecommendationService: Only found {len(diverse_articles)} categorized articles, adding {remaining_needed} uncategorized articles")
                
                query = self.db.query(Article).filter(
                    Article.category.is_(None),  # Uncategorized articles
                    Article.published_at >= datetime.now(timezone.utc) - timedelta(days=90)
                )
                
                # Apply exclusion filter
                if exclude_ids:
                    try:
                        import uuid
                        exclude_uuids = [uuid.UUID(article_id) for article_id in exclude_ids]
                        query = query.filter(~Article.id.in_(exclude_uuids))
                    except Exception as e:
                        print(f"🔍 Error converting exclusion IDs to UUIDs in uncategorized query: {e}")
                        query = query.filter(~Article.id.in_(exclude_ids))
                
                # Apply cursor pagination
                if cursor:
                    query = self._apply_simple_cursor_pagination(query, cursor)
                
                uncategorized_articles = query.order_by(
                    desc(Article.views + func.coalesce(Article.likes, 0) * 10),
                    func.random(),  # Add randomization
                    Article.id
                ).limit(remaining_needed).all()
                
                diverse_articles.extend(uncategorized_articles)
            
            # If still no articles, fall back to general trending
            if not diverse_articles:
                print(f"🔍 RecommendationService: No diverse articles found, falling back to general trending")
                return self._get_general_trending_fallback(limit, cursor, exclude_ids)
            
            # Shuffle and limit
            random.shuffle(diverse_articles)
            diverse_articles = diverse_articles[:limit]
            
            # Format as recommendations
            recommendations = []
            for i, article in enumerate(diverse_articles):
                category_label = article.category if article.category else "general"
                metadata = {
                    "reason": f"Trending in {category_label}" if article.category else "Trending article",
                    "confidence": 0.6,
                    "position_score": 1.0 - (i * 0.01),
                    "scores": {"popularity_score": 0.8, "diversity_score": 0.9}
                }
                recommendations.append((article, metadata))
            
            return recommendations
            
        except Exception as e:
            print(f"🔍 Error in diverse trending fallback: {e}")
            return self._get_general_trending_fallback(limit, cursor, exclude_ids)
    
    def _get_general_trending_fallback(self, limit: int, cursor: Optional[str] = None, exclude_ids: List[str] = None) -> List[Tuple[Article, Dict[str, Any]]]:
        """Get general trending articles as final fallback."""
        query = self.db.query(Article).filter(
            Article.published_at >= datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        # Apply exclusion filter
        if exclude_ids:
            try:
                import uuid
                exclude_uuids = [uuid.UUID(article_id) for article_id in exclude_ids]
                query = query.filter(~Article.id.in_(exclude_uuids))
                print(f"🔍 RecommendationService: Excluding {len(exclude_uuids)} articles from general trending fallback")
            except Exception as e:
                print(f"🔍 Error converting exclusion IDs to UUIDs in general trending: {e}")
                query = query.filter(~Article.id.in_(exclude_ids))
        
        # Apply cursor pagination
        if cursor:
            query = self._apply_simple_cursor_pagination(query, cursor)
        
        articles = query.order_by(
            desc(Article.views + func.coalesce(Article.likes, 0) * 10),
            func.random(),  # Add randomization
            Article.id
        ).limit(limit).all()
        
        print(f"🔍 RecommendationService: General trending fallback found {len(articles)} articles")
        
        recommendations = []
        for i, article in enumerate(articles):
            metadata = {
                "reason": "Trending article",
                "confidence": 0.5,
                "position_score": 1.0 - (i * 0.01),
                "scores": {"popularity_score": 0.8}
            }
            recommendations.append((article, metadata))
        
        return recommendations
    
    def _format_recommendations(self, articles: List[Article], reason: str) -> List[Tuple[Article, Dict[str, Any]]]:
        """Format articles as recommendations with metadata."""
        recommendations = []
        for i, article in enumerate(articles):
            metadata = {
                "reason": reason,
                "confidence": 0.7,
                "position_score": 1.0 - (i * 0.01),
                "scores": {"preference_score": 0.8}
            }
            recommendations.append((article, metadata))
        return recommendations
    
    # Keep existing methods for backward compatibility
    def _get_user_interactions_efficient(self, user_id: str) -> List[str]:
        """Get user interactions efficiently - now returns smart exclusion list."""
        return self._get_smart_exclusion_list(user_id)
    
    def _calculate_embedding_similarity(self, user_embedding: List[float], article_embedding: List[float]) -> float:
        """Calculate cosine similarity between user and article embeddings."""
        if not user_embedding or not article_embedding:
            return 0.0
        
        try:
            user_vec = np.array(user_embedding)
            article_vec = np.array(article_embedding)
            
            # Normalize vectors
            user_norm = np.linalg.norm(user_vec)
            article_norm = np.linalg.norm(article_vec)
            
            if user_norm == 0 or article_norm == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(user_vec, article_vec) / (user_norm * article_norm)
            return max(0.0, min(1.0, similarity))  # Clamp between 0 and 1
            
        except Exception:
            return 0.0
    
    def _calculate_collaborative_score(self, user: User, article: Article) -> float:
        """Calculate collaborative filtering score based on similar users."""
        try:
            # Find users with similar embeddings (simplified approach)
            if not user.embedding:
                return 0.0
            
            # Get users who liked this article
            users_who_liked = self.db.query(Like.user_id).filter(Like.article_id == article.id).limit(50).all()
            user_ids = [str(uid.user_id) for uid in users_who_liked]
            
            if not user_ids:
                return 0.0
            
            # Get embeddings of users who liked this article
            similar_users = self.db.query(User).filter(
                and_(User.id.in_(user_ids), User.embedding.isnot(None))
            ).limit(20).all()
            
            if not similar_users:
                return 0.0
            
            # Calculate average similarity to users who liked this article
            similarities = []
            user_vec = np.array(user.embedding)
            
            for similar_user in similar_users:
                if similar_user.embedding:
                    try:
                        similar_vec = np.array(similar_user.embedding)
                        user_norm = np.linalg.norm(user_vec)
                        similar_norm = np.linalg.norm(similar_vec)
                        
                        if user_norm > 0 and similar_norm > 0:
                            similarity = np.dot(user_vec, similar_vec) / (user_norm * similar_norm)
                            similarities.append(max(0.0, similarity))
                    except Exception:
                        continue
            
            if similarities:
                return sum(similarities) / len(similarities)
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_popularity_score(self, article: Article) -> float:
        """Calculate popularity score based on engagement metrics."""
        views = article.views or 0
        likes = article.likes or 0
        shares = article.shares or 0
        
        # Weighted engagement score
        engagement_score = views + likes * 10 + shares * 5
        
        # Normalize to 0-1 range (log scale to handle viral articles)
        if engagement_score > 0:
            return min(1.0, np.log10(engagement_score + 1) / 4.0)  # log10(10000) ≈ 4
        return 0.1  # Small base score instead of 0
    
    def _calculate_freshness_score(self, article: Article) -> float:
        """Calculate freshness score based on publication time."""
        if not article.published_at:
            return 0.3  # Default moderate score
        
        now = datetime.now(timezone.utc)
        
        # Ensure published_at is timezone-aware
        if article.published_at.tzinfo is None:
            # Assume UTC if no timezone info
            published_at = article.published_at.replace(tzinfo=timezone.utc)
        else:
            published_at = article.published_at
        
        hours_old = (now - published_at).total_seconds() / 3600
        
        # Exponential decay: newer articles get higher scores (14 day half-life for sparse data)
        freshness = np.exp(-hours_old / (14 * 24))  # 14 days half-life
        return max(0.1, min(1.0, freshness))  # Minimum 0.1 instead of 0
    
    def _calculate_preference_score(self, user: User, article: Article) -> float:
        """Calculate score based on user preferences."""
        if not user.preferences or not article.category:
            return 0.5  # Neutral score instead of 0
        
        user_categories = user.preferences.get("categories", [])
        if not user_categories:
            return 0.5
        
        # Check if article category matches user preferences
        if article.category.lower() in [cat.lower() for cat in user_categories]:
            return 0.9  # High score for preferred categories
        
        return 0.4  # Moderate score for non-preferred categories
    
    def _generate_recommendation_reason(self, metadata: Dict[str, Any], article: Article) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        if metadata.get("content_score", 0) > 0.7:
            reasons.append("Based on your reading history")
        
        if metadata.get("collab_score", 0) > 0.6:
            reasons.append("Similar users enjoyed this")
        
        if metadata.get("popularity_score", 0) > 0.8:
            reasons.append("Trending article")
        
        if metadata.get("preference_score", 0) > 0.7:
            reasons.append(f"Matches your {article.category} interests")
        
        if metadata.get("diversity_score", 0) > 0.7:
            reasons.append("Discover something new")
        
        if not reasons:
            if article.category:
                reasons.append(f"Popular in {article.category}")
            else:
                reasons.append("Recommended for you")
        
        return reasons[0] if reasons else "Recommended for you"
    
    def _generate_cache_key(self, user_id: str, limit: int, diversify: bool, content_type: str, cursor: Optional[str], force_fresh: bool) -> str:
        """Generate a cache key for recommendations with randomization component."""
        # Add time-based randomization to ensure fresh results
        time_bucket = int(datetime.now().timestamp() // (self.cache_ttl // 2))  # Change every 2.5 minutes
        random_seed = int(datetime.now().timestamp() // 60)  # Change every minute
        
        key_data = {
            "user_id": str(user_id),
            "limit": limit,
            "diversify": diversify,
            "content_type": content_type,
            "cursor": cursor,
            "force_fresh": force_fresh,
            "time_bucket": time_bucket,
            "random_seed": random_seed
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_recommendations(self, cache_key: str) -> Optional[List[Tuple[Article, Dict[str, Any]]]]:
        """Get cached recommendations (disabled to ensure fresh results)."""
        # Disabled to prevent showing same articles repeatedly
        return None
    
    def _cache_recommendations(self, cache_key: str, recommendations: List[Tuple[Article, Dict[str, Any]]]):
        """Cache recommendations (disabled to ensure fresh results)."""
        # Disabled to prevent showing same articles repeatedly
        pass
    
    # Legacy methods kept for backward compatibility
    def _get_scored_recommendations_db(
        self, 
        user: User, 
        exclude_ids: List[str], 
        limit: int, 
        diversify: bool, 
        content_type: str,
        cursor: Optional[str] = None
    ) -> List[Tuple[Article, float, Dict[str, Any]]]:
        """Legacy method - redirects to improved implementation."""
        recommendations = self._get_improved_recommendations(
            user, exclude_ids, limit, diversify, content_type, cursor
        )
        
        # Convert format for backward compatibility
        scored_articles = []
        for article, metadata in recommendations:
            total_score = metadata.get("scores", {}).get("total_score", 0.5)
            scores = metadata.get("scores", {})
            scored_articles.append((article, total_score, scores))
        
        return scored_articles
    
    def _build_scored_query(self, user: User, exclude_ids: List[str], content_type: str):
        """Legacy method - kept for backward compatibility."""
        # This method is replaced by the improved candidate selection
        # But kept to avoid breaking existing code
        query = self.db.query(Article)
        
        if exclude_ids:
            query = query.filter(~Article.id.in_(exclude_ids))
        
        if content_type == "videos":
            return query.filter(Article.id.is_(None))  # Return empty result
        
        # Filter for recent articles
        sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
        query = query.filter(Article.published_at >= sixty_days_ago)
        
        return query.order_by(desc(Article.published_at), Article.id)
    
    def _apply_robust_cursor_pagination(self, query, cursor: str):
        """Legacy method - kept for backward compatibility."""
        return self._apply_simple_cursor_pagination(query, cursor)
    
    def _apply_cursor_pagination(self, query, cursor: str):
        """Legacy method - kept for backward compatibility."""
        return self._apply_simple_cursor_pagination(query, cursor)
    
    def _apply_diversity_query(self, query, limit: int):
        """Legacy method - kept for backward compatibility."""
        return query
    
    def _get_user_interactions(self, user_id: str) -> List[str]:
        """Legacy method - redirects to smart exclusion list."""
        return self._get_smart_exclusion_list(user_id)
    
    def _get_candidate_articles(
        self, 
        exclude_article_ids: List[str], 
        content_type: str = "mixed",
        limit: int = 150,
        cursor: Optional[str] = None
    ) -> List[Article]:
        """Legacy method - redirects to improved implementation."""
        return self._get_candidate_articles_improved(
            exclude_article_ids, content_type, limit, cursor
        )
    
    def _apply_diversity_filter(
        self, 
        scored_articles: List[Tuple[Article, float, Dict]], 
        limit: int
    ) -> List[Tuple[Article, float, Dict]]:
        """Legacy method - redirects to improved implementation."""
        return self._apply_improved_diversity_filter(scored_articles, limit)
    
    def _get_trending_fallback(self, limit: int, cursor: Optional[str] = None) -> List[Tuple[Article, Dict[str, Any]]]:
        """Legacy method - redirects to diverse trending fallback."""
        return self._get_diverse_trending_fallback(limit, cursor)
    
    def _get_fallback_recommendations(self, limit: int) -> List[Tuple[Article, Dict[str, Any]]]:
        """Legacy method - redirects to diverse trending fallback."""
        return self._get_diverse_trending_fallback(limit)