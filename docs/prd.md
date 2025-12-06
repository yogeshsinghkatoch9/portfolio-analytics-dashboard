# Portfolio Builder + Portfolio Analytics Platform
## Complete Product Requirements Document

**Version:** 2.0 (Comprehensive)  
**Last Updated:** December 5, 2025  
**Prepared By:** Yogesh Singh Katoch  
**Status:** 🟢 Phase 1 Complete, Phase 2-5 Planned

---

## 🔵 SECTION 1 — PRODUCT SUMMARY

### Vision
Build the most complete, future-proof portfolio analytics platform, combining:

✔ **Portfolio Builder** - Manually add tickers and build portfolios from scratch  
✔ **Current Portfolio Analyzer** - Upload CSV/XLS files with real positions  
✔ **Automated Insights** - OpenAI-generated summaries and risk analysis  
✔ **Real-Time Market Data** - Auto-fetch from Yahoo Finance API  
✔ **Professional Reports** - Heatmaps, charts, benchmarks, PDF exports  
✔ **Unified Dashboard** - All features in one platform with perfect UX/UI  

### Current Status (Phase 1)
✅ **DEPLOYED & LIVE**
- Backend: https://portfolio-analytics-dashboard-tlan.onrender.com
- Frontend: https://portfolio-analytics-dashboard-seven.vercel.app
- API Docs: https://portfolio-analytics-dashboard-tlan.onrender.com/docs

---

## 🔵 SECTION 2 — USER REQUIREMENTS

Users can:
1. ✅ Search & add tickers to build portfolios
2. ✅ Automatically fetch data (price, sector, beta, yields)
3. ✅ View deep analytics: allocation, risk, correlation, sectors
4. ✅ Upload real portfolios (CSV/XLS) and analyze
5. ✅ Export client-ready reports
6. 🔄 Receive AI summaries (in progress)
7. ✅ See all analytics clearly and professionally

---

## 🔵 SECTION 3 — COMPETITIVE ADVANTAGE

### vs Morningstar
✅ AI summaries  
✅ CSV upload freedom  
✅ Custom professional reports  
✅ Real-time OpenAI analysis  

### vs Empower/Personal Capital
✅ Deep analytics  
✅ CSV ingest  
✅ Heatmaps, VaR, Sharpe  
✅ AI commentary  

### vs Kubera
✅ Advanced analytics  
✅ Professional reports  
✅ AI insights  

**Your Advantage**: Everything above + AI + Builder + Upload + Export in ONE product.

---

## 🔵 SECTION 4 — PLATFORM MODULES

### MODULE 1 — Portfolio Builder ✅

**Features:**
1. **Ticker Search**
   - Search bar with autocomplete
   - Fetches from Yahoo Finance:
     - Name, Price, Sector, Industry
     - Beta, Dividend yield, 1Y return
     - Market cap

2. **Add to Portfolio**
   - Choose shares or dollar amount
   - Auto-calculates value and weight

3. **Holdings Table**
   - Columns: Symbol, Name, Shares, Price, Value, Weight, Sector
   - Remove button per holding

4. **Live Analytics:**
   - 🔹 Asset Allocation (pie chart)
   - 🔹 Sector Exposure (bar chart)
   - 🔹 Correlation Heatmap
   - 🔹 Risk Metrics: Beta, Std Dev, Sharpe, Max Drawdown, VaR
   - 🔹 Benchmark vs S&P 500
   - 🔹 AI Summary (planned)

**Implementation Status:** ✅ Core complete, AI integration pending

---

### MODULE 2 — Portfolio Upload ✅

**Features:**
1. **File Upload**
   - Supports CSV, XLS, XLSX
   - Auto-detects columns
   - Validates data
   - Converts to standardized JSON

2. **Additional Analytics:**
   - ✅ Unrealized G/L
   - ✅ Cost basis analysis
   - 🔄 ST vs LT capital gains
   - ✅ Dividend forecast
   - 🔄 Wash-sale warnings
   - ✅ Attribution analysis
   - ✅ Benchmark comparison

3. **Export:**
   - ✅ PDF reports
   - ✅ Chart images
   - ✅ Processed CSV data

**Implementation Status:** ✅ Core complete, advanced features in progress

---

## 🔵 SECTION 5 — ANALYTICS ENGINE

### 1. Asset Allocation ✅
- Group by Asset Type, Sector, Region
- JSON output for charts

### 2. Risk Calculations ✅
```python
# Beta (weighted)
beta = Σ(weight_i × beta_i)

# Standard Deviation
std = sqrt(Σ(daily_returns²) / n)

# Sharpe Ratio
sharpe = (mean_return - risk_free_rate) / std

# Max Drawdown
max_dd = (trough - peak) / peak

# Value at Risk (95%)
var_95 = percentile(returns, 5)
```

### 3. Correlation Matrix ✅
```python
correlation = returns_dataframe.corr()
```

