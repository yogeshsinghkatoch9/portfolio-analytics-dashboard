"""
Yahoo Finance Integration Module - Phase 2
Real-time stock data, market updates, and live ticker information
"""

import yfinance as yf
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache
import json


class YahooFinanceClient:
    """
    Client for fetching real-time stock data from Yahoo Finance
    Includes caching, batch processing, and error handling
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize Yahoo Finance client
        
        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default 5 minutes)
        """
        self.cache_ttl = cache_ttl_seconds
        self.cache = {}
        self.last_cache_time = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid"""
        if key not in self.cache:
            return False
        
        cache_time = self.last_cache_time.get(key)
        if cache_time is None:
            return False
        
        # Handle case where cache_time might be a string
        if isinstance(cache_time, str):
            try:
                cache_time = datetime.fromisoformat(cache_time.replace('Z', '+00:00'))
            except:
                return False
        
        try:
            elapsed = (datetime.now() - cache_time).total_seconds()
            return elapsed < self.cache_ttl
        except:
            return False
    
    def get_quote(self, ticker: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetch real-time quote for a single ticker
        
        Returns:
        {
            'symbol': str,
            'price': float,
            'change': float,
            'change_pct': float,
            'volume': int,
            'market_cap': float,
            'pe_ratio': float,
            'dividend_yield': float,
            '52w_high': float,
            '52w_low': float,
            'open': float,
            'close': float,
            'bid': float,
            'ask': float,
            'timestamp': str,
            'status': 'success' | 'cached' | 'error'
        }
        """
        ticker = ticker.upper()
        cache_key = ticker
        
        # Check cache first
        if use_cache and self._is_cache_valid(cache_key):
            result = self.cache[cache_key].copy()
            result['status'] = 'cached'
            return result
        
        try:
            # Create Ticker with cache disabled to avoid yfinance datetime bug
            stock = yf.Ticker(ticker)
            # Override the session to disable caching
            stock._session = None
            info = stock.info
            
            # Handle missing data gracefully
            quote_data = {
                'symbol': ticker,
                'price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
                'change': info.get('regularMarketChange', 0),
                'change_pct': info.get('regularMarketChangePercent', 0),
                'volume': info.get('regularMarketVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                '52w_high': info.get('fiftyTwoWeekHigh', 0),
                '52w_low': info.get('fiftyTwoWeekLow', 0),
                'open': info.get('regularMarketOpen', 0),
                'close': info.get('regularMarketPrice', 0),
                'bid': info.get('bid', 0),
                'ask': info.get('ask', 0),
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
            # Cache the result
            self.cache[cache_key] = quote_data.copy()
            self.last_cache_time[cache_key] = datetime.now()
            
            return quote_data
            
        except Exception as e:
            return {
                'symbol': ticker,
                'error': str(e),
                'status': 'error',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_quotes_batch(self, tickers: List[str], use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Fetch quotes for multiple tickers
        
        Args:
            tickers: List of ticker symbols
            use_cache: Use cache if available
        
        Returns:
            Dictionary of {ticker: quote_data}
        """
        quotes = {}
        
        for ticker in tickers:
            quotes[ticker] = self.get_quote(ticker, use_cache)
        
        return quotes
    
    def get_historical_data(self, ticker: str, period: str = '1y', interval: str = '1d') -> pd.DataFrame:
        """
        Fetch historical price data
        
        Args:
            ticker: Stock ticker
            period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
            interval: '1m', '5m', '15m', '30m', '60m', '1d', '1wk', '1mo'
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Dividends, Stock Splits
        """
        try:
            stock = yf.Ticker(ticker.upper())
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                return pd.DataFrame()
            
            # Add additional metrics
            df['Returns'] = df['Close'].pct_change() * 100
            df['MA_20'] = df['Close'].rolling(window=20).mean()
            df['MA_50'] = df['Close'].rolling(window=50).mean()
            
            return df
            
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_dividends(self, ticker: str) -> pd.Series:
        """Get dividend history for a ticker"""
        try:
            stock = yf.Ticker(ticker.upper())
            return stock.dividends
        except Exception as e:
            print(f"Error fetching dividends for {ticker}: {e}")
            return pd.Series()
    
    def search_ticker(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for ticker by name or symbol
        Limited support - returns best guess
        
        Returns:
            List of matching tickers with basic info and current price
        """
        results = []
        
        try:
            # Try direct ticker lookup
            ticker = yf.Ticker(query.upper())
            info = ticker.info
            
            if info and 'symbol' in info:
                # Get current price
                try:
                    price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                except:
                    price = 0
                
                results.append({
                    'symbol': info.get('symbol'),
                    'name': info.get('longName', info.get('shortName', query)),
                    'type': info.get('quoteType', 'Unknown'),
                    'sector': info.get('sector', 'Unknown'),
                    'exchange': info.get('exchange', 'Unknown'),
                    'price': float(price) if price else 0
                })
        
        except Exception as e:
            print(f"Error searching for ticker {query}: {e}")
        
        return results
    
    def analyze_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Comprehensive ticker analysis with multiple data points
        """
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            # Get historical data for metrics
            hist = stock.history(period='1y')
            
            # Calculate returns
            if len(hist) > 0:
                year_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100)
                volatility = hist['Close'].pct_change().std() * np.sqrt(252) * 100
            else:
                year_return = 0
                volatility = 0
            
            analysis = {
                'symbol': ticker.upper(),
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'peg_ratio': info.get('pegRatio', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                '52w_high': info.get('fiftyTwoWeekHigh', 0),
                '52w_low': info.get('fiftyTwoWeekLow', 0),
                'avg_volume': info.get('averageVolume', 0),
                'current_volume': info.get('regularMarketVolume', 0),
                'year_return_pct': round(year_return, 2),
                'volatility_pct': round(volatility, 2),
                'recommendation': info.get('recommendationKey', 'none'),
                'target_price': info.get('targetMeanPrice', 0),
                'analyst_count': info.get('numberOfAnalystOpinions', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            return {
                'symbol': ticker.upper(),
                'error': str(e)
            }


class PortfolioMarketUpdater:
    """
    Updates portfolio holdings with live market data
    """
    
    def __init__(self, client: Optional[YahooFinanceClient] = None):
        """Initialize with Yahoo Finance client"""
        self.client = client or YahooFinanceClient()
    
    def update_portfolio_prices(self, portfolio_df: pd.DataFrame) -> pd.DataFrame:
        """
        Update portfolio with current market prices
        Adds live_price, live_change, live_change_pct columns
        """
        df = portfolio_df.copy()
        
        if 'ticker' not in df.columns:
            return df
        
        # Get quotes for all tickers
        unique_tickers = df['ticker'].dropna().unique().tolist()
        quotes = self.client.get_quotes_batch(unique_tickers)
        
        # Create mapping of ticker to quote data
        df['live_price'] = df['ticker'].map(lambda t: quotes.get(t, {}).get('price', 0))
        df['live_change'] = df['ticker'].map(lambda t: quotes.get(t, {}).get('change', 0))
        df['live_change_pct'] = df['ticker'].map(lambda t: quotes.get(t, {}).get('change_pct', 0))
        df['company_name'] = df['ticker'].map(lambda t: quotes.get(t, {}).get('company_name', ''))
        df['sector'] = df['ticker'].map(lambda t: quotes.get(t, {}).get('sector', ''))
        
        # Calculate live value and P&L
        df['live_value'] = df['quantity'] * df['live_price']
        if 'cost_basis' in df.columns:
            df['live_gain_loss'] = df['live_value'] - df['cost_basis']
            df['live_gain_loss_pct'] = (df['live_gain_loss'] / df['cost_basis'] * 100).fillna(0)
        
        return df
    
    def get_top_movers(self, portfolio_df: pd.DataFrame, top_n: int = 5) -> Dict[str, List[Dict]]:
        """
        Get top gainers and losers from portfolio
        """
        df = portfolio_df.copy()
        
        if 'live_change_pct' not in df.columns:
            df = self.update_portfolio_prices(df)
        
        gainers = df.nlargest(top_n, 'live_change_pct')[
            ['ticker', 'company_name', 'live_price', 'live_change', 'live_change_pct', 'live_value']
        ].to_dict('records')
        
        losers = df.nsmallest(top_n, 'live_change_pct')[
            ['ticker', 'company_name', 'live_price', 'live_change', 'live_change_pct', 'live_value']
        ].to_dict('records')
        
        return {
            'gainers': gainers,
            'losers': losers,
            'timestamp': datetime.now().isoformat()
        }


class MarketAlerts:
    """
    Price alerts and market notifications
    """
    
    def __init__(self, client: YahooFinanceClient):
        """Initialize alerts system"""
        self.client = client
        self.alerts = {}
    
    def set_price_alert(self, ticker: str, target_price: float, 
                       alert_type: str = 'above') -> Dict[str, Any]:
        """
        Set a price alert for a ticker
        alert_type: 'above' or 'below'
        """
        alert = {
            'ticker': ticker.upper(),
            'target_price': target_price,
            'type': alert_type,
            'created': datetime.now().isoformat(),
            'triggered': False
        }
        
        if ticker not in self.alerts:
            self.alerts[ticker] = []
        
        self.alerts[ticker].append(alert)
        return alert
    
    def check_alerts(self, portfolio_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check if any alerts have been triggered"""
        triggered = []
        
        for ticker, alert_list in self.alerts.items():
            quote = self.client.get_quote(ticker)
            current_price = quote.get('price', 0)
            
            for alert in alert_list:
                if not alert['triggered']:
                    if alert['type'] == 'above' and current_price >= alert['target_price']:
                        alert['triggered'] = True
                        triggered.append({
                            **alert,
                            'current_price': current_price,
                            'triggered_at': datetime.now().isoformat()
                        })
                    elif alert['type'] == 'below' and current_price <= alert['target_price']:
                        alert['triggered'] = True
                        triggered.append({
                            **alert,
                            'current_price': current_price,
                            'triggered_at': datetime.now().isoformat()
                        })
        
        return triggered


import numpy as np

# Module-level singleton instance
_client_instance = None

def get_client() -> 'YahooFinanceClient':
    """Get or create the module-level YahooFinanceClient singleton"""
    global _client_instance
    if _client_instance is None:
        _client_instance = YahooFinanceClient()
    return _client_instance

