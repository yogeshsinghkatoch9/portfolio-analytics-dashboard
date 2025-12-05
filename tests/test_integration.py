#!/usr/bin/env python3
"""
Portfolio Analytics Dashboard - Test Suite
Tests all backend functions and API endpoints
"""

import sys
import os
import requests
import json
from pathlib import Path

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_test(name, passed, details=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} {name}")
    if details:
        print(f"       {details}")

def test_backend_imports():
    """Test if backend modules can be imported"""
    print_header("Testing Backend Imports")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'backend'))
        from main import (
            parse_portfolio_file, 
            clean_portfolio_data, 
            compute_summary_metrics,
            generate_chart_data,
            prepare_holdings_table
        )
        print_test("Backend imports", True)
        return True
    except Exception as e:
        print_test("Backend imports", False, str(e))
        return False

def test_file_parsing():
    """Test CSV and Excel file parsing"""
    print_header("Testing File Parsing")
    
    from main import parse_portfolio_file
    
    # Test with actual uploaded file
    test_file = Path('/mnt/user-data/uploads/Holdings__13_.xlsx')
    
    if not test_file.exists():
        print_test("File exists", False, "Test file not found")
        return False
    
    try:
        with open(test_file, 'rb') as f:
            content = f.read()
        
        df = parse_portfolio_file(content, 'Holdings__13_.xlsx')
        print_test("Parse Excel file", len(df) > 0, f"Parsed {len(df)} rows")
        
        # Check for required columns
        required_cols = ['Symbol', 'Quantity', 'Price ($)', 'Value ($)']
        has_required = all(col in df.columns for col in required_cols)
        print_test("Required columns present", has_required)
        
        return has_required
        
    except Exception as e:
        print_test("Parse Excel file", False, str(e))
        return False

def test_data_cleaning():
    """Test data cleaning functionality"""
    print_header("Testing Data Cleaning")
    
    from main import parse_portfolio_file, clean_portfolio_data
    
    try:
        test_file = Path('/mnt/user-data/uploads/Holdings__13_.xlsx')
        with open(test_file, 'rb') as f:
            content = f.read()
        
        df = parse_portfolio_file(content, 'Holdings__13_.xlsx')
        original_len = len(df)
        
        df_cleaned = clean_portfolio_data(df)
        cleaned_len = len(df_cleaned)
        
        print_test("Clean data", True, f"Reduced from {original_len} to {cleaned_len} rows")
        
        # Check no NaN symbols
        has_no_nan = df_cleaned['Symbol'].notna().all()
        print_test("No NaN symbols", has_no_nan)
        
        # Check numeric columns are numeric
        numeric_check = df_cleaned['Value ($)'].dtype in ['float64', 'int64']
        print_test("Numeric columns converted", numeric_check)
        
        return has_no_nan and numeric_check
        
    except Exception as e:
        print_test("Clean data", False, str(e))
        return False

def test_metrics_computation():
    """Test summary metrics calculation"""
    print_header("Testing Metrics Computation")
    
    from main import parse_portfolio_file, clean_portfolio_data, compute_summary_metrics
    
    try:
        test_file = Path('/mnt/user-data/uploads/Holdings__13_.xlsx')
        with open(test_file, 'rb') as f:
            content = f.read()
        
        df = parse_portfolio_file(content, 'Holdings__13_.xlsx')
        df = clean_portfolio_data(df)
        
        metrics = compute_summary_metrics(df)
        
        # Check required metrics exist
        required_metrics = [
            'total_value', 'total_principal', 'total_gain_loss',
            'overall_return_pct', 'total_annual_income', 'avg_yield', 'num_holdings'
        ]
        
        has_all = all(key in metrics for key in required_metrics)
        print_test("All metrics computed", has_all)
        
        # Check reasonable values
        total_value = metrics['total_value']
        print_test("Total value > 0", total_value > 0, f"${total_value:,.2f}")
        
        num_holdings = metrics['num_holdings']
        print_test("Holdings count", num_holdings > 0, f"{num_holdings} holdings")
        
        return_pct = metrics['overall_return_pct']
        print_test("Return % calculated", isinstance(return_pct, (int, float)), f"{return_pct:.2f}%")
        
        return has_all and total_value > 0
        
    except Exception as e:
        print_test("Metrics computation", False, str(e))
        return False

