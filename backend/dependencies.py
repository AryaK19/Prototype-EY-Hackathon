from sqlalchemy.orm import Session
from db.session import SessionLocal, engine
import time
import logging
import threading
from contextlib import contextmanager

# Set up connection tracking
active_connections = {}
connection_lock = threading.Lock()
logger = logging.getLogger("db_connection")

# Database dependency to be used in all route functions
def get_db():
    # Generate a unique ID for this connection
    connection_id = f"conn_{threading.get_ident()}_{time.time()}"
    
    # Track this connection
    with connection_lock:
        active_connections[connection_id] = {
            "timestamp": time.time(),
            "thread": threading.current_thread().name
        }
    
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
            # Remove from tracking once closed
            with connection_lock:
                if connection_id in active_connections:
                    del active_connections[connection_id]
        except Exception as e:
            logger.error(f"Error closing DB connection {connection_id}: {str(e)}")
            # Try to clean up anyway
            with connection_lock:
                if connection_id in active_connections:
                    del active_connections[connection_id]


# Utility function to check for stale connections
def check_stale_connections(max_age_seconds=300):
    """Check for stale connections and log them"""
    stale_connections = []
    current_time = time.time()
    
    with connection_lock:
        for conn_id, details in active_connections.items():
            age = current_time - details["timestamp"]
            if age > max_age_seconds:
                stale_connections.append((conn_id, details, age))
    
    if stale_connections:
        logger.warning(f"Found {len(stale_connections)} stale DB connections")
        for conn_id, details, age in stale_connections:
            logger.warning(f"Stale connection: {conn_id}, age: {age:.1f}s, thread: {details['thread']}")


# Function to dispose engine connections on startup
def dispose_engine_connections():
    """Dispose all connections in the engine pool at startup"""
    try:
        logger.info("Disposing all DB engine connections")
        engine.dispose()
        logger.info("DB engine connections disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing DB connections: {str(e)}")


# Context manager for DB sessions - an alternative to the dependency injection
@contextmanager
def get_db_context():
    """Context manager for DB sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to get a database session without dependency injection
# Used for background tasks that need their own database session
def get_db_session():
    """Returns a new database session (not a dependency)"""
    return SessionLocal()