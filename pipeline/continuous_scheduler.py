#!/usr/bin/env python3
"""
Continuous Pipeline Scheduler

This script runs the news pipeline every 12 hours to fetch and process new articles.
It includes comprehensive logging, error handling, and monitoring capabilities.

Usage:
    python pipeline/continuous_scheduler.py [--daemon] [--interval-hours 12]
"""

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import schedule

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.run_pipeline import run_pipeline
from core.db import SessionLocal
from core.models import Article


class PipelineScheduler:
    """Manages continuous pipeline execution with monitoring and error handling."""
    
    def __init__(self, interval_hours: int = 12, log_level: str = "INFO"):
        self.interval_hours = interval_hours
        self.running = False
        self.last_run = None
        self.last_success = None
        self.error_count = 0
        self.success_count = 0
        
        # Setup logging
        self._setup_logging(log_level)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self, log_level: str):
        """Setup comprehensive logging configuration."""
        # Ensure log directory exists
        log_dir = Path("pipeline/logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "continuous_scheduler.log"),
                logging.StreamHandler()
            ],
            force=True
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Pipeline scheduler initialized with {self.interval_hours}h interval")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _get_database_stats(self) -> dict:
        """Get current database statistics."""
        try:
            session = SessionLocal()
            
            total_articles = session.query(Article).count()
            articles_with_embeddings = session.query(Article).filter(
                Article.embedding.isnot(None)
            ).count()
            
            # Recent articles (last 24 hours)
            since_24h = datetime.utcnow() - timedelta(hours=24)
            recent_articles = session.query(Article).filter(
                Article.fetched_at >= since_24h
            ).count()
            
            session.close()
            
            return {
                'total_articles': total_articles,
                'articles_with_embeddings': articles_with_embeddings,
                'recent_articles_24h': recent_articles
            }
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def _log_pipeline_stats(self):
        """Log current pipeline and database statistics."""
        stats = self._get_database_stats()
        if stats:
            self.logger.info(
                f"Database stats: {stats['total_articles']} total articles, "
                f"{stats['articles_with_embeddings']} with embeddings, "
                f"{stats['recent_articles_24h']} added in last 24h"
            )
        
        self.logger.info(
            f"Pipeline stats: {self.success_count} successful runs, "
            f"{self.error_count} failed runs"
        )
    
    def run_pipeline_job(self):
        """Execute the pipeline job with comprehensive error handling."""
        start_time = datetime.utcnow()
        self.logger.info(f"🚀 Starting pipeline job at {start_time}")
        
        try:
            # Run the pipeline
            run_pipeline(use_cache=False, force_refresh=True)
            
            # Update success metrics
            self.last_success = datetime.utcnow()
            self.success_count += 1
            duration = (self.last_success - start_time).total_seconds()
            
            self.logger.info(
                f"✅ Pipeline completed successfully in {duration:.2f}s "
                f"at {self.last_success}"
            )
            
            # Log statistics
            self._log_pipeline_stats()
            
        except Exception as e:
            # Update error metrics
            self.error_count += 1
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.error(
                f"❌ Pipeline failed after {duration:.2f}s: {str(e)}",
                exc_info=True
            )
            
            # Log statistics even on failure
            self._log_pipeline_stats()
    
    def setup_schedule(self):
        """Setup the scheduled job."""
        # Schedule the job to run every interval_hours
        schedule.every(self.interval_hours).hours.do(self.run_pipeline_job)
        
        self.logger.info(
            f"📅 Scheduled pipeline to run every {self.interval_hours} hours"
        )
    
    def run_once(self):
        """Run the pipeline once immediately."""
        self.logger.info("🔄 Running pipeline once (immediate execution)")
        self.run_pipeline_job()
    
    def run_daemon(self):
        """Run the scheduler as a daemon process."""
        self.running = True
        self.logger.info("🔄 Starting continuous scheduler daemon")
        
        # Run once immediately
        self.run_once()
        
        while self.running:
            try:
                # Check for scheduled jobs
                schedule.run_pending()
                
                # Sleep for a short interval
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in scheduler loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
        
        self.logger.info("🛑 Continuous scheduler stopped")


def main():
    """Main entry point for the continuous scheduler."""
    parser = argparse.ArgumentParser(
        description="Continuous Pipeline Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as daemon with 12-hour intervals
  python pipeline/continuous_scheduler.py --daemon
  
  # Run once immediately
  python pipeline/continuous_scheduler.py --run-once
  
  # Run as daemon with 6-hour intervals
  python pipeline/continuous_scheduler.py --daemon --interval-hours 6
  
  # Run with debug logging
  python pipeline/continuous_scheduler.py --daemon --log-level DEBUG
        """
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as a continuous daemon process"
    )
    
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run the pipeline once and exit"
    )
    
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=12,
        help="Interval between pipeline runs in hours (default: 12)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.daemon and not args.run_once:
        parser.error("Must specify either --daemon or --run-once")
    
    if args.interval_hours < 1:
        parser.error("Interval must be at least 1 hour")
    
    # Create and run scheduler
    scheduler = PipelineScheduler(
        interval_hours=args.interval_hours,
        log_level=args.log_level
    )
    
    if args.run_once:
        scheduler.run_once()
    else:
        scheduler.setup_schedule()
        scheduler.run_daemon()


if __name__ == "__main__":
    main() 