def test_chart_generation():
    """Test chart data generation"""
    print_header("Testing Chart Data Generation")
    
    from main import parse_portfolio_file, clean_portfolio_data, generate_chart_data
    
    try:
        test_file = Path('/mnt/user-data/uploads/Holdings__13_.xlsx')
        with open(test_file, 'rb') as f:
            content = f.read()
        
        df = parse_portfolio_file(content, 'Holdings__13_.xlsx')
        df = clean_portfolio_data(df)
        
        charts = generate_chart_data(df)
        
        # Check required charts
        required_charts = [
            'allocation_by_symbol', 'allocation_by_type', 
            'allocation_by_category', 'gain_loss_by_symbol',
            'daily_movement', 'yield_distribution'
        ]
        
        has_all = all(key in charts for key in required_charts)
        print_test("All charts generated", has_all)
        
        # Check data structure
        allocation = charts['allocation_by_symbol']
        print_test("Allocation chart data", len(allocation) > 0, f"{len(allocation)} items")
        
        gain_loss = charts['gain_loss_by_symbol']
        print_test("Gain/loss chart data", len(gain_loss) > 0, f"{len(gain_loss)} items")
        
        return has_all and len(allocation) > 0
        
    except Exception as e:
        print_test("Chart generation", False, str(e))
        return False

def test_api_health():
    """Test if API is running and healthy"""
    print_header("Testing API Endpoints")
    
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        is_healthy = response.status_code == 200
        print_test("API health check", is_healthy, f"Status: {response.status_code}")
        return is_healthy
    except requests.exceptions.ConnectionError:
        print_test("API health check", False, "Cannot connect (is server running?)")
        return False
    except Exception as e:
        print_test("API health check", False, str(e))
        return False

def test_api_upload():
    """Test file upload endpoint"""
    print_header("Testing File Upload API")
    
    try:
        test_file = Path('/mnt/user-data/uploads/Holdings__13_.xlsx')
        
        if not test_file.exists():
            print_test("Upload endpoint", False, "Test file not found")
            return False
        
        with open(test_file, 'rb') as f:
            files = {'file': ('Holdings__13_.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post('http://localhost:8000/upload-portfolio', files=files, timeout=30)
        
        success = response.status_code == 200
        print_test("Upload endpoint", success, f"Status: {response.status_code}")
        
        if success:
            data = response.json()
            has_summary = 'summary' in data
            has_charts = 'charts' in data
            has_holdings = 'holdings' in data
            
            print_test("Response has summary", has_summary)
            print_test("Response has charts", has_charts)
            print_test("Response has holdings", has_holdings)
            
            if has_summary:
                print_test("Total value in response", 'total_value' in data['summary'], 
                          f"${data['summary'].get('total_value', 0):,.2f}")
            
            return success and has_summary and has_charts and has_holdings
        
        return False
        
    except requests.exceptions.ConnectionError:
        print_test("Upload endpoint", False, "Cannot connect (is server running?)")
        return False
    except Exception as e:
        print_test("Upload endpoint", False, str(e))
        return False

def test_frontend_files():
    """Check if frontend files exist"""
    print_header("Testing Frontend Files")
    
    frontend_dir = Path(__file__).parent / 'frontend'
    index_file = frontend_dir / 'index.html'
    
    exists = index_file.exists()
    print_test("index.html exists", exists)
    
    if exists:
        with open(index_file, 'r') as f:
            content = f.read()
        
        has_chart_js = 'chart.js' in content.lower()
        has_tailwind = 'tailwindcss' in content.lower()
        has_upload = 'upload' in content.lower()
        
        print_test("Chart.js included", has_chart_js)
        print_test("Tailwind CSS included", has_tailwind)
        print_test("Upload functionality", has_upload)
        
        return exists and has_chart_js and has_tailwind
    
    return False

def run_all_tests():
    """Run all test suites"""
    print(f"\n{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Portfolio Analytics Dashboard - Test Suite            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    results = []
    
    # Backend tests
    results.append(("Backend Imports", test_backend_imports()))
    results.append(("File Parsing", test_file_parsing()))
    results.append(("Data Cleaning", test_data_cleaning()))
    results.append(("Metrics Computation", test_metrics_computation()))
    results.append(("Chart Generation", test_chart_generation()))
    
    # Frontend tests
    results.append(("Frontend Files", test_frontend_files()))
    
    # API tests (only if server is running)
    print(f"\n{Colors.YELLOW}Note: API tests require backend server to be running{Colors.END}")
    print(f"{Colors.YELLOW}Start with: ./start.sh or python3 backend/main.py{Colors.END}\n")
    
    results.append(("API Health", test_api_health()))
    results.append(("API Upload", test_api_upload()))
    
    # Summary
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed
    
    for name, result in results:
        status = f"{Colors.GREEN}✓{Colors.END}" if result else f"{Colors.RED}✗{Colors.END}"
        print(f"{status} {name}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"Total: {total} | Passed: {Colors.GREEN}{passed}{Colors.END} | Failed: {Colors.RED}{failed}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    if failed == 0:
        print(f"{Colors.GREEN}🎉 All tests passed!{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}❌ {failed} test(s) failed{Colors.END}\n")
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
