"""
Portfolio Visualization Platform - Backend API
FastAPI server for processing portfolio CSV/Excel files and generating analytics
"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import io
import json
import yfinance as yf
from functools import lru_cache
import analytics
import data_import
import market_data
import db as db_module
import portfolio_api
import wealth_api
import watchlist_api
import news_api
import ai_api
import ai_api
import os
import zipfile
import shutil
from latex_generator import LatexReportGenerator

# Import new authentication modules
try:
    from database import get_db, engine, Base
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
except ImportError as e:
    print(f"Warning: Auth modules not available: {e}")
    AUTH_ENABLED = False

from ai_service import AIService
from benchmark import BenchmarkService


# Pydantic schemas for authentication
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "client"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    
    class Config:
        from_attributes = True


import goals_api
import reports_api
import export_api

app = FastAPI(title="Portfolio Analytics API", version="2.0.0")

# Register portfolio API router immediately so routes are available to tests
app.include_router(portfolio_api.router, prefix='/api/v2')
app.include_router(wealth_api.router, prefix='/api/v2')
app.include_router(watchlist_api.router, prefix='/api/v2')
app.include_router(news_api.router, prefix='/api/v2')
app.include_router(ai_api.router, prefix='/api/v2')
app.include_router(goals_api.router, prefix='/api/v2')
app.include_router(reports_api.router, prefix='/api/v2')
app.include_router(export_api.router, prefix='/api/v2')


@app.on_event("startup")
async def startup_event():
    # Initialize existing database
    try:
        db_module.init_db()
    except Exception:
        pass
    
    # Initialize new auth database
    if AUTH_ENABLED:
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"⚠️  Database initialization failed: {e}")


# ========================================
# AUTHENTICATION ENDPOINTS
# ========================================

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    if user_data.role not in ["client", "advisor"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'client' or 'advisor'")
    
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
    
    return new_user


@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and receive JWT access token"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    # Find user
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    return current_user


@app.post("/auth/logout", tags=["Authentication"])
async def logout():
    """Logout (handled client-side by removing token)"""
    return {"message": "Logged out successfully"}


# Cache for real-time quotes (5 minute TTL)
quote_cache = {}
CACHE_TTL = 300  # 5 minutes in seconds

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://portfolio-analytics-dashboard-seven.vercel.app",
        "https://portfolio-analytics-dashboard-fqbxmihus.vercel.app",
        "http://localhost:8000",  # Keep for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_index():
    """Serve the main HTML file"""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"message": "Frontend not found, use API at /docs"}

# Expected CSV columns (exact match from specification)
EXPECTED_COLUMNS = [
    'Description', 'Symbol', 'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
    '1-Day Value Change ($)', '1-Day Price Change (%)', 'Account Type',
    'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
    'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
    'Asset Type', 'Asset Category', 'Est Annual Income ($)',
    'Current Yld/Dist Rate (%)', 'Dividend Instructions',
    'Cap Gain Instructions', 'Initial Purchase Date', 'Est Tax G/L ($)*'
]


def convert_numpy_types(obj):
    """
    Recursively convert numpy types to Python native types for JSON serialization
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
    elif pd.isna(obj):
        return None
    else:
        return obj


def clean_numeric_value(value: Any) -> float:
    """Convert any value to float, handling NaN and None"""
    if pd.isna(value) or value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0



def parse_portfolio_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV or Excel file and validate structure"""
    try:
        # Determine file type and read accordingly
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError("File must be CSV or Excel format")
        
        # Normalize column names (strip whitespace, etc)
        df.columns = df.columns.str.strip()
        
        # Validate critical columns exist - Relaxed to just Symbol and Quantity
        # We can fetch Price, and Calculate Value
        critical_columns = ['Symbol', 'Quantity']
        missing_critical = [col for col in critical_columns if col not in df.columns]
        
        if missing_critical:
            raise ValueError(f"Missing critical columns: {', '.join(missing_critical)}. File must at least have Symbol and Quantity.")
        
        return df
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")


def clean_portfolio_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize portfolio data, fetching missing info if needed"""
    # Remove header rows (rows where Symbol is NaN)
    df = df[df['Symbol'].notna()].copy()
    
    # Ensure standard columns exist with defaults
    if 'Description' not in df.columns:
        df['Description'] = ''
        
    if 'Asset Type' not in df.columns:
        df['Asset Type'] = 'Stock'

    if 'Asset Category' not in df.columns:
        df['Asset Category'] = df['Asset Type']
        
    if 'Price ($)' not in df.columns:
        df['Price ($)'] = 0.0
        
    if 'Value ($)' not in df.columns:
        df['Value ($)'] = 0.0
        
    # Clean numeric columns
    numeric_columns = [
        'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
        '1-Day Value Change ($)', '1-Day Price Change (%)',
        'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
        'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
        'Est Annual Income ($)', 'Current Yld/Dist Rate (%)', 'Est Tax G/L ($)*'
    ]
    
    for col in numeric_columns:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].apply(clean_numeric_value)

    # 1. Fetch Missing Prices (if Price is 0 but Symbol exists)
    rows_needing_price = df[(df['Price ($)'] == 0) & (df['Symbol'].str.len() > 0)]
    if not rows_needing_price.empty:
        # Optimization: Fetch in batch if possible, for now simple loop or yfinance batch
        symbols = rows_needing_price['Symbol'].unique().tolist()
        # Clean symbols
        symbols = [s for s in symbols if isinstance(s, str)]
        
        if symbols:
            try:
                # Limit to prevent long waits on huge files
                if len(symbols) <= 50:
                    tickers = yf.Tickers(' '.join(symbols))
                    for sym in symbols:
                        try:
                            # Try to get fast price
                            info = tickers.tickers[sym].info
                            price = info.get('regularMarketPrice', info.get('currentPrice', info.get('previousClose', 0.0)))
                            if price:
                                df.loc[df['Symbol'] == sym, 'Price ($)'] = price
                        except Exception:
                            pass # Keep as 0 if fetch fails
            except Exception as e:
                print(f"Failed to auto-fetch prices: {e}")

    # 2. Compute missing Values (Pro-rate)
    # Value = Quantity * Price
    df['Value ($)'] = df.apply(
        lambda row: (row['Quantity'] * row['Price ($)']) 
        if (row['Value ($)'] == 0 and row['Quantity'] > 0 and row['Price ($)'] > 0)
        else row['Value ($)'], 
        axis=1
    )
    
    # 3. Compute missing Assets %
    total_value = df['Value ($)'].sum()
    if total_value > 0:
        df['Assets (%)'] = df.apply(
            lambda row: (row['Value ($)'] / total_value * 100) 
            if row['Assets (%)'] == 0 
            else row['Assets (%)'], 
            axis=1
        )
    
    return df


