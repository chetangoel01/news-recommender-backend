#!/usr/bin/env python3
"""
Script to populate articles with realistic engagement data for testing trending API.
This will add views, likes, and shares to existing articles to make them appear in trending feeds.
"""

import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from core.db import engine
from core.models import Article

def populate_trending_data():
    """Populate articles with realistic engagement data."""
    
    session = Session(engine)
    
    try:
        # Get all articles
        articles = session.query(Article).all()
        print(f"Found {len(articles)} articles to update")
        
        if not articles:
            print("No articles found in database!")
            return
        
        # Categories that typically get more engagement
        high_engagement_categories = ['technology', 'business', 'entertainment', 'sports']
        
        for i, article in enumerate(articles):
            # Generate realistic engagement data based on category and recency
            base_views = random.randint(100, 5000)
            base_likes = random.randint(10, 500)
            base_shares = random.randint(5, 200)
            
            # Boost engagement for certain categories
            if article.category and article.category.lower() in high_engagement_categories:
                base_views *= random.uniform(1.5, 3.0)
                base_likes *= random.uniform(1.2, 2.5)
                base_shares *= random.uniform(1.1, 2.0)
            
            # Boost engagement for recent articles (trending effect)
            if article.published_at:
                hours_old = (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600
                if hours_old < 24:  # Articles published in last 24 hours
                    recency_boost = max(1.0, 3.0 - (hours_old / 8))  # Higher boost for newer articles
                    base_views *= recency_boost
                    base_likes *= recency_boost
                    base_shares *= recency_boost
            
            # Add some randomness
            views = int(base_views * random.uniform(0.8, 1.2))
            likes = int(base_likes * random.uniform(0.7, 1.3))
            shares = int(base_shares * random.uniform(0.6, 1.4))
            
            # Ensure minimum values
            views = max(50, views)
            likes = max(5, likes)
            shares = max(2, shares)
            
            # Update article
            article.views = views
            article.likes = likes
            article.shares = shares
            
            print(f"Updated article {i+1}/{len(articles)}: '{article.title[:50]}...'")
            print(f"  Views: {views}, Likes: {likes}, Shares: {shares}")
            
            # Commit every 10 articles to avoid long transactions
            if (i + 1) % 10 == 0:
                session.commit()
                print(f"Committed {i+1} articles...")
        
        # Final commit
        session.commit()
        print(f"\n✅ Successfully updated {len(articles)} articles with trending data!")
        
        # Show some examples
        print("\n📊 Sample updated articles:")
        sample_articles = session.query(Article).order_by(Article.views.desc()).limit(5).all()
        for article in sample_articles:
            trending_score = (article.views + article.likes * 10 + article.shares * 5)
            print(f"  '{article.title[:40]}...' - Views: {article.views}, Likes: {article.likes}, Shares: {article.shares}, Score: {trending_score:.0f}")
        
    except Exception as e:
        print(f"❌ Error updating articles: {e}")
        session.rollback()
    finally:
        session.close()

def create_viral_articles():
    """Create a few articles with very high engagement to test trending."""
    
    session = Session(engine)
    
    try:
        # Create some viral articles with high engagement
        viral_articles = [
            {
                'title': 'BREAKING: Major AI Breakthrough Changes Everything',
                'summary': 'Revolutionary AI technology that will transform industries worldwide.',
                'content': 'This is a test viral article with high engagement...',
                'url': 'https://example.com/viral-ai-article',
                'url_to_image': 'https://example.com/image.jpg',
                'source_name': 'TechNews',
                'category': 'technology',
                'language': 'en',
                'views': 25000,
                'likes': 1500,
                'shares': 800,
                'published_at': datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                'title': 'Incredible Sports Moment Goes Viral',
                'summary': 'Unbelievable play that has everyone talking.',
                'content': 'This is a test viral sports article...',
                'url': 'https://example.com/viral-sports-article',
                'url_to_image': 'https://example.com/sports-image.jpg',
                'source_name': 'SportsCentral',
                'category': 'sports',
                'language': 'en',
                'views': 18000,
                'likes': 1200,
                'shares': 600,
                'published_at': datetime.now(timezone.utc) - timedelta(hours=4)
            },
            {
                'title': 'Celebrity News That Broke the Internet',
                'summary': 'Major celebrity announcement that shocked everyone.',
                'content': 'This is a test viral entertainment article...',
                'url': 'https://example.com/viral-celebrity-article',
                'url_to_image': 'https://example.com/celebrity-image.jpg',
                'source_name': 'EntertainmentNow',
                'category': 'entertainment',
                'language': 'en',
                'views': 30000,
                'likes': 2000,
                'shares': 1000,
                'published_at': datetime.now(timezone.utc) - timedelta(hours=1)
            }
        ]
        
        for article_data in viral_articles:
            article = Article(**article_data)
            session.add(article)
            print(f"Created viral article: '{article.title}'")
        
        session.commit()
        print("✅ Created viral articles successfully!")
        
    except Exception as e:
        print(f"❌ Error creating viral articles: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Populating trending data...")
    
    # First, update existing articles
    populate_trending_data()
    
    # Then, create some viral articles
    print("\n🔥 Creating viral articles...")
    create_viral_articles()
    
    print("\n✅ Trending data population complete!")
    print("You can now test the trending API and it should return articles with engagement data.") 