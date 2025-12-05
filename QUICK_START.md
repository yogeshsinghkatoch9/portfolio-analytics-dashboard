# 🚀 Quick Start Guide - Portfolio Analytics Dashboard

## 📊 Access the Dashboard
```
Open your browser: http://localhost:8000
```

---

## Portfolio Builder - Add Stocks

### Step 1: Search for a Stock
1. Click on **"Portfolio Builder"** tab
2. Type any stock ticker in the search box (e.g., "AAPL", "MSFT", "GOOGL")
3. Wait 0.5 seconds for results to appear
4. You'll see:
   - Stock symbol
   - Company name
   - **Live price from Yahoo Finance**

### Step 2: Add Stock to Portfolio
1. Click on the stock in the search results
2. Stock appears in "Proposed Holdings"
3. You'll see:
   - Stock symbol
   - Current price (automatically fetched from Yahoo Finance)
   - Allocation % field (editable)

### Step 3: Set Allocation Percentage
1. Enter the percentage you want (0-100)
2. Total allocation shows at the top
3. Add more stocks by repeating steps 1-2

### Step 4: Analyze Portfolio
1. Make sure total allocation equals ~100%
2. Click **"Analyze Portfolio"** button
3. View:
   - Estimated Returns
   - Risk Metrics
   - Asset Allocation Chart
   - Risk Analysis

---

## 📁 Current Portfolio - Upload Files

### Step 1: Prepare Your File
File can be CSV or Excel with columns like:
```
Symbol, Quantity, Price, Description, Principal, etc.
AAPL,   100,     150,   Apple Inc.,   15000
MSFT,   50,      300,   Microsoft,    15000
```

### Step 2: Upload File
1. Click on **"Current Portfolio"** tab
2. You'll see upload area with:
   - Drag & drop support
   - Click to browse button
3. Select your CSV/Excel file
4. Wait for processing...

### Step 3: View Dashboard
After upload completes:

#### Summary Cards Show:
- **Total Value** - Your entire portfolio value
- **Total Gain/Loss** - Profit/loss in dollars and %
- **Annual Income** - Expected dividends/distributions
- **Holdings** - Number of stocks

#### Charts Show:
- **Portfolio Allocation** - Pie chart by stock
- **Asset Type Distribution** - Doughnut by type
- **Top Gainers & Losers** - Bar chart
- **Daily Movement** - Daily changes by stock

#### Holdings Table Shows:
- Symbol, Description, Quantity, Price
- Value, Gain/Loss, Return %, Yield %
- Search/filter functionality
- Export to CSV button

---

## 🔍 Search Tips

### Single Stock
```
Type: AAPL
Returns: Apple Inc. with live price from Yahoo Finance
```

### Variations All Work
```
AAPL          ✅ works
Apple         ✅ works  
MSFT          ✅ works
Microsoft     ✅ works
GOOGL         ✅ works
Alphabet      ✅ works
```

### Real-Time Prices
- Prices are fetched directly from Yahoo Finance
- Updated whenever you search
- Used automatically when you add stocks

---

## 📋 Analytics Tab

### Risk Analysis
View:
- Value at Risk (95%)
- Portfolio Volatility
- Diversification Score
- Tax Loss Harvesting Opportunities

### Recommendations
- Based on your risk profile
- Helps optimize allocation
- Choose Conservative/Moderate/Aggressive

### Sector Analysis
- See allocation by business sector
- Technology, Healthcare, Finance, etc.

### Dividends
- Monthly income projection
- Quarterly income projection
- Top dividend-paying stocks

---

## 💾 Export Data

### Export Holdings to CSV
1. Upload portfolio first
2. Go to holdings table
3. Click **"Export CSV"** button
4. File downloads: `portfolio_export.csv`

### Export Portfolio Report (PDF)
1. Click **"Export PDF Report"** button (top right)
2. Report generates with all analytics
3. File downloads: `Portfolio_Report_YYYY-MM-DD.pdf`

---

## ✅ Features Status

All features working and tested:

