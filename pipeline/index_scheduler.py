# pipeline/index_scheduler.py
"""
FAISS Index Scheduler - Automated maintenance for article embeddings index

NOTE: NOT CURRENTLY USED IN API ENDPOINTS

This script is kept for potential future integration when article scale
exceeds pgvector performance limits. Currently, the API uses direct
pgvector similarity search which automatically stays in sync.

This script handles automated updates to the FAISS index based on different triggers:
1. Time-based updates (e.g., every hour)
2. Article count thresholds (e.g., every 100 new articles)
3. Manual triggers via API

For future integration, this would run as a background service.
"""

import argparse
import logging
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline/logs/index_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ensure_log_directory():
    """Ensure log directory exists."""
    log_dir = Path("pipeline/logs")
    log_dir.mkdir(exist_ok=True)

def run_incremental_update():
    """Run incremental index update."""
    try:
        logger.info("Starting incremental index update")
        from pipeline.incremental_index_update import update_faiss_index_incremental
        update_faiss_index_incremental()
        logger.info("Incremental update completed successfully")
    except Exception as e:
        logger.error(f"Incremental update failed: {e}")

def run_full_rebuild():
    """Run full index rebuild."""
    try:
        logger.info("Starting full index rebuild")
        from pipeline.build_faiss_index import build_faiss_index
        build_faiss_index()
        logger.info("Full rebuild completed successfully")
    except Exception as e:
        logger.error(f"Full rebuild failed: {e}")

def run_cleanup():
    """Run index cleanup for deleted articles."""
    try:
        logger.info("Starting index cleanup")
        from pipeline.incremental_index_update import cleanup_deleted_articles
        cleanup_deleted_articles()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

def get_database_stats():
    """Get current database statistics."""
    try:
        from core.db import SessionLocal
        from core.models import Article
        
        session = SessionLocal()
        
        total_articles = session.query(Article).count()
        articles_with_embeddings = session.query(Article).filter(
            Article.embedding.isnot(None)
        ).count()
        
        # Recent articles (last 24 hours)
        since_24h = datetime.utcnow() - timedelta(hours=24)
        recent_articles = session.query(Article).filter(
            Article.fetched_at >= since_24h,
            Article.embedding.isnot(None)
        ).count()
        
        session.close()
        
        logger.info(f"Database stats: {total_articles} total articles, "
                   f"{articles_with_embeddings} with embeddings, "
                   f"{recent_articles} added in last 24h")
        
        return {
            'total_articles': total_articles,
            'articles_with_embeddings': articles_with_embeddings,
            'recent_articles': recent_articles
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return None

def smart_update_strategy():
    """
    Intelligent update strategy based on database changes.
    
    Rules:
    - If more than 100 new articles: full rebuild
    - If 1-100 new articles: incremental update
    - If no new articles but it's been >7 days: full rebuild (maintenance)
    - Always cleanup deleted articles weekly
    """
    stats = get_database_stats()
    if not stats:
        logger.warning("Could not get database stats, skipping update")
        return
    
    recent_count = stats['recent_articles']
    
    # Check when we last did a full rebuild
    index_path = Path("pipeline/embeddings/article_index.faiss")
    
    if index_path.exists():
        last_rebuild = datetime.fromtimestamp(index_path.stat().st_mtime)
        days_since_rebuild = (datetime.now() - last_rebuild).days
    else:
        days_since_rebuild = 999  # Force rebuild if no index exists
    
    logger.info(f"Recent articles: {recent_count}, Days since last rebuild: {days_since_rebuild}")
    
    if recent_count > 100 or days_since_rebuild > 7:
        logger.info("Running full rebuild due to high activity or maintenance schedule")
        run_full_rebuild()
    elif recent_count > 0:
        logger.info("Running incremental update for recent articles")
        run_incremental_update()
    else:
        logger.info("No new articles, skipping update")
    
    # Weekly cleanup
    if days_since_rebuild > 7:
        run_cleanup()

def run_scheduler(mode):
    """Run the scheduler in different modes."""
    ensure_log_directory()
    logger.info(f"Starting FAISS index scheduler in {mode} mode")
    
    if mode == "hourly":
        # Check for new articles every hour, smart strategy
        schedule.every().hour.do(smart_update_strategy)
        logger.info("Scheduled smart updates every hour")
        
    elif mode == "daily":
        # Full rebuild daily at 2 AM
        schedule.every().day.at("02:00").do(run_full_rebuild)
        # Cleanup weekly on Sunday
        schedule.every().sunday.at("03:00").do(run_cleanup)
        logger.info("Scheduled daily rebuilds at 2 AM and weekly cleanup on Sunday")
        
    elif mode == "on-demand":
        # Run once and exit
        logger.info("Running on-demand update")
        smart_update_strategy()
        return
        
    else:
        logger.error(f"Unknown mode: {mode}")
        return
    
    # Keep the scheduler running
    logger.info("Scheduler is running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")

def main():
    parser = argparse.ArgumentParser(description="FAISS Index Scheduler")
    parser.add_argument(
        "--mode",
        choices=["hourly", "daily", "on-demand"],
        default="on-demand",
        help="Scheduler mode: hourly (smart updates), daily (full rebuilds), or on-demand (run once)"
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force a full rebuild regardless of mode"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true", 
        help="Only run cleanup of deleted articles"
    )
    
    args = parser.parse_args()
    
    if args.force_rebuild:
        run_full_rebuild()
    elif args.cleanup_only:
        run_cleanup()
    else:
        run_scheduler(args.mode)

if __name__ == "__main__":
    main() 