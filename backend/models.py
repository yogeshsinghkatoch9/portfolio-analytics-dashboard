"""
SQLAlchemy database models for VisionWealth platform
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserRole(str, enum.Enum):
    """User role enum"""
    CLIENT = "client"
    ADVISOR = "advisor"


class User(Base):
    """User model - stores authentication and profile info"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.CLIENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    
    # For advisors: clients they manage
    clients_managed = relationship(
        "ClientAdvisor",
        foreign_keys="ClientAdvisor.advisor_id",
        back_populates="advisor",
        cascade="all, delete-orphan"
    )
    
    # For clients: their advisors
    advisors = relationship(
        "ClientAdvisor",
        foreign_keys="ClientAdvisor.client_id",
        back_populates="client",
        cascade="all, delete-orphan"
    )


class Portfolio(Base):
    """Portfolio model - contains user's portfolio metadata"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), default="My Portfolio")
    total_value = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    """Holding model - individual stocks/assets in a portfolio"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    
    # Stock information
    symbol = Column(String(20), nullable=False, index=True)
    description = Column(String(255))
    quantity = Column(Float, default=0.0)
    
    # Pricing
    price = Column(Float, default=0.0)
    cost_basis = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    
    # Performance
    total_return_pct = Column(Float, default=0.0)
    gain_loss = Column(Float, default=0.0)
    gain_loss_pct = Column(Float, default=0.0)
    
    # Allocation
    weight = Column(Float, default=0.0)  # Percentage of portfolio
    
    # Additional data
    sector = Column(String(100))
    asset_type = Column(String(100))
    asset_category = Column(String(100))
    
    # Dividends
    est_annual_income = Column(Float, default=0.0)
    dividend_yield = Column(Float, default=0.0)
    
    # Daily changes
    daily_change_value = Column(Float, default=0.0)
    daily_change_pct = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")


class ClientAdvisor(Base):
    """Client-Advisor relationship model"""
    __tablename__ = "client_advisor"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="advisors")
    advisor = relationship("User", foreign_keys=[advisor_id], back_populates="clients_managed")


class Goal(Base):
    """User financial goals"""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    target_value = Column(Float, nullable=False)
    target_date = Column(DateTime(timezone=True))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="goals")


class Report(Base):
    """Generated reports"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_url = Column(String(500))
    report_type = Column(String(50))  # e.g., "monthly", "quarterly", "custom"
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="reports")
