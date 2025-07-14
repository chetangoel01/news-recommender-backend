# Pipeline Directory

This directory contains the ML pipeline for processing news articles and managing embeddings.

## Currently Active

- ✅ **`fetch.py`** - News article fetching from APIs
- ✅ **`summarize.py`** - AI-powered article summarization  
- ✅ **`embed.py`** - Sentence transformer embeddings generation
- ✅ **`run_pipeline.py`** - Complete pipeline orchestration

## For Future Use (Not Currently Used in API)

- 🔄 **`build_faiss_index.py`** - FAISS index creation
- 🔄 **`incremental_index_update.py`** - FAISS index maintenance  
- 🔄 **`index_scheduler.py`** - Automated FAISS index updates

### Why FAISS is not used yet:

- **Current scale**: ~3k articles (pgvector handles this efficiently)
- **Performance target**: <100ms similarity search (pgvector meets this)
- **Complexity**: pgvector offers simpler architecture with database consistency
- **Future consideration**: When article count exceeds 100k+ articles

### Current similarity search:

The API uses **pgvector** directly for similarity search:
```sql
SELECT * FROM articles 
ORDER BY embedding <=> $1 
LIMIT 10;
```

This provides:
- ✅ Automatic sync with database
- ✅ Transactional consistency  
- ✅ Rich filtering capabilities
- ✅ Built-in pagination
- ✅ <100ms performance at current scale

### When to use FAISS:

Consider switching to FAISS when:
- Article count > 100k
- Advanced index types needed (HNSW, IVF)
- Horizontal scaling across multiple servers
- Performance requirements exceed pgvector capabilities 