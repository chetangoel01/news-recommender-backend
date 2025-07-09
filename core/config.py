import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig:
    """Database configuration for Supabase PostgreSQL"""
    
    # Database connection settings
    USER: str = os.getenv("user", "")
    PASSWORD: str = os.getenv("password", "")
    HOST: str = os.getenv("host", "localhost")
    PORT: str = os.getenv("port", "5432")
    DBNAME: str = os.getenv("dbname", "postgres")
    
    @classmethod
    def get_connection_params(cls) -> dict:
        """Get connection parameters for psycopg2"""
        return {
            'user': cls.USER,
            'password': cls.PASSWORD,
            'host': cls.HOST,
            'port': cls.PORT,
            'dbname': cls.DBNAME
        }

# Database connection function
def get_database_connection():
    """
    Create and return a database connection using psycopg2
    Returns: psycopg2 connection object or None if connection fails
    """
    import psycopg2
    
    try:
        connection = psycopg2.connect(**DatabaseConfig.get_connection_params())
        return connection
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None

def test_database_connection():
    """
    Test the database connection and print status
    """
    connection = get_database_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT NOW();")
            result = cursor.fetchone()
            print("Database connection successful!")
            print(f"Current database time: {result[0]}")
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Database test failed: {e}")
            connection.close()
            return False
    else:
        print("Could not establish database connection")
        return False

class Settings(BaseSettings):
    NEWS_API_KEY: str = None
    bart_api_token: str = None
    user: str = None
    password: str = None
    host: str = None
    port: str = None
    dbname: str = None
    DATABASE_URL: str = None

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields in the .env file

settings = Settings()