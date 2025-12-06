"""
SQLAlchemy Database Models for VisionWealth Platform
Comprehensive data models for users, portfolios, holdings, and related entities
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean, JSON, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Base from db module (configuration layer)
from db import Base

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


class GoalStatus(str, enum.Enum):
    """Goal status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Models

class User(Base):
    """User model - authentication and profile information"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)  # Changed from password_hash for consistency
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

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    
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


# NOTE: Portfolio and Holding models are now defined here (single source of truth)

class Portfolio(Base):
    """Portfolio model - investment portfolio metadata"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # nullable for backwards compatibility
    
    name = Column(String(255), default="My Portfolio", nullable=False)
    description = Column(Text)
    
    total_value = Column(Float, default=0.0)
    total_cost_basis = Column(Float, default=0.0)
    total_gain_loss = Column(Float, default=0.0)
    total_gain_loss_pct = Column(Float, default=0.0)
    
    currency = Column(String(3), default="USD")
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan", lazy="dynamic")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_portfolio_user_id', 'user_id'),
        Index('idx_portfolio_name', 'name'),
        Index('idx_portfolio_created', 'created_at'),
        UniqueConstraint('user_id', 'name', name='uq_user_portfolio_name'),
    )
    
    @validates('name')
    def validate_name(cls, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Portfolio name cannot be empty")
        return name.strip()
    
    def calculate_metrics(self):
        """Calculate and update portfolio metrics"""
        holdings = self.holdings.all()
        
        self.total_value = sum(h.quantity * h.price for h in holdings)
        self.total_cost_basis = sum(h.quantity * h.cost_basis for h in holdings)
        self.total_gain_loss = self.total_value - self.total_cost_basis
        if self.total_cost_basis > 0:
            self.total_gain_loss_pct = (self.total_gain_loss / self.total_cost_basis) * 100
        self.updated_at = func.now()
    
    def __repr__(self):
        return f"<Portfolio(id={self.id}, name='{self.name}', value=${self.total_value:,.2f})>"


class Holding(Base):
    """Holding model - individual securities in portfolio"""
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    
    ticker = Column(String(20), nullable=False, index=True)  # Changed from 'symbol' to match existing usage
    symbol = Column(String(20), nullable=False, index=True)  # Keep both for compatibility
    description = Column(String(255))
    
    quantity = Column(Float, default=0.0, nullable=False)
    price = Column(Float, default=0.0)
    cost_basis = Column(Float, default=0.0)
    
    # Asset classification
    sector = Column(String(100))
    asset_type = Column(String(50), default='Stock')  # Changed from Enum to String for flexibility
    asset_category = Column(String(50))
    
    # Additional metrics
    est_annual_income = Column(Float, default=0.0)
    dividend_yield = Column(Float, default=0.0)
    
    # Metadata
    currency = Column(String(3), default='USD')
    notes = Column(Text)
    meta_json = Column(Text, default='{}')  # JSON string for additional metadata
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    transactions = relationship("Transaction", back_populates="holding", cascade="all, delete-orphan", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_holding_portfolio_ticker', 'portfolio_id', 'ticker'),
        Index('idx_holding_portfolio_symbol', 'portfolio_id', 'symbol'),
        Index('idx_holding_asset_type', 'asset_type'),
        CheckConstraint('quantity >= 0', name='check_quantity_positive'),
    )
    
    @property
    def current_value(self) -> float:
        """Calculate current market value"""
        return self.quantity * self.price
    
    @property
    def gain_loss(self) -> float:
        """Calculate unrealized gain/loss"""
        return self.current_value - (self.quantity * self.cost_basis)
    
    @property
    def gain_loss_pct(self) -> float:
        """Calculate gain/loss percentage"""
        if self.cost_basis > 0:
            return ((self.price - self.cost_basis) / self.cost_basis) * 100
        return 0.0
    
    @property
    def weight(self) -> float:
        """Calculate weight in portfolio"""
        if self.portfolio and self.portfolio.total_value > 0:
            return (self.current_value / self.portfolio.total_value) * 100
        return 0.0
    
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
    
    meta_json = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved name)
    
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


class Goal(Base):
    """Goal model - financial goals for users"""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(DateTime(timezone=True))
    
    status = Column(Enum(GoalStatus), default=GoalStatus.NOT_STARTED, nullable=False)
    priority = Column(Integer, default=1) # 1 = High, 2 = Medium, 3 = Low
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="goals")
    
    __table_args__ = (
        Index('idx_goal_user_status', 'user_id', 'status'),
        CheckConstraint('target_amount > 0', name='check_target_amount_positive'),
        CheckConstraint('current_amount >= 0', name='check_current_amount_positive'),
    )
    
    @validates('target_amount', 'current_amount')
    def validate_amounts(cls, key, amount):
        if amount < 0:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} cannot be negative")
        return amount
    
    def __repr__(self):
        return f"<Goal(id={self.id}, name='{self.name}', status='{self.status.value}')>"


class Watchlist(Base):
    """
    Watchlist model - collection of securities to monitor.
    
    Users can create multiple watchlists to track different groups of securities.
    """
    __tablename__ = 'watchlists'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Watchlist details
    name = Column(String(255), default='My Watchlist', nullable=False)
    description = Column(Text)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    items = relationship(
        'WatchlistItem',
        back_populates='watchlist',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_watchlist_name', 'name'),
    )
    
    def __repr__(self):
        return f"<Watchlist(id={self.id}, name='{self.name}', items={self.items.count()})>"


class WatchlistItem(Base):
    """
    Watchlist item model - individual security in a watchlist.
    
    Links securities to watchlists with additional tracking metadata.
    """
    __tablename__ = 'watchlist_items'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key
    watchlist_id = Column(
        Integer,
        ForeignKey('watchlists.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Security details
    ticker = Column(String(20), index=True, nullable=False)
    notes = Column(Text)
    
    # Alert configuration
    alert_enabled = Column(Boolean, default=False)
    target_price = Column(Float)
    alert_price_above = Column(Float)
    alert_price_below = Column(Float)
    
    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    watchlist = relationship('Watchlist', back_populates='items')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('watchlist_id', 'ticker', name='uq_watchlist_ticker'),
        Index('idx_watchlist_item_ticker', 'ticker'),
    )
    
    def __repr__(self):
        return f"<WatchlistItem(id={self.id}, ticker='{self.ticker}', watchlist_id={self.watchlist_id})>"


class NetWorthHistory(Base):
    """
    Net worth history model - tracks portfolio value over time.
    
    Enables historical analysis and performance tracking.
    """
    __tablename__ = 'net_worth_history'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key
    portfolio_id = Column(
        Integer,
        ForeignKey('portfolios.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Financial data
    net_worth = Column(Float, nullable=False)
    total_assets = Column(Float, default=0.0)
    total_liabilities = Column(Float, default=0.0)
    
    # Breakdown (JSON string)
    breakdown_json = Column(Text, default='{}')
    
    # Timestamp
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_networth_portfolio_date', 'portfolio_id', 'calculated_at'),
    )
    
    def __repr__(self):
        return f"<NetWorthHistory(portfolio_id={self.portfolio_id}, net_worth=${self.net_worth:.2f}, date={self.calculated_at})>"


# NOTE: WatchlistItem is defined above - no need to redefine here

# Utility functions

def create_all_tables(engine):
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
