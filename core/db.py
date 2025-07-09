from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import DatabaseConfig

# Create SQLAlchemy engine
DATABASE_URL = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DBNAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()