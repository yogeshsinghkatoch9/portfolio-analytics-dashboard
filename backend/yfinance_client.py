"""
Yahoo Finance Integration Module
Real-time stock data, market updates, and comprehensive ticker information
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Enums

class QuoteStatus(str, Enum):
    """Quote fetch status"""
    SUCCESS = "success"
    CACHED = "cached"
    ERROR = "error"


class Period(str, Enum):
    """Historical data periods"""
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    MAX = "max"


# Data Classes

@dataclass
class Quote:
    """Structured quote data"""
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: float
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    week_52_high: float
    week_52_low: float
    company_name: str
    sector: str
    industry: str
    timestamp: str
    status: QuoteStatus
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Main Client Class

class YahooFinanceClient:
    """
    Advanced client for fetching real-time stock data from Yahoo Finance.
    
    Features:
    - Intelligent caching with TTL
    - Batch processing for efficiency
    - Comprehensive error handling
    - Historical data with technical indicators
    """
    
    def __init__(self, cache_ttl_seconds: int = 300, max_workers: int = 5, rate_limit_delay: float = 0.1):
        self.cache_ttl = cache_ttl_seconds
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.cache = {}
        self.cache_time = {}
        self.request_count = 0
        
        logger.info(f"Initialized YahooFinanceClient with cache_ttl={cache_ttl_seconds}s")
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid"""
        if key not in self.cache:
            return False
        
        cache_time = self.cache_time.get(key)
        if not cache_time:
            return False
        
        elapsed = (datetime.now() - cache_time).total_seconds()
        return elapsed < self.cache_ttl
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if valid"""
        if self._is_cache_valid(key):
            logger.debug(f"Cache hit: {key}")
            return self.cache[key]
        return None
    
    def _store_in_cache(self, key: str, value: Any):
        """Store value in cache"""
        self.cache[key] = value
        self.cache_time[key] = datetime.now()
        
        if len(self.cache) > 1000:
            self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Remove oldest cache entries"""
        sorted_keys = sorted(self.cache_time.keys(), key=lambda k: self.cache_time[k])
        
        for key in sorted_keys[:-500]:
            del self.cache[key]
            del self.cache_time[key]
        
        logger.info(f"Cache cleaned up, {len(self.cache)} entries remaining")
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_time.clear()
        logger.info("Cache cleared")
    
    def get_quote(self, ticker: str, use_cache: bool = True) -> Quote:
        """Fetch real-time quote for a single ticker"""
        ticker = ticker.upper().strip()
        cache_key = f"quote_{ticker}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                cached_quote = Quote(**cached)
                cached_quote.status = QuoteStatus.CACHED
                return cached_quote
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info or 'symbol' not in info:
                raise ValueError(f"Invalid ticker: {ticker}")
            
            quote = Quote(
                symbol=ticker,
                price=float(info.get('currentPrice') or info.get('regularMarketPrice') or 0),
                change=float(info.get('regularMarketChange') or 0),
                change_pct=float(info.get('regularMarketChangePercent') or 0),
                volume=int(info.get('regularMarketVolume') or 0),
                market_cap=int(info.get('marketCap') or 0),
                pe_ratio=float(info.get('trailingPE') or 0) if info.get('trailingPE') else None,
                dividend_yield=float(info.get('dividendYield') or 0) if info.get('dividendYield') else None,
                week_52_high=float(info.get('fiftyTwoWeekHigh') or 0),
                week_52_low=float(info.get('fiftyTwoWeekLow') or 0),
                company_name=str(info.get('longName') or info.get('shortName') or ticker),
                sector=str(info.get('sector') or 'Unknown'),
                industry=str(info.get('industry') or 'Unknown'),
                timestamp=datetime.now().isoformat(),
                status=QuoteStatus.SUCCESS
            )
            
            self._store_in_cache(cache_key, quote.to_dict())
            self.request_count += 1
            
            return quote
            
        except Exception as e:
            logger.error(f"Error fetching quote for {ticker}: {e}")
            return Quote(
                symbol=ticker, price=0.0, change=0.0, change_pct=0.0, volume=0,
                market_cap=0, pe_ratio=None, dividend_yield=None,
                week_52_high=0.0, week_52_low=0.0, company_name=ticker,
                sector='Unknown', industry='Unknown',
                timestamp=datetime.now().isoformat(), status=QuoteStatus.ERROR
            )
    
    def get_quotes_batch(self, tickers: List[str], use_cache: bool = True, parallel: bool = True) -> Dict[str, Quote]:
        """Fetch quotes for multiple tickers efficiently"""
        tickers = [t.upper().strip() for t in tickers if t]
        
        if not tickers:
            return {}
        
        logger.info(f"Fetching quotes for {len(tickers)} tickers")
        start_time = time.time()
        
        quotes = {}
        
        if parallel and len(tickers) > 3:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_ticker = {
                    executor.submit(self.get_quote, ticker, use_cache): ticker
                    for ticker in tickers
                }
                
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    try:
                        quotes[ticker] = future.result()
                    except Exception as e:
                        logger.error(f"Error fetching {ticker} in batch: {e}")
                        quotes[ticker] = self.get_quote(ticker, use_cache=False)
        else:
            for ticker in tickers:
                quotes[ticker] = self.get_quote(ticker, use_cache)
                time.sleep(self.rate_limit_delay)
        
        elapsed = time.time() - start_time
        logger.info(f"Fetched {len(quotes)} quotes in {elapsed:.2f}s")
        
        return quotes
    
    def get_historical_data(self, ticker: str, period: Union[str, Period] = Period.ONE_YEAR, include_indicators: bool = True) -> pd.DataFrame:
        """Fetch historical price data with optional technical indicators"""
        ticker = ticker.upper().strip()
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period.value if isinstance(period, Period) else period)
            
            if df.empty:
                logger.warning(f"No historical data for {ticker}")
                return pd.DataFrame()
            
            df['Returns'] = df['Close'].pct_change() * 100
            
            if include_indicators:
                df['MA_20'] = df['Close'].rolling(window=20).mean()
                df['MA_50'] = df['Close'].rolling(window=50).mean()
                df['MA_200'] = df['Close'].rolling(window=200).mean()
                
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                df['BB_Middle'] = df['Close'].rolling(window=20).mean()
                df['BB_Std'] = df['Close'].rolling(window=20).std()
                df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
                df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
            
            logger.info(f"Fetched {len(df)} historical records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def search_ticker(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for tickers by name or symbol"""
        results = []
        query = query.strip()
        
        if not query:
            return results
        
        try:
            stock = yf.Ticker(query.upper())
            info = stock.info
            
            if info and info.get('symbol'):
                results.append({
                    'symbol': info.get('symbol'),
                    'name': info.get('longName') or info.get('shortName') or query,
                    'type': info.get('quoteType', 'Unknown'),
                    'sector': info.get('sector', 'Unknown'),
                    'exchange': info.get('exchange', 'Unknown'),
                    'price': float(info.get('currentPrice') or info.get('regularMarketPrice') or 0),
                    'market_cap': int(info.get('marketCap') or 0)
                })
            
            logger.info(f"Search for '{query}' returned {len(results)} results")
            
        except Exception as e:
            logger.warning(f"Error searching for ticker {query}: {e}")
        
        return results[:max_results]


class PortfolioMarketUpdater:
    """Updates portfolio holdings with live market data"""
    
    def __init__(self, client: Optional[YahooFinanceClient] = None):
        self.client = client or YahooFinanceClient()
        logger.info("PortfolioMarketUpdater initialized")
    
    def update_portfolio_prices(self, portfolio_df: pd.DataFrame, ticker_column: str = 'ticker') -> pd.DataFrame:
        """Update portfolio DataFrame with current market prices"""
        df = portfolio_df.copy()
        
        if ticker_column not in df.columns:
            logger.warning(f"Column '{ticker_column}' not found")
            return df
        
        unique_tickers = df[ticker_column].dropna().unique().tolist()
        
        if not unique_tickers:
            return df
        
        quotes = self.client.get_quotes_batch(unique_tickers, parallel=True)
        
        def get_quote_field(ticker, field, default=0):
            quote = quotes.get(ticker)
            return getattr(quote, field, default) if quote else default
        
        df['live_price'] = df[ticker_column].apply(lambda t: get_quote_field(t, 'price'))
        df['live_change'] = df[ticker_column].apply(lambda t: get_quote_field(t, 'change'))
        df['live_change_pct'] = df[ticker_column].apply(lambda t: get_quote_field(t, 'change_pct'))
        df['company_name'] = df[ticker_column].apply(lambda t: get_quote_field(t, 'company_name', ''))
        df['sector'] = df[ticker_column].apply(lambda t: get_quote_field(t, 'sector', 'Unknown'))
        
        if 'quantity' in df.columns:
            df['live_value'] = df['quantity'] * df['live_price']
        
        if 'cost_basis' in df.columns and 'quantity' in df.columns:
            df['total_cost'] = df['quantity'] * df['cost_basis']
            df['live_gain_loss'] = df['live_value'] - df['total_cost']
            df['live_gain_loss_pct'] = (df['live_gain_loss'] / df['total_cost'] * 100).fillna(0)
        
        logger.info(f"Updated {len(df)} portfolio holdings with live data")
        
        return df


# Singleton instances
_client_instance = None
_updater_instance = None


def get_client(cache_ttl: int = 300) -> YahooFinanceClient:
    """Get or create YahooFinanceClient singleton"""
    global _client_instance
    if _client_instance is None:
        _client_instance = YahooFinanceClient(cache_ttl_seconds=cache_ttl)
    return _client_instance


def get_updater() -> PortfolioMarketUpdater:
    """Get or create PortfolioMarketUpdater singleton"""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = PortfolioMarketUpdater(get_client())
    return _updater_instance
