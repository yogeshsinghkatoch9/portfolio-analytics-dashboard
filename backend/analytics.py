"""
Advanced Portfolio Analytics Module
Provides risk analysis, rebalancing suggestions, and optimization tools
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from scipy import stats
from datetime import datetime, timedelta


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe Ratio: (Return - Risk Free Rate) / Standard Deviation
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_return = returns.mean() - (risk_free_rate / 252)  # Daily risk-free rate
    return (excess_return / returns.std()) * np.sqrt(252)  # Annualized


def calculate_portfolio_beta(portfolio_returns: pd.Series, market_returns: pd.Series) -> float:
    """
    Calculate Beta: Covariance(portfolio, market) / Variance(market)
    """
    if len(portfolio_returns) < 2 or len(market_returns) < 2:
        return 1.0
    
    covariance = np.cov(portfolio_returns, market_returns)[0][1]
    market_variance = np.var(market_returns)
    
    if market_variance == 0:
        return 1.0
    
    return covariance / market_variance


def calculate_volatility(returns: pd.Series) -> float:
    """
    Calculate annualized volatility (standard deviation)
    """
    if len(returns) == 0:
        return 0.0
    
    return returns.std() * np.sqrt(252)  # Annualized


def calculate_diversification_score(holdings: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate portfolio diversification metrics
    """
    if len(holdings) == 0:
        return {
            'score': 0,
            'concentration_risk': 'HIGH',
            'num_holdings': 0,
            'herfindahl_index': 1.0
        }
    
    # Herfindahl-Hirschman Index (HHI) - lower is more diversified
    weights = holdings['Assets (%)'] / 100
    hhi = (weights ** 2).sum()
    
    # Diversification score (0-100, higher is better)
    # HHI ranges from 1/n to 1, where n is number of holdings
    min_hhi = 1 / len(holdings)
    diversification_score = (1 - (hhi - min_hhi) / (1 - min_hhi)) * 100
    
    # Concentration risk assessment
    top_5_holdings = holdings.nlargest(5, 'Assets (%)')
    top_5_weight = top_5_holdings['Assets (%)'].sum()
    if top_5_weight > 70:
        concentration = 'HIGH'
    elif top_5_weight > 50:
        concentration = 'MEDIUM'
    else:
        concentration = 'LOW'
    
    return {
        'score': round(diversification_score, 2),
        'concentration_risk': concentration,
        'num_holdings': len(holdings),
        'herfindahl_index': round(hhi, 4),
        'top_5_concentration': round(top_5_weight, 2)
    }


