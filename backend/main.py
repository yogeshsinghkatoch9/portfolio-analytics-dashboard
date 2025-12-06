"""
Portfolio Visualization Platform - Backend API
FastAPI server for processing portfolio CSV/Excel files and generating analytics
Version 2.0.0 - Production Ready
"""

# ========================================
# IMPORTS
# ========================================

# Standard library
import os
import io
import json
import logging
import traceback
import tempfile
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager
from functools import lru_cache

# Third-party core
import pandas as pd
import numpy as np
import yfinance as yf

# FastAPI
from fastapi import (
    FastAPI, HTTPException, Depends, Request, Response,
    UploadFile, File, Form, Query, Path, Body, status, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm

# Pydantic
from pydantic import BaseModel, EmailStr, Field, validator

# SQLAlchemy
from sqlalchemy.orm import Session

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Internal modules
import analytics
import data_import
import market_data
import db as db_module
import portfolio_api
import wealth_api
import watchlist_api
import news_api
import ai_api
import goals_api
import reports_api
import export_api
# Authentication
import auth
from auth import get_current_active_user, get_current_user, get_optional_user
import monte_carlo_api

from ai_service import AIService
from benchmark import BenchmarkService
from latex_generator import LatexReportGenerator


# ========================================
# LOGGING CONFIGURATION
# ========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========================================
# AUTHENTICATION MODULE IMPORTS (OPTIONAL)
# ========================================

AUTH_ENABLED = False
try:
    from db import get_db, engine, Base
    from models import User, Portfolio, Holding, UserRole
    from auth import (
        get_password_hash,
        verify_password,
        create_access_token,
        get_current_user,
        get_current_active_user,
        require_role
    )
    AUTH_ENABLED = True
    logger.info("✅ Authentication modules loaded")
except ImportError as e:
    logger.warning(f"⚠️  Auth modules not available: {e}")


# ========================================
# CONSTANTS
# ========================================

CACHE_TTL = 300  # 5 minutes cache TTL
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size

# Expected CSV columns
EXPECTED_COLUMNS = [
    'Description', 'Symbol', 'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
    '1-Day Value Change ($)', '1-Day Price Change (%)', 'Account Type',
    'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
    'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
    'Asset Type', 'Asset Category', 'Est Annual Income ($)',
    'Current Yld/Dist Rate (%)', 'Dividend Instructions',
    'Cap Gain Instructions', 'Initial Purchase Date', 'Est Tax G/L ($)*'
]

# Cache for quotes
quote_cache = {}


# ========================================
# PYDANTIC MODELS
# ========================================

class UserRegister(BaseModel):
    """User registration model"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field("client", pattern="^(client|advisor)$")


class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    full_name: Optional[str]
    role: str
    
    class Config:
        from_attributes = True


class HoldingInput(BaseModel):
    """Portfolio holding input"""
    symbol: str = Field(..., min_length=1, max_length=10)
    weight: float = Field(..., gt=0, le=100)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper().strip()


class SimulationRequest(BaseModel):
    """Monte Carlo simulation request"""
    holdings: List[HoldingInput]
    current_portfolio_file: Optional[str] = None


class ProposalRequest(BaseModel):
    """Portfolio proposal request"""
    current_holdings: List[HoldingInput]
    proposed_holdings: List[HoldingInput]
    client_name: str = Field("Valued Client", max_length=100)
    advisor_name: str = Field("Advisor", max_length=100)


class BatchQuotesRequest(BaseModel):
    """Batch quotes request"""
    tickers: List[str] = Field(..., min_items=1, max_items=50)
    use_cache: bool = True
    
    @validator('tickers')
    def validate_tickers(cls, v):
        return [t.upper().strip() for t in v if t.strip()]


class RetirementPlanRequest(BaseModel):
    """Retirement planning request"""
    portfolio_id: int = Field(..., gt=0)
    years: int = Field(30, ge=1, le=50)
    monthly_contribution: float = Field(0, ge=0)
    inflation_rate: float = Field(0.025, ge=0, le=0.1)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]


class PortfolioUploadResponse(BaseModel):
    """Portfolio upload response"""
    success: bool
    filename: str
    summary: Dict[str, Any]
    charts: Dict[str, Any]
    holdings: List[Dict[str, Any]]
    metadata: Dict[str, Any]


# ========================================
# LIFESPAN CONTEXT MANAGER
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.
    
    Handles startup and shutdown tasks including:
    - Database initialization
    - Cache warmup
    - Resource cleanup
    """
    # ========== STARTUP ==========
    logger.info("🚀 Starting VisionWealth API v2.0.0...")
    
    # Initialize legacy database
    try:
        db_module.init_db()
        logger.info("✅ Legacy database initialized")
    except Exception as e:
        logger.warning(f"⚠️  Legacy database initialization skipped: {e}")
    
    # Initialize auth database
    if AUTH_ENABLED:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Auth database tables created")
        except Exception as e:
            logger.error(f"❌ Auth database initialization failed: {e}")
    
    # Clear old cache entries
    try:
        quote_cache.clear()
        logger.info("✅ Cache cleared")
    except Exception as e:
        logger.warning(f"⚠️  Cache clear failed: {e}")
    
    logger.info("✅ Application startup complete")
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("🛑 Shutting down VisionWealth API...")
    
    # Cleanup tasks
    try:
        quote_cache.clear()
        logger.info("✅ Cache cleared on shutdown")
    except Exception as e:
        logger.warning(f"⚠️  Shutdown cleanup failed: {e}")
    
    logger.info("✅ Shutdown complete")


# ========================================
# APP INITIALIZATION
# ========================================

app = FastAPI(
    title="VisionWealth Portfolio Analytics API",
    version="2.0.0",
    description="""
    Comprehensive portfolio analysis and management platform with:
    - Portfolio upload and analysis
    - Real-time market data
    - Advanced analytics and risk metrics
    - AI-powered insights
    - Monte Carlo simulations
    - Report generation
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "VisionWealth Support",
        "email": "support@visionwealth.com"
    },
    license_info={
        "name": "Proprietary"
    }
)


# ========================================
# MIDDLEWARE
# ========================================

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://portfolio-analytics-dashboard-seven.vercel.app",
        "https://portfolio-analytics-dashboard-fqbxmihus.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all HTTP requests with timing information.
    
    Captures:
    - Request method and path
    - Response status code
    - Request duration
    """
    start_time = datetime.now()
    
    try:
        response = await call_next(request)
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        
        return response
    
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"{request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Duration: {duration:.3f}s"
        )
        raise


# ========================================
# RATE LIMITING
# ========================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute", "1000/hour"],
    storage_uri="memory://"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ========================================
# EXCEPTION HANDLERS
# ========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions with detailed logging and user-friendly responses.
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail} - "
        f"Path: {request.url.path} - "
        f"Method: {request.method} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat(),
            "request_id": id(request)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unhandled errors.
    
    Logs full traceback but returns sanitized error to client.
    """
    error_id = id(exc)
    
    logger.error(
        f"Unhandled exception (ID: {error_id}): {exc}\n"
        f"Path: {request.url.path}\n"
        f"Method: {request.method}\n"
        f"Client: {request.client.host if request.client else 'unknown'}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )
    
    # Don't expose internal errors in production
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "message": "An unexpected error occurred. Please try again later.",
            "error_id": str(error_id),
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )


# ========================================
# API ROUTER REGISTRATION
# ========================================

# Register all API routers with appropriate prefixes and tags
app.include_router(
    portfolio_api.router,
    prefix='/api/v2',
    tags=["Portfolio Management"]
)

app.include_router(
    wealth_api.router,
    prefix='/api/v2',
    tags=["Wealth Analytics"]
)

app.include_router(
    watchlist_api.router,
    prefix='/api/v2',
    tags=["Watchlist"]
)

app.include_router(
    news_api.router,
    prefix='/api/v2',
    tags=["Market News"]
)

app.include_router(
    ai_api.router,
    prefix='/api/v2',
    tags=["AI Insights"]
)

app.include_router(
    goals_api.router,
    prefix='/api/v2',
    tags=["Financial Goals"]
)

app.include_router(
    reports_api.router,
    prefix='/api/v2',
    tags=["Reports"]
)

app.include_router(
    export_api.router,
    prefix='/api/v2',
    tags=["Export"]
)

app.include_router(
    monte_carlo_api.router,
    prefix='/api/v2',
    tags=["Monte Carlo Simulations"]
)

logger.info("✅ All API routers registered")


# ========================================
# UTILITY FUNCTIONS
# ========================================

def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy types to Python native types for JSON serialization.
    
    Args:
        obj: Object that may contain numpy types
    
    Returns:
        Object with numpy types converted to Python native types
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif pd.isna(obj):
        return None
    else:
        return obj


def clean_numeric_value(value: Any) -> float:
    """
    Convert any value to float, handling NaN, None, and invalid values.
    
    Args:
        value: Value to convert
    
    Returns:
        Float value or 0.0 if conversion fails
    """
    if pd.isna(value) or value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def parse_portfolio_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """
    Parse CSV or Excel file and validate structure.
    
    Args:
        file_content: Raw file bytes
        filename: Original filename
    
    Returns:
        Parsed DataFrame
    
    Raises:
        HTTPException: If file format is invalid or parsing fails
    """
    try:
        # Determine file type and read
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError("File must be CSV or Excel format (.csv, .xlsx, .xls)")
        
        # Normalize column names
        df.columns = df.columns.str.strip()
        
        # Validate critical columns exist
        critical_columns = ['Symbol', 'Quantity']
        missing_critical = [col for col in critical_columns if col not in df.columns]
        
        if missing_critical:
            raise ValueError(
                f"Missing critical columns: {', '.join(missing_critical)}. "
                f"File must at least have 'Symbol' and 'Quantity' columns."
            )
        
        logger.info(
            f"Successfully parsed file: {filename} "
            f"({len(df)} rows, {len(df.columns)} columns)"
        )
        
        return df
    
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="File is empty")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected file parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")


def clean_portfolio_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize portfolio data.
    
    - Removes invalid rows
    - Ensures required columns exist
    - Converts data types
    - Fetches missing prices if needed
    
    Args:
        df: Raw portfolio DataFrame
    
    Returns:
        Cleaned DataFrame
    """
    # Remove rows where Symbol is NaN
    df = df[df['Symbol'].notna()].copy()
    
    # Ensure standard columns exist with defaults
    default_columns = {
        'Description': '',
        'Asset Type': 'Stock',
        'Asset Category': '',
        'Price ($)': 0.0,
        'Value ($)': 0.0
    }
    
    for col, default_value in default_columns.items():
        if col not in df.columns:
            df[col] = default_value
    
    # Set Asset Category from Asset Type if missing
    if 'Asset Category' not in df.columns or df['Asset Category'].isna().all():
        df['Asset Category'] = df['Asset Type']
    
    # Define all numeric columns
    numeric_columns = [
        'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
        '1-Day Value Change ($)', '1-Day Price Change (%)',
        'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
        'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
        'Est Annual Income ($)', 'Current Yld/Dist Rate (%)', 'Est Tax G/L ($)*'
    ]
    
    # Ensure numeric columns exist and clean them
    for col in numeric_columns:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].apply(clean_numeric_value)
    
    # Fetch missing prices for symbols (limited to prevent long waits)
    rows_needing_price = df[(df['Price ($)'] == 0) & (df['Symbol'].str.len() > 0)]
    
    if not rows_needing_price.empty:
        symbols = rows_needing_price['Symbol'].unique().tolist()
        symbols = [s for s in symbols if isinstance(s, str) and len(s) > 0]
        
        if symbols and len(symbols) <= 50:
            logger.info(f"Fetching prices for {len(symbols)} symbols...")
            
            try:
                for sym in symbols[:50]:  # Limit to 50 to prevent timeout
                    try:
                        ticker = yf.Ticker(sym)
                        info = ticker.info
                        price = info.get('regularMarketPrice', 
                                       info.get('currentPrice', 
                                       info.get('previousClose', 0.0)))
                        
                        if price and price > 0:
                            df.loc[df['Symbol'] == sym, 'Price ($)'] = float(price)
                            logger.debug(f"Fetched price for {sym}: ${price}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch price for {sym}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Batch price fetch failed: {e}")
    
    # Compute missing Values (Value = Quantity × Price)
    mask = (df['Value ($)'] == 0) & (df['Quantity'] > 0) & (df['Price ($)'] > 0)
    df.loc[mask, 'Value ($)'] = df.loc[mask, 'Quantity'] * df.loc[mask, 'Price ($)']
    
    # Compute missing Assets %
    total_value = df['Value ($)'].sum()
    if total_value > 0:
        mask = df['Assets (%)'] == 0
        df.loc[mask, 'Assets (%)'] = (df.loc[mask, 'Value ($)'] / total_value * 100)
    
    logger.info(f"Cleaned portfolio data: {len(df)} holdings")
    
    return df


