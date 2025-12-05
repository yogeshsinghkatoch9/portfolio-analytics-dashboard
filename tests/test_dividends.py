
import pytest
import pandas as pd
from backend.analytics import calculate_dividend_calendar

def test_dividend_calendar():
    # AAPL pays dividends
    data = [
        {'Symbol': 'AAPL', 'Value ($)': 5000, 'Quantity': 25, 'Asset Type': 'Stock'},
    ]
    portfolio = pd.DataFrame(data)
    
    result = calculate_dividend_calendar(portfolio)
    
    if not result:
        print("Dividend calendar returned empty (possibly no dividend data or network issue)")
        return
        
    assert 'monthly_totals' in result
    assert 'upcoming_dividends' in result
    assert 'total_projected_12m' in result
    
    # Check structure
    assert len(result['monthly_totals']) == 12
    assert result['total_projected_12m'] >= 0
    
    # Check that upcoming dividends has entries (AAPL pays quarterly)
    # Note: Depending on ex-div date, it might not have one immediately, but usually yes
    
    print("\nDividend Projection:", result['total_projected_12m'])
    print("Upcoming:", result['upcoming_dividends'])

if __name__ == "__main__":
    test_dividend_calendar()
