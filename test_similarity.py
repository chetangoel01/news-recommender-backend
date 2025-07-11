#!/usr/bin/env python3
"""
Quick test script for pgvector similarity search
Tests finding sports-related articles
"""

import numpy as np
import psycopg2
from pipeline.embed import generate_article_embedding
from core.config import DatabaseConfig
import json

def test_sports_similarity():
    """Test similarity search for sports articles"""
    
    # Connect to database
    try:
        params = DatabaseConfig.get_connection_params()
        if 'dsn' in params:
            conn = psycopg2.connect(params['dsn'])
        else:
            conn = psycopg2.connect(**params)
        
        print("✅ Connected to database")
        
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return
    
    # Create a sports-related search query
    sports_query = "basketball game highlights scoring points"
    
    # Generate embedding for the search query
    print(f"🔍 Generating embedding for: '{sports_query}'")
    search_embedding = generate_article_embedding(
        title="",
        summary=sports_query,
        content=""
    )
    
    if search_embedding is None:
        print("❌ Failed to generate search embedding")
        return
    
    print(f"✅ Generated embedding: {search_embedding.shape}")
    
    # Query for similar articles
    query = """
    SELECT 
        id,
        title,
        summary,
        url,
        source_name,
        published_at,
        1 - (embedding <=> %s::vector) as similarity
    FROM articles 
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT 10;
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (search_embedding.tolist(), search_embedding.tolist()))
        results = cursor.fetchall()
        
        print(f"\n🎯 Found {len(results)} similar articles:")
        print("=" * 80)
        
        for i, (article_id, title, summary, url, source, published, similarity) in enumerate(results, 1):
            print(f"\n{i}. Similarity: {similarity:.3f}")
            print(f"   Title: {title}")
            print(f"   Source: {source}")
            print(f"   Summary: {summary[:150]}...")
            print(f"   URL: {url}")
            print(f"   Published: {published}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        cursor.close()
        conn.close()

def test_specific_sports_terms():
    """Test different sports-related search terms"""
    
    sports_terms = [
        "football touchdown quarterback",
        "basketball NBA playoffs",
        "baseball home run pitcher",
        "soccer goal striker",
        "tennis match serve"
    ]
    
    # Connect to database
    try:
        params = DatabaseConfig.get_connection_params()
        if 'dsn' in params:
            conn = psycopg2.connect(params['dsn'])
        else:
            conn = psycopg2.connect(**params)
        
        cursor = conn.cursor()
        
        for term in sports_terms:
            print(f"\n🏈 Testing: '{term}'")
            print("-" * 40)
            
            # Generate embedding
            search_embedding = generate_article_embedding(
                title="",
                summary=term,
                content=""
            )
            
            if search_embedding is None:
                print("❌ Failed to generate embedding")
                continue
            
            # Query
            query = """
            SELECT title, source_name, 1 - (embedding <=> %s::vector) as similarity
            FROM articles 
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT 3;
            """
            
            cursor.execute(query, (search_embedding.tolist(), search_embedding.tolist()))
            results = cursor.fetchall()
            
            for title, source, similarity in results:
                print(f"  {similarity:.3f} | {source} | {title[:60]}...")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing pgvector similarity search for sports articles")
    print("=" * 60)
    
    # Test 1: General sports similarity
    test_sports_similarity()
    
    print("\n" + "=" * 60)
    print("🏆 Testing specific sports terms")
    print("=" * 60)
    
    # Test 2: Specific sports terms
    test_specific_sports_terms()
    
    print("\n✅ Done!") 