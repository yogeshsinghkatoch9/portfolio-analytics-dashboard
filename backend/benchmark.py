"""
Benchmark Service for VisionWealth
Handles fetching and processing benchmark data (e.g., S&P 500)
"""

import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime, timedelta
from functools import lru_cache

class BenchmarkService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_sp500_data(period: str = "1y") -> Dict[str, Any]:
        """
        Fetch S&P 500 (SPY) historical data
        Cached to avoid excessive API calls
        """
        try:
            # Use SPY as proxy for S&P 500
            spy = yf.Ticker("SPY")
            hist = spy.history(period=period)
            
            if hist.empty:
                return {"dates": [], "values": []}
            
            # Normalize to percentage change
            start_price = hist['Close'].iloc[0]
            hist['pct_change'] = ((hist['Close'] - start_price) / start_price) * 100
            
            return {
                "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                "values": hist['pct_change'].round(2).tolist(),
                "current_price": round(hist['Close'].iloc[-1], 2),
                "period_return": round(hist['pct_change'].iloc[-1], 2)
            }
            
        except Exception as e:
            print(f"Error fetching benchmark data: {e}")
            return {"dates": [], "values": []}

    @staticmethod
    def compare_portfolio(portfolio_dates: List[str], portfolio_values: List[float]) -> Dict[str, Any]:
        """
        Align benchmark data with portfolio data for comparison
        """
        # This would be more complex in a real app with exact date matching
        # For now, we'll just return the 1-year SPY trend
        return BenchmarkService.get_sp500_data()