def compute_summary_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute portfolio-wide summary metrics"""
    
    total_value = df['Value ($)'].sum()
    total_principal = df['Principal ($)*'].sum()
    total_gain_loss = df['NFS G/L ($)'].sum()
    total_daily_change = df['1-Day Value Change ($)'].sum()
    total_annual_income = df['Est Annual Income ($)'].sum()
    
    # Calculate overall return percentage
    overall_return_pct = (total_gain_loss / total_principal * 100) if total_principal > 0 else 0
    
    # Calculate average yield
    avg_yield = (total_annual_income / total_value * 100) if total_value > 0 else 0
    
    # Daily return percentage
    daily_return_pct = (total_daily_change / total_value * 100) if total_value > 0 else 0
    
    # Count holdings
    num_holdings = len(df)
    
    # Get top gainers and losers
    top_gainers = df.nlargest(5, 'NFS G/L ($)')[['Symbol', 'Description', 'NFS G/L ($)', 'NFS G/L (%)']].to_dict('records')
    top_losers = df.nsmallest(5, 'NFS G/L ($)')[['Symbol', 'Description', 'NFS G/L ($)', 'NFS G/L (%)']].to_dict('records')
    
    return {
        'total_value': round(total_value, 2),
        'total_principal': round(total_principal, 2),
        'total_gain_loss': round(total_gain_loss, 2),
        'overall_return_pct': round(overall_return_pct, 2),
        'total_return_pct': round(overall_return_pct, 2),  # Alias for frontend
        'total_daily_change': round(total_daily_change, 2),
        'daily_return_pct': round(daily_return_pct, 2),
        'total_annual_income': round(total_annual_income, 2),
        'avg_yield': round(avg_yield, 2),
        'num_holdings': num_holdings,
        'top_gainers': top_gainers,
        'top_losers': top_losers
    }


def generate_chart_data(df: pd.DataFrame, fast_mode: bool = False) -> Dict[str, Any]:
    """
    Generate data structures for all dashboard charts
    fast_mode: Skip expensive operations for large portfolios (>50 holdings)
    """
    
    # Limit to top 10 for faster processing in fast_mode
    top_n = 10 if fast_mode else 15
    
    # 1. Portfolio Allocation by Symbol (Pie Chart)
    allocation_by_symbol = df[df['Value ($)'] > 0].nlargest(10, 'Value ($)')[['Symbol', 'Value ($)', 'Assets (%)']].to_dict('records')
    other_value = df[~df['Symbol'].isin([x['Symbol'] for x in allocation_by_symbol])]['Value ($)'].sum()
    if other_value > 0:
        allocation_by_symbol.append({
            'Symbol': 'Other',
            'Value ($)': round(other_value, 2),
            'Assets (%)': round(other_value / df['Value ($)'].sum() * 100, 2)
        })
    
    # 2. Allocation by Asset Type (Pie Chart)
    allocation_by_type = df.groupby('Asset Type').agg({
        'Value ($)': 'sum',
        'Assets (%)': 'sum'
    }).reset_index().to_dict('records')
    
    # 3. Allocation by Asset Category (Pie Chart)
    allocation_by_category = df.groupby('Asset Category').agg({
        'Value ($)': 'sum',
        'Assets (%)': 'sum'
    }).reset_index().to_dict('records')
    
    # 4. Gain/Loss by Symbol (Bar Chart) - Top N
    gain_loss_by_symbol = df.nlargest(top_n, 'NFS G/L ($)', keep='all')[['Symbol', 'NFS G/L ($)', 'NFS G/L (%)']].to_dict('records')
    
    # 5. Daily Movement by Symbol (Bar Chart) - Top N absolute changes
    if not fast_mode or '1-Day Value Change ($)' in df.columns:
        df['abs_daily_change'] = df['1-Day Value Change ($)'].abs()
        daily_movement = df.nlargest(top_n, 'abs_daily_change')[['Symbol', '1-Day Value Change ($)', '1-Day Price Change (%)']].to_dict('records')
    else:
        daily_movement = []
    
    # 6. Yield Distribution (Bar Chart) - Top yielding stocks
    yield_distribution = df[df['Current Yld/Dist Rate (%)'] > 0].nlargest(top_n, 'Current Yld/Dist Rate (%)')[
        ['Symbol', 'Current Yld/Dist Rate (%)', 'Est Annual Income ($)']
    ].to_dict('records')
    
    
    # 7. Benchmark Comparison (S&P 500)
    # Fetch 1-year S&P 500 data
    benchmark_data = BenchmarkService.get_sp500_data(period="1y")
    
    return {
        'allocation_by_symbol': allocation_by_symbol,
        'allocation_by_type': allocation_by_type,
        'allocation_by_category': allocation_by_category,
        'gain_loss_by_symbol': gain_loss_by_symbol,
        'daily_movement': daily_movement,
        'yield_distribution': yield_distribution,
        'benchmark_comparison': benchmark_data
    }
    
    # 7. Benchmark Comparison (S&P 500)
    # Fetch 1-year S&P 500 data
    benchmark_data = BenchmarkService.get_sp500_data(period="1y")
    
    return {
        'allocation_by_symbol': allocation_by_symbol,
        'allocation_by_type': allocation_by_type,
        'allocation_by_category': allocation_by_category,
        'gain_loss_by_symbol': gain_loss_by_symbol,
        'daily_movement': daily_movement,
        'yield_distribution': yield_distribution,
        'benchmark_comparison': benchmark_data
    }


def prepare_holdings_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Prepare holdings data for display table"""
    
    # Select and order columns for display
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
    
    # Convert to records
    holdings = df[available_columns].copy()
    
    # Format date column
    if 'Initial Purchase Date' in holdings.columns:
        holdings['Initial Purchase Date'] = holdings['Initial Purchase Date'].apply(
            lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ''
        )
    
    # Round numeric columns
    for col in holdings.columns:
        if holdings[col].dtype in ['float64', 'float32']:
            holdings[col] = holdings[col].round(2)
    
    return holdings.to_dict('records')


