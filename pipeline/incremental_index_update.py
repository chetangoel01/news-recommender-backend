# pipeline/incremental_index_update.py
#
# FAISS Incremental Index Updates - NOT CURRENTLY USED IN API ENDPOINTS
# 
# This module is kept for potential future integration when article scale
# exceeds pgvector performance limits. Currently, the API uses direct
# pgvector similarity search which automatically stays in sync with the database.
#
# To use FAISS index in the future, integrate this with a similarity service.

import logging
import numpy as np
import faiss
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from core.db import SessionLocal
from core.models import Article

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_existing_index():
    """Load existing FAISS index and article IDs."""
    embeddings_dir = Path("pipeline/embeddings")
    index_path = embeddings_dir / "article_index.faiss"
    ids_path = embeddings_dir / "article_index.faiss.ids"
    
    if not index_path.exists() or not ids_path.exists():
        logger.info("No existing index found, will create new one")
        return None, []
    
    try:
        index = faiss.read_index(str(index_path))
        with open(ids_path, 'rb') as f:
            article_ids = pickle.load(f)
        
        logger.info(f"Loaded existing index with {len(article_ids)} articles")
        return index, article_ids
    except Exception as e:
        logger.error(f"Failed to load existing index: {e}")
        return None, []

def get_new_articles(existing_ids, since_hours=24):
    """Get articles added/updated since last index update."""
    session = SessionLocal()
    
    try:
        # Get articles with embeddings that aren't in the existing index
        # Or articles updated in the last N hours
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        
        query = session.query(Article).filter(
            Article.embedding.isnot(None)
        )
        
        # Filter out articles already in index
        if existing_ids:
            query = query.filter(~Article.id.in_(existing_ids))
        
        new_articles = query.all()
        logger.info(f"Found {len(new_articles)} new articles with embeddings")
        
        return new_articles
    finally:
        session.close()

def update_faiss_index_incremental(rebuild_threshold=1000):
    """
    Incrementally update FAISS index with new articles.
    
    Args:
        rebuild_threshold: If more than this many articles need updating,
                          rebuild the entire index instead
    """
    session = SessionLocal()
    
    try:
        # Load existing index
        index, existing_ids = get_existing_index()
        
        # Get new articles
        new_articles = get_new_articles(existing_ids)
        
        if not new_articles:
            logger.info("No new articles to add to index")
            return
        
        # If too many new articles, rebuild entire index
        if len(new_articles) > rebuild_threshold:
            logger.info(f"Too many new articles ({len(new_articles)}), rebuilding entire index")
            from pipeline.build_faiss_index import build_faiss_index
            build_faiss_index()
            return
        
        # Extract embeddings from new articles
        new_embeddings = []
        new_ids = []
        
        for article in new_articles:
            if article.embedding:
                embedding_array = np.array(article.embedding, dtype=np.float32)
                new_embeddings.append(embedding_array)
                new_ids.append(str(article.id))
        
        if not new_embeddings:
            logger.info("No valid embeddings in new articles")
            return
        
        # Convert to numpy array
        new_embeddings_array = np.array(new_embeddings).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(new_embeddings_array)
        
        if index is None:
            # Create new index if none exists
            dimension = new_embeddings_array.shape[1]
            index = faiss.IndexFlatIP(dimension)
            all_ids = new_ids
        else:
            # Add to existing index
            all_ids = existing_ids + new_ids
        
        # Add new embeddings to index
        index.add(new_embeddings_array)
        
        # Save updated index
        embeddings_dir = Path("pipeline/embeddings")
        embeddings_dir.mkdir(exist_ok=True)
        
        index_path = embeddings_dir / "article_index.faiss"
        faiss.write_index(index, str(index_path))
        
        ids_path = embeddings_dir / "article_index.faiss.ids"
        with open(ids_path, 'wb') as f:
            pickle.dump(all_ids, f)
        
        logger.info(f"Successfully added {len(new_embeddings)} new articles to index")
        logger.info(f"Total index size: {len(all_ids)} articles")
        
    except Exception as e:
        logger.error(f"Failed to update index incrementally: {e}")
        logger.info("Consider running full rebuild: python -m pipeline.build_faiss_index")
    finally:
        session.close()

def cleanup_deleted_articles():
    """Remove articles from index that no longer exist in database."""
    session = SessionLocal()
    
    try:
        # Load existing index
        index, existing_ids = get_existing_index()
        
        if not existing_ids:
            logger.info("No existing index to clean up")
            return
        
        # Check which articles still exist in database
        existing_articles = session.query(Article.id).filter(
            Article.id.in_(existing_ids),
            Article.embedding.isnot(None)
        ).all()
        
        still_exist_ids = {str(article.id) for article in existing_articles}
        deleted_ids = set(existing_ids) - still_exist_ids
        
        if not deleted_ids:
            logger.info("No deleted articles found in index")
            return
        
        logger.info(f"Found {len(deleted_ids)} deleted articles in index")
        logger.info("Full rebuild required to remove deleted articles")
        
        from pipeline.build_faiss_index import build_faiss_index
        build_faiss_index()
        
    except Exception as e:
        logger.error(f"Failed to cleanup deleted articles: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_deleted_articles()
    else:
        update_faiss_index_incremental() 