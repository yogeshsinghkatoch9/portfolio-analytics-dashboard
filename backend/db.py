from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), 'data')
os.makedirs(DB_PATH, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DB_PATH, 'portfolio.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Portfolio(Base):
    __tablename__ = 'portfolios'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='My Portfolio')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    holdings = relationship('Holding', back_populates='portfolio', cascade='all, delete-orphan')


class Holding(Base):
    __tablename__ = 'holdings'
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False)
    ticker = Column(String, index=True)
    quantity = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    cost_basis = Column(Float, default=0.0)
    asset_type = Column(String, default='Stock')  # Stock, Crypto, Real Estate, Cash, Liability
    currency = Column(String, default='USD')
    meta_json = Column(Text, default='')
    portfolio = relationship('Portfolio', back_populates='holdings')


class Watchlist(Base):
    __tablename__ = 'watchlists'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default='My Watchlist')
    items = relationship('WatchlistItem', back_populates='watchlist', cascade='all, delete-orphan')


class WatchlistItem(Base):
    __tablename__ = 'watchlist_items'
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id', ondelete='CASCADE'), nullable=False)
    ticker = Column(String, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    watchlist = relationship('Watchlist', back_populates='items')


def init_db():
    Base.metadata.create_all(bind=engine)
    # Simple migration for SQLite to add new columns if they don't exist
    try:
        with engine.connect() as conn:
            # Check if asset_type exists
            result = conn.execute(Text("PRAGMA table_info(holdings)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'asset_type' not in columns:
                conn.execute(Text("ALTER TABLE holdings ADD COLUMN asset_type VARCHAR DEFAULT 'Stock'"))
            if 'currency' not in columns:
                conn.execute(Text("ALTER TABLE holdings ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
    except Exception as e:
        print(f"Migration warning: {e}")


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