@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "online",
        "service": "Portfolio Analytics API",
        "version": "1.0.0"
    }


@app.post("/upload-portfolio")
async def upload_portfolio(file: UploadFile = File(...)):
    """
    Upload and process portfolio CSV/Excel file
    Returns summary metrics, chart data, and holdings table
    OPTIMIZED: Skips heavy analytics for large portfolios with complete data
    """
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse file
        df = parse_portfolio_file(content, file.filename)
        
        # Clean data
        df = clean_portfolio_data(df)
        
        # Validate we have data
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="No valid holdings found in file")
        
        # Check if we should use fast mode (large portfolio with complete data)
        use_fast_mode = len(df) > 50 and 'Total Return (%)' in df.columns
        
        if use_fast_mode:
            print(f"Using fast mode for {len(df)} holdings")
        
        # Compute metrics (fast mode skips heavy calculations)
        summary = compute_summary_metrics(df)
        
        # Generate chart data (simplified for large portfolios)
        charts = generate_chart_data(df, fast_mode=use_fast_mode)
        
        # Prepare holdings table
        holdings = prepare_holdings_table(df)
        
        # Convert numpy types to Python native types
        response_data = {
            "success": True,
            "filename": file.filename,
            "summary": summary,
            "charts": charts,
            "holdings": holdings
        }
        
        response_data = convert_numpy_types(response_data)
        
        return JSONResponse(response_data)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/market/quote/{ticker}")
