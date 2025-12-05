
import pytest
import pandas as pd
from backend.analytics import calculate_retirement_projection

def test_retirement_planner():
    # Simple portfolio
    data = [
        {'Symbol': 'SPY', 'Value ($)': 100000, 'Asset Type': 'ETF'},
        {'Symbol': 'BND', 'Value ($)': 50000, 'Asset Type': 'Bond'},
    ]
    portfolio = pd.DataFrame(data)
    
    # Run simulation
    result = calculate_retirement_projection(portfolio, years=20, monthly_contribution=1000)
    
    if not result:
        pytest.fail("Retirement projection returned empty result")
        
    assert result['years'] == 20
    assert result['start_value'] == 150000
    assert result['monthly_contribution'] == 1000
    assert 'results' in result
    assert 'chart' in result
    
    p50_final = result['results']['p50_final']
    print(f"\nMedian Final Value: ${p50_final:,.2f}")
    
    # Basic sanity check: with contributions, it should grow
    # Approx: 150k + 20*12*1k = 390k principal. + growth.
    assert p50_final > 390000 

if __name__ == "__main__":
    test_retirement_planner()
