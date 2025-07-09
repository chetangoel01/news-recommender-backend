# News Summarizer and Embedding Pipeline

This application ingests news articles in real-time, summarizes them using a transformer model, and stores the summaries along with semantic embeddings in a vector database. These embeddings support semantic search, personalized recommendations, and content discovery.

---

## Technology Stack

- **Summarization**: [`facebook/bart-large-cnn`](https://huggingface.co/facebook/bart-large-cnn), hosted via Hugging Face Spaces (FastAPI)
- **Embeddings**: [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from `sentence-transformers`
- **Storage**: Supabase (PostgreSQL with `pgvector`)
- **News Extraction**: NewsAPI and `newspaper3k`

---

## Project Structure

```
. 📂 app/
│
├── 📂 api/                         # FastAPI routes & API logic
│   ├── 📄 main.py                  # FastAPI app setup
│   └── 📂 routes/
│       ├── 📄 __init__.py
│       ├── 📄 articles.py
│       └── 📄 users.py
│
├── 📂 pipeline/                    # Summarization, embeddings, indexing
│   ├── 📄 summarize.py
│   ├── 📄 embed.py
│   └── 📂 embeddings/
│       ├── 📄 article_index.faiss
│
├── 📂 core/                        # Shared code for DB, models, logic
│   ├── 📄 db.py                    # Supabase or pgvector interface
│   ├── 📄 models.py                # Pydantic/ORM models
│   ├── 📄 recommender.py          # Vector search, similarity, ranking
│   └── 📄 config.py               # API keys, constants
│
├── 📄 requirements.txt
└── 📄 README.md
````

---

## Workflow Overview

### 1. Fetch Articles
- Retrieves top headlines from NewsAPI
- Extracts full article text using `newspaper3k`

### 2. Summarize
- Sends article text to a Hugging Face-hosted FastAPI summarization endpoint
- Applies chunked summarization for long-form content
- Summaries are approximately 1,000 characters in length

### 3. Store in Supabase
- Inserts metadata and summaries into a Supabase PostgreSQL database
- Duplicate URLs are ignored to prevent reprocessing

### 4. Generate Embeddings
- Uses `all-MiniLM-L6-v2` to produce a 384-dimensional vector for each summary
- Stores the vector in a `pgvector` column for similarity search and recommendation

---

## Supabase Table Schema

```sql
CREATE TABLE summaries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  url text UNIQUE,
  title text,
  summary text,
  raw_text text,
  source text,
  embedding float8[],
  created_at timestamp with time zone DEFAULT now()
);
````

> Ensure the `pgvector` extension is enabled in your Supabase project.

---

## Usage

### Run summarization and store new articles:

```bash
python summarize.py
```

### Generate embeddings for stored summaries:

```bash
python embed.py
```

---

## Model Details

### Summarization: `facebook/bart-large-cnn`

* Transformer-based abstractive summarizer
* Token limit: 1024
* Chunked summarization is used for longer inputs
* Deployed via Hugging Face Spaces (FastAPI)

### Embedding: `all-MiniLM-L6-v2`

* 384-dimensional output
* Optimized for sentence-level semantic similarity
* Lightweight and suitable for CPU inference

---

## Applications

* Semantic search
* Personalized news recommendations
* Topic clustering
* Content deduplication and similarity scoring

---

## Deployment Overview

| Component         | Host                | Description                             |
| ----------------- | ------------------- | --------------------------------------- |
| Summarization API | Hugging Face Spaces | Summarization service for article text  |
| Embedding Engine  | Render or local     | CPU-based semantic embedding generation |
| Database          | Supabase            | Vectorized storage and metadata         |

---

This system enables vectorized news summarization and retrieval pipelines that scale across devices and platforms, without requiring GPU hosting or local heavy inference.