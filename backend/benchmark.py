"""
Benchmark Service for VisionWealth
Handles fetching and processing benchmark data with multiple indices,
performance comparison, and statistical analysis.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# CONSTANTS AND ENUMS
# ========================================

class BenchmarkIndex(str, Enum):
    """Available benchmark indices"""
    SP500 = "SPY"  # S&P 500
    NASDAQ = "QQQ"  # Nasdaq 100
    DOW = "DIA"  # Dow Jones
    RUSSELL2000 = "IWM"  # Russell 2000
    TOTAL_MARKET = "VTI"  # Total US Market
    INTERNATIONAL = "VXUS"  # International
    EMERGING = "VWO"  # Emerging Markets
    BONDS = "AGG"  # US Aggregate Bonds
    TIPS = "TIP"  # Treasury Inflation-Protected
    GOLD = "GLD"  # Gold
    REITS = "VNQ"  # Real Estate


BENCHMARK_NAMES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "DIA": "Dow Jones",
    "IWM": "Russell 2000",
    "VTI": "Total US Market",
    "VXUS": "International",
    "VWO": "Emerging Markets",
    "AGG": "US Bonds",
    "TIP": "TIPS",
    "GLD": "Gold",
    "VNQ": "REITs"
}


# ========================================
# BENCHMARK SERVICE
# ========================================

class BenchmarkService:
    """
    Service for fetching and analyzing benchmark data.
    
    Features:
    - Multiple benchmark indices
    - Historical data with caching
    - Performance comparison
    - Statistical analysis
    - Correlation calculations
    """
    
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize benchmark service.
        
        Args:
            cache_duration: Cache duration in seconds (default 1 hour)
        """
        self.cache_duration = cache_duration
        self._cache = {}
        self._cache_timestamps = {}
        logger.info("BenchmarkService initialized")
    
    def _is_cache_valid(self, key: str) -> bool:
        """
        Check if cached data is still valid.
        
        Args:
            key: Cache key
        
        Returns:
            True if cache is valid
        """
        if key not in self._cache_timestamps:
            return False
        
        age = (datetime.now() - self._cache_timestamps[key]).total_seconds()
        return age < self.cache_duration
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """
        Get data from cache if valid.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None
        """
        if self._is_cache_valid(key):
            logger.debug(f"Cache hit: {key}")
            return self._cache.get(key)
        return None
    
    def _set_cache(self, key: str, value: Any):
        """
        Store data in cache.
        
        Args:
            key: Cache key
            value: Data to cache
        """
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now()
        logger.debug(f"Cached: {key}")
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cache cleared")
    
    def get_benchmark_data(
        self,
        ticker: str = "SPY",
        period: str = "1y",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        Fetch benchmark historical data.
        
        Args:
            ticker: Benchmark ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            Dictionary with benchmark data and statistics
        """
        cache_key = f"{ticker}_{period}_{interval}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        try:
            logger.info(f"Fetching benchmark data: {ticker} ({period})")
            
            # Fetch data from yfinance
            benchmark = yf.Ticker(ticker)
            hist = benchmark.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"No data returned for {ticker}")
                return self._empty_response(ticker)
            
            # Calculate metrics
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            
            # Percentage change from start
            hist['pct_change'] = ((hist['Close'] - start_price) / start_price) * 100
            
            # Daily returns
            hist['daily_return'] = hist['Close'].pct_change() * 100
            
            # Calculate statistics
            period_return = ((end_price - start_price) / start_price) * 100
            volatility = hist['daily_return'].std()
            max_price = hist['Close'].max()
            min_price = hist['Close'].min()
            avg_price = hist['Close'].mean()
            
            # Calculate drawdown
            cumulative = (1 + hist['daily_return'] / 100).cumprod()
            running_max = cumulative.cummax()
            drawdown = ((cumulative - running_max) / running_max * 100)
            max_drawdown = drawdown.min()
            
            # Prepare response
            response = {
                'ticker': ticker,
                'name': BENCHMARK_NAMES.get(ticker, ticker),
                'period': period,
                'interval': interval,
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'close_prices': hist['Close'].round(2).tolist(),
                'pct_changes': hist['pct_change'].round(2).tolist(),
                'daily_returns': hist['daily_return'].round(2).fillna(0).tolist(),
                'volume': hist['Volume'].tolist(),
                'current_price': round(end_price, 2),
                'start_price': round(start_price, 2),
                'period_return': round(period_return, 2),
                'period_return_annualized': self._annualize_return(period_return, period),
                'volatility': round(volatility, 2),
                'volatility_annualized': round(volatility * np.sqrt(252), 2),  # Annualized
                'max_price': round(max_price, 2),
                'min_price': round(min_price, 2),
                'avg_price': round(avg_price, 2),
                'max_drawdown': round(max_drawdown, 2),
                'sharpe_ratio': self._calculate_sharpe_ratio(hist['daily_return']),
                'data_points': len(hist),
                'fetched_at': datetime.now().isoformat()
            }
            
            # Cache the response
            self._set_cache(cache_key, response)
            
            logger.info(f"Benchmark data fetched: {ticker}, return: {period_return:.2f}%")
            
            return response
        
        except Exception as e:
            logger.error(f"Error fetching benchmark data for {ticker}: {e}")
            return self._empty_response(ticker)
    
    def _empty_response(self, ticker: str) -> Dict[str, Any]:
        """
        Return empty response structure.
        
        Args:
            ticker: Benchmark ticker
        
        Returns:
            Empty response dictionary
        """
        return {
            'ticker': ticker,
            'name': BENCHMARK_NAMES.get(ticker, ticker),
            'dates': [],
            'close_prices': [],
            'pct_changes': [],
            'daily_returns': [],
            'volume': [],
            'error': 'No data available'
        }
    
    def _annualize_return(self, period_return: float, period: str) -> float:
        """
        Annualize a period return.
        
        Args:
            period_return: Period return percentage
            period: Period string
        
        Returns:
            Annualized return percentage
        """
        # Map periods to approximate days
        period_days = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90,
            '6mo': 180, '1y': 365, '2y': 730, '5y': 1825,
            'ytd': (datetime.now() - datetime(datetime.now().year, 1, 1)).days
        }
        
        days = period_days.get(period, 365)
        years = days / 365
        
        if years == 0:
            return period_return
        
        # Compound annual growth rate
        annualized = (((1 + period_return / 100) ** (1 / years)) - 1) * 100
        
        return round(annualized, 2)
    
    def _calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: Daily returns series
            risk_free_rate: Annual risk-free rate (default 2%)
        
        Returns:
            Sharpe ratio
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        # Convert annual risk-free rate to daily
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        daily_rf_pct = daily_rf * 100
        
        # Calculate excess returns
        excess_returns = returns - daily_rf_pct
        
        # Sharpe ratio
        sharpe = excess_returns.mean() / returns.std()
        
        # Annualize
        sharpe_annualized = sharpe * np.sqrt(252)
        
        return round(sharpe_annualized, 2)
    
    def get_sp500_data(self, period: str = "1y") -> Dict[str, Any]:
        """
        Fetch S&P 500 (SPY) historical data.
        
        Convenience method for S&P 500.
        
        Args:
            period: Time period
        
        Returns:
            S&P 500 benchmark data
        """
        return self.get_benchmark_data("SPY", period)
    
    def get_multiple_benchmarks(
        self,
        tickers: List[str],
        period: str = "1y"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch data for multiple benchmarks.
        
        Args:
            tickers: List of benchmark tickers
            period: Time period
        
        Returns:
            Dictionary mapping ticker to benchmark data
        """
        results = {}
        
        for ticker in tickers:
            results[ticker] = self.get_benchmark_data(ticker, period)
        
        return results
    
    def compare_portfolio_to_benchmark(
        self,
        portfolio_dates: List[str],
        portfolio_values: List[float],
        benchmark_ticker: str = "SPY",
        period: str = "1y"
    ) -> Dict[str, Any]:
        """
        Compare portfolio performance to benchmark.
        
        Args:
            portfolio_dates: List of portfolio dates
            portfolio_values: List of portfolio values
            benchmark_ticker: Benchmark ticker
            period: Time period
        
        Returns:
            Comparison analysis
        """
        try:
            logger.info(f"Comparing portfolio to {benchmark_ticker}")
            
            # Get benchmark data
            benchmark_data = self.get_benchmark_data(benchmark_ticker, period)
            
            if not benchmark_data.get('dates'):
                return {'error': 'Benchmark data not available'}
            
            # Convert portfolio data to DataFrame
            portfolio_df = pd.DataFrame({
                'date': pd.to_datetime(portfolio_dates),
                'value': portfolio_values
            })
            
            # Normalize portfolio values to percentage change
            start_value = portfolio_df['value'].iloc[0]
            portfolio_df['pct_change'] = (
                (portfolio_df['value'] - start_value) / start_value * 100
            )
            
            # Calculate portfolio return
            portfolio_return = portfolio_df['pct_change'].iloc[-1]
            
            # Calculate portfolio volatility
            portfolio_df['daily_return'] = portfolio_df['value'].pct_change() * 100
            portfolio_volatility = portfolio_df['daily_return'].std()
            
            # Get benchmark return
            benchmark_return = benchmark_data['period_return']
            benchmark_volatility = benchmark_data['volatility']
            
            # Calculate relative performance
            outperformance = portfolio_return - benchmark_return
            
            # Calculate correlation
            correlation = self._calculate_correlation(
                portfolio_df, benchmark_data
            )
            
            # Calculate beta
            beta = self._calculate_beta(
                portfolio_df, benchmark_data
            )
            
            return {
                'portfolio': {
                    'return': round(portfolio_return, 2),
                    'volatility': round(portfolio_volatility, 2),
                    'sharpe_ratio': self._calculate_sharpe_ratio(
                        portfolio_df['daily_return']
                    )
                },
                'benchmark': {
                    'ticker': benchmark_ticker,
                    'name': benchmark_data['name'],
                    'return': round(benchmark_return, 2),
                    'volatility': round(benchmark_volatility, 2),
                    'sharpe_ratio': benchmark_data['sharpe_ratio']
                },
                'comparison': {
                    'outperformance': round(outperformance, 2),
                    'outperformance_pct': round(
                        (outperformance / abs(benchmark_return) * 100)
                        if benchmark_return != 0 else 0, 2
                    ),
                    'correlation': round(correlation, 2),
                    'beta': round(beta, 2),
                    'risk_adjusted_outperformance': round(
                        (portfolio_return - benchmark_return) /
                        portfolio_volatility if portfolio_volatility > 0 else 0,
                        2
                    )
                },
                'interpretation': self._interpret_comparison(
                    outperformance, correlation, beta
                )
            }
        
        except Exception as e:
            logger.error(f"Error comparing portfolio to benchmark: {e}")
            return {'error': str(e)}
    
    def _calculate_correlation(
        self,
        portfolio_df: pd.DataFrame,
        benchmark_data: Dict[str, Any]
    ) -> float:
        """
        Calculate correlation between portfolio and benchmark.
        
        Args:
            portfolio_df: Portfolio DataFrame
            benchmark_data: Benchmark data
        
        Returns:
            Correlation coefficient
        """
        try:
            # Align dates
            benchmark_df = pd.DataFrame({
                'date': pd.to_datetime(benchmark_data['dates']),
                'return': benchmark_data['daily_returns']
            })
            
            # Merge on dates
            merged = pd.merge(
                portfolio_df[['date', 'daily_return']],
                benchmark_df,
                on='date',
                how='inner'
            )
            
            if len(merged) < 2:
                return 0.0
            
            # Calculate correlation
            correlation = merged['daily_return'].corr(merged['return'])
            
            return correlation if not pd.isna(correlation) else 0.0
        
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0
    
    def _calculate_beta(
        self,
        portfolio_df: pd.DataFrame,
        benchmark_data: Dict[str, Any]
    ) -> float:
        """
        Calculate portfolio beta relative to benchmark.
        
        Args:
            portfolio_df: Portfolio DataFrame
            benchmark_data: Benchmark data
        
        Returns:
            Beta coefficient
        """
        try:
            # Align dates
            benchmark_df = pd.DataFrame({
                'date': pd.to_datetime(benchmark_data['dates']),
                'return': benchmark_data['daily_returns']
            })
            
            # Merge on dates
            merged = pd.merge(
                portfolio_df[['date', 'daily_return']],
                benchmark_df,
                on='date',
                how='inner'
            )
            
            if len(merged) < 2:
                return 1.0
            
            # Calculate covariance and variance
            covariance = merged['daily_return'].cov(merged['return'])
            benchmark_variance = merged['return'].var()
            
            if benchmark_variance == 0:
                return 1.0
            
            beta = covariance / benchmark_variance
            
            return beta if not pd.isna(beta) else 1.0
        
        except Exception as e:
            logger.error(f"Error calculating beta: {e}")
            return 1.0
    
    def _interpret_comparison(
        self,
        outperformance: float,
        correlation: float,
        beta: float
    ) -> str:
        """
        Generate interpretation of comparison results.
        
        Args:
            outperformance: Outperformance percentage
            correlation: Correlation coefficient
            beta: Beta coefficient
        
        Returns:
            Interpretation string
        """
        interpretations = []
        
        # Outperformance
        if outperformance > 0:
            interpretations.append(
                f"Portfolio outperformed benchmark by {abs(outperformance):.2f}%"
            )
        else:
            interpretations.append(
                f"Portfolio underperformed benchmark by {abs(outperformance):.2f}%"
            )
        
        # Correlation
        if correlation > 0.8:
            interpretations.append("Highly correlated with benchmark")
        elif correlation > 0.5:
            interpretations.append("Moderately correlated with benchmark")
        elif correlation > 0:
            interpretations.append("Weakly correlated with benchmark")
        else:
            interpretations.append("Negatively correlated with benchmark")
        
        # Beta
        if beta > 1.2:
            interpretations.append("High volatility relative to benchmark")
        elif beta > 0.8:
            interpretations.append("Similar volatility to benchmark")
        else:
            interpretations.append("Low volatility relative to benchmark")
        
        return ". ".join(interpretations) + "."
    
    def get_benchmark_summary(self, period: str = "1y") -> Dict[str, Any]:
        """
        Get summary of major benchmarks.
        
        Args:
            period: Time period
        
        Returns:
            Summary of benchmark performances
        """
        major_benchmarks = ["SPY", "QQQ", "DIA", "IWM", "AGG"]
        
        summaries = []
        
        for ticker in major_benchmarks:
            data = self.get_benchmark_data(ticker, period)
            
            if not data.get('error'):
                summaries.append({
                    'ticker': ticker,
                    'name': data['name'],
                    'return': data['period_return'],
                    'volatility': data['volatility_annualized'],
                    'sharpe_ratio': data['sharpe_ratio'],
                    'current_price': data['current_price']
                })
        
        # Sort by return
        summaries.sort(key=lambda x: x['return'], reverse=True)
        
        return {
            'period': period,
            'benchmarks': summaries,
            'best_performer': summaries[0] if summaries else None,
            'worst_performer': summaries[-1] if summaries else None,
            'fetched_at': datetime.now().isoformat()
        }


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

def get_sp500_data(period: str = "1y") -> Dict[str, Any]:
    """
    Convenience function to get S&P 500 data.
    
    Args:
        period: Time period
    
    Returns:
        S&P 500 benchmark data
    """
    service = BenchmarkService()
    return service.get_sp500_data(period)


def compare_to_sp500(
    portfolio_dates: List[str],
    portfolio_values: List[float],
    period: str = "1y"
) -> Dict[str, Any]:
    """
    Convenience function to compare portfolio to S&P 500.
    
    Args:
        portfolio_dates: Portfolio dates
        portfolio_values: Portfolio values
        period: Time period
    
    Returns:
        Comparison analysis
    """
    service = BenchmarkService()
    return service.compare_portfolio_to_benchmark(
        portfolio_dates,
        portfolio_values,
        "SPY",
        period
    )


# Export all public items
__all__ = [
    'BenchmarkService',
    'BenchmarkIndex',
    'BENCHMARK_NAMES',
    'get_sp500_data',
    'compare_to_sp500'
]
