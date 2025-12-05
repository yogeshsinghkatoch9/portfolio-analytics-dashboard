#!/usr/bin/env python3
"""
Phase 2 Test Script
Test all Phase 2 endpoints with practical examples
Run this after starting the backend: python test_phase2.py
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# ANSI Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_header(text):
    """Print test header"""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")

def print_test(name):
    """Print test name"""
    print(f"{YELLOW}→ {name}{RESET}")

def print_success(msg):
    """Print success message"""
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    """Print error message"""
    print(f"{RED}✗ {msg}{RESET}")

def print_response(data):
    """Pretty print JSON response"""
    print(json.dumps(data, indent=2))

# ==============================================================================
# TEST 1: GET LIVE QUOTE
# ==============================================================================
def test_live_quote():
    print_header("TEST 1: GET LIVE STOCK QUOTE")
    
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    for ticker in tickers:
        print_test(f"Getting quote for {ticker}")
        try:
            response = requests.get(f"{BASE_URL}/api/v2/market/quote/{ticker}")
            data = response.json()
            
            if response.status_code == 200 and data.get('status') == 'success':
                print_success(f"{ticker}: ${data['price']:.2f} " +
                            f"({data['change_pct']:+.2f}%)")
                print(f"   Market Cap: ${data['market_cap']:,.0f}")
                print(f"   P/E Ratio: {data['pe_ratio']:.2f}")
                print(f"   52W High: ${data['52w_high']:.2f} | " +
                      f"52W Low: ${data['52w_low']:.2f}")
            else:
                print_error(f"Failed to get quote: {data.get('error', 'Unknown')}")
        except Exception as e:
            print_error(f"Request failed: {str(e)}")

# ==============================================================================
# TEST 2: BATCH QUOTES
# ==============================================================================
def test_batch_quotes():
    print_header("TEST 2: GET BATCH QUOTES (MULTIPLE TICKERS)")
    
    print_test("Fetching quotes for AAPL, MSFT, GOOGL, AMZN")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v2/market/quotes/batch",
            json={"tickers": ["AAPL", "MSFT", "GOOGL", "AMZN"]}
        )
        data = response.json()
        
        if response.status_code == 200 and data.get('success'):
            print_success(f"Retrieved {data['count']} quotes")
            
            # Display summary
            print("\nQuote Summary:")
            for ticker, quote in data['quotes'].items():
                if 'error' not in quote:
                    change = f"{quote['change_pct']:+.2f}%"
                    color = GREEN if quote['change_pct'] >= 0 else RED
                    print(f"  {ticker}: ${quote['price']:.2f} {color}{change}{RESET}")
                else:
                    print_error(f"  {ticker}: {quote['error']}")
        else:
            print_error("Batch quote fetch failed")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

# ==============================================================================
# TEST 3: TICKER SEARCH
# ==============================================================================
def test_ticker_search():
    print_header("TEST 3: SEARCH FOR TICKERS")
    
    searches = ["AAPL", "Microsoft", "Tesla"]
    
    for query in searches:
        print_test(f"Searching for '{query}'")
        try:
            response = requests.get(f"{BASE_URL}/api/v2/market/search/{query}")
            data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                if data['results']:
                    print_success(f"Found {data['count']} result(s)")
                    for result in data['results']:
                        print(f"   {result['symbol']}: {result['name']}")
                        print(f"   Type: {result.get('type', 'N/A')} | " +
                              f"Sector: {result.get('sector', 'N/A')}")
                else:
                    print(f"   No results found")
            else:
                print_error("Search failed")
        except Exception as e:
            print_error(f"Request failed: {str(e)}")
        
        time.sleep(1)  # Rate limiting

# ==============================================================================
# TEST 4: TICKER ANALYSIS
# ==============================================================================
def test_ticker_analysis():
    print_header("TEST 4: COMPREHENSIVE TICKER ANALYSIS")
    
    tickers = ["AAPL", "MSFT"]
    
    for ticker in tickers:
        print_test(f"Analyzing {ticker}")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v2/market/ticker/{ticker}/analysis"
            )
            data = response.json()
            
            if response.status_code == 200 and 'error' not in data:
                print_success(f"{data['company_name']} ({ticker})")
                print(f"\n  Fundamentals:")
                print(f"    Market Cap: ${data['market_cap']:,.0f}")
                print(f"    P/E Ratio: {data['pe_ratio']:.2f}")
                print(f"    PEG Ratio: {data['peg_ratio']:.2f}")
                print(f"    Dividend Yield: {data['dividend_yield']*100:.2f}%")
                
                print(f"\n  Price:")
                print(f"    Current: ${data['current_price']:.2f}")
                print(f"    52W High: ${data['52w_high']:.2f}")
                print(f"    52W Low: ${data['52w_low']:.2f}")
                
                print(f"\n  Performance:")
                print(f"    1Y Return: {data['year_return_pct']:.2f}%")
                print(f"    Volatility: {data['volatility_pct']:.2f}%")
                
                print(f"\n  Analysis:")
                print(f"    Recommendation: {data['recommendation'].upper()}")
                print(f"    Target Price: ${data['target_price']:.2f}")
                print(f"    Analyst Count: {data['analyst_count']}")
            else:
                print_error(f"Analysis failed: {data.get('error', 'Unknown')}")
        except Exception as e:
            print_error(f"Request failed: {str(e)}")
        
        time.sleep(1)  # Rate limiting

# ==============================================================================
# TEST 5: HISTORICAL DATA
# ==============================================================================
def test_historical_data():
    print_header("TEST 5: HISTORICAL PRICE DATA")
    
    print_test("Fetching 3-month historical data for AAPL")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/market/historical/AAPL",
            params={"period": "3mo", "interval": "1d"}
        )
        data = response.json()
        
        if response.status_code == 200 and data.get('success'):
            print_success(f"Retrieved {data['data_points']} data points")
            print(f"\nFirst 5 trading days:")
            
            for i, record in enumerate(data['data'][:5]):
                date = record['Date'].split('T')[0]
                print(f"  {date}: Open ${record['Open']:.2f}, " +
                      f"Close ${record['Close']:.2f}, " +
                      f"Volume {record['Volume']:,.0f}")
            
            print(f"\nLast 5 trading days:")
            for record in data['data'][-5:]:
                date = record['Date'].split('T')[0]
                print(f"  {date}: Open ${record['Open']:.2f}, " +
                      f"Close ${record['Close']:.2f}, " +
                      f"MA20 ${record['MA_20']:.2f}")
        else:
            print_error("Historical data fetch failed")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

# ==============================================================================
# TEST 6: DIVIDENDS
# ==============================================================================
def test_dividends():
    print_header("TEST 6: DIVIDEND HISTORY")
    
    dividend_stocks = ["MSFT", "JNJ", "PG"]
    
    for ticker in dividend_stocks:
        print_test(f"Getting dividends for {ticker}")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v2/market/ticker/{ticker}/dividends"
            )
            data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                if data['dividends']:
                    print_success(f"Found {data['count']} dividend payments")
                    print(f"  Recent dividends:")
                    for div in data['dividends'][-5:]:
                        date = div['date'].split('T')[0]
                        print(f"    {date}: ${div['amount']:.4f}")
                else:
                    print(f"  No dividend history available")
            else:
                print_error("Dividend fetch failed")
        except Exception as e:
            print_error(f"Request failed: {str(e)}")
        
        time.sleep(1)

# ==============================================================================
# TEST 7: SMART IMPORT
# ==============================================================================
def test_smart_import():
    print_header("TEST 7: SMART PORTFOLIO IMPORT")
    
    print_test("Creating test CSV file")
    
    # Create test CSV
    csv_content = """Symbol,Quantity,Price ($),Value ($),Principal ($)*,Principal G/L ($)*
