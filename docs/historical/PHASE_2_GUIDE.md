# Portfolio Analytics Dashboard - Phase 2 Documentation

## Phase 2: Advanced File Import & Live Market Data Integration

### Overview
Phase 2 introduces intelligent portfolio file importing with automatic format detection, support for multiple brokerage formats, and real-time stock data integration via Yahoo Finance. This enables users to easily upload portfolios in various formats and receive live market updates.

---

## New Features

### 1. Smart Portfolio Import (`/api/v2/import/smart`)
**Automatic Format Detection & Column Mapping**

Intelligently parses CSV/Excel files from various sources with minimal user input.

**Supported Brokerage Formats:**
- Charles Schwab
- Fidelity
- Vanguard
- E*TRADE
- Interactive Brokers
- Generic CSV/Excel formats

**Features:**
- ✅ Automatic column name detection
- ✅ Format recognition (detects brokerage source)
- ✅ Data validation and integrity checks
- ✅ Missing metric computation
- ✅ Detailed import report with warnings/errors

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v2/import/smart \
  -F "file=@portfolio.csv"
```

**Response:**
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
      "Price": "price",
      "Market Value": "value"
    },
    "import_timestamp": "2025-12-04T10:30:00"
  },
  "holdings": [...],
  "warnings": [],
  "errors": []
}
```

---

### 2. Live Market Data Endpoints

#### Get Single Stock Quote
**Endpoint:** `GET /api/v2/market/quote/{ticker}`

Returns comprehensive real-time quote data.

**Response:**
```json
{
  "symbol": "AAPL",
  "price": 189.50,
  "change": 2.15,
  "change_pct": 1.14,
  "volume": 45632100,
  "market_cap": 2950000000000,
  "pe_ratio": 28.5,
  "dividend_yield": 0.0048,
  "52w_high": 199.62,
  "52w_low": 164.08,
  "open": 187.35,
  "close": 189.50,
  "bid": 189.48,
  "ask": 189.52,
  "company_name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "timestamp": "2025-12-04T15:45:00Z",
  "status": "success"
}
```

#### Get Multiple Quotes (Batch)
**Endpoint:** `POST /api/v2/market/quotes/batch`

Fetch quotes for multiple tickers efficiently with caching.

**Request:**
```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN"]
}
```

**Response:**
```json
{
  "success": true,
  "quotes": {
    "AAPL": {...},
    "MSFT": {...},
    "GOOGL": {...},
    "AMZN": {...}
  },
  "count": 4,
  "timestamp": "2025-12-04T15:45:00Z"
}
```

---

### 3. Enrich Portfolio with Live Data
**Endpoint:** `POST /api/v2/portfolio/enrich-live-data`

Upload a portfolio file and automatically enrich it with live market prices and calculations.

**Added Columns:**
- `live_price`: Current market price
- `live_change`: Daily change ($)
- `live_change_pct`: Daily change (%)
- `live_value`: Current position value
- `live_gain_loss`: Current unrealized G/L
- `live_gain_loss_pct`: Current unrealized G/L %
- `company_name`: Company full name
- `sector`: Stock sector

**Example Response:**
```json
{
  "success": true,
  "filename": "portfolio.xlsx",
  "portfolio": [
    {
      "ticker": "AAPL",
      "quantity": 100,
      "price": 150.00,
      "value": 15000.00,
      "cost_basis": 14500.00,
      "live_price": 189.50,
      "live_value": 18950.00,
      "live_gain_loss": 4450.00,
      "live_gain_loss_pct": 30.66,
      "company_name": "Apple Inc.",
      "sector": "Technology"
    },
    ...
  ],
  "summary": {
    "total_live_value": 250000.00,
    "total_live_gain_loss": 35000.00,
    "num_holdings": 15
  },
  "market_movers": {
    "gainers": [
      {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "live_price": 875.50,
        "live_change": 15.25,
        "live_change_pct": 1.77,
        "live_value": 87550.00
      }
    ],
    "losers": [
      {
        "ticker": "TSLA",
        "company_name": "Tesla Inc.",
        "live_price": 195.30,
        "live_change": -5.50,
        "live_change_pct": -2.74,
        "live_value": 19530.00
      }
    ]
  },
  "timestamp": "2025-12-04T15:45:00Z"
}
```

---

### 4. Ticker Analysis
**Endpoint:** `GET /api/v2/market/ticker/{ticker}/analysis`

Comprehensive analysis of a single ticker with fundamentals, valuations, and performance metrics.

