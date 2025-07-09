from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY, FLOAT
import uuid
from core.db import Base

class Article(Base):
    __tablename__ = "articles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String)
    source_name = Column(String, nullable=False)
    author = Column(String)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(Text)
    summary = Column(Text)
    url = Column(Text, nullable=False, unique=True)
    url_to_image = Column(Text)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime)
    language = Column(String)
    category = Column(String)
    embedding = Column(ARRAY(FLOAT))  # Store semantic embedding as float array