| Feature | Status | How to Use |
|---------|--------|-----------|
| Search stocks by ticker | ✅ Working | Type in "Add Assets" search |
| Real-time prices from Yahoo Finance | ✅ Working | Automatically fetched when searching |
| Add stocks to portfolio | ✅ Working | Click search result to add |
| Upload CSV/Excel | ✅ Working | Use "Current Portfolio" tab |
| Portfolio dashboard | ✅ Working | Displays after upload |
| Charts & analytics | ✅ Working | Auto-generated from data |
| Holdings table | ✅ Working | Shows all stocks with metrics |
| Export CSV | ✅ Working | Click export button on table |
| Export PDF | ✅ Working | Click export button on top |

---

## 🐛 Troubleshooting

### Search Returns No Results
- Make sure ticker is valid
- Try different variations (AAPL vs Apple)
- Check spelling

### Upload Fails
- File must be CSV or Excel (.xlsx, .xls)
- Must have headers like Symbol, Quantity, Price
- Columns can be in any order

### Dashboard Won't Load
- Refresh the browser (Cmd+R on Mac)
- Check internet connection
- Server needs to be running on port 8000

### Charts Not Showing
- Wait a moment for data to load
- Try refreshing page
- Check browser console (F12) for errors

---

## 🎯 Example Workflow

### Build and Analyze a Portfolio
```
1. Go to Portfolio Builder tab
2. Search "AAPL" → Click to add (20%)
3. Search "MSFT" → Click to add (20%)
4. Search "GOOGL" → Click to add (20%)
5. Search "AMZN" → Click to add (20%)
6. Search "TSLA" → Click to add (20%)
7. Total shows 100%
8. Click "Analyze Portfolio"
9. View projected returns and risk metrics
```

### Upload and Analyze Existing Portfolio
```
1. Go to Current Portfolio tab
2. Drag-drop your portfolio CSV/Excel file
3. Dashboard populates automatically
4. View summary cards and charts
5. Go to Analytics tab for detailed insights
6. Export CSV or PDF for reports
```

---

## 📊 Real-Time Data

The dashboard uses:
- **Stock Prices**: Yahoo Finance API (updated real-time)
- **Historical Data**: 3+ months of OHLCV data
- **Dividends**: Historical dividend records
- **Company Info**: Sector, industry, market cap

---

**Dashboard URL:** http://localhost:8000  
**Server Status:** Running on 0.0.0.0:8000  
**Framework:** FastAPI + HTML5/JavaScript + Chart.js  

Enjoy using your Portfolio Analytics Dashboard! 🚀

**Stop**:
```bash
docker-compose down
```

---

## ☁️ Option 3: Cloud Deploy (Railway + Vercel)

### Backend on Railway

1. **Install Railway CLI**:
```bash
npm install -g @railway/cli
```

2. **Deploy**:
```bash
cd backend
railway login
railway init
railway up
```

3. **Get your URL**:
```bash
railway domain
```

### Frontend on Vercel

1. **Install Vercel CLI**:
```bash
npm install -g vercel
```

2. **Update API URL in `frontend/index.html`**:
```javascript
const API_URL = 'https://your-backend.railway.app';
```

3. **Deploy**:
```bash
cd frontend
vercel deploy --prod
```

**Done!** Your dashboard is live on the internet! 🌐

---

## 📋 Testing the Platform

### Test with Sample File

1. Use the included `sample_portfolio.xlsx`
2. Upload it through the dashboard
3. Verify you see:
   - ✅ Total portfolio value: ~$513K
   - ✅ 77 holdings
   - ✅ 28.36% return
   - ✅ Interactive charts
   - ✅ Holdings table

### Run Automated Tests

```bash
python3 test.py
```

Expected: 6/8 tests pass (2 API tests fail if server not running)

---

## 🔧 Troubleshooting

### "Cannot connect to backend"
**Solution**: Make sure backend is running
```bash
cd backend
python3 main.py
```

### "File parsing error"
**Solution**: Ensure your CSV/Excel has these required columns:
- Symbol
- Quantity  
- Price ($)
- Value ($)