def suggest_rebalancing(current_allocation: pd.DataFrame, target_weights: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Generate rebalancing recommendations based on target allocation
    """
    suggestions = []
    
    for symbol, target_pct in target_weights.items():
        current = current_allocation[current_allocation['Symbol'] == symbol]
        
        if len(current) == 0:
            suggestions.append({
                'symbol': symbol,
                'action': 'BUY',
                'current_weight': 0,
                'target_weight': target_pct,
                'difference': target_pct,
                'priority': 'HIGH' if target_pct > 5 else 'MEDIUM'
            })
        else:
            current_pct = current['Assets (%)'].iloc[0]
            difference = target_pct - current_pct
            
            if abs(difference) > 2:  # Only suggest if difference > 2%
                suggestions.append({
                    'symbol': symbol,
                    'action': 'BUY' if difference > 0 else 'SELL',
                    'current_weight': round(current_pct, 2),
                    'target_weight': target_pct,
                    'difference': round(abs(difference), 2),
                    'priority': 'HIGH' if abs(difference) > 5 else 'MEDIUM'
                })
    
    return sorted(suggestions, key=lambda x: x['difference'], reverse=True)


def identify_tax_loss_harvesting(holdings: pd.DataFrame, tax_threshold: float = -1000) -> List[Dict[str, Any]]:
    """
    Identify tax loss harvesting opportunities
    """
    opportunities = []
    
    # Filter holdings with losses
    losers = holdings[holdings['NFS G/L ($)'] < tax_threshold].copy()
    
    for _, holding in losers.iterrows():
        opportunities.append({
            'symbol': holding['Symbol'],
            'description': holding.get('Description', ''),
            'current_loss': round(holding['NFS G/L ($)'], 2),
            'loss_percentage': round(holding['NFS G/L (%)'], 2),
            'holding_value': round(holding['Value ($)'], 2),
            'recommendation': 'Consider selling to realize loss for tax purposes',
            'estimated_tax_benefit': round(abs(holding['NFS G/L ($)']) * 0.24, 2)  # Assuming 24% tax bracket
        })
    
    return sorted(opportunities, key=lambda x: x['current_loss'])


def calculate_risk_metrics(portfolio: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate comprehensive risk metrics for the portfolio
    """
    total_value = portfolio['Value ($)'].sum()
    
    # Value at Risk (VaR) - simplified using historical volatility
    returns_std = portfolio['1-Day Price Change (%)'].std() / 100
    var_95 = total_value * returns_std * 1.65  # 95% confidence
    var_99 = total_value * returns_std * 2.33  # 99% confidence
    
    # Downside deviation
    negative_returns = portfolio[portfolio['1-Day Price Change (%)'] < 0]['1-Day Price Change (%)'] / 100
    downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
    
    # Maximum drawdown approximation
    max_loss = portfolio['NFS G/L ($)'].min()
    
    # Calculate portfolio volatility with fallback
    portfolio_vol = returns_std * 100 * np.sqrt(252) if not np.isnan(returns_std) else 15.0  # Default 15% if no data
    
    return {
        'value_at_risk_95': round(var_95, 2) if not np.isnan(var_95) else 0,
        'value_at_risk_99': round(var_99, 2) if not np.isnan(var_99) else 0,
        'downside_deviation': round(downside_deviation * 100, 2) if not np.isnan(downside_deviation) else 0,
        'max_single_position_loss': round(max_loss, 2) if not np.isnan(max_loss) else 0,
        'total_at_risk': round(portfolio[portfolio['NFS G/L ($)'] < 0]['Value ($)'].sum(), 2),
        'portfolio_volatility': round(portfolio_vol, 2),
        'volatility': round(portfolio_vol / 100, 4)  # As decimal for frontend (e.g., 0.15 for 15%)
    }


def generate_sector_allocation(portfolio: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate sector-based allocation.
    Attempts to fetch real sector from yfinance for top holdings.
    """
    try:
        import yfinance as yf
        
        # 1. Aggregate by existing 'Asset Type' first as fallback
        type_data = portfolio.groupby('Asset Type')['Value ($)'].sum().to_dict()
        
        # 2. For Stocks/ETFs, try to get real Sector
        # Limit to top 15 holdings to keep speed reasonable
        stocks = portfolio[
            (portfolio['Asset Type'].isin(['Stock', 'ETF', 'Equity'])) & 
            (portfolio['Value ($)'] > 0)
        ].nlargest(15, 'Value ($)')
        
        sector_map = {}
        processed_value = 0
        total_value = portfolio['Value ($)'].sum()
        
        if not stocks.empty and total_value > 0:
            symbols = stocks['Symbol'].unique().tolist()
            
            # Helper to normalize sector names
            def norm(s): return s.replace(' ', '_').replace('Services', 'Svc') if s else 'Unknown'
            
            for sym in symbols:
                try:
                    # Using individual Ticker often safer for .info than batch in some versions
                    # But batch is faster. Let's try Ticker first for reliability on 'sector'
                    info = yf.Ticker(sym).info
                    sector = info.get('sector', 'Unknown')
                    if sector == 'Unknown':
                         # Fallback to category or type
                         sector = info.get('quoteType', 'Other')
                    
                    val = stocks[stocks['Symbol'] == sym]['Value ($)'].sum()
                    sector_map[sector] = sector_map.get(sector, 0) + val
                    processed_value += val
                except:
                    pass
            
            # Add "Other/Unknown" for the rest of the portfolio
            remaining = total_value - processed_value
            if remaining > 0:
                sector_map['Other'] = sector_map.get('Other', 0) + remaining
                
            # Convert to list
            sector_data = [{'sector': k, 'value': round(v, 2), 'percent': round(v/total_value*100, 2)} for k,v in sector_map.items()]
            sector_data.sort(key=lambda x: x['value'], reverse=True)
            
            return {
                'sectors': sector_data,
                'most_allocated': sector_data[0]['sector'] if sector_data else 'N/A',
                'least_allocated': sector_data[-1]['sector'] if sector_data else 'N/A',
                'sector_count': len(sector_data)
            }
            
        else:
             # Fallback to Asset Type if no stocks/fetch fails
             fallback_data = [{'sector': k, 'value': round(v, 2), 'percent': round(v/total_value*100, 2)} for k,v in type_data.items() if total_value > 0]
             return {
                'sectors': fallback_data,
                'most_allocated': 'N/A', 
                'least_allocated': 'N/A',
                'sector_count': len(fallback_data)
            }
            
    except Exception as e:
        print(f"Sector Alloc Error: {e}")
        return {'sectors': [], 'most_allocated': 'Error', 'least_allocated': 'Error', 'sector_count': 0}


def optimize_asset_allocation(portfolio: pd.DataFrame, risk_tolerance: str = 'moderate') -> Dict[str, Any]:
    """
    Suggest optimal asset allocation based on risk tolerance
    Target allocations based on modern portfolio theory
    """
    # Target allocations by risk profile
    ALLOCATIONS = {
        'conservative': {
            'Equity': 40,
            'Fixed Income': 50,
            'Cash': 10
        },
        'moderate': {
            'Equity': 60,
            'Fixed Income': 30,
            'Cash': 10
        },
        'aggressive': {
            'Equity': 80,
            'Fixed Income': 15,
            'Cash': 5
        }
    }
    
    target = ALLOCATIONS.get(risk_tolerance, ALLOCATIONS['moderate'])
    
    # Current allocation by asset type
    current_allocation = portfolio.groupby('Asset Type')['Assets (%)'].sum().to_dict()
    
    recommendations = []
    for asset_type, target_pct in target.items():
        current_pct = current_allocation.get(asset_type, 0)
        difference = target_pct - current_pct
        
        if abs(difference) > 5:
            recommendations.append({
                'asset_type': asset_type,
                'current': round(current_pct, 2),
                'target': target_pct,
                'difference': round(difference, 2),
                'action': 'INCREASE' if difference > 0 else 'DECREASE'
            })
    
    return {
        'risk_profile': risk_tolerance,
        'target_allocation': target,
        'current_allocation': {k: round(v, 2) for k, v in current_allocation.items()},
        'recommendations': recommendations
    }


def calculate_dividend_metrics(portfolio: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate dividend-related metrics and projections
    """
    total_value = portfolio['Value ($)'].sum()
    total_annual_income = portfolio['Est Annual Income ($)'].sum()
    
    # Dividend-paying stocks
    dividend_stocks = portfolio[portfolio['Est Annual Income ($)'] > 0]
    
    # Dividend growth estimate (simplified)
    avg_yield = (total_annual_income / total_value * 100) if total_value > 0 else 0
    
    # Top dividend payers
    top_dividend_stocks = dividend_stocks.nlargest(10, 'Est Annual Income ($)')[
        ['Symbol', 'Description', 'Est Annual Income ($)', 'Current Yld/Dist Rate (%)']
    ].to_dict('records')
    
    return {
        'total_annual_income': round(total_annual_income, 2),
        'average_yield': round(avg_yield, 2),
        'dividend_stocks_count': len(dividend_stocks),
        'monthly_income': round(total_annual_income / 12, 2),
        'quarterly_income': round(total_annual_income / 4, 2),
        'top_dividend_payers': top_dividend_stocks,
        'income_diversity': len(dividend_stocks)
    }


def calculate_performance_vs_weight(portfolio: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate data for Performance vs Weight scatter plot
    Returns scatter points and regression line data
    """
    try:
        from scipy.stats import linregress
        
        # Filter valid data
        data = portfolio[['Symbol', 'Assets (%)', 'Total Return (%)']].dropna()
        data = data[data['Assets (%)'] > 0]  # Only positive weights
        
        if len(data) < 2:
            return {'points': [], 'trendline': None}
            
        points = data.to_dict('records')
        
        # Calculate regression line
        slope, intercept, r_value, p_value, std_err = linregress(
            data['Assets (%)'], 
            data['Total Return (%)']
        )
        
        # Trendline points (min and max x)
        min_x = data['Assets (%)'].min()
        max_x = data['Assets (%)'].max()
        
        trendline = [
            {'x': min_x, 'y': slope * min_x + intercept},
            {'x': max_x, 'y': slope * max_x + intercept}
        ]
        
        return {
            'points': points,
            'trendline': trendline,
            'stats': {
                'slope': round(slope, 4),
                'intercept': round(intercept, 4),
                'r_squared': round(r_value**2, 4)
            }
        }
    except Exception as e:
        print(f"Error calculating performance vs weight: {e}")
        return {'points': [], 'trendline': None}


def calculate_advanced_risk_analytics(portfolio: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate advanced risk metrics including Monte Carlo and Correlation
    """
    try:
        import yfinance as yf
        import numpy as np
        from datetime import datetime, timedelta
        
        # Get top 10 holdings by weight for analysis to keep performance reasonable
        top_holdings = portfolio.nlargest(10, 'Assets (%)')
        symbols = top_holdings['Symbol'].tolist()
        weights = (top_holdings['Assets (%)'] / top_holdings['Assets (%)'].sum()).values
        
        if not symbols:
            return {}
            
        # Fetch historical data (1 year)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Download data
        # Use ThreadPool to speed up if needed, but yfinance handles list well
        hist_data = yf.download(symbols, start=start_date, end=end_date, progress=False)
        
        # Handle yfinance column structure (Adj Close preferred, else Close)
        if 'Adj Close' in hist_data.columns:
            hist_data = hist_data['Adj Close']
        elif 'Close' in hist_data.columns:
            hist_data = hist_data['Close']
        else:
            # Fallback for weird multi-index or single column cases
            pass
        
        if hist_data.empty:
            return {}
            
        # Calculate daily returns
        returns = hist_data.pct_change().dropna()
        
        # 1. Correlation Matrix
        correlation_matrix = returns.corr().round(2)
        corr_data = {
            'labels': correlation_matrix.columns.tolist(),
            'values': correlation_matrix.values.tolist()
        }
        
        # 2. Monte Carlo Simulation
        # Simulation parameters
        num_simulations = 1000
        num_days = 252 # 1 trading year
        
        # Portfolio stats
        mean_returns = returns.mean()
        cov_matrix = returns.cov()
        
        # Run simulation
        # Cholesky decomposition for correlated random variables
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            # Fallback if matrix is not positive definite (e.g. insufficient data)
            return {'correlation_matrix': corr_data, 'monte_carlo': None}
        
        portfolio_sims = np.zeros((num_simulations, num_days))
        initial_value = portfolio['Value ($)'].sum()
        
        for i in range(num_simulations):
            # Generate random shocks
            daily_shocks = np.random.normal(0, 1, (len(symbols), num_days))
            correlated_shocks = np.dot(L, daily_shocks)
            
            # Calculate portfolio daily returns
            simulated_returns = np.dot(weights, correlated_shocks) + np.dot(weights, mean_returns.values[:, None])
            
            # Calculate cumulative value
            portfolio_sims[i, :] = initial_value * np.cumprod(1 + simulated_returns)
            
        # Process simulation results for chart
        # We'll return percentiles (10th, 50th, 90th) to keep payload small
        percentiles = np.percentile(portfolio_sims, [10, 50, 90], axis=0)
        
        monte_carlo_data = {
            'labels': list(range(1, num_days + 1)),
            'p90': percentiles[2].tolist(), # Best case
            'p50': percentiles[1].tolist(), # Median
            'p10': percentiles[0].tolist(), # Worst case
            'start_value': initial_value
        }
        
        # 3. Calculate Advanced Metrics (Sharpe, Beta)
        # Beta requires Market history
        # Beta requires Market history
        market_data_df = yf.download('SPY', start=start_date, end=end_date, progress=False)
        if 'Adj Close' in market_data_df.columns:
            market_data = market_data_df['Adj Close']
        elif 'Close' in market_data_df.columns:
            market_data = market_data_df['Close']
        else:
             market_data = market_data_df # Fallback, might work if it's series

        # Ensure Series
        if hasattr(market_data, 'squeeze'):
            market_data = market_data.squeeze()

        market_returns = market_data.pct_change().dropna()
        
        # Portfolio daily returns (weighted)
        # Align dates
        common_dates = returns.index.intersection(market_returns.index)
        portfolio_daily = returns.loc[common_dates].dot(weights)
        market_daily = market_returns.loc[common_dates]
        
        # Beta
        covariance = np.cov(portfolio_daily, market_daily)[0][1]
        market_var = np.var(market_daily)
        beta = float(covariance / market_var) if market_var != 0 else 1.0
        
        # Sharpe (assume RF = 4% currently)
        rf_daily = 0.04 / 252
        excess_returns = portfolio_daily - rf_daily
        std_dev = portfolio_daily.std()
        sharpe = float(excess_returns.mean() / std_dev * np.sqrt(252)) if std_dev != 0 else 0.0
        
        return {
            'correlation_matrix': corr_data,
            'monte_carlo': monte_carlo_data,
            'metrics': {
                'beta': round(beta, 2),
                'sharpe': round(sharpe, 2),
                'volatility': round(std_dev * np.sqrt(252) * 100, 2) # Annualized %
            }
        }
        
    except Exception as e:
        print(f"Error calculating advanced risk analytics: {e}")
        import traceback
        traceback.print_exc()
        return {}


def analyze_portfolio_from_json(holdings: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert JSON holdings list [{'symbol': 'AAPL', 'weight': 50}] to DataFrame
    with minimal API calls for fast response
    """
    try:
        import yfinance as yf
        
        if not holdings:
            return pd.DataFrame()
            
        symbols = [h['symbol'].upper() for h in holdings]
        weight_map = {h['symbol'].upper(): h['weight'] for h in holdings}
        
        # Assume $100k portfolio for simulation
        total_portfolio_value = 100000
        
        data = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                
                # Use ONLY fast_info for speed - no history or full info calls
                try:
                    price = ticker.fast_info.last_price
                except:
                    # Fallback to minimal info if fast_info fails
                    price = 100.0  # Default price for estimation
                
                if price is None or price == 0:
                    price = 100.0  # Default
                
                # Calculate values
                weight = weight_map[symbol]
                value = total_portfolio_value * (weight / 100)
                shares = value / price if price > 0 else 0
                
                # Use defaults for fields that would require slow API calls
                data.append({
                    'Symbol': symbol,
                    'Description': symbol,
                    'Quantity': shares,
                    'Price ($)': price,
                    'Value ($)': value,
                    'Assets (%)': weight,
                    'Total Return (%)': 0,  # Default - would need history
                    'Sector': 'Technology',  # Default - would need full info
                    'Asset Type': 'Stock',   # Default
                    'Asset Category': 'Equity',  # Default
                    'Est Annual Income ($)': 0,  # Default - would need full info
                    'NFS G/L ($)': 0,
                    'Principal ($)*': value,  # Assume cost basis = current value
                    'NFS G/L (%)': 0,
                    '1-Day Value Change ($)': 0,
                    '1-Day Price Change (%)': 0,
                    'Current Yld/Dist Rate (%)': 0
                })
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                # Add with defaults even if it fails
                weight = weight_map.get(symbol, 0)
                value = total_portfolio_value * (weight / 100)
                data.append({
                    'Symbol': symbol,
                    'Description': symbol,
                    'Quantity': 0,
                    'Price ($)': 0,
                    'Value ($)': value,
                    'Assets (%)': weight,
                    'Total Return (%)': 0,
                    'Sector': 'Unknown',
                    'Asset Type': 'Stock',
                    'Asset Category': 'Equity',
                    'Est Annual Income ($)': 0,
                    'NFS G/L ($)': 0,
                    'Principal ($)*': value,
                    'NFS G/L (%)': 0,
                    '1-Day Value Change ($)': 0,
                    '1-Day Price Change (%)': 0,
                    'Current Yld/Dist Rate (%)': 0
                })
                
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"Error analyzing portfolio from JSON: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def compare_portfolios(current_df: pd.DataFrame, proposed_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compare two portfolios and return delta metrics
    """
    try:
        # Calculate metrics for both
        def get_metrics(df):
            if df.empty: return {}
            return {
                'yield': calculate_dividend_metrics(df)['average_yield'],
                'beta': calculate_portfolio_beta(df),
                'sharpe': calculate_sharpe_ratio(df),
                'expense_ratio': 0.0, # Placeholder
                'total_return': (df['Total Return (%)'] * df['Assets (%)'] / 100).sum()
            }
            
        current = get_metrics(current_df)
        proposed = get_metrics(proposed_df)
        
        if not current or not proposed:
            return {}
            
        return {
            'current': current,
            'proposed': proposed,
            'delta': {
                'yield': round(proposed['yield'] - current['yield'], 2),
                'beta': round(proposed['beta'] - current['beta'], 2),
                'sharpe': round(proposed['sharpe'] - current['sharpe'], 2),
                'total_return': round(proposed['total_return'] - current['total_return'], 2)
            }
        }
    except Exception as e:
        print(f"Error comparing portfolios: {e}")
        return {}


def calculate_benchmark_comparison(portfolio: pd.DataFrame, benchmark_ticker: str = 'SPY', period: str = '1y') -> Dict[str, Any]:
    """
    Compare portfolio performance against a benchmark (e.g., S&P 500)
    Uses a 'backcast' assumption: assumes current holdings were held over the period.
    """
    try:
        import yfinance as yf
        
        # 1. Filter valid assets (Stock/ETF/Crypto)
        # We can't easily get history for "My House" or "Cash" unless we track it manually.
        # For now, we'll index the investable metrics.
        valid_assets = portfolio[portfolio['Symbol'].notna() & (portfolio['Value ($)'] > 0)].copy()
        
        if valid_assets.empty:
            return {}
            
        symbols = valid_assets['Symbol'].tolist()
        # weights relative to the *investable* part of the portfolio
        total_investable_value = valid_assets['Value ($)'].sum()
        weights = (valid_assets['Value ($)'] / total_investable_value).values
        
        # 2. Fetch Historical Data
        tickers_to_fetch = symbols + [benchmark_ticker]
        
        # Calculate start date
        end_date = datetime.now()
        if period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == 'YTD':
            start_date = datetime(end_date.year, 1, 1)
        elif period == '6m':
            start_date = end_date - timedelta(days=180)
        else:
            start_date = end_date - timedelta(days=365)
            
        data = yf.download(tickers_to_fetch, start=start_date, end=end_date, progress=False)
        
        # Handle yfinance column structure
        # If auto_adjust=True (default in new versions), 'Adj Close' might be missing, use 'Close'
        if 'Adj Close' in data.columns:
            data = data['Adj Close']
        elif 'Close' in data.columns:
            data = data['Close']
        else:
            print(f"yfinance data has unexpected columns: {data.columns}")
            return {}
        
        if data.empty:
            return {}
            
        # 3. Calculate Portfolio History
        # Drop columns with all NaNs (failed downloads)
        data = data.dropna(axis=1, how='all')
        
        # Re-align weights to available data
        available_symbols = [s for s in symbols if s in data.columns]
        if not available_symbols:
            return {}
            
        # Recalculate weights for available symbols only
        # This is an approximation, but better than crashing
        valid_assets = valid_assets[valid_assets['Symbol'].isin(available_symbols)]
        new_total = valid_assets['Value ($)'].sum()
        if new_total == 0:
            return {}
            
        aligned_weights = (valid_assets.set_index('Symbol').loc[available_symbols]['Value ($)'] / new_total).values
        
        # Calculate daily returns for components
        returns = data[available_symbols].pct_change().fillna(0)
        
        # Calculate portfolio daily returns (weighted sum)
        portfolio_returns = returns.dot(aligned_weights)
        
        # Calculate benchmark returns
        if benchmark_ticker in data.columns:
            benchmark_returns = data[benchmark_ticker].pct_change().fillna(0)
        else:
            # Fallback if benchmark fails
            benchmark_returns = pd.Series(0, index=portfolio_returns.index)
            
        # 4. Construct Cumulative Performance (Growth of $10000)
        # Normalize to start at 100
        portfolio_cumulative = (1 + portfolio_returns).cumprod() * 100
        benchmark_cumulative = (1 + benchmark_returns).cumprod() * 100
        
        # Align indices
        common_index = portfolio_cumulative.index.intersection(benchmark_cumulative.index)
        
        # Prepare response
        dates = [d.strftime('%Y-%m-%d') for d in common_index]
        portfolio_vals = portfolio_cumulative.loc[common_index].tolist()
        benchmark_vals = benchmark_cumulative.loc[common_index].tolist()
        
        # Metrics
        port_total_return = (portfolio_vals[-1] - portfolio_vals[0]) / portfolio_vals[0] * 100 if portfolio_vals else 0
        bench_total_return = (benchmark_vals[-1] - benchmark_vals[0]) / benchmark_vals[0] * 100 if benchmark_vals else 0
        
        return {
            'dates': dates,
            'portfolio': portfolio_vals,
            'benchmark': benchmark_vals,
            'metrics': {
                'portfolio_return': round(port_total_return, 2),
                'benchmark_return': round(bench_total_return, 2),
                'alpha': round(port_total_return - bench_total_return, 2)
            }
        }
        
    except Exception as e:
        return {
            'dates': dates,
            'portfolio': portfolio_vals,
            'benchmark': benchmark_vals,
            'metrics': {
                'portfolio_return': round(port_total_return, 2),
                'benchmark_return': round(bench_total_return, 2),
                'alpha': round(port_total_return - bench_total_return, 2)
            }
        }
        
    except Exception as e:
        print(f"Error calculating benchmark comparison: {e}")
        return {}


def calculate_dividend_calendar(portfolio: pd.DataFrame) -> Dict[str, Any]:
    """
    Project future dividend payments based on historical frequency.
    Returns months and projected income for the next 12 months.
    """
    try:
        import yfinance as yf
        from dateutil.relativedelta import relativedelta
        
        # Filter potential dividend payers (stocks)
        payers = portfolio[
            (portfolio['Asset Type'].isin(['Stock', 'ETF'])) & 
            (portfolio['Quantity'] > 0)
        ].copy()
        
        if payers.empty:
            return {}
            
        calendar = {} # month_key -> total amount
        projections = []
        
        # Pre-initialize next 12 months
        today = datetime.now()
        for i in range(12):
            month_date = today + relativedelta(months=i)
            key = month_date.strftime('%Y-%m')
            calendar[key] = 0.0
            
        symbols = payers['Symbol'].unique().tolist()
        
        # Batch Fetch logic (though dividends is per ticker usually)
        # yfinance doesn't easily batch dividends history, iterate for now
        # Might be slow if many tickers!
        
        for idx, row in payers.iterrows():
            symbol = row['Symbol']
            qty = row['Quantity']
            
            try:
                ticker = yf.Ticker(symbol)
                # Get last year of dividends
                divs = ticker.dividends
                if divs.empty:
                    continue
                    
                # Sort by date
                divs = divs.sort_index()
                last_payment = divs.index[-1]
                last_amount = divs.iloc[-1]
                
                # Determine frequency (simple heuristic)
                if len(divs) >= 2:
                    intervals = (divs.index[-1] - divs.index[0]).days / (len(divs) - 1)
                    if 25 < intervals < 35: freq_months = 1 # Monthly
                    elif 85 < intervals < 95: freq_months = 3 # Quarterly
                    elif 175 < intervals < 190: freq_months = 6 # Semi-Annual
                    elif 350 < intervals < 380: freq_months = 12 # Annual
                    else: freq_months = 3 # Default to Quarterly if unsure but pays
                else:
                    freq_months = 3 # Default Assumption
                
                # Project forward 12 months
                # Start from last payment, add frequency until > today
                next_date = last_payment.replace(tzinfo=None) + relativedelta(months=freq_months)
                while next_date < today - timedelta(days=30): # Allow for slight delay
                    next_date += relativedelta(months=freq_months)
                    
                # Add for next 12 months
                cutoff = today + relativedelta(months=12)
                
                while next_date <= cutoff:
                    month_key = next_date.strftime('%Y-%m')
                    if month_key in calendar:
                        amount = last_amount * qty
                        calendar[month_key] += amount
                        projections.append({
                            'symbol': symbol,
                            'date': next_date.strftime('%Y-%m-%d'),
                            'amount': round(amount, 2),
                            'per_share': round(last_amount, 4)
                        })
                    next_date += relativedelta(months=freq_months)
                    
            except Exception as e:
                # print(f"Div algo error for {symbol}: {e}")
                continue
                
        # Format for chart/list
        monthly_totals = [{'month': k, 'amount': round(v, 2)} for k, v in calendar.items()]
        monthly_totals.sort(key=lambda x: x['month'])
        
        # Sort detail list
        projections.sort(key=lambda x: x['date'])
        
        return {
            'monthly_totals': monthly_totals,
            'upcoming_dividends': projections[:10], # Next 10 payments
            'total_projected_12m': round(sum(calendar.values()), 2)
        }
        
    except Exception as e:
        print(f"Error calculating dividend calendar: {e}")
        return {}


def calculate_retirement_projection(
    portfolio: pd.DataFrame, 
    years: int = 30, 
    monthly_contribution: float = 0,
    inflation_rate: float = 0.025
) -> Dict[str, Any]:
    """
    Run a long-term Monte Carlo simulation for retirement planning.
    Projects portfolio value with contributions and inflation.
    """
    try:
        import numpy as np
        import yfinance as yf
        
        # 1. Estimate Portfolio Stats (Return & Volatility)
        # We need investable assets only
        investable = portfolio[portfolio['Value ($)'] > 0].copy()
        if investable.empty:
            return {}
            
        total_value = investable['Value ($)'].sum()
        
        # Simplify: If we can't get history, assume based on Asset Type
        # Stocks: 7% real return, 15% vol
        # Bonds: 2% real return, 5% vol
        # Crypto: 10% real return, 60% vol
        # Cash: -2% real return (drag), 1% vol
        
        # We will calculate weighted average stats
        avg_return = 0.0
        avg_vol = 0.0
        
        for _, row in investable.iterrows():
            weight = row['Value ($)'] / total_value
            atype = str(row.get('Asset Type', 'Stock')).lower()
            
            if 'crypto' in atype:
                r, v = 0.10, 0.60
            elif 'bond' in atype or 'fixed' in atype:
                r, v = 0.04, 0.05
            elif 'cash' in atype:
                r, v = 0.01, 0.01
            elif 'real estate' in atype:
                r, v = 0.05, 0.10
            else: # Stock/ETF default
                r, v = 0.08, 0.15
                
            avg_return += r * weight
            avg_vol += v * weight
            
        # Adjust for standard deviation of portfolio (diversification benefit approximation)
        # We'll multiply vol by 0.7 to assume some diversification
        avg_vol *= 0.7
        
        # 2. Run Simulation
        num_simulations = 1000
        months = years * 12
        monthly_return_mean = avg_return / 12
        monthly_vol = avg_vol / np.sqrt(12)
        
        results = np.zeros((num_simulations, months))
        
        for i in range(num_simulations):
            # Random monthly returns
            # log-normal assumption
            rand_returns = np.random.normal(monthly_return_mean, monthly_vol, months)
            
            val = total_value
            for m in range(months):
                val = val * (1 + rand_returns[m]) + monthly_contribution
                # Inflation adjustment (nominal to real)? 
                # Let's keep it nominal for now, or real if we assumed real returns.
                # The assumption above (8%) is nominal.
                results[i, m] = val
                
        # 3. Analyze Results
        final_values = results[:, -1]
        
        # Percentiles
        p10 = np.percentile(final_values, 10)
        p50 = np.percentile(final_values, 50)
        p90 = np.percentile(final_values, 90)
        
        # Chart Data (decimated for speed)
        # Return annual points
        chart_labels = list(range(1, years + 1))
        chart_p10 = []
        chart_p50 = []
        chart_p90 = []
        
        for y in range(years):
            idx = (y + 1) * 12 - 1
            chart_p10.append(np.percentile(results[:, idx], 10))
            chart_p50.append(np.percentile(results[:, idx], 50))
            chart_p90.append(np.percentile(results[:, idx], 90))
            
        return {
            'years': years,
            'start_value': round(total_value, 2),
            'monthly_contribution': monthly_contribution,
            'expected_annual_return': round(avg_return * 100, 2),
            'expected_volatility': round(avg_vol * 100, 2),
            'results': {
                'p10_final': round(p10, 2),
                'p50_final': round(p50, 2),
                'p90_final': round(p90, 2),
            },
            'chart': {
                'labels': chart_labels,
                'p10': [round(x, 2) for x in chart_p10],
                'p50': [round(x, 2) for x in chart_p50],
                'p90': [round(x, 2) for x in chart_p90]
            }
        }
    except Exception as e:
        print(f"Error calculating retirement projection: {e}")
        return {}
