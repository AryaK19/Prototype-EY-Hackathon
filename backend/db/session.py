from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
import urllib.parse 
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory as this script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

USER = os.getenv("DATABASE_USER")
PASSWORD = os.getenv("DATABASE_PASSWORD")
HOST = os.getenv("DATABASE_HOST")
PORT = os.getenv("DATABASE_PORT")  
DBNAME = os.getenv("DATABASE_dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Configure engine with explicit pooling parameters optimized for Supabase free tier
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},
    poolclass=QueuePool,
    pool_size=10,         # Keep this small for free tier
    max_overflow=0,      # Don't allow extra connections beyond pool_size
    pool_timeout=30,     # Wait time for a connection (seconds)
    pool_recycle=1800,   # Recycle connections after 30 minutes
    pool_pre_ping=True   # Check connection validity before using
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for SQLAlchemy models
Base = declarative_base()

# Dependency for database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            # Ensure we explicitly close the connection to release it back to the pool
            print("Closing database session")
            db.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")
            # If close fails, try more aggressive cleanup
            try:
                db.expire_all()
            except:
                pass

# Function to get database connection string for background tasks
def get_db_connection():
    return DATABASE_URL

# Create a new database session for background tasks
def get_background_db_session():
    """
    Creates a fresh database session for background tasks.
    Unlike get_db(), this returns a session directly, not a generator.
    
    Returns:
        SQLAlchemy session object
    
    Note: 
        The caller is responsible for closing this session when done.
    """
    db = SessionLocal()
    return db
