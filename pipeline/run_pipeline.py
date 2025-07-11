# pipeline/run_pipeline.py
import logging
import numpy as np
from pipeline.fetch import fetch_articles
from pipeline.summarize import summarize
from pipeline.embed import generate_article_embedding
from core.models import Article
from core.db import SessionLocal
from datetime import datetime
from newspaper import Article as NewsArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    # Reduce logging overhead
    force=True
)


def get_full_content(url, api_content=None, api_description=None):
    """
    Extract full article content using newspaper3k, fallback to API content if needed.
    If newspaper content is over 20k characters, use News API fields instead.
    
    Returns:
        tuple: (content, summary, use_api_fields)
        - content: The article content to use
        - summary: The summary to use (None if should be generated)
        - use_api_fields: Boolean indicating if we're using API fields
    """
    try:
        logging.info(f"Fetching full content from: {url}")
        news_article = NewsArticle(url)
        news_article.download()
        news_article.parse()
        
        if news_article.text:
            content_length = len(news_article.text)
            logging.info(f"Successfully extracted {content_length} characters")
            
            # If content is over 20k characters, use News API fields instead
            if content_length > 20000:
                logging.info(f"Content too long ({content_length} chars), using News API fields")
                if api_content and api_description:
                    return api_content, api_description, True
                elif api_content:
                    return api_content, None, True
                else:
                    # Truncate newspaper content if no API fallback
                    truncated_content = news_article.text[:20000] + "..."
                    return truncated_content, None, False
            
            return news_article.text, None, False
        else:
            logging.warning(f"No text content found for: {url}")
            return None, None, False
    except Exception as e:
        logging.error(f"Failed to fetch full content for {url}: {e}")
        # Fallback to API content if available
        if api_content:
            logging.info(f"Using API content as fallback for: {url}")
            return f"[API_CONTENT_FALLBACK] {api_content}", api_description, True
        return None, None, False


def run_pipeline(use_cache=True, force_refresh=False):
    """
    Run the news pipeline.
    
    Args:
        use_cache: Whether to use cached articles if available
        force_refresh: Whether to force refresh and ignore cache
    """
    logging.info("Starting news pipeline...")
    session = SessionLocal()
    try:
        articles = fetch_articles(use_cache=use_cache, force_refresh=force_refresh)
        logging.info(f"Fetched {len(articles)} articles from NewsAPI.")
    except Exception as e:
        logging.error(f"Failed to fetch articles: {e}")
        return
    
    processed_count = 0
    skipped_count = 0
    
    for item in articles:
        if not item.get("url"):
            logging.warning(f"Skipping article with missing URL: {item.get('title', 'No Title')}")
            continue
        
        # Check if article already exists in database
        existing_article = session.query(Article).filter(Article.url == item.get("url")).first()
        if existing_article:
            skipped_count += 1
            continue
            
        # Get full article content using newspaper3k, with API content as fallback
        api_content = item.get("content", "")
        api_description = item.get("description", "")
        full_content, api_summary, use_api_fields = get_full_content(item.get("url"), api_content, api_description)
        if not full_content:
            logging.warning(f"Skipping article - could not extract any content: {item.get('title', 'No Title')}")
            continue
        
        # Determine summary to use
        if use_api_fields and api_summary:
            # Use News API description as summary
            summary = api_summary
            logging.info(f"Using News API description as summary for: {item.get('title', 'No Title')}")
        else:
            # Generate summary from content
            try:
                summary = summarize(full_content)
            except Exception as e:
                logging.error(f"Failed to summarize article '{item.get('title', 'No Title')}': {e}")
                continue

        # Generate semantic embedding for the article
        try:
            embedding = generate_article_embedding(
                title=item.get('title', ''),
                summary=summary,
                content=full_content
            )
            if embedding is None:
                logging.warning(f"Failed to generate embedding for: {item.get('title', 'No Title')}")
        except Exception as e:
            logging.error(f"Failed to generate embedding for '{item.get('title', 'No Title')}': {e}")
            embedding = None

        article = Article(
            source_id=item["source"]["id"] if item["source"] else None,
            source_name=item["source"]["name"] if item["source"] else None,
            author=item.get("author"),
            title=item.get("title"),
            description=item.get("description"),
            content=full_content,  # Use the full content (either newspaper3k or API fallback)
            summary=summary,
            url=item.get("url"),
            url_to_image=item.get("urlToImage"),
            published_at=item.get("publishedAt"),
            fetched_at=datetime.utcnow(),
            embedding=embedding.tolist() if embedding is not None else None,  # Convert numpy array to list for storage
        )

        try:
            session.add(article)
            session.commit()
            processed_count += 1
            # Log progress every 10 articles to reduce logging overhead
            if processed_count % 10 == 0:
                logging.info(f"Processed {processed_count} articles so far...")
        except Exception as e:
            session.rollback()  # likely a duplicate
            logging.warning(f"Failed to save article '{article.title}': {e}")
    
    session.close()
    logging.info(f"Pipeline completed. Processed {processed_count} new articles, skipped {skipped_count} existing articles.")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    use_cache = True
    force_refresh = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-cache":
            use_cache = False
        elif sys.argv[1] == "--force-refresh":
            force_refresh = True
    
    run_pipeline(use_cache=use_cache, force_refresh=force_refresh)
