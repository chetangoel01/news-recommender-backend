# pipeline/embed.py
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional

# Configure logging - reduce overhead
logger = logging.getLogger(__name__)

class ArticleEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the article embedder with a sentence transformer model.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        
    def load_model(self):
        """Load the sentence transformer model."""
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a given text.
        
        Args:
            text: Text to embed
            
        Returns:
            numpy array of the embedding, or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
            
        try:
            self.load_model()
            # Clean and prepare text for embedding
            cleaned_text = self._prepare_text_for_embedding(text)
            embedding = self.model.encode(cleaned_text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _prepare_text_for_embedding(self, text: str) -> str:
        """
        Prepare text for embedding by cleaning and truncating if necessary.
        
        Args:
            text: Raw text to prepare
            
        Returns:
            Cleaned and prepared text
        """
        # Remove extra whitespace and newlines
        cleaned = " ".join(text.split())
        
        # Truncate if too long (most models have token limits)
        # For all-MiniLM-L6-v2, max sequence length is 256 tokens
        # Approximate: 1 token ≈ 4 characters
        max_chars = 1000  # Conservative limit
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "..."
            
        return cleaned
    
    def create_embedding_text(self, title: str, summary: str, content: str = None) -> str:
        """
        Create a combined text for embedding from article components.
        
        Args:
            title: Article title
            summary: Article summary
            content: Article content (optional, used if summary is short)
            
        Returns:
            Combined text for embedding
        """
        # Start with title and summary
        combined = f"{title}. {summary}"
        
        # If summary is too short, add some content
        if len(summary) < 100 and content:
            # Take first 200 characters of content as additional context
            content_preview = content[:200].strip()
            if content_preview:
                combined += f" {content_preview}"
        
        return combined

# Global embedder instance
_embedder = None

def get_embedder() -> ArticleEmbedder:
    """Get or create the global embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = ArticleEmbedder()
    return _embedder

def generate_article_embedding(title: str, summary: str, content: str = None) -> Optional[np.ndarray]:
    """
    Generate embedding for an article.
    
    Args:
        title: Article title
        summary: Article summary
        content: Article content (optional)
        
    Returns:
        numpy array of the embedding, or None if failed
    """
    embedder = get_embedder()
    embedding_text = embedder.create_embedding_text(title, summary, content)
    return embedder.generate_embedding(embedding_text)