def compute_summary_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute portfolio-wide summary metrics.
    
    Args:
        df: Portfolio DataFrame
    
    Returns:
        Dictionary with summary metrics
    """
    total_value = df['Value ($)'].sum()
    total_principal = df['Principal ($)*'].sum()
    total_gain_loss = df['NFS G/L ($)'].sum()
    total_daily_change = df['1-Day Value Change ($)'].sum()
    total_annual_income = df['Est Annual Income ($)'].sum()
    
    # Calculate percentages
    overall_return_pct = (
        (total_gain_loss / total_principal * 100) 
        if total_principal > 0 else 0
    )
    
    avg_yield = (
        (total_annual_income / total_value * 100) 
        if total_value > 0 else 0
    )
    
    daily_return_pct = (
        (total_daily_change / total_value * 100) 
        if total_value > 0 else 0
    )
    
    # Get top gainers and losers
    top_gainers = df.nlargest(5, 'NFS G/L ($)')[
        ['Symbol', 'Description', 'NFS G/L ($)', 'NFS G/L (%)']
    ].to_dict('records')
    
    top_losers = df.nsmallest(5, 'NFS G/L ($)')[
        ['Symbol', 'Description', 'NFS G/L ($)', 'NFS G/L (%)']
    ].to_dict('records')
    
    return {
        'total_value': round(total_value, 2),
        'total_principal': round(total_principal, 2),
        'total_gain_loss': round(total_gain_loss, 2),
        'overall_return_pct': round(overall_return_pct, 2),
        'total_return_pct': round(overall_return_pct, 2),
        'total_daily_change': round(total_daily_change, 2),
        'daily_return_pct': round(daily_return_pct, 2),
        'total_annual_income': round(total_annual_income, 2),
        'avg_yield': round(avg_yield, 2),
        'num_holdings': len(df),
        'top_gainers': convert_numpy_types(top_gainers),
        'top_losers': convert_numpy_types(top_losers)
    }


def generate_chart_data(df: pd.DataFrame, fast_mode: bool = False) -> Dict[str, Any]:
    """
    Generate data structures for all dashboard charts.
    
    Args:
        df: Portfolio DataFrame
        fast_mode: Skip expensive operations for large portfolios (>50 holdings)
    
    Returns:
        Dictionary containing data for various chart types
    """
    # Limit to top N for performance
    top_n = 10 if fast_mode else 15
    
    try:
        # 1. Portfolio Allocation by Symbol (Pie Chart)
        allocation_by_symbol = df[df['Value ($)'] > 0].nlargest(10, 'Value ($)')[
            ['Symbol', 'Value ($)', 'Assets (%)']
        ].to_dict('records')
        
        # Add "Other" category for remaining holdings
        other_symbols = df[~df['Symbol'].isin([x['Symbol'] for x in allocation_by_symbol])]
        other_value = other_symbols['Value ($)'].sum()
        
        if other_value > 0:
            total_value = df['Value ($)'].sum()
            allocation_by_symbol.append({
                'Symbol': 'Other',
                'Value ($)': round(other_value, 2),
                'Assets (%)': round(other_value / total_value * 100, 2) if total_value > 0 else 0
            })
        
        # 2. Allocation by Asset Type (Pie Chart)
        allocation_by_type = df.groupby('Asset Type').agg({
            'Value ($)': 'sum',
            'Assets (%)': 'sum'
        }).reset_index()
        
        allocation_by_type['Value ($)'] = allocation_by_type['Value ($)'].round(2)
        allocation_by_type['Assets (%)'] = allocation_by_type['Assets (%)'].round(2)
        allocation_by_type_list = allocation_by_type.to_dict('records')
        
        # 3. Allocation by Asset Category (Pie Chart)
        allocation_by_category = df.groupby('Asset Category').agg({
            'Value ($)': 'sum',
            'Assets (%)': 'sum'
        }).reset_index()
        
        allocation_by_category['Value ($)'] = allocation_by_category['Value ($)'].round(2)
        allocation_by_category['Assets (%)'] = allocation_by_category['Assets (%)'].round(2)
        allocation_by_category_list = allocation_by_category.to_dict('records')
        
        # 4. Gain/Loss by Symbol (Bar Chart) - Top N
        gain_loss_by_symbol = df.nlargest(top_n, 'NFS G/L ($)', keep='all')[
            ['Symbol', 'NFS G/L ($)', 'NFS G/L (%)']
        ].copy()
        
        gain_loss_by_symbol['NFS G/L ($)'] = gain_loss_by_symbol['NFS G/L ($)'].round(2)
        gain_loss_by_symbol['NFS G/L (%)'] = gain_loss_by_symbol['NFS G/L (%)'].round(2)
        gain_loss_list = gain_loss_by_symbol.to_dict('records')
        
        # 5. Daily Movement by Symbol (Bar Chart) - Top N absolute changes
        daily_movement = []
        if not fast_mode or '1-Day Value Change ($)' in df.columns:
            df_daily = df.copy()
            df_daily['abs_daily_change'] = df_daily['1-Day Value Change ($)'].abs()
            
            daily_movement_df = df_daily.nlargest(top_n, 'abs_daily_change')[
                ['Symbol', '1-Day Value Change ($)', '1-Day Price Change (%)']
            ].copy()
            
            daily_movement_df['1-Day Value Change ($)'] = daily_movement_df['1-Day Value Change ($)'].round(2)
            daily_movement_df['1-Day Price Change (%)'] = daily_movement_df['1-Day Price Change (%)'].round(2)
            daily_movement = daily_movement_df.to_dict('records')
        
        # 6. Yield Distribution (Bar Chart) - Top yielding stocks
        yield_distribution = df[df['Current Yld/Dist Rate (%)'] > 0].nlargest(
            top_n, 'Current Yld/Dist Rate (%)'
        )[['Symbol', 'Current Yld/Dist Rate (%)', 'Est Annual Income ($)']].copy()
        
        yield_distribution['Current Yld/Dist Rate (%)'] = yield_distribution['Current Yld/Dist Rate (%)'].round(2)
        yield_distribution['Est Annual Income ($)'] = yield_distribution['Est Annual Income ($)'].round(2)
        yield_list = yield_distribution.to_dict('records')
        
        # 7. Benchmark Comparison (S&P 500)
        benchmark_data = {}
        try:
            benchmark_data = BenchmarkService.get_sp500_data(period="1y")
        except Exception as e:
            logger.warning(f"Failed to fetch benchmark data: {e}")
            benchmark_data = {
                'symbol': 'SPY',
                'error': 'Failed to fetch benchmark data'
            }
        
        result = {
            'allocation_by_symbol': allocation_by_symbol,
            'allocation_by_type': allocation_by_type_list,
            'allocation_by_category': allocation_by_category_list,
            'gain_loss_by_symbol': gain_loss_list,
            'daily_movement': daily_movement,
            'yield_distribution': yield_list,
            'benchmark_comparison': benchmark_data
        }
        
        # Convert all numpy types
        result = convert_numpy_types(result)
        
        logger.info(f"Generated chart data (fast_mode={fast_mode})")
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating chart data: {e}")
        # Return empty structure on error
        return {
            'allocation_by_symbol': [],
            'allocation_by_type': [],
            'allocation_by_category': [],
            'gain_loss_by_symbol': [],
            'daily_movement': [],
            'yield_distribution': [],
            'benchmark_comparison': {}
        }


def prepare_holdings_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Prepare holdings data for display table.
    
    Args:
        df: Portfolio DataFrame
    
    Returns:
        List of holdings as dictionaries
    """
    try:
        # Select columns for display (in order)
        display_columns = [
            'Symbol', 'Description', 'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
            'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
            'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
            '1-Day Value Change ($)', '1-Day Price Change (%)',
            'Asset Type', 'Asset Category',
            'Est Annual Income ($)', 'Current Yld/Dist Rate (%)',
            'Initial Purchase Date'
        ]
        
        # Filter to only existing columns
        available_columns = [col for col in display_columns if col in df.columns]
        
        # Create holdings copy
        holdings = df[available_columns].copy()
        
        # Format date column if exists
        if 'Initial Purchase Date' in holdings.columns:
            holdings['Initial Purchase Date'] = holdings['Initial Purchase Date'].apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) and hasattr(x, 'strftime') else ''
            )
        
        # Round numeric columns to 2 decimal places
        for col in holdings.columns:
            if holdings[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                holdings[col] = holdings[col].round(2)
        
        # Convert to records
        holdings_list = holdings.to_dict('records')
        
        # Convert numpy types
        holdings_list = convert_numpy_types(holdings_list)
        
        logger.info(f"Prepared holdings table: {len(holdings_list)} rows")
        
        return holdings_list
    
    except Exception as e:
        logger.error(f"Error preparing holdings table: {e}")
        return []


# ========================================
# AUTHENTICATION ENDPOINTS
# ========================================

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    **Requirements**:
    - Valid email address
    - Password minimum 8 characters
    - Role must be 'client' or 'advisor'
    
    **Returns**:
    - User information (without password)
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not configured"
        )
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            role=UserRole(user_data.role)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {user_data.email} (role: {user_data.role})")
        
        return new_user
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again."
        )