async def get_realtime_quote(ticker: str):
    """
    Fetch real-time quote for a single stock ticker
    """
    try:
        # Check cache first
        cache_key = f"{ticker}_{datetime.now().strftime('%Y%m%d%H%M')}"
        if cache_key in quote_cache:
            return quote_cache[cache_key]
        
        # Fetch from Yahoo Finance
        stock = yf.Ticker(ticker)
        info = stock.info
        
        quote_data = {
            'symbol': ticker.upper(),
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
        
        return quote_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quote for {ticker}: {str(e)}")


@app.post("/api/market/quotes")
async def get_batch_quotes(tickers: List[str]):
    """
    Fetch real-time quotes for multiple tickers
    """
    try:
        quotes = {}
        
        for ticker in tickers:
            try:
                # Check cache first
                cache_key = f"{ticker}_{datetime.now().strftime('%Y%m%d%H%M')}"
                
                if cache_key in quote_cache:
                    quotes[ticker] = quote_cache[cache_key]
                else:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    quote_data = {
                        'symbol': ticker.upper(),
                        'price': info.get('regularMarketPrice', info.get('currentPrice', 0)),
                        'change': info.get('regularMarketChange', 0),
                        'change_percent': info.get('regularMarketChangePercent', 0),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    quote_cache[cache_key] = quote_data
                    quotes[ticker] = quote_data
            
            except Exception as e:
                quotes[ticker] = {'error': str(e)}
        
        return {'quotes': quotes, 'timestamp': datetime.now().isoformat()}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch quote fetch failed: {str(e)}")


@app.post("/api/portfolio/analyze")
async def analyze_portfolio(file: UploadFile = File(...)):
    """
    Comprehensive portfolio analysis with advanced metrics
    """
    try:
        content = await file.read()
        df = parse_portfolio_file(content, file.filename)
        df = clean_portfolio_data(df)
        
        # Get all analytics
        summary_metrics = compute_summary_metrics(df)
        chart_data = generate_chart_data(df)
        holdings_data = prepare_holdings_table(df)
        
        # Calculate advanced analytics
        diversification_score = analytics.calculate_diversification_score(df)
        risk_metrics = analytics.calculate_risk_metrics(df)
        sector_allocation = analytics.generate_sector_allocation(df)
        dividend_metrics = analytics.calculate_dividend_metrics(df)
        tax_loss_harvesting = analytics.identify_tax_loss_harvesting(df)
        performance_vs_weight = analytics.calculate_performance_vs_weight(df)
        advanced_risk = analytics.calculate_advanced_risk_analytics(df)
        
        # Benchmarking (new)
        benchmark_comparison = analytics.calculate_benchmark_comparison(df, benchmark_ticker='SPY', period='1y')
        
        # Dividend Calendar (new)
        dividend_calendar = analytics.calculate_dividend_calendar(df)
        
        return JSONResponse({
            'success': True,
            'filename': file.filename,
            "summary": summary_metrics,
            "charts": chart_data,
            "holdings": holdings_data,
            "analytics": {
                "diversification": diversification_score,
                "risk_metrics": risk_metrics,
                "sector_allocation": sector_allocation,
                "dividend_metrics": dividend_metrics,
                "tax_loss_harvesting": tax_loss_harvesting,
                "performance_vs_weight": performance_vs_weight,
                'advanced_risk': advanced_risk,
                'benchmark_comparison': benchmark_comparison,
                'dividend_calendar': dividend_calendar
            }
        })
    
    except Exception as e:
        print(f"Analysis Failed: {e}")
        # Return fallback error instead of 500 to keep UI alive? 
        # No, raise for now but print details
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/v2/portfolio/{portfolio_id}/analytics")
async def get_portfolio_analytics(portfolio_id: int, benchmark: str = 'SPY', period: str = '1y'):
    """
    Generate analytics for a saved portfolio (fetched from DB)
    """
    try:
        session = next(db_module.get_session())
        p = session.get(db_module.Portfolio, portfolio_id)
        if not p:
            raise HTTPException(status_code=404, detail='Portfolio not found')

        # Convert holdings to DataFrame
        import pandas as pd
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
                'NFS G/L (%)': (((h.quantity * h.price) - h.cost_basis) / h.cost_basis * 100) if h.cost_basis > 0 else 0.0,
                'Asset Type': h.asset_type,
                'Asset Category': h.asset_type, # Default category to type
                'Description': meta.get('description', ''),
                'Current Yld/Dist Rate (%)': 0.0, # TODO: fetch if possible or store
                'Est Annual Income ($)': 0.0,
                '1-Day Value Change ($)': 0.0,
                '1-Day Price Change (%)': 0.0
            })
            
        if not rows:
             return JSONResponse({'success': False, 'error': 'Empty portfolio'})

        df = pd.DataFrame(rows)
        # Calculate % assets
        total_val = df['Value ($)'].sum()
        if total_val > 0:
            df['Assets (%)'] = df['Value ($)'] / total_val * 100
        else:
            df['Assets (%)'] = 0

        # Calculate analytics
        summary_metrics = compute_summary_metrics(df)
        chart_data = generate_chart_data(df)
        risk_metrics = analytics.calculate_risk_metrics(df)
        advanced_risk = analytics.calculate_advanced_risk_analytics(df)
        sector_allocation = analytics.generate_sector_allocation(df)
        benchmark_comparison = analytics.calculate_benchmark_comparison(df, benchmark_ticker=benchmark, period=period)
        dividend_calendar = analytics.calculate_dividend_calendar(df)
        
        return JSONResponse({
            'success': True,
            "summary": summary_metrics,
            "charts": chart_data,
            "analytics": {
                "risk_metrics": risk_metrics,
                "advanced_risk": advanced_risk,
                "sector_allocation": sector_allocation,
                "benchmark_comparison": benchmark_comparison,
                "dividend_calendar": dividend_calendar
            }
        })
    except Exception as e:
        print(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/recommendations")
async def get_recommendations(file: UploadFile = File(...), risk_profile: str = 'moderate'):
    """
    Get portfolio rebalancing and optimization recommendations
    """
    try:
        content = await file.read()
        df = parse_portfolio_file(content, file.filename)
        df = clean_portfolio_data(df)
        
        # Generate optimization recommendations
        allocation_optimization = analytics.optimize_asset_allocation(df, risk_profile)
        
        return JSONResponse({
            'success': True,
            'recommendations': allocation_optimization
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")


@app.get("/api/portfolio/risk-assessment")
async def risk_assessment_info():
    """
    Get information about risk assessment metrics
    """
    return {
        'metrics_available': [
            'Value at Risk (VaR) 95%',
            'Value at Risk (VaR) 99%',
            'Downside Deviation',
            'Portfolio Volatility',
            'Sharpe Ratio',
            'Beta',
            'Diversification Score',
            'Concentration Risk'
        ],
        'risk_profiles': ['conservative', 'moderate', 'aggressive'],
        'description': 'Comprehensive risk analysis for portfolio optimization'
    }



@app.post("/api/portfolio/export-pdf")
async def export_portfolio_pdf(
    file: UploadFile = File(None),
    background_tasks: BackgroundTasks = None,
    client_name: str = Form(None),
    portfolio_id: Optional[int] = Form(None)
):
    """
    Generate and download professional PDF portfolio report
    Tries Latex first, falls back to Python-native PDF if Latex is missing
    Bundles both in a ZIP if compilation fails
    """
    try:
        import pdf_generator
        import tempfile
        from fastapi.responses import FileResponse
        
        # Prepare Data (Common Logic)
        if portfolio_id:
            # Load portfolio from DB
            session = next(db_module.get_session())
            p = session.get(db_module.Portfolio, portfolio_id)
            if not p:
                raise HTTPException(status_code=404, detail='Portfolio not found')

            # Build DataFrame from holdings
            import pandas as pd
            rows = []
            for h in p.holdings:
                rows.append({
                    'Description': (json.loads(h.meta_json or '{}').get('description') if h.meta_json else ''),
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
                raise HTTPException(status_code=400, detail='No file provided')

            # Read file content
            content = await file.read()
            df = parse_portfolio_file(content, file.filename)
            client_display_name = client_name or 'Portfolio Report'

        # Common Data Cleaning
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
                
        for col in required_numeric:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            except Exception:
                df[col] = 0

        # Compute Metrics
        summary = compute_summary_metrics(df)
        charts = generate_chart_data(df)
        holdings = prepare_holdings_table(df)

        portfolio_data = {'summary': summary, 'charts': charts, 'holdings': holdings}

        # Analytics
        try:
            risk_metrics = analytics.calculate_risk_metrics(df)
            diversification = analytics.calculate_diversification_score(df)
            tax_loss_harvesting = analytics.identify_tax_loss_harvesting(df)
            dividend_metrics = analytics.calculate_dividend_metrics(df)
            analytics_data = {
                'risk_metrics': risk_metrics,
                'diversification': diversification,
                'tax_loss_harvesting': tax_loss_harvesting,
                'dividend_metrics': dividend_metrics
            }
        except Exception:
            analytics_data = {}

        # 1. Generate Fallback PDF (Standard ReportLab)
        # We always generate this because it's reliable
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        fallback_pdf_path = temp_pdf.name
        temp_pdf.close()
        
        pdf_generator.generate_portfolio_pdf(portfolio_data, analytics_data, fallback_pdf_path, client_name=client_display_name)

        # 2. Try Latex Generation
        latex_gen = LatexReportGenerator()
        success, latex_result, build_dir = latex_gen.generate_report(portfolio_data, analytics_data, "unused.pdf", client_name=client_display_name)

        # Decision Logic
        if success:
            # If Latex worked (someone installed pdflatex), give them the PDF directly
            # Cleanup fallback
            os.unlink(fallback_pdf_path)
            shutil.rmtree(build_dir, ignore_errors=True)
            
            return FileResponse(
                latex_result, 
                media_type='application/pdf', 
                filename=f"Portfolio_Report_Pro_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
        else:
            # Compilation failed (expected on minimal envs)
            # Create a ZIP containing:
            # 1. Fallback PDF (renamed to Portfolio_Report.pdf)
            # 2. Source Folder (containing .tex and images)
            # 3. README explaining why
            
            zip_filename = f"Portfolio_Report_Bundle_{datetime.now().strftime('%Y%m%d')}.zip"
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            zip_path = temp_zip.name
            temp_zip.close()

            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Add Fallback PDF
                zf.write(fallback_pdf_path, "Portfolio_Report_QuickView.pdf")
                
                # Add Latex Source
                tex_source_name = "latex_source"
                # Walk the build dir which contains .tex and .pngs
                for root, dirs, files in os.walk(build_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Archive path: latex_source/filename
                        arcname = os.path.join(tex_source_name, file)
                        zf.write(file_path, arcname)
                
                # Add README
                readme_content = """
VisionWealth Portfolio Report Bundle
====================================

This bundle contains two versions of your report:

1. Portfolio_Report_QuickView.pdf
   - This is a standard PDF report generated immediately for your convenience.

2. latex_source/
   - This folder contains the professional Latex source code and charts.
   - We attempted to compile this into a high-quality PDF, but 'pdflatex' was not found on the server.
   - You can upload the contents of this folder to a service like Overleaf.com or compile it locally if you have MacTeX/TeXLive installed.

Thank you for using VisionWealth.
                """
                zf.writestr("README.txt", readme_content)

            # Cleanup temps
            os.unlink(fallback_pdf_path)
            if build_dir and os.path.exists(build_dir):
                shutil.rmtree(build_dir, ignore_errors=True)
            
            # Use background tasks to remove the zip after sending
            if background_tasks:
                background_tasks.add_task(os.unlink, zip_path)
                
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=zip_filename
            )

    except Exception as e:
        print(f"Error exporting PDF: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)





class HoldingInput(BaseModel):
    symbol: str
    weight: float

class SimulationRequest(BaseModel):
    holdings: List[HoldingInput]
    current_portfolio_file: Optional[str] = None

class ProposalRequest(BaseModel):
    current_holdings: List[HoldingInput]
    proposed_holdings: List[HoldingInput]
    client_name: str = "Valued Client"
    advisor_name: str = "Advisor"

class BatchQuotesRequest(BaseModel):
    tickers: List[str]
    use_cache: bool = True

class RetirementPlanRequest(BaseModel):
    portfolio_id: int
    years: int = 30
    monthly_contribution: float = 0
    inflation_rate: float = 0.025


@app.post("/api/v2/planning/retirement")
async def simulate_retirement_plan(request: RetirementPlanRequest):
    """
    Run retirement Monte Carlo simulation for a specific portfolio
    """
    try:
        session = next(db_module.get_session())
        p = session.get(db_module.Portfolio, request.portfolio_id)
        if not p:
            raise HTTPException(status_code=404, detail='Portfolio not found')

        # Convert to DataFrame
        import pandas as pd
        rows = []
        for h in p.holdings:
            rows.append({
                'Symbol': h.ticker,
                'Value ($)': h.quantity * h.price,
                'Asset Type': h.asset_type
            })
        
        if not rows:
             return JSONResponse({'success': False, 'error': 'Empty portfolio'})

        df = pd.DataFrame(rows)
        
        result = analytics.calculate_retirement_projection(
            df, 
            years=request.years, 
            monthly_contribution=request.monthly_contribution,
            inflation_rate=request.inflation_rate
        )
        
        return JSONResponse({'success': True, 'result': result})
        
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/search")
async def search_ticker(q: str):
    """
    Search for a ticker (Basic implementation using yfinance info)
    """
    try:
        symbol = q.upper()
        ticker = yf.Ticker(symbol)
        
        # Try to fetch info to validate
        info = ticker.info
        if not info or 'symbol' not in info:
             # Try fast_info as fallback
            if not ticker.fast_info.last_price:
                return JSONResponse({'results': []})
            
            return JSONResponse({'results': [{
                'symbol': symbol,
                'name': symbol, # Name not available in fast_info
                'type': 'Unknown',
                'price': ticker.fast_info.last_price
            }]})

        return JSONResponse({'results': [{
            'symbol': info.get('symbol'),
            'name': info.get('longName', info.get('shortName', symbol)),
            'type': info.get('quoteType', 'Unknown'),
            'price': info.get('currentPrice', info.get('regularMarketPrice'))
        }]})
    except Exception as e:
        print(f"Search error: {e}")
        return JSONResponse({'results': []})

@app.post("/api/portfolio/simulate")
async def simulate_portfolio(request: SimulationRequest):
    """
    Analyze a hypothetical portfolio from JSON holdings
    """
    try:
        # Convert request holdings to list of dicts
        holdings_list = [{'symbol': h.symbol, 'weight': h.weight} for h in request.holdings]
        
        # Analyze proposed portfolio
        proposed_df = analytics.analyze_portfolio_from_json(holdings_list)
        
        if proposed_df.empty:
             return JSONResponse({'success': False, 'error': 'Could not analyze portfolio'})

        # Calculate analytics for proposed
        summary = compute_summary_metrics(proposed_df)
        charts = generate_chart_data(proposed_df)
        risk = analytics.calculate_risk_metrics(proposed_df)
        advanced_risk = analytics.calculate_advanced_risk_analytics(proposed_df)
        
        response_data = {
            'success': True,
            'proposed': {
                'summary': summary,
                'charts': charts,
                'analytics': {
                    'risk_metrics': risk,
                    'advanced_risk': advanced_risk
                }
            }
        }
        
        # Convert all numpy types to Python native types for JSON serialization
        response_data = convert_numpy_types(response_data)
        
        # If current portfolio file provided, compare
        if request.current_portfolio_file:
            # Load current portfolio (assuming it's in uploads)
            # For simplicity in this prototype, we'll skip loading the file again 
            # and assume the frontend sends the current holdings if needed, 
            # OR we implement file loading here.
            # Let's keep it simple: The frontend can send "current_holdings" if it wants comparison,
            # but for now we'll just return the proposed analysis.
            pass
            
        return JSONResponse(response_data)
        
    except Exception as e:
        print(f"Simulation error: {e}")
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.post("/api/proposal/generate")
async def generate_proposal(request: ProposalRequest):
    """
    Generate a PDF proposal comparing current vs proposed portfolios
    """
    try:
        # Analyze both
        current_list = [{'symbol': h.symbol, 'weight': h.weight} for h in request.current_holdings]
        proposed_list = [{'symbol': h.symbol, 'weight': h.weight} for h in request.proposed_holdings]
        
        current_df = analytics.analyze_portfolio_from_json(current_list)
        proposed_df = analytics.analyze_portfolio_from_json(proposed_list)
        
        if current_df.empty or proposed_df.empty:
            return JSONResponse({'success': False, 'error': 'Could not analyze portfolios'})
            
        # Compare
        comparison = analytics.compare_portfolios(current_df, proposed_df)
        
        # Generate PDF (Placeholder for now, we need to update pdf_generator)
        # For now, return success
        return JSONResponse({
            'success': True, 
            'message': 'Proposal generation logic to be implemented',
            'comparison': comparison
        })
        
    except Exception as e:
        print(f"Proposal error: {e}")
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)


# ===========================
# PHASE 2: ADVANCED FILE IMPORT & LIVE MARKET DATA ENDPOINTS
# ===========================

@app.post("/api/v2/import/smart")
async def smart_import_portfolio(file: UploadFile = File(...)):
    """
    Smart CSV/Excel import with automatic column detection and format recognition
    Supports multiple brokerage formats (Charles Schwab, Fidelity, Vanguard, etc.)
    
    Returns:
    {
        'success': bool,
        'data': {
            'holdings': [...],
            'summary': {...},
            'metadata': {...}
        },
        'warnings': [...],
        'errors': [...]
    }
    """
    try:
        content = await file.read()
        
        # Use smart importer
        importer = data_import.PortfolioImporter()
        result = importer.import_file(content, file.filename)
        
        if not result['success'] and len(result['errors']) > 0:
            raise HTTPException(status_code=400, detail=f"Import failed: {result['errors'][0]}")
        
        df = result['dataframe']
        
        # Generate basic metrics
        total_value = df['value'].sum() if 'value' in df.columns else 0
        
        # Convert datetime objects to strings for JSON serialization
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)
        
        # Replace NaN values with None for JSON serialization
        df = df.replace({np.nan: None})
        
        
        response = {
            'success': True,
            'metadata': {
                'filename': result['metadata'].get('filename'),
                'format': result['metadata'].get('format'),
                'total_holdings': result['metadata'].get('num_holdings'),
                'total_value': result['metadata'].get('total_value'),
                'auto_mapped_columns': result['metadata'].get('auto_mapped'),
                'import_timestamp': datetime.now().isoformat()
            },
            'holdings': df.to_dict('records'),
            'warnings': result['warnings'],
            'errors': result['errors']
        }
        
        return JSONResponse(response)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart import failed: {str(e)}")


@app.post("/api/v2/import/with-mapping")
async def import_with_column_mapping(file: UploadFile = File(...), column_mapping: Dict[str, str] = None):
    """
    Import portfolio file with explicit column mapping
    
    Args:
        file: CSV/Excel file
        column_mapping: Dict mapping detected columns to standard names
                       Example: {'ticker': 'Symbol', 'quantity': 'Qty', 'price': 'Price'}
    
    Returns:
        Normalized portfolio data with all computed metrics
    """
    try:
        content = await file.read()
        
        importer = data_import.PortfolioImporter()
        result = importer.import_file(content, file.filename, column_mapping)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=f"Import failed: {', '.join(result['errors'])}")
        
        df = result['dataframe']
        
        return JSONResponse({
            'success': True,
            'metadata': result['metadata'],
            'holdings': df.to_dict('records'),
            'warnings': result['warnings']
        })
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import with mapping failed: {str(e)}")


@app.get("/api/v2/market/quote/{ticker}")
async def get_live_quote(ticker: str):
    """
    Get comprehensive real-time stock data for a ticker
    
    Returns detailed market information:
    - Current price and daily changes
    - Volume and market cap
    - PE ratio, dividend yield
    - 52-week high/low
    - Company sector and industry
    """
    try:
        client = market_data.get_client()
        quote = client.get_quote(ticker)
        
        if 'error' in quote:
            raise HTTPException(status_code=404, detail=f"Failed to fetch data for {ticker}: {quote['error']}")
        
        return JSONResponse(quote)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote fetch failed: {str(e)}")


@app.post("/api/v2/market/quotes/batch")
async def get_batch_live_quotes(request: BatchQuotesRequest):
    """
    Get real-time quotes for multiple tickers
    
    Request body:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "use_cache": true
    }
    
    Returns:
    {
        'quotes': {
            'AAPL': {...},
            'GOOGL': {...},
            ...
        },
        'timestamp': ISO timestamp
    }
    """
    try:
        client = market_data.get_client()
        quotes = client.get_quotes_batch(request.tickers, request.use_cache)
        
        return JSONResponse({
            'success': True,
            'quotes': quotes,
            'count': len(quotes),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch quotes failed: {str(e)}")


@app.post("/api/v2/portfolio/enrich-live-data")
async def enrich_portfolio_with_live_data(file: UploadFile = File(...)):
    """
    Upload portfolio and enrich it with live market data
    
    Returns portfolio with added live price columns:
    - live_price: Current market price
    - live_change: Daily price change ($)
    - live_change_pct: Daily price change (%)
    - live_value: Current portfolio value
    - live_gain_loss: Current unrealized gain/loss
    - live_gain_loss_pct: Current unrealized gain/loss %
    """
    try:
        content = await file.read()
        
        # Import portfolio
        importer = data_import.PortfolioImporter()
        result = importer.import_file(content, file.filename)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=f"Import failed: {result['errors'][0]}")
        
        df = result['dataframe']
        
        # Enrich with live data
        updater = market_data.PortfolioMarketUpdater(market_data.get_client())
        df_enriched = updater.update_portfolio_prices(df)
        
        # Get top movers
        movers = updater.get_top_movers(df_enriched, top_n=5)
        
        # Calculate totals
        total_live_value = df_enriched['live_value'].sum() if 'live_value' in df_enriched.columns else 0
        total_live_gain_loss = df_enriched['live_gain_loss'].sum() if 'live_gain_loss' in df_enriched.columns else 0
        
        return JSONResponse({
            'success': True,
            'filename': file.filename,
            'portfolio': df_enriched.to_dict('records'),
            'summary': {
                'total_live_value': round(total_live_value, 2),
                'total_live_gain_loss': round(total_live_gain_loss, 2),
                'num_holdings': len(df_enriched)
            },
            'market_movers': movers,
            'timestamp': datetime.now().isoformat()
        })
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Live enrichment failed: {str(e)}")


@app.get("/api/v2/market/search/{query}")
async def search_market_ticker(query: str):
    """
    Search for ticker by symbol or company name
    
    Returns matching tickers with company info
    """
    try:
        client = market_data.get_client()
        results = client.search_ticker(query)
        
        return JSONResponse({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/v2/market/ticker/{ticker}/analysis")
async def get_ticker_analysis(ticker: str):
    """
    Get comprehensive analysis for a single ticker
    
    Returns:
    - Company fundamentals
    - Valuation metrics
    - Performance metrics
    - Risk metrics
    - Analyst recommendations
    """
    try:
        client = market_data.get_client()
        analysis = client.analyze_ticker(ticker)
        
        if 'error' in analysis:
            raise HTTPException(status_code=404, detail=f"Analysis failed: {analysis['error']}")
        
        return JSONResponse(analysis)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ticker analysis failed: {str(e)}")


@app.get("/api/v2/market/historical/{ticker}")
async def get_ticker_historical_data(ticker: str, period: str = '1y', interval: str = '1d'):
    """
    Get historical price data for technical analysis
    
    Args:
        ticker: Stock ticker
        period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
        interval: '1m', '5m', '15m', '30m', '60m', '1d', '1wk', '1mo'
    
    Returns:
        Historical OHLCV data with moving averages
    """
    try:
        client = market_data.get_client()
        hist_data = client.get_historical_data(ticker, period=period, interval=interval)
        
        if hist_data.empty:
            raise HTTPException(status_code=404, detail=f"No historical data for {ticker}")
        
        # Convert to JSON-friendly format
        hist_dict = hist_data.reset_index().to_dict('records')
        
        # Convert datetime to ISO format and handle NaN values
        for record in hist_dict:
            if 'Date' in record and hasattr(record['Date'], 'isoformat'):
                record['Date'] = record['Date'].isoformat()
            # Replace NaN with None for JSON compatibility
            for key in record:
                if isinstance(record[key], float) and (record[key] != record[key] or record[key] == float('inf')):  # NaN or Inf check
                    record[key] = None
        
        return JSONResponse({
            'success': True,
            'ticker': ticker.upper(),
            'period': period,
            'interval': interval,
            'data_points': len(hist_dict),
            'data': hist_dict,
            'timestamp': datetime.now().isoformat()
        })
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Historical data fetch failed: {str(e)}")


@app.get("/api/v2/market/ticker/{ticker}/dividends")
async def get_ticker_dividends(ticker: str):
    """
    Get dividend history for a ticker
    
    Returns:
        List of dividend payments with dates and amounts
    """
    try:
        client = market_data.get_client()
        dividends = client.get_dividends(ticker)
        
        if dividends.empty:
            return JSONResponse({
                'success': True,
                'ticker': ticker.upper(),
                'dividends': [],
                'total_annual': 0
            })
        
        # Convert to JSON-friendly format
        div_list = []
        for date, amount in dividends.items():
            div_list.append({
                'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
                'amount': float(amount)
            })
        
        return JSONResponse({
            'success': True,
            'ticker': ticker.upper(),
            'dividends': div_list,
            'count': len(div_list),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dividend fetch failed: {str(e)}")


@app.post("/api/v2/portfolio/compare-with-market")
async def compare_portfolio_with_market(file: UploadFile = File(...)):
    """
    Compare portfolio performance against market benchmarks
    
    Returns:
    - Portfolio total return vs S&P 500, Nasdaq, etc.
    - Outperformance/underperformance metrics
    - Volatility comparison
    """
    try:
        content = await file.read()
        
        # Import portfolio
        importer = data_import.PortfolioImporter()
        result = importer.import_file(content, file.filename)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail="Import failed")
        
        df = result['dataframe']
        
        # Get market benchmarks
        client = market_data.get_client()
        benchmarks = {
            'SPY': client.get_quote('SPY'),  # S&P 500
            'QQQ': client.get_quote('QQQ'),  # Nasdaq 100
            'IWM': client.get_quote('IWM'),  # Russell 2000
        }
        
        # Get portfolio metrics
        updater = market_data.PortfolioMarketUpdater(market_data.get_client())
        df_enriched = updater.update_portfolio_prices(df)
        portfolio_value = df_enriched['live_value'].sum() if 'live_value' in df_enriched.columns else 0
        
        return JSONResponse({
            'success': True,
            'portfolio_value': round(portfolio_value, 2),
            'num_holdings': len(df_enriched),
            'benchmarks': benchmarks,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
