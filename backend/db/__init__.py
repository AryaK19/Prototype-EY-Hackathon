import logging
from sqlalchemy.sql import text
from db.session import engine, Base
from db.models import DoctorReport

def init_db():
    try:
        # First dispose any existing connections in the pool
        logging.getLogger("Disposing all existing database connections").setLevel(logging.INFO)
        engine.dispose()
        
        # Try executing a simple query to test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logging.getLogger("Database connection successful!").setLevel(logging.INFO)
            
            # Check active connections (PostgreSQL specific)
            try:
                result = connection.execute(text("""
                    SELECT count(*) as conn_count 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """))
                row = result.fetchone()
                if row:
                    logging.getLogger(f"Active database connections: {row[0]}").setLevel(logging.INFO)
            except Exception as e:
                logging.getLogger(f"Could not check active connections: {e}").setLevel(logging.WARNING)
       
        return True
    except Exception as e:
        logging.getLogger(f"Database connection failed: {e}").setLevel(logging.ERROR)
        return False
    
# Export all models for easy importing
__all__ = [
    "DoctorReport"
]