**Response:**
```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 2950000000000,
  "pe_ratio": 28.5,
  "peg_ratio": 2.1,
  "dividend_yield": 0.0048,
  "current_price": 189.50,
  "52w_high": 199.62,
  "52w_low": 164.08,
  "avg_volume": 45632100,
  "current_volume": 42156000,
  "year_return_pct": 28.45,
  "volatility_pct": 18.32,
  "recommendation": "buy",
  "target_price": 210.00,
  "analyst_count": 45,
  "timestamp": "2025-12-04T15:45:00Z"
}
```

---

### 5. Historical Data
**Endpoint:** `POST /api/v2/market/historical/{ticker}`

Fetch historical OHLCV data with moving averages for technical analysis.

**Query Parameters:**
- `period`: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
- `interval`: '1m', '5m', '15m', '30m', '60m', '1d', '1wk', '1mo'

**Response:**
```json
{
  "success": true,
  "ticker": "AAPL",
  "period": "1y",
  "interval": "1d",
  "data_points": 252,
  "data": [
    {
      "Date": "2024-12-04T00:00:00",
      "Open": 150.25,
      "High": 151.80,
      "Low": 149.90,
      "Close": 151.20,
      "Volume": 45632100,
      "Dividends": 0.0,
      "Stock Splits": 0.0,
      "Returns": 0.85,
      "MA_20": 150.15,
      "MA_50": 148.90
    },
    ...
  ],
  "timestamp": "2025-12-04T15:45:00Z"
}
```

---

### 6. Dividend History
**Endpoint:** `GET /api/v2/market/ticker/{ticker}/dividends`

Get complete dividend payment history for a ticker.

**Response:**
```json
{
  "success": true,
  "ticker": "MSFT",
  "dividends": [
    {
      "date": "2025-09-11T00:00:00",
      "amount": 0.68
    },
    {
      "date": "2025-06-13T00:00:00",
      "amount": 0.68
    },
    {
      "date": "2025-03-13T00:00:00",
      "amount": 0.68
    },
    {
      "date": "2024-12-12T00:00:00",
      "amount": 0.68
    }
  ],
  "count": 4,
  "timestamp": "2025-12-04T15:45:00Z"
}
```

---

### 7. Market Ticker Search
**Endpoint:** `GET /api/v2/market/search/{query}`

Search for tickers by symbol or company name.

**Response:**
```json
{
  "success": true,
  "query": "apple",
  "results": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "type": "EQUITY",
      "sector": "Technology",
      "exchange": "NASDAQ"
    }
  ],
  "count": 1
}
```

---

### 8. Compare Portfolio with Market Benchmarks
**Endpoint:** `POST /api/v2/portfolio/compare-with-market`

Compare portfolio performance against major market indices.

**Response:**
```json
{
  "success": true,
  "portfolio_value": 250000.00,
  "num_holdings": 15,
  "benchmarks": {
    "SPY": {
      "symbol": "SPY",
      "price": 489.50,
      "change_pct": 1.25,
      ...
    },
    "QQQ": {...},
    "IWM": {...}
  },
  "timestamp": "2025-12-04T15:45:00Z"
}
```

---

## New Backend Modules

### 1. `data_import.py`
Smart portfolio file importer with format detection and column mapping.

**Key Classes:**
- `DataImporter`: Core import logic with format detection
- `PortfolioImporter`: High-level import interface

**Features:**
- Automatic column mapping from various formats
- Data validation and integrity checks
- Missing metric computation (value, cost basis, gain/loss, yield)
- Detailed import metadata

### 2. `market_data.py`
Yahoo Finance integration and real-time market data handling.

**Key Classes:**
- `YahooFinanceClient`: Fetch real-time quotes and historical data
- `PortfolioMarketUpdater`: Enrich portfolios with live prices
- `MarketAlerts`: Price alert system

**Features:**
- Real-time quote fetching with 5-minute caching
- Batch quote fetching for efficiency
- Historical data with moving averages
- Dividend history retrieval
- Top movers identification
- Price alert system

---

## Updated Requirements

Added packages for Phase 2:
```
aiofiles==23.2.1          # Async file handling
requests==2.31.0          # HTTP requests
lxml==4.9.3              # XML parsing
beautifulsoup4==4.12.2   # HTML parsing
```

---

## API Summary

### Phase 1 Endpoints (Existing)
- `POST /upload-portfolio` - Upload and process portfolio
- `GET /api/market/quote/{ticker}` - Single quote
- `POST /api/market/quotes` - Batch quotes
- `GET /health` - Health check

