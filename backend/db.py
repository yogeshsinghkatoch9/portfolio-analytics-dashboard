"""
Database Configuration and Session Management
Handles SQLAlchemy engine, session factory, and database utilities
with support for multiple database types (SQLite, PostgreSQL, MySQL)
"""

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool, NullPool
from typing import Generator, Optional
import os
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# DATABASE URL CONFIGURATION
# ========================================

def get_database_url() -> str:
    """
    Get database URL from environment or use default.
    
    Supports:
    - SQLite (default)
    - PostgreSQL
    - MySQL
    
    Returns:
        Database connection URL
    """
    database_url = os.getenv("DATABASE_URL")
    
    # Handle Heroku/Railway PostgreSQL URL format
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")
    
    # Default to SQLite if no URL provided
    if not database_url:
        database_url = "sqlite:///./portfolio.db"
        logger.info("Using default SQLite database")
    else:
        # Don't log credentials
        safe_url = database_url.split('@')[0] if '@' in database_url else database_url.split('://')[0]
        logger.info(f"Using database: {safe_url}://...")
    
    return database_url


DATABASE_URL = get_database_url()


# ========================================
# ENGINE CONFIGURATION
# ========================================

def create_db_engine(database_url: str = DATABASE_URL):
    """
    Create SQLAlchemy engine with appropriate configuration.
    
    Args:
        database_url: Database connection URL
    
    Returns:
        SQLAlchemy Engine
    """
    # Determine database type
    is_sqlite = database_url.startswith("sqlite")
    is_postgresql = database_url.startswith("postgresql")
    is_mysql = database_url.startswith("mysql")
    
    # Base configuration
    engine_kwargs = {
        "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
        "future": True,  # Use SQLAlchemy 2.0 style
    }
    
    # SQLite-specific configuration
    if is_sqlite:
        engine_kwargs.update({
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,  # Better for SQLite
        })
        logger.info("Configured SQLite engine with StaticPool")
    
    # PostgreSQL-specific configuration
    elif is_postgresql:
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        })
        logger.info("Configured PostgreSQL engine with QueuePool")
    
    # MySQL-specific configuration
    elif is_mysql:
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        })
        logger.info("Configured MySQL engine with QueuePool")
    
    # Unknown database type
    else:
        logger.warning(f"Unknown database type, using default configuration")
        engine_kwargs.update({
            "poolclass": NullPool,  # Safe default
        })
    
    # Create engine
    try:
        engine = create_engine(database_url, **engine_kwargs)
        logger.info("Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


# Create global engine instance
engine = create_db_engine()


# ========================================
# SESSION CONFIGURATION
# ========================================

# Create SessionLocal class for creating sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Don't expire objects after commit
)


# ========================================
# BASE CLASS
# ========================================

# Base class for declarative models
Base = declarative_base()


# ========================================
# DATABASE EVENTS
# ========================================

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Set SQLite pragmas for better performance.
    
    Only executed for SQLite databases.
    """
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
        logger.debug("SQLite pragmas set for connection")


@event.listens_for(engine, "first_connect")
def receive_first_connect(dbapi_conn, connection_record):
    """Log first database connection"""
    logger.info("First database connection established")


# ========================================
# SESSION MANAGEMENT
# ========================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session for FastAPI.
    
    Yields:
        SQLAlchemy Session
    
    Usage:
```python
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
```
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Yields:
        SQLAlchemy Session
    
    Usage:
```python
        with get_db_context() as db:
            items = db.query(Item).all()
```
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a new database session (manual management).
    
    Returns:
        SQLAlchemy Session
    
    Warning:
        You must manually close this session when done!
    
    Usage:
```python
        db = get_db_session()
        try:
            items = db.query(Item).all()
        finally:
            db.close()
```
    """
    return SessionLocal()


# ========================================
# DATABASE UTILITIES
# ========================================

def init_database():
    """
    Initialize database by creating all tables.
    
    Safe to call multiple times - only creates missing tables.
    """
    try:
        # Import all models to ensure they're registered with Base
        import models
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


