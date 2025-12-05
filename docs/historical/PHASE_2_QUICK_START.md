# Phase 2 Quick Start Guide

## Installation & Setup

### 1. Update Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Backend
```bash
python main.py
```
Server will run on `http://localhost:8000`

---

## Quick API Tests

### Test 1: Smart Import Portfolio
```bash
# Upload any CSV/Excel portfolio file (Schwab, Fidelity, or generic)
curl -X POST http://localhost:8000/api/v2/import/smart \
  -F "file=@your_portfolio.csv"
```

### Test 2: Get Live Stock Quote
```bash
# Get current price and data for any stock
curl http://localhost:8000/api/v2/market/quote/AAPL
```

### Test 3: Get Multiple Quotes
```bash
curl -X POST http://localhost:8000/api/v2/market/quotes/batch \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT", "GOOGL", "AMZN"]}'
```

### Test 4: Enrich Portfolio with Live Data
```bash
# Upload portfolio and get live prices automatically
curl -X POST http://localhost:8000/api/v2/portfolio/enrich-live-data \
  -F "file=@portfolio.xlsx"
```

### Test 5: Analyze a Stock
```bash
# Get comprehensive analysis of any ticker
curl http://localhost:8000/api/v2/market/ticker/MSFT/analysis
```

### Test 6: Get Historical Data
```bash
# Get 1 year of daily data with moving averages
curl "http://localhost:8000/api/v2/market/historical/AAPL?period=1y&interval=1d"
```

### Test 7: Get Dividend History
```bash
# Get all dividends paid by a company
curl http://localhost:8000/api/v2/market/ticker/MSFT/dividends
```

### Test 8: Search for Ticker
```bash
# Search for a stock by symbol
curl http://localhost:8000/api/v2/market/search/apple
```

### Test 9: Compare Portfolio vs Market
```bash
# See how portfolio performs vs S&P 500, Nasdaq, Russell 2000
curl -X POST http://localhost:8000/api/v2/portfolio/compare-with-market \
  -F "file=@portfolio.csv"
```

---

## Key Features in Phase 2

### 📁 Smart File Import
- ✅ Auto-detects brokerage format (Schwab, Fidelity, Vanguard, etc.)
- ✅ Automatic column mapping
- ✅ Data validation
- ✅ Missing metric computation
- ✅ Detailed import report

**Supported Formats:**
- Charles Schwab CSV/Excel
- Fidelity CSV/Excel
- Vanguard CSV/Excel
- E*TRADE CSV/Excel
- Interactive Brokers CSV/Excel
- Generic CSV/Excel with standard columns

### 📊 Live Market Data
- ✅ Real-time stock quotes (5-min cache)
- ✅ Batch quote fetching
- ✅ Historical price data
- ✅ Dividend history
- ✅ Technical analysis (moving averages)
- ✅ Ticker search
- ✅ Comprehensive ticker analysis

### 💰 Portfolio Enrichment
- ✅ Add live prices to uploaded portfolio
- ✅ Calculate live P&L in real-time
- ✅ Identify top gainers/losers
- ✅ Compare against market benchmarks

---

## Supported Column Names (Auto-detection)

The system auto-detects these column names:

**Ticker/Symbol:**
- symbol, ticker, stock, symbol name, security id

**Quantity:**
- qty, quantity, shares, units, share count

**Price:**
- price, current price, market price, last price, close price

**Value:**
- market value, total value, value, current value, position value

**Dividends/Yield:**
- dividend, annual dividend, yield, dividend yield

**Cost Basis:**
- cost basis, cost base, initial cost, purchase cost, basis

**Gain/Loss:**
- gain/loss, gl, profit/loss, pnl

---

## Sample Portfolio Formats

### Charles Schwab Format
```
Symbol,Quantity,Price ($),Value ($),Principal ($)*,Principal G/L ($)*
AAPL,100,189.50,18950.00,15000.00,3950.00
MSFT,50,420.25,21012.50,18000.00,3012.50
```

### Generic CSV Format
```
Ticker,Qty,Price,Value,CostBasis,GainLoss
AAPL,100,189.50,18950.00,15000.00,3950.00
MSFT,50,420.25,21012.50,18000.00,3012.50
```

### Excel Format
Works the same as CSV - just upload .xlsx file and it auto-detects!

---

## API Endpoints Overview

### File Import (v2)
- `POST /api/v2/import/smart` - Smart auto-detection import
- `POST /api/v2/import/with-mapping` - Import with custom column mapping

### Live Market Data (v2)
- `GET /api/v2/market/quote/{ticker}` - Single stock quote
- `POST /api/v2/market/quotes/batch` - Multiple quotes
- `GET /api/v2/market/search/{query}` - Search ticker
- `GET /api/v2/market/ticker/{ticker}/analysis` - Comprehensive analysis
- `POST /api/v2/market/historical/{ticker}` - Historical data
- `GET /api/v2/market/ticker/{ticker}/dividends` - Dividend history