### Phase 2 Endpoints (New)
- `POST /api/v2/import/smart` - Smart file import
- `POST /api/v2/import/with-mapping` - Import with column mapping
- `GET /api/v2/market/quote/{ticker}` - Live quote (enhanced)
- `POST /api/v2/market/quotes/batch` - Batch live quotes
- `POST /api/v2/portfolio/enrich-live-data` - Add live prices to portfolio
- `GET /api/v2/market/search/{query}` - Ticker search
- `GET /api/v2/market/ticker/{ticker}/analysis` - Comprehensive analysis
- `POST /api/v2/market/historical/{ticker}` - Historical data
- `GET /api/v2/market/ticker/{ticker}/dividends` - Dividend history
- `POST /api/v2/portfolio/compare-with-market` - Market comparison

---

## Usage Examples

### Example 1: Smart Import Portfolio
```bash
# Upload a Schwab or Fidelity export - auto-detection handles it
curl -X POST http://localhost:8000/api/v2/import/smart \
  -F "file=@schwab_portfolio.csv"
```

### Example 2: Get Live Stock Data
```bash
# Get current AAPL price
curl http://localhost:8000/api/v2/market/quote/AAPL

# Get multiple quotes
curl -X POST http://localhost:8000/api/v2/market/quotes/batch \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT", "GOOGL"]}'
```

### Example 3: Enrich Portfolio with Live Data
```bash
# Upload portfolio and get live prices + analysis
curl -X POST http://localhost:8000/api/v2/portfolio/enrich-live-data \
  -F "file=@my_portfolio.xlsx"
```

### Example 4: Analyze a Stock
```bash
# Get comprehensive analysis of AAPL
curl http://localhost:8000/api/v2/market/ticker/AAPL/analysis
```

### Example 5: Get Historical Data for Charting
```bash
# Get 1 year of daily data with moving averages
curl "http://localhost:8000/api/v2/market/historical/AAPL?period=1y&interval=1d"
```

---

## Frontend Integration Points

The frontend can now:

1. **Smart File Upload**
   - Drag-and-drop CSV/Excel files
   - Auto-detect format and column mappings
   - Show import status with validation results

2. **Live Price Updates**
   - Fetch live quotes for all holdings
   - Display real-time P&L changes
   - Show market movers (gainers/losers)

3. **Ticker Search**
   - Search for stocks by symbol or name
   - Display company info (sector, industry)

4. **Stock Details**
   - Show historical price charts
   - Display dividend history
   - Show analyst recommendations

5. **Portfolio Enrichment**
   - Automatically add live prices to uploaded portfolio
   - Calculate live P&L in real-time
   - Compare against market benchmarks

---

## Caching & Performance

- **Quote Cache**: 5-minute TTL for all quotes
- **Batch Operations**: Efficient multi-ticker fetches
- **Async Support**: Non-blocking file operations
- **Rate Limiting**: Respects Yahoo Finance rate limits

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

HTTP Status Codes:
- `200`: Success
- `400`: Bad request (invalid file, missing params)
- `404`: Ticker not found
- `500`: Server error

---

## Next Steps for Frontend

1. Create file upload component with progress indicator
2. Implement live quote ticker widget
3. Add stock search dropdown with autocomplete
4. Create market movers display (gainers/losers)
5. Add historical price charts with Chart.js
6. Implement dividend history table
7. Add portfolio vs benchmark comparison chart

---

## Testing Phase 2 Features

```bash
# Test smart import
curl -X POST http://localhost:8000/api/v2/import/smart \
  -F "file=@test_portfolio.csv"

# Test live quote
curl http://localhost:8000/api/v2/market/quote/AAPL

# Test enrich portfolio
curl -X POST http://localhost:8000/api/v2/portfolio/enrich-live-data \
  -F "file=@portfolio.xlsx"

# Test ticker analysis
curl http://localhost:8000/api/v2/market/ticker/MSFT/analysis

# Test historical data
curl "http://localhost:8000/api/v2/market/historical/GOOGL?period=3mo&interval=1d"
```

---

## Known Limitations

1. **Ticker Search**: Limited by Yahoo Finance limitations (may need third-party service for full search)
2. **Real-time Data**: 5-minute cache delay (not true real-time)
3. **Column Mapping**: Auto-detection works best with common column names
4. **Historical Data**: Limited to data available from Yahoo Finance

---

## Future Enhancements

1. **WebSocket Support**: Real-time updates without polling
2. **Price Alerts**: Configurable alerts for threshold breaches
3. **Technical Indicators**: RSI, MACD, Bollinger Bands
4. **Multiple Data Sources**: Alpha Vantage, IEX Cloud, etc.
5. **Portfolio Optimization**: Efficient frontier calculations
6. **Risk Analysis**: VaR, stress testing
7. **Tax Reporting**: Gain/loss harvesting suggestions

---

## Support

For issues or questions:
1. Check the error message details
2. Verify file format (CSV/Excel with standard columns)
3. Check internet connection for market data
4. Review Phase 2 API documentation above