def drop_all_tables():
    """
    Drop all database tables.
    
    WARNING: This will delete ALL data!
    Only use in development/testing.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️  All database tables dropped")
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("✅ Database connection check: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection check: FAILED - {e}")
        return False


def get_database_info() -> dict:
    """
    Get information about the database.
    
    Returns:
        Dictionary with database information
    """
    info = {
        "url": DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL.split('://')[0] + "://...",
        "dialect": engine.dialect.name,
        "driver": engine.driver,
        "pool_size": getattr(engine.pool, 'size', lambda: 'N/A')(),
        "pool_timeout": getattr(engine.pool, '_timeout', 'N/A'),
        "echo": engine.echo,
    }
    
    return info


def get_connection_pool_status() -> dict:
    """
    Get current status of the connection pool.
    
    Returns:
        Dictionary with pool statistics
    """
    try:
        pool = engine.pool
        
        status = {
            "size": pool.size() if hasattr(pool, 'size') else 'N/A',
            "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else 'N/A',
            "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else 'N/A',
            "pool_class": pool.__class__.__name__,
        }
        
        return status
    except Exception as e:
        logger.warning(f"Could not get pool status: {e}")
        return {"error": str(e)}


def reset_connection_pool():
    """
    Reset the connection pool.
    
    Useful for recovering from connection issues.
    """
    try:
        engine.dispose()
        logger.info("✅ Connection pool reset successfully")
    except Exception as e:
        logger.error(f"❌ Failed to reset connection pool: {e}")
        raise


# ========================================
# HEALTH CHECK
# ========================================

def database_health_check() -> dict:
    """
    Comprehensive database health check.
    
    Returns:
        Dictionary with health status and diagnostics
    """
    health = {
        "status": "unknown",
        "connected": False,
        "info": {},
        "pool_status": {},
        "error": None
    }
    
    try:
        # Check connection
        health["connected"] = check_database_connection()
        
        if health["connected"]:
            health["status"] = "healthy"
            health["info"] = get_database_info()
            health["pool_status"] = get_connection_pool_status()
        else:
            health["status"] = "unhealthy"
            health["error"] = "Connection check failed"
    
    except Exception as e:
        health["status"] = "unhealthy"
        health["error"] = str(e)
        logger.error(f"Health check failed: {e}")
    
    return health


# ========================================
# TRANSACTION UTILITIES
# ========================================

@contextmanager
def transaction():
    """
    Context manager for database transactions.
    
    Automatically commits on success, rolls back on error.
    
    Usage:
```python
        with transaction() as db:
            db.add(new_item)
            # Automatically committed
```
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def execute_in_transaction(func, *args, **kwargs):
    """
    Execute a function within a database transaction.
    
    Args:
        func: Function to execute (must accept db as first argument)
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
    
    Returns:
        Result of the function
    
    Usage:
```python
        def create_item(db, name):
            item = Item(name=name)
            db.add(item)
            return item
        
        result = execute_in_transaction(create_item, "Test Item")
```
    """
    with transaction() as db:
        return func(db, *args, **kwargs)


# ========================================
# INITIALIZATION
# ========================================

# Log database configuration on import
logger.info(f"Database configured: {engine.dialect.name}")
logger.info(f"Pool class: {engine.pool.__class__.__name__}")

# Check connection on startup if configured
if os.getenv("CHECK_DB_ON_STARTUP", "true").lower() == "true":
    if check_database_connection():
        logger.info("✅ Database startup check: PASSED")
    else:
        logger.warning("⚠️  Database startup check: FAILED")


# ========================================
# BACKWARDS COMPATIBILITY
# ========================================

# Alias for backwards compatibility
get_session = get_db

# Note: Models should be imported from models.py, not from db.py
# This prevents circular import issues


# ========================================
# EXPORTS
# ========================================

__all__ = [
    # Core objects
    'engine',
    'SessionLocal',
    'Base',
    'get_db',
    'get_session',  # Backwards compatibility alias
    
    # Session management
    'get_db_context',
    'get_db_session',
    'transaction',
    'execute_in_transaction',
    
    # Database operations
    'init_database',
    'drop_all_tables',
    'check_database_connection',
    'reset_connection_pool',
    
    # Information and diagnostics
    'get_database_info',
    'get_connection_pool_status',
    'database_health_check',
    
    # Configuration
    'DATABASE_URL',
]