### 4. Benchmark Comparison ✅
- Fetches SPY or ^GSPC data
- Compares portfolio performance

### 5. Dividend Forecast ✅
```python
dividend = quantity × dividend_per_share
```

### 6. AI Insights 🔄
**Planned OpenAI Integration:**

```python
prompt = f"""
Analyze this portfolio:
{analytics_json}

Provide:
1. Summary
2. Risks
3. Concentration issues
4. Opportunities
5. 12-month outlook

Use simple client-friendly language.
"""
```

---

## 🔵 SECTION 6 — REPORT GENERATION

### PDF Components ✅
1. **Cover Page**
   - Portfolio name, owner, date

2. **Charts**
   - Asset allocation pie
   - Sector bar chart
   - Correlation heatmap
   - Performance line chart
   - Dividend forecast

3. **Tables**
   - Holdings table
   - Risk metrics
   - G/L analysis

4. **AI Sections** 🔄
   - Summary
   - Risk outlook
   - Rebalancing suggestions

**Storage:** Local/S3 compatible

---

## 🔵 SECTION 7 — TECHNICAL ARCHITECTURE

### Frontend (Current)
```
- Framework: Vanilla HTML/CSS/JavaScript
- Styling: Tailwind CSS
- Charts: Chart.js 4.4.0
- State: Local variables
- API: Fetch API
- Hosting: Vercel
```

### Backend (Current)
```
- Framework: FastAPI (Python 3.11)
- Database: SQLite (production-ready)
- Cache: In-memory (Redis planned)
- Market Data: yfinance
- Analytics: Pandas, NumPy
- Reports: LaTeX/PDF generation
- Hosting: Render.com (Docker)
```

### Planned Enhancements
```
- AI: OpenAI API integration
- Cache: Redis for pricing
- Frontend: Migrate to React/Next.js
- State: Redux Toolkit
- Real-time: WebSocket pricing
```

---

## 🔵 SECTION 8 — API ROUTES

### Authentication 🔄
```
POST /auth/signup
POST /auth/login
GET /auth/me
```

### Portfolio Builder ✅
```
GET /api/market/search?q=TSLA
POST /api/v2/portfolio
POST /api/v2/portfolio/{id}/holdings
DELETE /api/v2/portfolio/{id}/holdings/{position_id}
GET /api/v2/portfolio/{id}/analytics
POST/api/v2/portfolio/{id}/report
```

### File Upload ✅
```
POST /upload-portfolio
GET /api/portfolio/summary
GET /api/portfolio/analytics
POST /api/portfolio/export
```

### Implemented Endpoints
```
GET /health
GET /docs
POST /api/v2/market/quotes/batch
GET /api/v2/market/ticker/{ticker}/analysis
GET /api/v2/market/historical/{ticker}
POST /api/v2/ai/analyze
```

---

## 🔵 SECTION 9 — DATABASE DESIGN

### Current Tables
```sql
-- Portfolio storage
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Holdings
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER,
    ticker VARCHAR(10),
    quantity FLOAT,
    price FLOAT,
    cost_basis FLOAT,
    asset_type VARCHAR(50),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

-- Watchlist
CREATE TABLE watchlists (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE watchlist_items (
    id INTEGER PRIMARY KEY,
    watchlist_id INTEGER,
    ticker VARCHAR(10),
    added_at TIMESTAMP,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id)
);
```

### Planned Tables
```sql
-- Users (authentication)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50),
    created_at TIMESTAMP
);

-- Reports
CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER,
    user_id INTEGER,
    report_type VARCHAR(50),
    file_path VARCHAR(500),
    created_at TIMESTAMP
);
```

---

## 🔵 SECTION 10 — UI WIREFRAMES

### Current Implementation

#### 1. Dashboard Layout
```
┌─────────────────────────────────────────┐
│ Logo    Portfolio Analytics    Profile  │
├─────────────────────────────────────────┤
│ [Builder] [Current Portfolio] [Analytics]│
├─────────────────────────────────────────┤
│                                          │
│  Tab Content (Builder/Dashboard/Analytics)│
│                                          │
│  - Summary Cards                         │
│  - Charts (Pie, Bar, Line)              │
│  - Holdings Table                        │
│  - Risk Metrics                          │
│                                          │
└─────────────────────────────────────────┘
```

#### 2. Portfolio Builder
```
Search Section:
[Search ticker...] [🔍]

Results:
┌────────────────────────────────┐
│ AAPL | Apple Inc | [+ Add]     │
│ TSLA | Tesla Inc | [+ Add]     │
└────────────────────────────────┘

Holdings Table:
Symbol | Shares | Price | Value | % | Sector | [×]

Charts:
[Pie: Asset Types] [Bar: Sectors]
[Heatmap: Correlation] [Line: vs S&P 500]

AI Summary Box:
┌────────────────────────────────┐
│ 📊 AI Analysis                 │
│ Your portfolio shows...        │
└────────────────────────────────┘

[Generate PDF Report]
```