@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login and receive JWT access token.
    
    **Returns**:
    - JWT access token
    - Token type (bearer)
    
    **Token Usage**:
    Include in subsequent requests as:
    `Authorization: Bearer <token>`
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not configured"
        )
    
    try:
        # Find user
        user = db.query(User).filter(User.email == user_data.email).first()
        
        # Verify credentials
        if not user or not verify_password(user_data.password, user.password_hash):
            logger.warning(f"Failed login attempt for: {user_data.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        
        logger.info(f"User logged in: {user_data.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Login failed. Please try again."
        )


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.
    
    **Requires**: Valid JWT token
    
    **Returns**:
    - User profile information
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not configured"
        )
    
    return current_user


@app.post("/auth/logout", tags=["Authentication"])
async def logout():
    """
    Logout endpoint.
    
    **Note**: JWT tokens are stateless, so logout is handled client-side
    by removing the token from storage.
    
    **Returns**:
    - Success message
    """
    return {
        "success": True,
        "message": "Logged out successfully. Please remove token from client storage."
    }


@app.post("/auth/refresh", response_model=Token, tags=["Authentication"])
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh JWT access token.
    
    **Requires**: Valid (but possibly expiring soon) JWT token
    
    **Returns**:
    - New JWT access token
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not configured"
        )
    
    try:
        # Create new access token
        access_token = create_access_token(data={"sub": current_user.email})
        
        logger.info(f"Token refreshed for user: {current_user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Token refresh failed"
        )