AAPL,100,189.50,18950.00,15000.00,3950.00
MSFT,50,420.25,21012.50,18000.00,3012.50
GOOGL,30,140.00,4200.00,3500.00,700.00
AMZN,25,190.00,4750.00,4000.00,750.00
TSLA,15,250.00,3750.00,3500.00,250.00"""
    
    try:
        # Save test CSV
        with open('/tmp/test_portfolio.csv', 'w') as f:
            f.write(csv_content)
        
        print_success("Test CSV created")
        print_test("Uploading portfolio for smart import")
        
        # Upload file
        with open('/tmp/test_portfolio.csv', 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{BASE_URL}/api/v2/import/smart",
                files=files
            )
        
        data = response.json()
        
        if response.status_code == 200 and data.get('success'):
            print_success("Smart import successful!")
            print(f"\n  Format Detected: {data['metadata']['format']}")
            print(f"  Total Holdings: {data['metadata']['total_holdings']}")
            print(f"  Portfolio Value: ${data['metadata']['total_value']:,.2f}")
            print(f"\n  Auto-Mapped Columns:")
            for detected, standard in data['metadata']['auto_mapped_columns'].items():
                print(f"    '{detected}' → '{standard}'")
            
            print(f"\n  Holdings Imported:")
            for holding in data['holdings']:
                print(f"    {holding['ticker']}: {holding['quantity']} shares @ ${holding['price']:.2f}")
        else:
            print_error(f"Import failed: {data.get('errors', ['Unknown error'])}")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

# ==============================================================================
# TEST 8: ENRICH WITH LIVE DATA
# ==============================================================================
def test_enrich_with_live_data():
    print_header("TEST 8: ENRICH PORTFOLIO WITH LIVE DATA")
    
    print_test("Creating test portfolio CSV")
    
    csv_content = """Symbol,Quantity,Price ($),Value ($),Principal ($)*,Principal G/L ($)*
