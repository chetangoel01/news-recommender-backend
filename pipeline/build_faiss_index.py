# pipeline/build_faiss_index.py
import logging
import numpy as np
import faiss
import pickle
from pathlib import Path
from core.db import SessionLocal
from core.models import Article

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_faiss_index():
    """Build FAISS index from all articles with embeddings in the database."""
    session = SessionLocal()
    
    try:
        # Query only articles that have embeddings
        articles = session.query(Article).filter(Article.embedding.isnot(None)).all()
        logger.info(f"Found {len(articles)} articles with embeddings")
        
        if not articles:
            logger.warning("No articles with embeddings found in database")
            return
        
        # Extract embeddings and article IDs
        embeddings = []
        article_ids = []
        
        for article in articles:
            if article.embedding:
                # Convert list back to numpy array
                embedding_array = np.array(article.embedding, dtype=np.float32)
                embeddings.append(embedding_array)
                article_ids.append(str(article.id))
        
        if not embeddings:
            logger.warning("No valid embeddings found")
            return
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings_array)
        
        # Add to index
        index.add(embeddings_array)
        
        # Save index and article IDs
        embeddings_dir = Path("pipeline/embeddings")
        embeddings_dir.mkdir(exist_ok=True)
        
        index_path = embeddings_dir / "article_index.faiss"
        faiss.write_index(index, str(index_path))
        
        ids_path = embeddings_dir / "article_index.faiss.ids"
        with open(ids_path, 'wb') as f:
            pickle.dump(article_ids, f)
        
        logger.info(f"Successfully built and saved FAISS index with {len(embeddings)} articles")
        logger.info(f"Index saved to: {index_path}")
        logger.info(f"Article IDs saved to: {ids_path}")
        
    except Exception as e:
        logger.error(f"Failed to build index: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    build_faiss_index() 