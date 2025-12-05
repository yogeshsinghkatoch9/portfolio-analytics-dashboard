"""
Portfolio Visualization Platform - Backend API
FastAPI server for processing portfolio CSV/Excel files and generating analytics
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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
import os

app = FastAPI(title="Portfolio Analytics API", version="2.0.0")

# Register portfolio API router immediately so routes are available to tests
app.include_router(portfolio_api.router, prefix='/api/v2')
app.include_router(wealth_api.router, prefix='/api/v2')
app.include_router(watchlist_api.router, prefix='/api/v2')
app.include_router(news_api.router, prefix='/api/v2')
app.include_router(ai_api.router, prefix='/api/v2')


@app.on_event("startup")
async def startup_event():
    # Initialize database
    try:
        db_module.init_db()
    except Exception:
        pass

# Cache for real-time quotes (5 minute TTL)
quote_cache = {}
CACHE_TTL = 300  # 5 minutes in seconds

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        
        # Validate critical columns exist
        critical_columns = ['Symbol', 'Quantity', 'Price ($)', 'Value ($)']
        missing_critical = [col for col in critical_columns if col not in df.columns]
        
        if missing_critical:
            raise ValueError(f"Missing critical columns: {', '.join(missing_critical)}")
        
        return df
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")


def clean_portfolio_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize portfolio data"""
    # Remove header rows (rows where Symbol is NaN and Description contains account info)
    df = df[df['Symbol'].notna()].copy()
    
    # Clean numeric columns
    numeric_columns = [
        'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
        '1-Day Value Change ($)', '1-Day Price Change (%)',
        'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)*',
        'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
        'Est Annual Income ($)', 'Current Yld/Dist Rate (%)', 'Est Tax G/L ($)*'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_value)
    
    # Compute missing Values if needed
    if 'Value ($)' in df.columns:
        df['Value ($)'] = df.apply(
            lambda row: row['Quantity'] * row['Price ($)'] 
            if row['Value ($)'] == 0 and row['Quantity'] > 0 
            else row['Value ($)'], 
            axis=1
        )
    
    # Compute missing Assets % if needed
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
        'total_daily_change': round(total_daily_change, 2),
        'daily_return_pct': round(daily_return_pct, 2),
        'total_annual_income': round(total_annual_income, 2),
        'avg_yield': round(avg_yield, 2),
        'num_holdings': num_holdings,
        'top_gainers': top_gainers,
        'top_losers': top_losers
    }


def generate_chart_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate data structures for all dashboard charts"""
    
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
    
    # 4. Gain/Loss by Symbol (Bar Chart) - Top 15
    gain_loss_by_symbol = df.nlargest(15, 'NFS G/L ($)', keep='all')[['Symbol', 'NFS G/L ($)', 'NFS G/L (%)']].to_dict('records')
    
    # 5. Daily Movement by Symbol (Bar Chart) - Top 15 absolute changes
    df['abs_daily_change'] = df['1-Day Value Change ($)'].abs()
    daily_movement = df.nlargest(15, 'abs_daily_change')[['Symbol', '1-Day Value Change ($)', '1-Day Price Change (%)']].to_dict('records')
    
    # 6. Yield Distribution (Bar Chart) - Top yielding stocks
    yield_distribution = df[df['Current Yld/Dist Rate (%)'] > 0].nlargest(15, 'Current Yld/Dist Rate (%)')[
        ['Symbol', 'Current Yld/Dist Rate (%)', 'Est Annual Income ($)']
    ].to_dict('records')
    
    return {
        'allocation_by_symbol': allocation_by_symbol,
        'allocation_by_type': allocation_by_type,
        'allocation_by_category': allocation_by_category,
        'gain_loss_by_symbol': gain_loss_by_symbol,
        'daily_movement': daily_movement,
        'yield_distribution': yield_distribution
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
        
        # Compute metrics
        summary = compute_summary_metrics(df)
        
        # Generate chart data
        charts = generate_chart_data(df)
        
        # Prepare holdings table
        holdings = prepare_holdings_table(df)
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "summary": summary,
            "charts": charts,
            "holdings": holdings
        })
    
    except HTTPException as he:
        raise he
    except Exception as e:
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
    """
    try:
        import pdf_generator
        import tempfile
        from fastapi.responses import FileResponse
        
        # If a portfolio_id is provided, generate report from DB
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

            # Compute assets %
            total_value = df['Value ($)'].sum() if not df.empty else 0
            if total_value > 0:
                df['Assets (%)'] = df['Value ($)'] / total_value * 100

            # Ensure numeric columns exist to avoid KeyErrors in analytics/pdf generator
            required_numeric = [
                'Quantity', 'Price ($)', 'Value ($)', 'Assets (%)',
                '1-Day Value Change ($)', '1-Day Price Change (%)',
                'Principal ($)*', 'Principal G/L ($)*', 'Principal G/L (%)',
                'NFS Cost ($)', 'NFS G/L ($)', 'NFS G/L (%)',
                'Est Annual Income ($)', 'Current Yld/Dist Rate (%)', 'Est Tax G/L ($)*'
            ]
            for col in required_numeric:
                if col not in df.columns:
                    df[col] = 0

            # Convert numerics safely
            for col in required_numeric:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                except Exception:
                    df[col] = 0

            # Create temporary PDF file
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_pdf_path = temp_pdf.name
            temp_pdf.close()

            # Use pdf_generator.generate_portfolio_pdf directly
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

            pdf_path = pdf_generator.generate_portfolio_pdf(portfolio_data, analytics_data, temp_pdf_path, client_name or p.name)

        else:
            if file is None:
                raise HTTPException(status_code=400, detail='No file provided')

            # Read file content
            content = await file.read()

            # Create temporary PDF file
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_pdf_path = temp_pdf.name
            temp_pdf.close()

            # Generate PDF report from upload (passes client_name)
            pdf_path = pdf_generator.generate_pdf_from_upload(
                content,
                file.filename,
                temp_pdf_path,
                client_name=client_name or 'Portfolio Report'
            )
        
        # Clean up temp file
        if background_tasks is not None:
            background_tasks.add_task(os.unlink, pdf_path)
        else:
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
        
        return FileResponse(
            pdf_path, 
            media_type='application/pdf', 
            filename=f"Portfolio_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
    except Exception as e:
        print(f"Error exporting PDF: {e}")
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)


# Builder Models
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
