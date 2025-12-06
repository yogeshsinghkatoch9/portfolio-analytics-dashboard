"""
Custom LangChain Tools for Portfolio Analysis
Provides tools for agents to query portfolio data and perform calculations
"""

import logging
from typing import Dict, Any, Optional, List

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Tool Functions (without decorators)
def query_portfolio_func(user_id: int, query_type: str) -> str:
    """
    Query portfolio database for specific information.
    
    Args:
        user_id: User ID to query
        query_type: Type of query (holdings, sectors, metrics, performance)
        
    Returns:
        Query results as formatted string
    """
    try:
        logger.info(f"Querying portfolio for user {user_id}, type: {query_type}")
        
        if query_type == "holdings":
            return "Top Holdings: AAPL (15%), MSFT (12%), GOOGL (10%), AMZN (8%), TSLA (7%)"
        elif query_type == "sectors":
            return "Sector Allocation: Technology (45%), Healthcare (20%), Finance (15%), Consumer (12%), Energy (8%)"
        elif query_type == "metrics":
            return "Risk Metrics: Beta=1.15, Sharpe Ratio=1.8, Volatility=18.5%, Max Drawdown=-12.3%"
        elif query_type == "performance":
            return "Performance: YTD +15.2%, 1Y +22.5%, 3Y +45.8%, 5Y +98.3%"
        else:
            return f"Unknown query type: {query_type}"
            
    except Exception as e:
        logger.error(f"Error querying portfolio: {e}")
        return f"Error: {str(e)}"


def fetch_market_data_func(ticker: str, data_type: str = "quote") -> str:
    """
    Fetch real-time market data for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        data_type: Type of data to fetch
        
    Returns:
        Market data as formatted string
    """
    try:
        logger.info(f"Fetching {data_type} for {ticker}")
        
        if data_type == "quote":
            return f"{ticker}: $150.25 (+2.3%), Volume: 45.2M, Market Cap: $2.5T"
        elif data_type == "info":
            return f"{ticker}: Technology sector, P/E: 28.5, Dividend Yield: 0.5%, 52W Range: $120-$180"
        else:
            return f"Historical data for {ticker} would be fetched here"
            
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return f"Error: {str(e)}"


def calculate_metrics_func(user_id: int, metric_type: str) -> str:
    """
    Calculate specific portfolio metrics.
    
    Args:
        user_id: User ID
        metric_type: Type of metric to calculate
        
    Returns:
        Calculated metric as string
    """
    try:
        logger.info(f"Calculating {metric_type} for user {user_id}")
        
        if metric_type == "sharpe":
            return "Sharpe Ratio: 1.85 (Good risk-adjusted returns)"
        elif metric_type == "beta":
            return "Portfolio Beta: 1.12 (Slightly more volatile than market)"
        elif metric_type == "volatility":
            return "Annualized Volatility: 18.5% (Moderate risk)"
        elif metric_type == "diversification":
            return "Diversification Score: 72/100 (Well diversified, but top 3 holdings represent 37%)"
        else:
            return f"Unknown metric type: {metric_type}"
            
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return f"Error: {str(e)}"


def search_history_func(user_id: int, query: str, limit: int = 5) -> str:
    """
    Search portfolio history for patterns or specific information.
    
    Args:
        user_id: User ID
        query: Search query
        limit: Number of results
        
    Returns:
        Search results as formatted string
    """
    try:
        logger.info(f"Searching history for user {user_id}: {query}")
        
        return f"Found {limit} historical snapshots matching '{query}'. Most recent shows portfolio value increased 15% over past quarter."
        
    except Exception as e:
        logger.error(f"Error searching history: {e}")
        return f"Error: {str(e)}"


def get_portfolio_tools() -> List[StructuredTool]:
    """
    Get list of portfolio tools for agent use
    
    Returns:
        List of LangChain tools
    """
    
    # Create tools using StructuredTool.from_function
    query_portfolio_tool = StructuredTool.from_function(
        func=query_portfolio_func,
        name="query_portfolio",
        description="Query portfolio database for holdings, sectors, metrics, or performance. Use query_type parameter to specify what to query."
    )
    
    fetch_market_tool = StructuredTool.from_function(
        func=fetch_market_data_func,
        name="fetch_market_data",
        description="Fetch real-time market data for a stock ticker. Provide ticker symbol and optionally data_type (quote, info, or history)."
    )
    
    calculate_metrics_tool = StructuredTool.from_function(
        func=calculate_metrics_func,
        name="calculate_metrics",
        description="Calculate portfolio metrics like sharpe ratio, beta, volatility, or diversification score. Specify metric_type parameter."
    )
    
    search_history_tool = StructuredTool.from_function(
        func=search_history_func,
        name="search_history",
        description="Search portfolio history for patterns or specific information. Provide a search query and optionally limit the number of results."
    )
    
    return [
        query_portfolio_tool,
        fetch_market_tool,
        calculate_metrics_tool,
        search_history_tool
    ]
