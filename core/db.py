from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Use DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "connect_timeout": 15,
        "application_name": "news-recommender-backend",
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "sslmode": "require",  # Important for Supabase-hosted Postgres
    },
    pool_pre_ping=True,
    pool_recycle=300
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model
Base = declarative_base()

# Dependency to get DB session (e.g. in FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