### "Port already in use"
**Solution**: Change port in backend/main.py:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Changed from 8000
```

And update `API_URL` in frontend/index.html:
```javascript
const API_URL = 'http://localhost:8001';
```

### Charts not showing
**Solution**: 
1. Check browser console for errors (F12)
2. Verify Chart.js is loading
3. Try a different browser (Chrome recommended)

---

## 📁 Expected File Format

Your portfolio file should have these columns (order doesn't matter):

**Required**:
- Description
- Symbol
- Quantity
- Price ($)
- Value ($)

**Recommended for full functionality**:
- Assets (%)
- 1-Day Value Change ($)
- 1-Day Price Change (%)
- Account Type
- Principal ($)*
- Principal G/L ($)*
- Principal G/L (%)*
- NFS Cost ($)
- NFS G/L ($)
- NFS G/L (%)
- Asset Type
- Asset Category
- Est Annual Income ($)
- Current Yld/Dist Rate (%)
- Initial Purchase Date

---

## 🎯 What You Get

### Summary Metrics
- 💰 Total Portfolio Value
- 📈 Total Gain/Loss
- 💵 Annual Income
- 📊 Average Yield
- 🔢 Holdings Count
- 📅 Daily Change

### Interactive Charts
- 🥧 Portfolio Allocation (Pie Chart)
- 📊 Asset Type Distribution (Doughnut Chart)
- 📈 Top Gainers & Losers (Bar Chart)
- 📉 Daily Price Movement (Bar Chart)

### Holdings Table
- 🔍 Searchable
- ⬇️ Sortable
- 📥 Exportable to CSV
- 📱 Mobile-responsive

---

## 💡 Pro Tips

### 1. Use Sample Data First
Test with `sample_portfolio.xlsx` before uploading your actual portfolio

### 2. Export Processed Data
Click "Export CSV" to download cleaned data with calculated metrics

### 3. Search Holdings
Use the search box to quickly find specific stocks

### 4. Mobile Access
The dashboard is fully responsive - works great on phones/tablets

### 5. Multiple Portfolios
Upload different files to compare performance (no data is saved)

---

## 🔐 Privacy & Security

- ✅ All processing happens locally or on your server
- ✅ No data is stored permanently
- ✅ No tracking or analytics
- ✅ No account required
- ✅ Files processed in-memory only

---

## 📖 Next Steps

### Learn More
- Read `README.md` for detailed documentation
- Check `DEPLOYMENT.md` for production deployment
- Review `PROJECT_STRUCTURE.md` for architecture

### Customize
- Modify `frontend/index.html` to change UI
- Edit `backend/main.py` to add metrics
- Adjust colors/styling in Tailwind classes

### Get Help
- Run `python3 test.py` to diagnose issues
- Check browser console (F12) for errors
- Review troubleshooting section above

---

## 🎉 Success Checklist

- [ ] Backend running (see terminal output)
- [ ] Frontend accessible in browser
- [ ] Sample file uploads successfully
- [ ] Dashboard displays metrics and charts
- [ ] Holdings table shows data
- [ ] Search and export work

---

## 🔄 Continuous Integration & Testing

### Running Tests Locally

**Backend Unit Tests:**
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

**Frontend E2E Tests (Playwright):**
```bash
npm install
npm run install:playwright

# In one terminal:
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal:
npm start

# In a third terminal:
npx playwright test --ui
```

### GitHub Actions CI

The repository automatically runs tests on:
- Every push to `main` or `master`
- Every pull request

**CI checks:**
- ✅ Backend API starts and responds
- ✅ Frontend dev server starts
- ✅ Playwright E2E test suite passes
- 📊 HTML report artifact uploaded (30-day retention)

See `.github/workflows/playwright-e2e.yml` for full workflow details.

---

## 📞 Need Help?

**Common Issues**:
1. Python dependencies → Run: `pip install -r backend/requirements.txt --break-system-packages`
2. CORS errors → Check API_URL in frontend/index.html matches backend port
3. File parsing → Verify required columns exist in your file
4. Tests failing locally → Ensure both backend and frontend are running on correct ports

**Test Everything**:
```bash
# Test backend
curl http://localhost:8000/health

# Test file upload
curl -X POST -F "file=@sample_portfolio.xlsx" http://localhost:8000/upload-portfolio

# Test API (portfolio save/load)
curl http://localhost:8000/api/v2/portfolio
```

---

## 🚀 You're Ready!

Your portfolio analytics dashboard is now running. Upload your portfolio file and start exploring your investments with beautiful, interactive visualizations!

**Enjoy!** 💼📊✨

---

*Last Updated: December 2024*
*Version: 1.0.0*