# ========================================
# STATIC FILES
# ========================================

# Serve frontend static files if available
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    logger.info(f"✅ Static files mounted from: {frontend_dir}")


# ========================================
# CORE ENDPOINTS
# ========================================

@app.get("/", response_class=HTMLResponse, tags=["General"])
async def serve_index():
    """
    Serve the main application or API documentation.
    
    If frontend is available, serves the HTML interface.
    Otherwise, returns API documentation links.
    """
    index_file = os.path.join(frontend_dir, "index.html") if os.path.exists(frontend_dir) else None
    
    if index_file and os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    
    # Return API info page
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VisionWealth API v2.0.0</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    line-height: 1.6;
                    color: #333;
                }
                h1 { color: #2563eb; }
                .endpoint { 
                    background: #f8fafc;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    border-left: 4px solid #2563eb;
                }
                a { color: #2563eb; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .badge {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 8px;
                }
                .badge-success { background: #10b981; color: white; }
                .badge-info { background: #06b6d4; color: white; }
            </style>
        </head>
        <body>
            <h1>🚀 VisionWealth Portfolio Analytics API</h1>
            <p><span class="badge badge-success">v2.0.0</span> <span class="badge badge-info">PRODUCTION</span></p>
            
            <h2>📚 Documentation</h2>
            <div class="endpoint">
                <strong>Interactive API Docs (Swagger UI):</strong><br>
                <a href="/docs">/docs</a>
            </div>
            <div class="endpoint">
                <strong>Alternative Documentation (ReDoc):</strong><br>
                <a href="/redoc">/redoc</a>
            </div>
            
            <h2>🔌 API Endpoints</h2>
            <div class="endpoint">
                <strong>Health Check:</strong> <a href="/health">GET /health</a>
            </div>
            <div class="endpoint">
                <strong>Portfolio Upload:</strong> POST /upload-portfolio
            </div>
            <div class="endpoint">
                <strong>Portfolio Management:</strong> /api/v2/portfolio/*
            </div>
            <div class="endpoint">
                <strong>Market Data:</strong> /api/v2/market/*
            </div>
            <div class="endpoint">
                <strong>Analytics:</strong> /api/v2/analytics/*
            </div>
            
            <h2>🔐 Authentication</h2>
            <p>Authentication status: <strong>""" + ("ENABLED" if AUTH_ENABLED else "DISABLED") + """</strong></p>
            """ + ("""
            <div class="endpoint">
                <strong>Register:</strong> POST /auth/register<br>
                <strong>Login:</strong> POST /auth/login<br>
                <strong>Current User:</strong> GET /auth/me
            </div>
            """ if AUTH_ENABLED else """
            <p><em>Enable authentication by configuring the database and auth modules.</em></p>
            """) + """
            
            <h2>📞 Support</h2>
            <p>For support and documentation, visit the <a href="/docs">API documentation</a>.</p>
            
            <hr>
            <p style="color: #64748b; font-size: 14px;">
                © 2024 VisionWealth Platform | Powered by FastAPI
            </p>
        </body>
        </html>
        """,
        status_code=200
    )


@app.get("/health", response_model=HealthResponse, tags=["General"])
@limiter.limit("30/minute")
async def health_check(request: Request):
    """
    Comprehensive health check endpoint.
    
    Checks:
    - API availability
    - Database connectivity
    - Authentication system status
    - External service availability
    
    **Returns**:
    - Overall status (healthy/degraded/unhealthy)
    - Individual service statuses
    - Version information
    - Timestamp
    """
    services = {
        "api": "healthy",
        "database": "unknown",
        "auth": "disabled" if not AUTH_ENABLED else "enabled",
        "analytics": "available",
        "market_data": "available",
        "ai_service": "available"
    }
    
    overall_status = "healthy"
    
    # Check database connectivity
    try:
        session = next(db_module.get_session())
        session.execute("SELECT 1")
        services["database"] = "healthy"
        session.close()
        logger.debug("Database health check: PASSED")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = "unhealthy"
        overall_status = "degraded"
    
    # Check auth database if enabled
    if AUTH_ENABLED:
        try:
            db_session = next(get_db())
            db_session.execute("SELECT 1")
            services["auth"] = "healthy"
            db_session.close()
            logger.debug("Auth database health check: PASSED")
        except Exception as e:
            logger.error(f"Auth database health check failed: {e}")
            services["auth"] = "unhealthy"
            overall_status = "degraded"
    
    # Check market data service
    try:
        client = market_data.get_client()
        # Quick test - just check if client exists
        if client:
            services["market_data"] = "healthy"
    except Exception as e:
        logger.warning(f"Market data service check failed: {e}")
        services["market_data"] = "degraded"
    
    return HealthResponse(
        status=overall_status,
        version="2.0.0",
        timestamp=datetime.now().isoformat(),
        services=services
    )


@app.get("/api/info", tags=["General"])
async def api_info():
    """
    Get API information and capabilities.
    
    **Returns**:
    - Version information
    - Available features
    - Endpoint statistics
    - System capabilities
    """
    return {
        "api_name": "VisionWealth Portfolio Analytics API",
        "version": "2.0.0",
        "description": "Comprehensive portfolio analysis and management platform",
        "features": {
            "portfolio_upload": True,
            "real_time_market_data": True,
            "advanced_analytics": True,
            "ai_insights": True,
            "monte_carlo_simulations": True,
            "report_generation": True,
            "authentication": AUTH_ENABLED,
            "multi_user": AUTH_ENABLED
        },
        "supported_file_formats": [".csv", ".xlsx", ".xls"],
        "supported_brokerages": [
            "Charles Schwab",
            "Fidelity",
            "Vanguard",
            "Generic CSV/Excel"
        ],
        "rate_limits": {
            "default": "100 requests/minute, 1000 requests/hour",
            "authenticated": "Varies by endpoint"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "timestamp": datetime.now().isoformat()
    }


# ========================================
# PORTFOLIO UPLOAD & ANALYSIS
# ========================================

@app.post("/upload-portfolio", tags=["Portfolio Upload"])
@limiter.limit("10/minute")
async def upload_portfolio(
    request: Request,
    file: UploadFile = File(
        ...,
        description="Portfolio CSV or Excel file"
    )
):
    """
    Upload and process portfolio CSV/Excel file.
    
    **Features**:
    - Automatic file format detection
    - Smart column mapping
    - Missing data enrichment (prices, calculations)
    - Comprehensive analytics
    - Fast mode for large portfolios (>50 holdings)
    
    **Supported Formats**:
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    
    **Returns**:
    - Summary metrics (total value, gains/losses, returns)
    - Chart data (allocations, performance, yields)
    - Holdings table (detailed position information)
    - Metadata (file info, processing stats)
    """
    try:
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Read file content
        content = await file.read()
        
        logger.info(
            f"Processing portfolio upload: {file.filename} "
            f"({file_size / 1024:.2f} KB)"
        )
        
        # Try smart importer first (better format detection)
        importer = data_import.PortfolioImporter()
        import_result = importer.import_file(content, file.filename)
        
        if import_result.get('success') and import_result.get('dataframe') is not None:
            df = import_result['dataframe']
            logger.info("Used smart importer for file processing")
        else:
            # Fallback to basic parser
            df = parse_portfolio_file(content, file.filename)
            df = clean_portfolio_data(df)
            logger.info("Used basic parser for file processing")
        
        # Validate data
        if len(df) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid holdings found in file. Please check file format."
            )
        
        # Determine if we should use fast mode
        use_fast_mode = len(df) > 50
        
        if use_fast_mode:
            logger.info(f"Using fast mode for {len(df)} holdings")
        
        # Compute metrics
        start_time = datetime.now()
        
        summary = compute_summary_metrics(df)
        charts = generate_chart_data(df, fast_mode=use_fast_mode)
        holdings = prepare_holdings_table(df)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Build response
        response_data = {
            "success": True,
            "filename": file.filename,
            "summary": summary,
            "charts": charts,
            "holdings": holdings,
            "metadata": {
                "total_holdings": len(df),
                "file_size_kb": round(file_size / 1024, 2),
                "processing_time_seconds": round(processing_time, 3),
                "fast_mode": use_fast_mode,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Convert numpy types
        response_data = convert_numpy_types(response_data)
        
        logger.info(
            f"Successfully processed portfolio: {file.filename} "
            f"({len(df)} holdings in {processing_time:.2f}s)"
        )
        
        return JSONResponse(response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Portfolio upload error: {e}\n"
            f"File: {file.filename}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )


# Continue the file in the next message due to length constraints...
# This establishes the foundation with ~2000 lines
# The complete file will be split into two parts


# ========================================
# MARKET DATA ENDPOINTS  
# ========================================

@app.get("/api/market/quote/{ticker}", tags=["Market Data"])
@limiter.limit("30/minute")
async def get_realtime_quote(
    request: Request,  # Required by slowapi rate limiter
    ticker: str = Path(..., description="Stock ticker symbol")
):
    """Fetch real-time quote for a single stock ticker."""
    try:
        ticker = ticker.upper().strip()
        
        # Check cache first (5 minute cache)
        cache_key = f"{ticker}_{datetime.now().strftime('%Y%m%d%H%M')}"
        
        if cache_key in quote_cache:
            logger.debug(f"Cache hit for quote: {ticker}")
            return quote_cache[cache_key]
        
        # Fetch from market data service
        try:
            client = market_data.get_client()
            quote = client.get_quote(ticker)
            
            if hasattr(quote, 'status') and quote.status == 'error':
                raise HTTPException(
                    status_code=404,
                    detail=f"Failed to fetch data for {ticker}"
                )
            
            # Convert to dict if needed
            quote_data = quote.to_dict() if hasattr(quote, 'to_dict') else quote
            
        except Exception as e:
            logger.warning(f"Market data service failed, trying yfinance: {e}")
            
            # Fallback to yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            
            quote_data = {
                'symbol': ticker,
                'price': info.get('regularMarketPrice', info.get('currentPrice', 0)),
                'change': info.get('regularMarketChange', 0),
                'change_percent': info.get('regularMarketChangePercent', 0),
                'volume': info.get('regularMarketVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'timestamp': datetime.now().isoformat()
            }
        
        # Cache the result
        quote_cache[cache_key] = quote_data
        
        logger.info(f"Fetched quote for {ticker}: ${quote_data.get('price', 0)}")
        
        return quote_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch quote for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch quote for {ticker}: {str(e)}"
        )


@app.post("/api/market/quotes", tags=["Market Data"])
@limiter.limit("20/minute")
async def get_batch_quotes(
    request: Request,
    tickers: List[str] = Body(..., description="List of ticker symbols")
):
    """Fetch real-time quotes for multiple tickers in one request."""
    try:
        # Validate and clean tickers
        tickers = [t.upper().strip() for t in tickers if t.strip()]
        
        if len(tickers) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid tickers provided"
            )
        
        if len(tickers) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 tickers per request"
            )
        
        logger.info(f"Fetching batch quotes for {len(tickers)} tickers")
        
        quotes = {}
        
        # Try market data service first
        try:
            client = market_data.get_client()
            quotes_result = client.get_quotes_batch(tickers, use_cache=True)
            
            # Convert Quote objects to dicts
            for ticker, quote in quotes_result.items():
                if hasattr(quote, 'to_dict'):
                    quotes[ticker] = quote.to_dict()
                else:
                    quotes[ticker] = quote
        
        except Exception as e:
            logger.warning(f"Batch quotes via market data failed, using fallback: {e}")
            
            # Fallback: fetch individually
            for ticker in tickers:
                try:
                    cache_key = f"{ticker}_{datetime.now().strftime('%Y%m%d%H%M')}"
                    
                    if cache_key in quote_cache:
                        quotes[ticker] = quote_cache[cache_key]
                    else:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        
                        quote_data = {
                            'symbol': ticker,
                            'price': info.get('regularMarketPrice', info.get('currentPrice', 0)),
                            'change': info.get('regularMarketChange', 0),
                            'change_percent': info.get('regularMarketChangePercent', 0),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        quote_cache[cache_key] = quote_data
                        quotes[ticker] = quote_data
                
                except Exception as ticker_error:
                    logger.warning(f"Failed to fetch {ticker}: {ticker_error}")
                    quotes[ticker] = {'error': str(ticker_error)}
        
        return {
            'success': True,
            'quotes': quotes,
            'count': len(quotes),
            'timestamp': datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch quote fetch failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch quote fetch failed: {str(e)}"
        )


@app.get("/api/market/search", tags=["Market Data"])
@limiter.limit("20/minute")
async def search_ticker(
    request: Request,
    q: str = Query(..., description="Search query (ticker or company name)", min_length=1)
):
    """Search for ticker by symbol or company name."""
    try:
        query = q.strip()
        
        if len(query) < 1:
            raise HTTPException(
                status_code=400,
                detail="Search query must be at least 1 character"
            )
        
        logger.info(f"Searching for ticker: {query}")
        
        # Try market data service
        try:
            client = market_data.get_client()
            results = client.search_ticker(query, max_results=10)
        except Exception as e:
            logger.warning(f"Market data search failed, using fallback: {e}")
            
            # Fallback: try direct ticker lookup
            results = []
            try:
                symbol = query.upper()
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info and 'symbol' in info:
                    results.append({
                        'symbol': info.get('symbol'),
                        'name': info.get('longName', info.get('shortName', symbol)),
                        'type': info.get('quoteType', 'Unknown'),
                        'sector': info.get('sector', 'Unknown'),
                        'exchange': info.get('exchange', 'Unknown'),
                        'price': info.get('currentPrice', info.get('regularMarketPrice', 0))
                    })
            except Exception:
                pass
        
        return {
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for query '{q}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ========================================
# PORTFOLIO ANALYSIS ENDPOINTS
# ========================================

@app.post("/api/portfolio/analyze", tags=["Portfolio Analysis"])
@limiter.limit("10/minute")
async def analyze_portfolio(
    request: Request,
    file: UploadFile = File(..., description="Portfolio CSV/Excel file")
):
    """Comprehensive portfolio analysis with advanced metrics."""
    try:
        content = await file.read()
        df = parse_portfolio_file(content, file.filename)
        df = clean_portfolio_data(df)
        
        logger.info(f"Starting comprehensive analysis for {file.filename}")
        
        # Basic metrics
        summary_metrics = compute_summary_metrics(df)
        chart_data = generate_chart_data(df)
        holdings_data = prepare_holdings_table(df)
        
        # Advanced analytics
        analytics_data = {}
        
        try:
            analytics_data['diversification'] = analytics.calculate_diversification_score(df)
        except Exception as e:
            logger.warning(f"Diversification calculation failed: {e}")
            analytics_data['diversification'] = {}
        
        try:
            analytics_data['risk_metrics'] = analytics.calculate_risk_metrics(df)
        except Exception as e:
            logger.warning(f"Risk metrics calculation failed: {e}")
            analytics_data['risk_metrics'] = {}
        
        try:
            analytics_data['sector_allocation'] = analytics.generate_sector_allocation(df)
        except Exception as e:
            logger.warning(f"Sector allocation failed: {e}")
            analytics_data['sector_allocation'] = {}
        
        try:
            analytics_data['dividend_metrics'] = analytics.calculate_dividend_metrics(df)
        except Exception as e:
            logger.warning(f"Dividend metrics failed: {e}")
            analytics_data['dividend_metrics'] = {}
        
        try:
            analytics_data['tax_loss_harvesting'] = analytics.identify_tax_loss_harvesting(df)
        except Exception as e:
            logger.warning(f"Tax loss harvesting failed: {e}")
            analytics_data['tax_loss_harvesting'] = []
        
        try:
            analytics_data['performance_vs_weight'] = analytics.calculate_performance_vs_weight(df)
        except Exception as e:
            logger.warning(f"Performance vs weight failed: {e}")
            analytics_data['performance_vs_weight'] = {}
        
        try:
            analytics_data['advanced_risk'] = analytics.calculate_advanced_risk_analytics(df)
        except Exception as e:
            logger.warning(f"Advanced risk analytics failed: {e}")
            analytics_data['advanced_risk'] = {}
        
        try:
            analytics_data['benchmark_comparison'] = analytics.calculate_benchmark_comparison(
                df, benchmark_ticker='SPY', period='1y'
            )
        except Exception as e:
            logger.warning(f"Benchmark comparison failed: {e}")
            analytics_data['benchmark_comparison'] = {}
        
        try:
            analytics_data['dividend_calendar'] = analytics.calculate_dividend_calendar(df)
        except Exception as e:
            logger.warning(f"Dividend calendar failed: {e}")
            analytics_data['dividend_calendar'] = {}
        
        response = {
            'success': True,
            'filename': file.filename,
            'summary': summary_metrics,
            'charts': chart_data,
            'holdings': holdings_data,
            'analytics': analytics_data
        }
        
        # Convert numpy types
        response = convert_numpy_types(response)
        
        logger.info(f"Successfully analyzed portfolio: {file.filename}")
        
        return JSONResponse(response)
    
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/api/v2/portfolio/{portfolio_id}/analytics", tags=["Portfolio Analysis"])
@limiter.limit("20/minute")
async def get_portfolio_analytics(
    request: Request,
    portfolio_id: int,
    benchmark: str = Query("SPY", description="Benchmark ticker"),
    period: str = Query("1y", description="Analysis period")
):
    """Generate analytics for a saved portfolio from database."""
    try:
        session = next(db_module.get_session())
        p = session.get(db_module.Portfolio, portfolio_id)
        
        if not p:
            raise HTTPException(
                status_code=404,
                detail='Portfolio not found'
            )
        
        # Convert holdings to DataFrame
        rows = []
        for h in p.holdings:
            meta = json.loads(h.meta_json or '{}')
            rows.append({
                'Symbol': h.ticker,
                'Quantity': h.quantity,
                'Price ($)': h.price,
                'Value ($)': h.quantity * h.price,
                'Principal ($)*': h.cost_basis,
                'NFS G/L ($)': (h.quantity * h.price) - h.cost_basis,
                'NFS G/L (%)': (
                    ((h.quantity * h.price) - h.cost_basis) / h.cost_basis * 100
                ) if h.cost_basis > 0 else 0.0,
                'Asset Type': h.asset_type,
                'Asset Category': h.asset_type,
                'Description': meta.get('description', ''),
                'Current Yld/Dist Rate (%)': 0.0,
                'Est Annual Income ($)': 0.0,
                '1-Day Value Change ($)': 0.0,
                '1-Day Price Change (%)': 0.0
            })
        
        if not rows:
            return JSONResponse({
                'success': False,
                'error': 'Empty portfolio'
            })
        
        df = pd.DataFrame(rows)
        
        # Calculate Assets %
        total_val = df['Value ($)'].sum()
        if total_val > 0:
            df['Assets (%)'] = df['Value ($)'] / total_val * 100
        else:
            df['Assets (%)'] = 0
        
        # Calculate analytics
        summary_metrics = compute_summary_metrics(df)
        chart_data = generate_chart_data(df)
        
        analytics_data = {}
        try:
            analytics_data['risk_metrics'] = analytics.calculate_risk_metrics(df)
            analytics_data['advanced_risk'] = analytics.calculate_advanced_risk_analytics(df)
            analytics_data['sector_allocation'] = analytics.generate_sector_allocation(df)
            analytics_data['benchmark_comparison'] = analytics.calculate_benchmark_comparison(
                df, benchmark_ticker=benchmark, period=period
            )
            analytics_data['dividend_calendar'] = analytics.calculate_dividend_calendar(df)
        except Exception as e:
            logger.warning(f"Some analytics failed: {e}")
        
        response = {
            'success': True,
            'summary': summary_metrics,
            'charts': chart_data,
            'analytics': analytics_data
        }
        
        response = convert_numpy_types(response)
        
        return JSONResponse(response)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio analytics error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/api/portfolio/recommendations", tags=["Portfolio Analysis"])
@limiter.limit("5/minute")
async def get_recommendations(
    request: Request,
    file: UploadFile = File(...),
    risk_profile: str = Query("moderate", description="Risk profile: conservative, moderate, aggressive")
):
    """Get portfolio rebalancing and optimization recommendations."""
    try:
        content = await file.read()
        df = parse_portfolio_file(content, file.filename)
        df = clean_portfolio_data(df)
        
        # Validate risk profile
        if risk_profile not in ['conservative', 'moderate', 'aggressive']:
            raise HTTPException(
                status_code=400,
                detail="Risk profile must be: conservative, moderate, or aggressive"
            )
        
        # Generate optimization recommendations
        allocation_optimization = analytics.optimize_asset_allocation(df, risk_profile)
        
        return JSONResponse({
            'success': True,
            'risk_profile': risk_profile,
            'recommendations': convert_numpy_types(allocation_optimization)
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation generation failed: {str(e)}"
        )


# ========================================
# PDF EXPORT ENDPOINT
# ========================================

@app.post("/api/portfolio/export-pdf", tags=["Export"])
@limiter.limit("3/minute")
async def export_portfolio_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    client_name: str = Form(None),
    portfolio_id: Optional[int] = Form(None)
):
    """Generate and download professional PDF portfolio report."""
    try:
        import pdf_generator
        
        logger.info("Starting PDF export")
        
        # Prepare Data (common logic)
        if portfolio_id:
            # Load from database
            session = next(db_module.get_session())
            p = session.get(db_module.Portfolio, portfolio_id)
            
            if not p:
                raise HTTPException(
                    status_code=404,
                    detail='Portfolio not found'
                )
            
            # Build DataFrame from holdings
            rows = []
            for h in p.holdings:
                meta = json.loads(h.meta_json or '{}') if h.meta_json else {}
                rows.append({
                    'Description': meta.get('description', ''),
                    'Symbol': h.ticker,
                    'Quantity': h.quantity,
                    'Price ($)': h.price,
                    'Value ($)': h.quantity * h.price,
                    'Assets (%)': 0,
                    'NFS G/L ($)': 0,
                    'Principal ($)*': h.cost_basis or 0
                })
            
            df = pd.DataFrame(rows)
            client_display_name = client_name or p.name
        
        else:
            if file is None:
                raise HTTPException(
                    status_code=400,
                    detail='Either file or portfolio_id must be provided'
                )
            
            # Read uploaded file
            content = await file.read()
            df = parse_portfolio_file(content, file.filename)
            client_display_name = client_name or 'Portfolio Report'
        
        # Clean data
        df = clean_portfolio_data(df)
        
        # Ensure numeric columns exist
        required_numeric = [
            'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
            '1-Day Value Change ($)', '1-Day Price Change (%)',
            'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
            'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
            'Est Annual Income ($)', 'Current Yld/Dist Rate (%)', 'Est Tax G/L ($)*'
        ]
        
        for col in required_numeric:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Compute metrics
        summary = compute_summary_metrics(df)
        charts = generate_chart_data(df)
        holdings = prepare_holdings_table(df)
        
        portfolio_data = {
            'summary': summary,
            'charts': charts,
            'holdings': holdings
        }
        
        # Analytics
        analytics_data = {}
        try:
            analytics_data['risk_metrics'] = analytics.calculate_risk_metrics(df)
            analytics_data['diversification'] = analytics.calculate_diversification_score(df)
            analytics_data['tax_loss_harvesting'] = analytics.identify_tax_loss_harvesting(df)
            analytics_data['dividend_metrics'] = analytics.calculate_dividend_metrics(df)
        except Exception as e:
            logger.warning(f"Some analytics failed: {e}")
        
        # Generate fallback PDF (always reliable)
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        fallback_pdf_path = temp_pdf.name
        temp_pdf.close()
        
        pdf_generator.generate_portfolio_pdf(
            portfolio_data,
            analytics_data,
            fallback_pdf_path,
            client_name=client_display_name
        )
        
        logger.info("Fallback PDF generated successfully")
        
        # Try LaTeX generation
        latex_gen = LatexReportGenerator()
        success, latex_result, build_dir = latex_gen.generate_report(
            portfolio_data,
            analytics_data,
            "unused.pdf",
            client_name=client_display_name
        )
        
        if success:
            # LaTeX succeeded - return professional PDF
            logger.info("LaTeX compilation successful, returning pro PDF")
            
            # Cleanup fallback and build dir
            try:
                os.unlink(fallback_pdf_path)
                if build_dir:
                    shutil.rmtree(build_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")
            
            return FileResponse(
                latex_result,
                media_type='application/pdf',
                filename=f"Portfolio_Report_Pro_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
        
        else:
            # LaTeX failed - create bundle
            logger.info("LaTeX failed, creating ZIP bundle")
            
            zip_filename = f"Portfolio_Report_Bundle_{datetime.now().strftime('%Y%m%d')}.zip"
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            zip_path = temp_zip.name
            temp_zip.close()
            
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Add fallback PDF
                zf.write(fallback_pdf_path, "Portfolio_Report_QuickView.pdf")
                
                # Add LaTeX source
                if build_dir and os.path.exists(build_dir):
                    for root, dirs, files in os.walk(build_dir):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            arcname = os.path.join("latex_source", file_name)
                            zf.write(file_path, arcname)
                
                # Add README
                readme_content = """
VisionWealth Portfolio Report Bundle
====================================

This bundle contains two versions of your report:

1. Portfolio_Report_QuickView.pdf
   - Standard PDF report generated immediately for your convenience.

2. latex_source/
   - Professional LaTeX source code and charts.
   - You can upload these files to Overleaf.com or compile locally.

Thank you for using VisionWealth Portfolio Analytics!
                """
                zf.writestr("README.txt", readme_content)
            
            # Cleanup
            try:
                os.unlink(fallback_pdf_path)
                if build_dir:
                    shutil.rmtree(build_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")
            
            # Schedule background cleanup of ZIP
            background_tasks.add_task(
                lambda: os.unlink(zip_path) if os.path.exists(zip_path) else None
            )
            
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=zip_filename
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


# ========================================
# PORTFOLIO SIMULATION ENDPOINTS
# ========================================

@app.post("/api/portfolio/simulate", tags=["Portfolio Simulation"])
@limiter.limit("10/minute")
async def simulate_portfolio(
    request: Request,
    simulation_request: SimulationRequest
):
    """Analyze a hypothetical portfolio from JSON holdings."""
    try:
        logger.info(f"Simulating portfolio with {len(simulation_request.holdings)} holdings")
        
        # Convert holdings to dict list
        holdings_list = [
            {'symbol': h.symbol, 'weight': h.weight}
            for h in simulation_request.holdings
        ]
        
        # Analyze proposed portfolio
        proposed_df = analytics.analyze_portfolio_from_json(holdings_list)
        
        if proposed_df.empty:
            return JSONResponse({
                'success': False,
                'error': 'Could not analyze portfolio. Check ticker symbols.'
            })
        
        # Calculate analytics
        summary = compute_summary_metrics(proposed_df)
        charts = generate_chart_data(proposed_df)
        
        analytics_data = {}
        try:
            analytics_data['risk_metrics'] = analytics.calculate_risk_metrics(proposed_df)
            analytics_data['advanced_risk'] = analytics.calculate_advanced_risk_analytics(proposed_df)
            analytics_data['diversification'] = analytics.calculate_diversification_score(proposed_df)
            analytics_data['sector_allocation'] = analytics.generate_sector_allocation(proposed_df)
        except Exception as e:
            logger.warning(f"Some analytics failed in simulation: {e}")
        
        response_data = {
            'success': True,
            'proposed': {
                'summary': summary,
                'charts': charts,
                'analytics': analytics_data
            }
        }
        
        # Convert numpy types
        response_data = convert_numpy_types(response_data)
        
        logger.info("Portfolio simulation completed successfully")
        
        return JSONResponse(response_data)
    
    except Exception as e:
        logger.error(f"Portfolio simulation error: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@app.post("/api/proposal/generate", tags=["Portfolio Simulation"])
@limiter.limit("5/minute")
async def generate_proposal(
    request: Request,
    proposal_request: ProposalRequest
):
    """Generate a portfolio proposal comparing current vs proposed allocations."""
    try:
        logger.info(
            f"Generating proposal: "
            f"Current: {len(proposal_request.current_holdings)}, "
            f"Proposed: {len(proposal_request.proposed_holdings)}"
        )
        
        # Analyze current portfolio
        current_list = [
            {'symbol': h.symbol, 'weight': h.weight}
            for h in proposal_request.current_holdings
        ]
        
        # Analyze proposed portfolio
        proposed_list = [
            {'symbol': h.symbol, 'weight': h.weight}
            for h in proposal_request.proposed_holdings
        ]
        
        current_df = analytics.analyze_portfolio_from_json(current_list)
        proposed_df = analytics.analyze_portfolio_from_json(proposed_list)
        
        if current_df.empty or proposed_df.empty:
            return JSONResponse({
                'success': False,
                'error': 'Could not analyze one or both portfolios'
            })
        
        # Compare portfolios
        comparison = analytics.compare_portfolios(current_df, proposed_df)
        
        # Get detailed metrics for both
        current_metrics = {
            'summary': compute_summary_metrics(current_df),
            'risk': analytics.calculate_risk_metrics(current_df)
        }
        
        proposed_metrics = {
            'summary': compute_summary_metrics(proposed_df),
            'risk': analytics.calculate_risk_metrics(proposed_df)
        }
        
        response = {
            'success': True,
            'client_name': proposal_request.client_name,
            'advisor_name': proposal_request.advisor_name,
            'current_portfolio': convert_numpy_types(current_metrics),
            'proposed_portfolio': convert_numpy_types(proposed_metrics),
            'comparison': convert_numpy_types(comparison),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("Proposal generated successfully")
        
        return JSONResponse(response)
    
    except Exception as e:
        logger.error(f"Proposal generation error: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


# ========================================
# APPLICATION ENTRY POINT
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )
