#!/usr/bin/env python3
"""
Pipeline Monitor

This script monitors the health and status of the continuous pipeline scheduler.
It provides metrics, logs, and status information for operational monitoring.

Usage:
    python pipeline/monitor_pipeline.py [--status] [--logs] [--metrics]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import SessionLocal
from core.models import Article


class PipelineMonitor:
    """Monitors the health and status of the continuous pipeline."""
    
    def __init__(self):
        self.log_dir = Path("pipeline/logs")
        self.scheduler_log = self.log_dir / "continuous_scheduler.log"
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get comprehensive pipeline status information."""
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'pipeline_running': False,
            'last_run': None,
            'last_success': None,
            'error_count': 0,
            'success_count': 0,
            'database_stats': {},
            'log_entries': []
        }
        
        # Check if scheduler log exists and get recent entries
        if self.scheduler_log.exists():
            try:
                with open(self.scheduler_log, 'r') as f:
                    lines = f.readlines()
                    status['log_entries'] = lines[-50:]  # Last 50 lines
                    
                    # Parse log entries for status information
                    for line in lines[-100:]:  # Check last 100 lines
                        if '🚀 Starting pipeline job' in line:
                            status['pipeline_running'] = True
                            status['last_run'] = self._extract_timestamp(line)
                        elif '✅ Pipeline completed successfully' in line:
                            status['last_success'] = self._extract_timestamp(line)
                            status['success_count'] += 1
                        elif '❌ Pipeline failed' in line:
                            status['error_count'] += 1
                        elif 'Pipeline stats:' in line:
                            # Extract stats from log line
                            self._extract_pipeline_stats(line, status)
            except Exception as e:
                status['log_error'] = str(e)
        
        # Get database statistics
        status['database_stats'] = self._get_database_stats()
        
        return status
    
    def _extract_timestamp(self, log_line: str) -> str:
        """Extract timestamp from log line."""
        try:
            # Parse timestamp from log format: 2024-01-01 12:00:00,000
            timestamp_str = log_line.split(' - ')[0]
            return timestamp_str
        except:
            return None
    
    def _extract_pipeline_stats(self, log_line: str, status: Dict[str, Any]):
        """Extract pipeline statistics from log line."""
        try:
            if 'successful runs' in log_line and 'failed runs' in log_line:
                # Extract numbers from: "Pipeline stats: 5 successful runs, 2 failed runs"
                parts = log_line.split('Pipeline stats: ')[1].split(',')
                if len(parts) >= 2:
                    success_part = parts[0].strip()
                    error_part = parts[1].strip()
                    
                    status['success_count'] = int(success_part.split()[0])
                    status['error_count'] = int(error_part.split()[0])
        except:
            pass
    
    def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
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
            
            # Articles from last 12 hours
            since_12h = datetime.utcnow() - timedelta(hours=12)
            recent_12h = session.query(Article).filter(
                Article.fetched_at >= since_12h
            ).count()
            
            session.close()
            
            return {
                'total_articles': total_articles,
                'articles_with_embeddings': articles_with_embeddings,
                'recent_articles_24h': recent_articles,
                'recent_articles_12h': recent_12h,
                'embedding_coverage': round((articles_with_embeddings / total_articles * 100), 2) if total_articles > 0 else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_health_status(self) -> str:
        """Get overall health status."""
        status = self.get_pipeline_status()
        
        # Check if pipeline is healthy
        if not status['pipeline_running']:
            return "STOPPED"
        
        # Check if there are too many errors
        if status['error_count'] > status['success_count']:
            return "UNHEALTHY"
        
        # Check if last success was too long ago (more than 24 hours)
        if status['last_success']:
            try:
                last_success = datetime.fromisoformat(status['last_success'].replace(',', '.'))
                if datetime.utcnow() - last_success > timedelta(hours=24):
                    return "WARNING"
            except:
                pass
        
        return "HEALTHY"
    
    def print_status(self, detailed: bool = False):
        """Print pipeline status to console."""
        status = self.get_pipeline_status()
        health = self.get_health_status()
        
        print(f"🔍 Pipeline Monitor - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Health Status: {health}")
        print(f"🔄 Pipeline Running: {status['pipeline_running']}")
        print(f"✅ Successful Runs: {status['success_count']}")
        print(f"❌ Failed Runs: {status['error_count']}")
        
        if status['last_success']:
            print(f"🎯 Last Success: {status['last_success']}")
        
        if status['last_run']:
            print(f"🕐 Last Run: {status['last_run']}")
        
        print("\n📈 Database Statistics:")
        db_stats = status['database_stats']
        if 'error' not in db_stats:
            print(f"   Total Articles: {db_stats['total_articles']}")
            print(f"   Articles with Embeddings: {db_stats['articles_with_embeddings']}")
            print(f"   Embedding Coverage: {db_stats['embedding_coverage']}%")
            print(f"   Recent Articles (24h): {db_stats['recent_articles_24h']}")
            print(f"   Recent Articles (12h): {db_stats['recent_articles_12h']}")
        else:
            print(f"   Error: {db_stats['error']}")
        
        if detailed and status['log_entries']:
            print(f"\n📋 Recent Log Entries (last {len(status['log_entries'])} lines):")
            for entry in status['log_entries'][-10:]:  # Show last 10 entries
                print(f"   {entry.strip()}")
    
    def print_metrics(self):
        """Print metrics in JSON format for monitoring systems."""
        status = self.get_pipeline_status()
        status['health'] = self.get_health_status()
        print(json.dumps(status, indent=2))


def main():
    """Main entry point for the pipeline monitor."""
    parser = argparse.ArgumentParser(
        description="Pipeline Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check basic status
  python pipeline/monitor_pipeline.py --status
  
  # Check detailed status with logs
  python pipeline/monitor_pipeline.py --status --detailed
  
  # Get metrics in JSON format
  python pipeline/monitor_pipeline.py --metrics
        """
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline status"
    )
    
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed status including recent logs"
    )
    
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Output metrics in JSON format"
    )
    
    args = parser.parse_args()
    
    monitor = PipelineMonitor()
    
    if args.metrics:
        monitor.print_metrics()
    elif args.status:
        monitor.print_status(detailed=args.detailed)
    else:
        # Default: show basic status
        monitor.print_status()


if __name__ == "__main__":
    main() 