AAPL,100,150.00,15000.00,15000.00,0.00
MSFT,50,400.00,20000.00,20000.00,0.00
GOOGL,30,130.00,3900.00,3900.00,0.00"""
    
    try:
        with open('/tmp/test_portfolio_live.csv', 'w') as f:
            f.write(csv_content)
        
        print_success("Test CSV created")
        print_test("Uploading portfolio for live enrichment")
        
        with open('/tmp/test_portfolio_live.csv', 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{BASE_URL}/api/v2/portfolio/enrich-live-data",
                files=files
            )
        
        data = response.json()
        
        if response.status_code == 200 and data.get('success'):
            print_success("Portfolio enriched with live data!")
            print(f"\n  Portfolio Summary:")
            print(f"    Total Live Value: ${data['summary']['total_live_value']:,.2f}")
            print(f"    Total Gain/Loss: ${data['summary']['total_live_gain_loss']:,.2f}")
            print(f"    Holdings: {data['summary']['num_holdings']}")
            
            print(f"\n  Top Gainers:")
            for gainer in data['market_movers']['gainers']:
                print(f"    {gainer['ticker']}: ${gainer['live_price']:.2f} " +
                      f"({gainer['live_change_pct']:+.2f}%)")
            
            print(f"\n  Top Losers:")
            for loser in data['market_movers']['losers']:
                print(f"    {loser['ticker']}: ${loser['live_price']:.2f} " +
                      f"({loser['live_change_pct']:+.2f}%)")
        else:
            print_error("Enrichment failed")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

# ==============================================================================
# TEST 9: PORTFOLIO COMPARISON
# ==============================================================================
def test_portfolio_comparison():
    print_header("TEST 9: PORTFOLIO VS MARKET COMPARISON")
    
    print_test("Creating test portfolio")
    
    csv_content = """Symbol,Quantity,Price ($),Value ($),Principal ($)*,Principal G/L ($)*
AAPL,50,189.50,9475.00,8000.00,1475.00
MSFT,30,420.25,12607.50,10000.00,2607.50
NVDA,20,875.50,17510.00,12000.00,5510.00"""
    
    try:
        with open('/tmp/test_compare.csv', 'w') as f:
            f.write(csv_content)
        
        with open('/tmp/test_compare.csv', 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{BASE_URL}/api/v2/portfolio/compare-with-market",
                files=files
            )
        
        data = response.json()
        
        if response.status_code == 200 and data.get('success'):
            print_success("Portfolio comparison retrieved!")
            print(f"\n  Portfolio Value: ${data['portfolio_value']:,.2f}")
            print(f"  Holdings: {data['num_holdings']}")
            
            print(f"\n  Market Benchmarks:")
            for ticker, quote in data['benchmarks'].items():
                if 'error' not in quote:
                    print(f"    {ticker}: ${quote['price']:.2f} " +
                          f"({quote['change_pct']:+.2f}%)")
        else:
            print_error("Comparison failed")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
def main():
    print(f"\n{BLUE}{'#' * 70}{RESET}")
    print(f"{BLUE}#{'PHASE 2 - COMPREHENSIVE API TEST SUITE':^68}#{RESET}")
    print(f"{BLUE}#{'Portfolio Analytics Dashboard':^68}#{RESET}")
    print(f"{BLUE}{'#' * 70}{RESET}")
    print(f"\nTest Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend URL: {BASE_URL}\n")
    
    # Run all tests
    try:
        test_live_quote()
        time.sleep(1)
        
        test_batch_quotes()
        time.sleep(1)
        
        test_ticker_search()
        time.sleep(1)
        
        test_ticker_analysis()
        time.sleep(1)
        
        test_historical_data()
        time.sleep(1)
        
        test_dividends()
        time.sleep(1)
        
        test_smart_import()
        time.sleep(1)
        
        test_enrich_with_live_data()
        time.sleep(1)
        
        test_portfolio_comparison()
        
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Tests interrupted by user{RESET}")
        return
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return
    
    print(f"\n{BLUE}{'#' * 70}{RESET}")
    print(f"{GREEN}{'✓ ALL TESTS COMPLETED SUCCESSFULLY':^70}{RESET}")
    print(f"{BLUE}{'#' * 70}{RESET}\n")

if __name__ == "__main__":
    main()
