# pipeline/run_pipeline.py

# Suppress all warnings BEFORE any imports
import os
import warnings
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
warnings.filterwarnings("ignore")

import logging
import numpy as np
from tqdm import tqdm
from pipeline.fetch import fetch_articles
from pipeline.summarize import summarize
from pipeline.embed import generate_article_embedding
from core.models import Article
from core.db import SessionLocal
from datetime import datetime, timezone
from newspaper import Article as NewsArticle

# Configure logging to only show critical errors
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s [%(levelname)s] %(message)s',
    force=True
)

# Suppress urllib3 warnings
import urllib3
urllib3.disable_warnings()


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
        news_article = NewsArticle(url)
        news_article.download()
        news_article.parse()
        
        if news_article.text:
            content_length = len(news_article.text)
            
            # If content is over 20k characters, use News API fields instead
            if content_length > 20000:
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
            return None, None, False
    except Exception as e:
        # Silently handle errors - they'll be caught by the progress bar status
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
    session = SessionLocal()
    try:
        print("🚀 Starting news pipeline...")
        articles = fetch_articles(use_cache=use_cache, force_refresh=force_refresh)
        print(f"📰 Loaded {len(articles)} articles for processing")
    except Exception as e:
        print(f"❌ Failed to fetch articles: {e}")
        return
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # Create progress bar
    progress_bar = tqdm(
        articles, 
        desc="Processing articles",
        unit="article",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )
    
    for item in progress_bar:
        title = item.get('title', 'Untitled')[:50] + "..." if len(item.get('title', '')) > 50 else item.get('title', 'Untitled')
        
        try:
            if not item.get("url"):
                progress_bar.set_postfix_str(f"⚠️  Skipping: No URL")
                error_count += 1
                continue
            
            # Update status: Checking for duplicates
            progress_bar.set_postfix_str(f"🔍 Checking: {title}")
            
            # Check if article already exists in database
            existing_article = session.query(Article).filter(Article.url == item.get("url")).first()
            if existing_article:
                skipped_count += 1
                progress_bar.set_postfix_str(f"⏭️  Skipped: Already exists")
                continue
                
            # Update status: Fetching content
            progress_bar.set_postfix_str(f"📄 Fetching: {title}")
            
            # Get full article content using newspaper3k, with API content as fallback
            api_content = item.get("content", "")
            api_description = item.get("description", "")
            full_content, api_summary, use_api_fields = get_full_content(item.get("url"), api_content, api_description)
            
            if not full_content or len(full_content.strip()) < 100:
                progress_bar.set_postfix_str(f"⚠️  Skipping: Too short")
                error_count += 1
                continue
            
            # Update status: Processing content
            progress_bar.set_postfix_str(f"📝 Processing: {title}")
            
            # Determine summary to use
            if use_api_fields and api_summary:
                summary = api_summary
            else:
                # Generate summary from content
                try:
                    summary = summarize(full_content)
                except Exception as e:
                    progress_bar.set_postfix_str(f"⚠️  Summary failed: {title}")
                    error_count += 1
                    continue

            # Update status: Generating embedding
            progress_bar.set_postfix_str(f"🧠 Embedding: {title}")
            
            # Generate semantic embedding for the article
            try:
                embedding = generate_article_embedding(
                    title=item.get('title', ''),
                    summary=summary,
                    content=full_content
                )
                if embedding is None:
                    progress_bar.set_postfix_str(f"⚠️  Embedding failed: {title}")
                    error_count += 1
                    continue
            except Exception as e:
                progress_bar.set_postfix_str(f"⚠️  Embedding error: {title}")
                error_count += 1
                continue

            # Update status: Saving to database
            progress_bar.set_postfix_str(f"💾 Saving: {title}")
            
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
                fetched_at=datetime.now(timezone.utc),
                embedding=embedding.tolist() if embedding is not None else None,  # Convert numpy array to list for storage
            )

            try:
                session.add(article)
                session.commit()
                processed_count += 1
                progress_bar.set_postfix_str(f"✅ Saved: {title}")
            except Exception as e:
                session.rollback()  # likely a duplicate
                progress_bar.set_postfix_str(f"⚠️  Save failed: {title}")
                error_count += 1
                
        except Exception as e:
            # Catch any unexpected errors in the processing loop
            progress_bar.set_postfix_str(f"❌ Error: {title}")
            error_count += 1
            # Silently continue - error is already shown in progress bar
    
    session.close()
    progress_bar.close()
    
    # Final summary
    print(f"\n🎉 Pipeline completed!")
    print(f"✅ Processed: {processed_count} new articles")
    print(f"⏭️  Skipped: {skipped_count} existing articles")
    if error_count > 0:
        print(f"⚠️  Errors: {error_count} articles failed")
    print(f"📊 Total: {processed_count + skipped_count + error_count} articles processed")

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
