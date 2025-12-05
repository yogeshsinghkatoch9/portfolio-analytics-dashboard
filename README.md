# Portfolio Analytics Dashboard

A professional, full-stack portfolio visualization platform that processes CSV/Excel files and generates interactive analytics, charts, and insights.

## Features

### 📊 Analytics Dashboard
- **Real-time Metrics**: Total value, gain/loss, returns, annual income, yield
- **Interactive Charts**: 
  - Portfolio allocation (pie chart)
  - Asset type distribution (doughnut chart)
  - Top gainers/losers (bar chart)
  - Daily price movements (bar chart)
- **Searchable Holdings Table**: View all positions with detailed metrics
- **Export Functionality**: Download processed data as CSV

### 🔐 Data Processing
- Parses CSV and Excel files (.csv, .xlsx, .xls)
- Validates data integrity
- Computes derived metrics automatically
- Handles missing data gracefully

### 💻 Technology Stack
- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, Tailwind CSS, Chart.js
- **Data Processing**: Pandas, NumPy, OpenPyXL

## Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser

### Installation

1. **Install Python dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

2. **Start the backend server**:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

3. **Open the frontend**:
```bash
cd ../frontend
# Open index.html in your browser, or use a local server:
python -m http.server 3000
```

Then navigate to `http://localhost:3000`

## Usage

### Upload Portfolio File

1. Click the upload area or drag-and-drop your CSV/Excel file
2. The system will automatically:
   - Parse and validate the file
   - Clean and normalize data
   - Compute all metrics
   - Generate visualizations

### Expected File Format

The CSV/Excel file should contain these columns:

**Core Holdings Data**:
- Description
- Symbol
- Quantity
- Price ($)
- Value ($)
- Assets (%)

**Performance Metrics**:
- 1-Day Value Change ($)
- 1-Day Price Change (%)
- Principal ($)*
- Principal G/L ($)*
- Principal G/L (%)*
- NFS Cost ($)
- NFS G/L ($)
- NFS G/L (%)

**Classifications**:
- Account Type
- Asset Type
- Asset Category

**Income Data**:
- Est Annual Income ($)
- Current Yld/Dist Rate (%)
- Dividend Instructions
- Cap Gain Instructions

**Other**:
- Initial Purchase Date
- Est Tax G/L ($)*

*Note: Fields marked with * are optional

### API Endpoints

#### `POST /upload-portfolio`
Upload and process portfolio file

**Request**: Multipart form data with file
**Response**:
```json
{
  "success": true,
  "filename": "portfolio.xlsx",
  "summary": {
    "total_value": 514082.95,
    "total_principal": 198745.27,
    "total_gain_loss": 315337.68,
    "overall_return_pct": 158.67,
    "total_daily_change": -1234.56,
    "daily_return_pct": -0.24,
    "total_annual_income": 12345.67,
    "avg_yield": 2.4,
    "num_holdings": 75
  },
  "charts": { ... },
  "holdings": [ ... ]
}
```

#### `GET /health`
Health check endpoint

## Deployment

### Option 1: Railway (Recommended for Backend)

1. Create `railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
```

2. Deploy:
```bash
railway login
railway init
railway up
```

### Option 2: Vercel (Frontend)

```bash
cd frontend
vercel deploy
```

Update `API_URL` in `index.html` to your Railway backend URL.

### Option 3: Docker

**Backend Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run**:
```bash
docker build -t portfolio-backend .
docker run -p 8000:8000 portfolio-backend
```

## Data Security

- All processing happens locally or on your server
- No data is stored permanently
- Files are processed in memory only
- CORS enabled for local development (restrict in production)

## Customization

### Adding New Chart Types

Edit `frontend/index.html`, add chart in `renderCharts()`:

```javascript
const newChart = new Chart(ctx, {
    type: 'line',
    data: { ... },
    options: { ... }
});
```

### Modifying Metrics

Edit `backend/main.py`, update `compute_summary_metrics()`:

```python
def compute_summary_metrics(df):
    # Add your custom calculations
    custom_metric = df['Value ($)'].std()
    return {
        ...
        'custom_metric': custom_metric
    }
```

## Troubleshooting

### "File parsing error"
- Ensure file has required columns: Symbol, Quantity, Price ($), Value ($)
- Check for valid CSV/Excel format
- Remove any merged cells in Excel files

### "CORS Error"
- Ensure backend is running on `http://localhost:8000`
- Update `API_URL` in `index.html` if using different port
- For production, configure proper CORS origins in `main.py`

### Charts not rendering
- Check browser console for errors
- Verify Chart.js loaded correctly
- Ensure data is in correct format

## Testing

Test with the provided sample file:
```bash
cd backend
python main.py
```

Then upload `Holdings__13_.xlsx` through the web interface.

## Performance

- Handles portfolios up to 1000+ holdings
- Processing time: <1 second for typical files
- Chart rendering: <500ms

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

MIT License - feel free to modify and use for your projects.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation
3. Check browser console for errors

## Roadmap

- [ ] Historical performance tracking
- [ ] Sector analysis
- [ ] Risk metrics (volatility, Sharpe ratio)
- [ ] Portfolio comparison
- [ ] PDF report generation
- [ ] Multi-account consolidation
- [ ] Real-time price updates via API

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

Built with ❤️ for portfolio management
