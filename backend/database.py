"""
Database Module for VisionWealth
Database utilities and helper functions - imports models from models.py
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Generator, Optional
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# IMPORT DATABASE CONFIGURATION FROM db.py
# ========================================

# Import engine, session factory, and base from db module
from db import engine, SessionLocal, Base

# Import all models from models module (single source of truth)
from models import (
    User, Portfolio, Holding, Watchlist, WatchlistItem, 
    NetWorthHistory, Transaction, Goal,
    UserRole, UserStatus, AssetType, TransactionType, GoalStatus
)

logger.info("Imported database configuration and models successfully")


# ========================================
# NOTE: All models are now defined in models.py
# database.py provides utility functions for database operations
# ========================================


# ========================================
# DATABASE UTILITIES
# ========================================

def init_db():
    """
    Initialize database tables.
    
    Creates all tables if they don't exist.
    Safe for Railway and other cloud deployments.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Log created tables
        table_names = Base.metadata.tables.keys()
        logger.info(f"Tables: {', '.join(table_names)}")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def drop_all_tables():
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    Use only for development/testing.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️  All database tables dropped")
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """
    Get database session.
    
    Yields:
        SQLAlchemy Session
    
    Usage:
```python
        session = next(get_session())
        try:
            # Use session
            session.query(Portfolio).all()
        finally:
            session.close()
```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI endpoints.
    
    Yields:
        SQLAlchemy Session
    
    Usage:
```python
        @app.get("/portfolios")
        def get_portfolios(db: Session = Depends(get_db)):
            return db.query(Portfolio).all()
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


def create_portfolio(
    db: Session,
    name: str = "My Portfolio",
    description: Optional[str] = None
) -> Portfolio:
    """
    Create a new portfolio.
    
    Args:
        db: Database session
        name: Portfolio name
        description: Optional description
    
    Returns:
        Created Portfolio object
    """
    portfolio = Portfolio(
        name=name,
        description=description
    )
    
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    
    logger.info(f"Created portfolio: {portfolio.name} (ID: {portfolio.id})")
    
    return portfolio


def create_holding(
    db: Session,
    portfolio_id: int,
    ticker: str,
    quantity: float,
    price: float,
    cost_basis: float,
    asset_type: str = "Stock",
    **kwargs
) -> Holding:
    """
    Create a new holding.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
        ticker: Ticker symbol
        quantity: Number of shares/units
        price: Current price
        cost_basis: Cost basis per share
        asset_type: Asset type
        **kwargs: Additional fields
    
    Returns:
        Created Holding object
    """
    holding = Holding(
        portfolio_id=portfolio_id,
        ticker=ticker,
        quantity=quantity,
        price=price,
        cost_basis=cost_basis,
        asset_type=asset_type,
        **kwargs
    )
    
    db.add(holding)
    db.commit()
    db.refresh(holding)
    
    logger.info(f"Created holding: {ticker} in portfolio {portfolio_id}")
    
    return holding


def get_portfolio_with_holdings(
    db: Session,
    portfolio_id: int
) -> Optional[Portfolio]:
    """
    Get portfolio with all holdings loaded.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
    
    Returns:
        Portfolio object or None
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id
    ).first()
    
    if portfolio:
        # Trigger loading of holdings
        _ = portfolio.holdings.all()
    
    return portfolio


def update_portfolio_value(
    db: Session,
    portfolio_id: int
) -> Optional[Portfolio]:
    """
    Recalculate and update portfolio metrics.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
    
    Returns:
        Updated Portfolio object or None
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id
    ).first()
    
    if portfolio:
        portfolio.calculate_metrics()
        db.commit()
        db.refresh(portfolio)
        
        logger.info(
            f"Updated portfolio {portfolio_id}: "
            f"value=${portfolio.total_value:.2f}, "
            f"gain/loss=${portfolio.total_gain_loss:.2f}"
        )
    
    return portfolio


def get_database_stats() -> dict:
    """
    Get database statistics.
    
    Returns:
        Dictionary with table counts and statistics
    """
    db = next(get_session())
    
    try:
        # Import DATABASE_URL from db module
        from db import DATABASE_URL
        IS_SQLITE = DATABASE_URL.startswith("sqlite")
        
        stats = {
            'portfolios': db.query(Portfolio).count(),
            'holdings': db.query(Holding).count(),
            'watchlists': db.query(Watchlist).count(),
            'watchlist_items': db.query(WatchlistItem).count(),
            'database_type': 'SQLite' if IS_SQLITE else 'Other',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return stats
    
    finally:
        db.close()


def check_database_health() -> dict:
    """
    Check database health and connectivity.
    
    Returns:
        Dictionary with health status
    """
    try:
        db = next(get_session())
        
        # Test query
        db.execute("SELECT 1")
        
        stats = get_database_stats()
        
        db.close()
        
        return {
            'status': 'healthy',
            'connected': True,
            'stats': stats
        }
    
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'connected': False,
            'error': str(e)
        }


# ========================================
# INITIALIZATION
# ========================================

# Automatically create tables on import (development only)
if os.getenv('AUTO_INIT_DB', 'false').lower() == 'true':
    logger.info("Auto-initializing database...")
    init_db()


# Export commonly used items
__all__ = [
    'Base',
    'engine',
    'SessionLocal',
    'get_session',
    'get_db',
    'init_db',
    'drop_all_tables',
    # Models (imported from models.py)
    'User',
    'Portfolio',
    'Holding',
    'Watchlist',
    'WatchlistItem',
    'NetWorthHistory',
    'Transaction',
    'Goal',
    # Enums
    'UserRole',
    'UserStatus',
    'AssetType',
    'TransactionType',
    'GoalStatus',
    # Utility functions
    'create_portfolio',
    'create_holding',
    'get_portfolio_with_holdings',
    'update_portfolio_value',
    'get_database_stats',
    'check_database_health',
]