#### 3. Upload Portfolio
```
Upload Section:
┌────────────────────────────────┐
│ 📁 Drag & drop or click        │
│    to upload CSV/Excel         │
└────────────────────────────────┘

Preview Table:
Symbol | Qty | Price | Value | Sector

[Run Analytics] → Shows same analytics as Builder
```

---

## 🔵 SECTION 11 — DEVELOPMENT ROADMAP

### Phase 1 — Core Infrastructure ✅ COMPLETE
- [x] Auth framework (basic)
- [x] Portfolio Builder backend
- [x] Ticker search integration
- [x] Database setup
- [x] Deployment (Render + Vercel)

### Phase 2 — Analytics Engine ✅ COMPLETE
- [x] Risk metrics
- [x] Asset allocation
- [x] Correlation heatmap
- [x] Benchmark comparison
- [x] Dividend analysis

### Phase 3 — Upload Engine ✅ COMPLETE
- [x] Auto-mapping columns
- [x] CSV/Excel parser
- [x] Data validation
- [x] Analytics integration

### Phase 4 — Reports + AI 🔄 IN PROGRESS
- [x] PDF export framework
- [ ] OpenAI integration
- [ ] AI-generated summaries
- [ ] Enhanced PDF templates

### Phase 5 — Polish & Advanced Features 📋 PLANNED
- [ ] UI/UX refinements
- [ ] Monte Carlo simulation
- [ ] Auto-rebalancing suggestions
- [ ] Broker integrations (Plaid)
- [ ] Real-time streaming data
- [ ] ML optimization

---

## 🔵 SECTION 12 — ADVANCED FEATURES (Future)

### Planned Enhancements
1. **Monte Carlo Simulation**
   - Predict portfolio outcomes over time
   - Risk-adjusted return projections

2. **Auto Rebalancing**
   - Suggest trades to maintain target allocation
   - Tax-aware rebalancing

3. **Broker Connections**
   - Integrate with Plaid
   - Auto-sync positions

4. **Real-Time Streaming**
   - WebSocket price updates
   - Live portfolio value

5. **Machine Learning**
   - Portfolio optimization
   - Risk prediction
   - Correlation forecasting

---

## 🔵 SECTION 13 — IMPLEMENTATION STATUS

### Features Completed ✅
| Feature | Status | Notes |
|---------|--------|-------|
| Portfolio Builder | ✅ | Fully functional |
| CSV Upload | ✅ | Multiple formats supported |
| Asset Allocation Charts | ✅ | Pie, bar, line charts |
| Risk Metrics | ✅ | Beta, Sharpe, VaR, etc. |
| Correlation Heatmap | ✅ | Python backend |
| Benchmark Comparison | ✅ | vs S&P 500 |
| PDF Reports | ✅ | LaTeX-based |
| API Documentation | ✅ | Swagger UI |
| Deployment | ✅ | Render + Vercel |
| Confluence Integration | ✅ | Auto-sync docs |

### In Progress 🔄
| Feature | Status | ETA |
|---------|--------|-----|
| AI Insights | 🔄 | Q1 2026 |
| User Authentication | 🔄 | Q1 2026 |
| Advanced Tax Analysis | 🔄 | Q2 2026 |

### Planned 📋
| Feature | Status | ETA |
|---------|--------|-----|
| Monte Carlo | 📋 | Q2 2026 |
| Broker Integration | 📋 | Q3 2026 |
| Mobile App | 📋 | Q4 2026 |

---

## 🎯 NEXT STEPS

### For Developers
1. Review complete codebase at GitHub
2. Check API docs at `/docs` endpoint
3. Follow Confluence setup guide for documentation
4. Review PRD for roadmap alignment

### For Product Team
1. Prioritize Phase 4 features
2. Define OpenAI integration requirements
3. Design advanced PDF templates
4. Plan user authentication flow

### For Stakeholders
1. Review live deployment
2. Test current features
3. Provide feedback on UX/UI
4. Approve Phase 4 budget

---

## 📞 RESOURCES

**Live Platform:**
- Frontend: https://portfolio-analytics-dashboard-seven.vercel.app
- Backend API: https://portfolio-analytics-dashboard-tlan.onrender.com
- API Docs: https://portfolio-analytics-dashboard-tlan.onrender.com/docs

**Documentation:**
- GitHub: https://github.com/yogeshsinghkatoch9/portfolio-analytics-dashboard
- Deployment Guide: See `walkthrough.md`
- API Reference: See `/docs` endpoint

**Development:**
- Language: Python 3.11, JavaScript
- Frameworks: FastAPI, Vanilla JS
- Database: SQLite
- Hosting: Render.com, Vercel

---

**Document Status:** 🟢 Active and Maintained  
**Review Cycle:** Monthly  
**Next Review:** January 5, 2026

**This PRD will be automatically synced to Confluence** using the automation setup created.
