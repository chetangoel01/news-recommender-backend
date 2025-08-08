-- Initialize database with pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database user if not exists (this will be handled by environment variables)
-- The actual user creation is handled by PostgreSQL environment variables

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE news_recommender TO news_user;
GRANT ALL ON SCHEMA public TO news_user;

-- Set search path
SET search_path TO public; 