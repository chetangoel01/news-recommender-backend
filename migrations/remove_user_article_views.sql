-- Migration: Remove user_article_views table
-- Date: 2024-01-XX
-- Description: Remove individual article view tracking since we're moving to local-first approach

-- Drop the user_article_views table
DROP TABLE IF EXISTS user_article_views CASCADE;

-- Update the users table to remove the article_views relationship
-- (This is handled by the SQLAlchemy model changes)

-- Add a comment to document the change
COMMENT ON TABLE users IS 'User table - article views now tracked locally on device';

-- Verify the table was dropped
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'user_article_views'
        ) 
        THEN 'user_article_views table still exists - migration failed'
        ELSE 'user_article_views table successfully removed'
    END as migration_status; 