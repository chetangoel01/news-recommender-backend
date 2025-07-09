# pipeline/fetch.py
import requests
import json
import os
from datetime import datetime, timedelta
from core.config import settings

def fetch_articles(use_cache=True, force_refresh=False):
    """
    Fetch top headlines from the past month by making daily requests.
    
    Args:
        use_cache: Whether to use cached articles if available
        force_refresh: Whether to force refresh and ignore cache
    """
    cache_file = "pipeline/cached_articles.json"
    
    # Try to load from cache first
    if use_cache and not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                print(f"Loaded {len(cached_data['articles'])} articles from cache (fetched on {cached_data['fetched_date']})")
                return cached_data['articles']
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    # Fetch fresh articles from API
    url = "https://newsapi.org/v2/everything"
    
    # Calculate date range for the past month
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    all_articles = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        params = {
            "q": "US",  # Search for US news
            "language": "en",
            "sortBy": "publishedAt",
            "from": date_str,
            "to": date_str,
            "pageSize": 100,  # Maximum articles per day
            "apiKey": settings.NEWS_API_KEY,
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            if articles:
                all_articles.extend(articles)
                print(f"  Found {len(articles)} articles for {date_str}")
            else:
                print(f"  No articles found for {date_str}")
            
            # Add a small delay to be respectful to the API
            import time
            time.sleep(0.1)
            
        except requests.exceptions.HTTPError as e:
            if "maximumResultsReached" in str(e):
                print(f"Reached free tier limit. Stopping at {date_str}. Total articles: {len(all_articles)}")
                break
            else:
                print(f"Error fetching articles for {date_str}: {e}")
        except Exception as e:
            print(f"Error fetching articles for {date_str}: {e}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_articles = []
    
    for article in all_articles:
        if article.get("url") and article["url"] not in seen_urls:
            seen_urls.add(article["url"])
            unique_articles.append(article)
    
    print(f"Total unique articles fetched: {len(unique_articles)}")
    
    # Save to cache
    print(f"Attempting to save cache: use_cache={use_cache}, articles_count={len(unique_articles)}")
    if use_cache and unique_articles:
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            cache_data = {
                "fetched_date": datetime.now().isoformat(),
                "articles": unique_articles
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Saved {len(unique_articles)} articles to cache: {cache_file}")
        except Exception as e:
            print(f"Error saving cache: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Not saving cache: use_cache={use_cache}, articles_count={len(unique_articles)}")
    
    return unique_articles

def fetch_diverse_articles(use_cache=True, force_refresh=False):
    """
    Fetch articles from multiple topic queries for diverse content (free tier friendly)
    
    Args:
        use_cache: Whether to use cached articles if available
        force_refresh: Whether to force refresh and ignore cache
    """
    cache_file = "pipeline/cached_diverse_articles.json"
    
    # Try to load from cache first
    if use_cache and not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                print(f"Loaded {len(cached_data['articles'])} diverse articles from cache (fetched on {cached_data['fetched_date']})")
                return cached_data['articles']
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    # Fetch fresh articles from API
    url = "https://newsapi.org/v2/everything"
    
    # Calculate date range for the past 3 days (shorter range to get more recent articles)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    # Smaller set of focused queries to stay within limits
    queries = [
        "technology",
        "business", 
        "politics",
        "health",
        "science"
    ]
    
    all_articles = []
    
    for query in queries:
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "pageSize": 20,  # Smaller page size to stay within limits
            "apiKey": settings.NEWS_API_KEY,
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            all_articles.extend(articles)
            
            print(f"Fetched {len(articles)} articles for query: {query}")
            
        except requests.exceptions.HTTPError as e:
            if "maximumResultsReached" in str(e):
                print(f"Reached free tier limit for query '{query}'. Stopping.")
                break
            else:
                print(f"Error fetching articles for query '{query}': {e}")
                continue
        except Exception as e:
            print(f"Error fetching articles for query '{query}': {e}")
            continue
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_articles = []
    
    for article in all_articles:
        if article.get("url") and article["url"] not in seen_urls:
            seen_urls.add(article["url"])
            unique_articles.append(article)
    
    print(f"Total unique articles fetched: {len(unique_articles)}")
    
    # Save to cache
    if use_cache and unique_articles:
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            cache_data = {
                "fetched_date": datetime.now().isoformat(),
                "articles": unique_articles
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Saved {len(unique_articles)} diverse articles to cache: {cache_file}")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    return unique_articles

def clear_cache(cache_type="all"):
    """
    Clear cached articles.
    
    Args:
        cache_type: "all", "daily", or "diverse"
    """
    cache_files = {
        "daily": "pipeline/cached_articles.json",
        "diverse": "pipeline/cached_diverse_articles.json"
    }
    
    if cache_type == "all":
        files_to_remove = cache_files.values()
    elif cache_type in cache_files:
        files_to_remove = [cache_files[cache_type]]
    else:
        print(f"Invalid cache type: {cache_type}. Use 'all', 'daily', or 'diverse'")
        return
    
    for cache_file in files_to_remove:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"Removed cache file: {cache_file}")
        else:
            print(f"Cache file not found: {cache_file}")