### Portfolio Enrichment (v2)
- `POST /api/v2/portfolio/enrich-live-data` - Add live prices to portfolio
- `POST /api/v2/portfolio/compare-with-market` - Compare with benchmarks

---

## Frontend Implementation

### Step 1: Add Smart Upload
```html
<input type="file" id="portfolioFile" accept=".csv,.xlsx,.xls">
<button onclick="smartImportFile(document.getElementById('portfolioFile').files[0])">
    Import Portfolio
</button>
```

### Step 2: Add Live Data Enrichment
```javascript
// After import, enrich with live data
enrichPortfolioWithLiveData(file);
```

### Step 3: Display Live Quotes
```javascript
// Update quotes every 60 seconds
startLiveUpdates('AAPL', 'quote-element-id', 60000);
```

### Step 4: Add Ticker Search
```html
<input type="text" id="tickerSearch" placeholder="Search stock..."
       onkeyup="searchTicker(this.value)">
```

---

## Response Examples

### Smart Import Success
```json
{
  "success": true,
  "metadata": {
    "filename": "portfolio.csv",
    "format": "charles_schwab",
    "total_holdings": 15,
    "total_value": 250000.00,
    "auto_mapped_columns": {
      "Symbol": "ticker",
      "Quantity": "quantity",
      "Price": "price"
    }
  },
  "holdings": [...]
}
```

### Live Quote
```json
{
  "symbol": "AAPL",
  "price": 189.50,
  "change": 2.15,
  "change_pct": 1.14,
  "volume": 45632100,
  "pe_ratio": 28.5,
  "dividend_yield": 0.0048,
  "status": "success"
}
```

### Enriched Portfolio
```json
{
  "success": true,
  "portfolio": [
    {
      "ticker": "AAPL",
      "quantity": 100,
      "live_price": 189.50,
      "live_value": 18950.00,
      "live_gain_loss": 3950.00,
      "live_gain_loss_pct": 26.33,
      "company_name": "Apple Inc.",
      "sector": "Technology"
    }
  ],
  "market_movers": {
    "gainers": [...],
    "losers": [...]
  }
}
```

---

## Error Handling

All errors follow this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Common errors:
- **400**: Invalid file format or missing required columns
- **404**: Ticker not found
- **500**: Server error (check backend logs)

---

## Performance & Caching

- **Quote Cache**: 5 minutes (reduces API calls)
- **Batch Processing**: Up to 50+ tickers at once
- **Async Operations**: Non-blocking file uploads
- **Rate Limiting**: Respects Yahoo Finance limits

---

## Troubleshooting

**Q: File upload fails with "Missing critical columns"**
A: Ensure your CSV/Excel has at least: Ticker/Symbol, Quantity, Price, Value

**Q: "Ticker not found" error**
A: Check ticker symbol spelling (e.g., AAPL not apple). Use search endpoint first.

**Q: Live prices not updating**
A: Quotes are cached for 5 minutes. Wait or restart server to clear cache.

**Q: No data from historical endpoint**
A: Ticker may be delisted or invalid. Try a well-known ticker like AAPL.

---

## Next Steps

1. ✅ **Phase 2 Complete** - Smart import + live market data
2. 📋 **Phase 3 (Future)** - WebSocket real-time updates
3. 📈 **Phase 4 (Future)** - Portfolio optimization & rebalancing
4. 🎯 **Phase 5 (Future)** - Advanced risk analytics

---

## Support & Documentation

- **Full Phase 2 Guide**: See `PHASE_2_GUIDE.md`
- **Frontend Integration**: See `FRONTEND_INTEGRATION.md`
- **API Docs**: See endpoint descriptions above
- **Issues**: Check Python backend logs

---

## Example Use Cases

### Use Case 1: Import Schwab Export
```bash
# User exports from Charles Schwab
# Upload directly - no mapping needed!
curl -X POST http://localhost:8000/api/v2/import/smart \
  -F "file=@schwab_export.csv"
# Returns: portfolio with all columns auto-detected
```

### Use Case 2: Get Real-time P&L
```bash
# Upload portfolio and get live values
curl -X POST http://localhost:8000/api/v2/portfolio/enrich-live-data \
  -F "file=@my_portfolio.xlsx"
# Returns: portfolio with live_price, live_value, live_gain_loss
```

### Use Case 3: Monitor Stock
```javascript
// Watch AAPL price in real-time
const updateId = startLiveUpdates('AAPL', 'aapl-quote', 60000);
// ... later ...
stopLiveUpdates(updateId);
```

### Use Case 4: Research Stock
```bash
# Get full analysis of Microsoft
curl http://localhost:8000/api/v2/market/ticker/MSFT/analysis
# Returns: PE, dividend, recommendations, analyst count, etc.
```

---

**Last Updated**: December 4, 2025  
**Version**: Phase 2.0  
**Status**: Production Ready
