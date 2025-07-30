#!/usr/bin/env python3
"""
Database optimization script for the news recommender backend.
This script creates performance indexes and tests query optimization.
"""

import asyncio
import time
from sqlalchemy.orm import Session
from core.db import engine, init_db, get_db
from core.models import User, Article
from services.recommendation import RecommendationService
from sqlalchemy import text

def create_performance_indexes():
    """Create database indexes for performance optimization."""
    print("🔧 Creating performance indexes...")
    
    try:
        with engine.connect() as conn:
            # Drop existing indexes if they exist
            conn.execute(text("DROP INDEX IF EXISTS idx_articles_published_at;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_articles_category;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_articles_engagement;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_articles_feed_query;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_likes_user_article;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_shares_user_article;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_bookmarks_user_article;"))
            conn.execute(text("DROP INDEX IF EXISTS idx_users_preferences;"))
            
            # Create optimized indexes
            print("  📊 Creating article indexes...")
            conn.execute(text("""
                CREATE INDEX idx_articles_published_at 
                ON articles(published_at DESC);
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_articles_category 
                ON articles(category);
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_articles_engagement 
                ON articles(views DESC, likes DESC, shares DESC);
            """))
            
            # Composite index for the main feed query
            conn.execute(text("""
                CREATE INDEX idx_articles_feed_query 
                ON articles(published_at DESC, category, views DESC, likes DESC, shares DESC);
            """))
            
            print("  👥 Creating user interaction indexes...")
            conn.execute(text("""
                CREATE INDEX idx_likes_user_article 
                ON likes(user_id, article_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_shares_user_article 
                ON shares(user_id, article_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_bookmarks_user_article 
                ON bookmarks(user_id, article_id);
            """))
            
            print("  ⚙️ Creating user preference indexes...")
            conn.execute(text("""
                CREATE INDEX idx_users_preferences 
                ON users USING GIN(preferences);
            """))
            
            conn.commit()
            print("✅ All indexes created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        raise

def test_query_performance():
    """Test the performance of the optimized queries."""
    print("\n🧪 Testing query performance...")
    
    db = next(get_db())
    
    try:
        # Get a test user
        user = db.query(User).first()
        if not user:
            print("❌ No users found in database!")
            return
        
        print(f"👤 Testing with user: {user.username}")
        
        # Create recommendation service
        service = RecommendationService(db)
        
        # Test 1: Basic recommendations (before optimization)
        print("\n📊 Test 1: Basic Recommendations")
        start_time = time.time()
        
        recommendations = asyncio.run(
            service.get_personalized_recommendations(user, limit=50)
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        print(f"⏱️  Response time: {response_time:.2f}ms")
        print(f"📄 Found {len(recommendations)} recommendations")
        
        if response_time < 1000:  # Less than 1 second
            print("✅ Performance is good!")
        elif response_time < 5000:  # Less than 5 seconds
            print("⚠️  Performance is acceptable but could be better")
        else:
            print("❌ Performance is too slow!")
        
        # Test 2: Pagination performance
        print("\n📄 Test 2: Pagination Performance")
        if recommendations:
            # Get cursor from first recommendation
            first_article, first_metadata = recommendations[0]
            cursor_score = first_metadata.get('scores', {}).get('total_score', 0.0)
            
            start_time = time.time()
            
            # Test pagination
            next_page = asyncio.run(
                service.get_personalized_recommendations(
                    user, limit=50, cursor=f"test_cursor_{cursor_score}_{first_article.id}"
                )
            )
            
            end_time = time.time()
            pagination_time = (end_time - start_time) * 1000
            print(f"⏱️  Pagination time: {pagination_time:.2f}ms")
            
            if pagination_time < 500:
                print("✅ Pagination performance is good!")
            else:
                print("⚠️  Pagination could be faster")
        
        # Test 3: Database query analysis
        print("\n🔍 Test 3: Database Query Analysis")
        with engine.connect() as conn:
            # Enable query logging
            conn.execute(text("SET log_statement = 'all';"))
            conn.execute(text("SET log_min_duration_statement = 100;"))  # Log queries > 100ms
            
            # Run a test query
            test_query = conn.execute(text("""
                EXPLAIN (ANALYZE, BUFFERS) 
                SELECT id, title, summary, url_to_image, source_id, source_name, 
                       published_at, category, views, likes, shares
                FROM articles 
                WHERE published_at >= NOW() - INTERVAL '30 days'
                ORDER BY (views + COALESCE(likes, 0) * 10 + COALESCE(shares, 0) * 5) DESC, id
                LIMIT 50;
            """))
            
            print("📋 Query execution plan:")
            for row in test_query:
                print(f"  {row[0]}")
        
    except Exception as e:
        print(f"❌ Error testing performance: {e}")
    finally:
        db.close()

def analyze_database_stats():
    """Analyze database statistics for optimization."""
    print("\n📈 Analyzing database statistics...")
    
    try:
        with engine.connect() as conn:
            # Get table sizes
            sizes = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE tablename IN ('articles', 'users', 'likes', 'shares', 'bookmarks')
                ORDER BY tablename, attname;
            """))
            
            print("📊 Table statistics:")
            for row in sizes:
                print(f"  {row[1]}.{row[2]}: {row[3]} distinct values, correlation: {row[4]:.3f}")
            
            # Get index usage
            index_usage = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE tablename IN ('articles', 'users', 'likes', 'shares', 'bookmarks')
                ORDER BY idx_scan DESC;
            """))
            
            print("\n🔍 Index usage statistics:")
            for row in index_usage:
                print(f"  {row[2]}: {row[3]} scans, {row[4]} tuples read, {row[5]} tuples fetched")
                
    except Exception as e:
        print(f"❌ Error analyzing statistics: {e}")

def main():
    """Main optimization function."""
    print("🚀 Starting database optimization...")
    
    # Create indexes
    create_performance_indexes()
    
    # Analyze current state
    analyze_database_stats()
    
    # Test performance
    test_query_performance()
    
    print("\n🎉 Database optimization completed!")
    print("\n📋 Summary of optimizations:")
    print("  ✅ Created composite indexes for feed queries")
    print("  ✅ Added user interaction indexes")
    print("  ✅ Optimized query to select only necessary columns")
    print("  ✅ Implemented batch processing for user interactions")
    print("  ✅ Simplified scoring calculations")
    print("  ✅ Added GIN index for user preferences")

if __name__ == "__main__":
    main() 