"""
SQLAlchemy Database Models for VisionWealth Platform
Comprehensive data models for users, portfolios, holdings, and related entities
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean, JSON, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


# Enums

class UserRole(str, enum.Enum):
    """User role enumeration"""
    CLIENT = "client"
    ADVISOR = "advisor"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class AssetType(str, enum.Enum):
    """Asset type classification"""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    CRYPTOCURRENCY = "cryptocurrency"
    CASH = "cash"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class TransactionType(str, enum.Enum):
    """Transaction type"""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"


# Models

class User(Base):
    """User model - authentication and profile information"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    phone_number = Column(String(20))
    
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    preferences = Column(JSON, default=dict)
    risk_tolerance = Column(String(20))
    
    email_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_user_email_status', 'email', 'status'),
        Index('idx_user_role_status', 'role', 'status'),
    )
    
    @validates('email')
    def validate_email(cls, key, email):
        if '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower().strip()
    
    @hybrid_property
    def is_active(self):
        return self.status == UserStatus.ACTIVE and self.deleted_at is None
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"


class Portfolio(Base):
    """Portfolio model - investment portfolio metadata"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), default="My Portfolio", nullable=False)
    description = Column(Text)
    
    total_value = Column(Float, default=0.0)
    total_cost_basis = Column(Float, default=0.0)
    total_gain_loss = Column(Float, default=0.0)
    total_gain_loss_pct = Column(Float, default=0.0)
    
    currency = Column(String(3), default="USD")
    is_primary = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan", lazy="dynamic")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_portfolio_user_id', 'user_id'),
        UniqueConstraint('user_id', 'name', name='uq_user_portfolio_name'),
    )
    
    @validates('name')
    def validate_name(cls, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Portfolio name cannot be empty")
        return name.strip()
    
    def __repr__(self):
        return f"<Portfolio(id={self.id}, name='{self.name}', value=${self.total_value:,.2f})>"


class Holding(Base):
    """Holding model - individual securities in portfolio"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    
    symbol = Column(String(20), nullable=False, index=True)
    description = Column(String(255))
    
    quantity = Column(Float, default=0.0, nullable=False)
    price = Column(Float, default=0.0)
    cost_basis = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    
    gain_loss = Column(Float, default=0.0)
    gain_loss_pct = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)
    
    sector = Column(String(100))
    asset_type = Column(Enum(AssetType), default=AssetType.STOCK)
    
    est_annual_income = Column(Float, default=0.0)
    dividend_yield = Column(Float, default=0.0)
    
    metadata = Column(JSON, default=dict)
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    portfolio = relationship("Portfolio", back_populates="holdings")
    transactions = relationship("Transaction", back_populates="holding", cascade="all, delete-orphan", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_holding_portfolio_symbol', 'portfolio_id', 'symbol'),
        Index('idx_holding_asset_type', 'asset_type'),
        CheckConstraint('quantity >= 0', name='check_quantity_positive'),
    )
    
    @validates('quantity')
    def validate_quantity(cls, key, quantity):
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        return quantity
    
    def __repr__(self):
        return f"<Holding(id={self.id}, symbol='{self.symbol}', quantity={self.quantity})>"


class Transaction(Base):
    """Transaction model - portfolio transaction history"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    holding_id = Column(Integer, ForeignKey("holdings.id", ondelete="SET NULL"))
    
    transaction_type = Column(Enum(TransactionType), nullable=False)
    symbol = Column(String(20), index=True)
    quantity = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text)
    
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="transactions")
    portfolio = relationship("Portfolio", back_populates="transactions")
    holding = relationship("Holding", back_populates="transactions")
    
    __table_args__ = (
        Index('idx_transaction_user_date', 'user_id', 'transaction_date'),
        Index('idx_transaction_portfolio_date', 'portfolio_id', 'transaction_date'),
        Index('idx_transaction_type', 'transaction_type'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.transaction_type.value}', symbol='{self.symbol}')>"


class WatchlistItem(Base):
    """Watchlist item model - securities users monitor"""
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(255))
    notes = Column(Text)
    target_price = Column(Float)
    
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="watchlist_items")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_watchlist_symbol'),
        Index('idx_watchlist_user_symbol', 'user_id', 'symbol'),
    )
    
    def __repr__(self):
        return f"<WatchlistItem(id={self.id}, symbol='{self.symbol}')>"


# Utility functions

def create_all_tables(engine):
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
