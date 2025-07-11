import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

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
    DATABASE_URL: str = os.getenv("DATABASE_URL", None)
    
    @classmethod
    def get_connection_params(cls) -> dict:
        """Get connection parameters for psycopg2"""
        if cls.DATABASE_URL:
            return {'dsn': cls.DATABASE_URL}
        params = {
            'user': cls.USER,
            'password': cls.PASSWORD,
            'host': cls.HOST,
            'port': cls.PORT,
            'dbname': cls.DBNAME,
            'connect_timeout': 15,
            'application_name': 'news-recommender-backend',
            'keepalives_idle': 60,
            'keepalives_interval': 10,
            'keepalives_count': 5
        }
        return params

# Database connection function
def get_database_connection():
    """
    Create and return a database connection using psycopg2
    Returns: psycopg2 connection object or None if connection fails
    """
    import psycopg2
    
    try:
        params = DatabaseConfig.get_connection_params()
        if 'dsn' in params:
            connection = psycopg2.connect(params['dsn'])
        else:
            connection = psycopg2.connect(**params)
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
    # News API settings
    NEWS_API_KEY: str | None = None
    bart_api_token: str | None = None
    
    # Database settings
    user: str | None = None
    password: str | None = None
    host: str | None = None
    port: str | None = None
    dbname: str | None = None
    DATABASE_URL: str | None = None
    
    # Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-please")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    CORS_ORIGINS: list = ["*"]  # Configure properly for production

    model_config = ConfigDict(env_file=".env", extra="allow")

settings = Settings()