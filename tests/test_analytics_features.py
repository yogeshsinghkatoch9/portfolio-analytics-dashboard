
import pytest
import pandas as pd
from backend.analytics import calculate_benchmark_comparison

def test_benchmark_comparison():
    # Create sample portfolio
    data = [
        {'Symbol': 'AAPL', 'Value ($)': 5000},
        {'Symbol': 'MSFT', 'Value ($)': 5000}
    ]
    portfolio = pd.DataFrame(data)
    
    # Run comparison (this will make real network calls to Yahoo Finance)
    # We use a short period 'YTD' or '1mo' to be faster, but let's stick to default 1y
    result = calculate_benchmark_comparison(portfolio, benchmark_ticker='SPY', period='1y')
    
    # Assertions
    assert isinstance(result, dict)
    if not result:
        pytest.skip("Benchmark calculation returned empty result (possibly network issue or yfinance rate limit)")
        
    assert 'dates' in result
    assert 'portfolio' in result
    assert 'benchmark' in result
    assert 'metrics' in result
    
    assert len(result['dates']) > 0
    assert len(result['portfolio']) == len(result['dates'])
    assert len(result['benchmark']) == len(result['dates'])
    
    # Check normalization (starts at 100)
    assert abs(result['portfolio'][0] - 100) < 0.1
    assert abs(result['benchmark'][0] - 100) < 0.1
    
    print("\nBenchmark Test Metrics:", result['metrics'])

if __name__ == "__main__":
    test_benchmark_comparison()
