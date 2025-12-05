# Phase 2 Installation & Deployment Guide

## 📦 Installation Steps

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Modern web browser
- Internet connection (for Yahoo Finance data)

---

## 🚀 Local Installation

### Step 1: Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

This installs all required packages:
- fastapi - API framework
- uvicorn - ASGI server
- pandas - Data processing
- numpy - Numerical computing
- yfinance - Stock market data
- openpyxl - Excel support
- and more...

### Step 2: Verify Installation
```bash
python -c "import fastapi, pandas, yfinance; print('✓ All dependencies installed')"
```

### Step 3: Start Backend Server
```bash
# From backend directory
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 4: Test Backend
```bash
# In another terminal
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "timestamp": "2025-12-04T..."}
```

### Step 5: Run Test Suite
```bash
# From project root directory
python test_phase2.py
```

This runs all 9 comprehensive tests.

---

## 🌐 Frontend Setup

### Option 1: Simple HTTP Server
```bash
# From frontend directory
python -m http.server 3000

# Access at: http://localhost:3000
```

### Option 2: Live Server (VS Code)
- Install "Live Server" extension
- Right-click index.html → "Open with Live Server"
- Automatically opens in browser

### Option 3: Production Web Server
```bash
# Using Node.js http-server
npm install -g http-server
http-server frontend -p 3000
```

---

## 🐳 Docker Deployment

### Step 1: Build Backend Image
```bash
docker build -f Dockerfile.backend -t portfolio-backend:phase2 .
```

### Step 2: Build Frontend (Optional)
```bash
# If using Nginx
docker build -f Dockerfile.frontend -t portfolio-frontend:phase2 .
```

### Step 3: Run with Docker Compose
```bash
docker-compose up -d
```

This starts:
- Backend on port 8000
- Frontend on port 3000 (or 80 if Nginx)

---

## ☁️ Cloud Deployment

### Heroku Deployment
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Create Heroku app
heroku create your-app-name

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### Railway.app Deployment
1. Connect GitHub repository
2. Create "Python" service
3. Set start command: `cd backend && python main.py`
4. Deploy automatically on push

### AWS Deployment
```bash
# Using EC2
# 1. Launch EC2 instance (Ubuntu 22.04)
# 2. SSH into instance
# 3. Clone repository
# 4. Install Python 3.9+
# 5. Run installation steps above
# 6. Use systemd or supervisor for process management

# Example systemd service file:
# /etc/systemd/system/portfolio-api.service
[Unit]
Description=Portfolio Analytics API
After=network.target

[Service]
Type=notify
User=ec2-user
WorkingDirectory=/home/ec2-user/portfolio-analytics-dashboard/backend
ExecStart=/usr/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🔧 Configuration

### Environment Variables
Create `.env` file in backend directory:
```bash
# Optional - for future API keys
YAHOO_FINANCE_API_KEY=your_key_here
ALPHA_VANTAGE_KEY=your_key_here
```

### Backend Settings
In `backend/main.py`:
```python
# Quote cache TTL (seconds)
CACHE_TTL = 300  # 5 minutes

# CORS settings (already enabled for all origins)
# Change as needed for production:
allow_origins=["http://localhost:3000", "https://yourdomain.com"]
```

### Server Configuration
Change port in `backend/main.py`:
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # Change port here
```

---

## 🧪 Testing & Validation

### Run Test Suite
```bash
python test_phase2.py
```

### Manual API Testing
```bash
# Test all endpoints
bash test_endpoints.sh  # (if you create this script)

# Or use individual curl commands
curl http://localhost:8000/api/v2/market/quote/AAPL
curl -X POST http://localhost:8000/api/v2/market/quotes/batch \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL"]}'
```

### Frontend Testing
1. Open http://localhost:3000 in browser
2. Test file upload
3. Test live quote fetching
4. Test ticker search

---

## 📝 Maintenance

### Update Dependencies
```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package_name

# Update all packages
pip install --upgrade -r requirements.txt
```

### Clear Cache (if needed)
```python
# In Python shell or script:
import requests
# Cache is in memory, automatically cleared every 5 minutes
# Manual clear: Restart backend server
```

### Monitor Backend
```bash
# Check Python process
ps aux | grep python

# Monitor system resources
top  # or use Activity Monitor on Mac

# Check logs
# Backend logs print to console
# For persistent logging, redirect to file:
python main.py > backend.log 2>&1 &
```

---

## 🆘 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'fastapi'"
**Solution**: Run `pip install -r requirements.txt` in backend directory

### Error: "Address already in use"
**Solution**: 
```bash
# Kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
# Edit main.py: uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Error: "Connection refused" from frontend
**Solution**:
1. Ensure backend is running on correct port
2. Check CORS is enabled in main.py
3. Verify frontend is using correct API URL

### Error: "No module named 'yfinance'"
**Solution**: `pip install yfinance`

### Error: "Failed to fetch quote"
**Solution**:
1. Check internet connection
2. Verify ticker symbol is valid (e.g., AAPL not apple)
3. Yahoo Finance might be rate limiting - wait a minute

### File Import Not Working
**Solution**:
1. Verify file format (.csv or .xlsx)
2. Check file has required columns
3. Ensure column names match expected format
4. Check file isn't corrupted

---

## 🔒 Security Checklist

For production deployment:

- [ ] Disable CORS for all origins
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] Enable HTTPS/SSL
- [ ] Use environment variables for sensitive data
- [ ] Set strong file upload limits
- [ ] Add authentication/authorization
- [ ] Enable rate limiting
- [ ] Monitor for suspicious activity
- [ ] Keep dependencies updated
- [ ] Use `.gitignore` for sensitive files
- [ ] Store uploaded files securely
- [ ] Add logging for audit trail

---

## 📊 Performance Optimization

### For Production:
```bash
# Use Gunicorn instead of Uvicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### Caching Optimization:
```python
# In market_data.py
# Increase cache TTL for less frequently updated data
CACHE_TTL = 600  # 10 minutes instead of 5

# Or implement Redis caching for scale
import redis
redis_client = redis.Redis(host='localhost', port=6379)
```

### Database (Optional):
For future features, consider:
```bash
# PostgreSQL for data persistence
pip install psycopg2-binary sqlalchemy

# MongoDB for flexible schema
pip install pymongo

# Or use SQLite for simplicity
import sqlite3
```

---

## 📈 Monitoring & Logging

### Basic Logging
```python
# Add to backend/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use in code:
logger.info(f"Portfolio imported: {filename}")
logger.error(f"Failed to fetch quote for {ticker}: {error}")
```

### Advanced Monitoring (Production):
```bash
# Install monitoring tools
pip install prometheus-client  # Metrics
pip install python-json-logger  # JSON logging

# Set up alerts
# Use services like: Sentry, DataDog, New Relic
```

---

## 🎯 Deployment Checklist

Before going live, verify:

- [ ] All dependencies installed
- [ ] Backend starts without errors
- [ ] All API endpoints responding correctly
- [ ] Test suite passes (9/9 tests)
- [ ] Frontend can connect to backend
- [ ] File upload works (CSV and Excel)
- [ ] Live quotes updating correctly
- [ ] Portfolio enrichment working
- [ ] Error handling in place
- [ ] Logging configured
- [ ] Security settings reviewed
- [ ] Performance optimized
- [ ] Documentation updated

---

## 📚 Additional Resources

### Official Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Uvicorn Guide](https://www.uvicorn.org/)
- [yfinance Library](https://github.com/ranaroussi/yfinance)
- [Pandas Documentation](https://pandas.pydata.org/docs/)

### Deployment Guides
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Heroku Python Apps](https://devcenter.heroku.com/articles/getting-started-with-python)
- [AWS EC2 Setup](https://aws.amazon.com/ec2/getting-started/)

### API Testing
- [Postman Collection](https://www.postman.com/)
- [Insomnia REST Client](https://insomnia.rest/)
- [curl Tutorial](https://curl.se/)

---

## 📞 Getting Help

### Common Issues
1. Check test_phase2.py output for specific errors
2. Review PHASE_2_GUIDE.md for API details
3. Check backend console logs
4. Verify requirements.txt installed correctly

### Testing Specific Features
```bash
# Test individual components
python -c "import yfinance as yf; stock = yf.Ticker('AAPL'); print(stock.info['currentPrice'])"
python -c "import pandas as pd; df = pd.read_csv('test.csv'); print(df.head())"
```

---

## 🚀 Quick Reference

### Start Development
```bash
cd backend && python main.py
# In another terminal:
cd frontend && python -m http.server 3000
```

### Run Tests
```bash
python test_phase2.py
```

### Check Status
```bash
curl http://localhost:8000/health
```

### Stop Server
```bash
# Ctrl+C in terminal
# Or kill process:
pkill -f "python main.py"
```

---

## ✅ You're Ready!

Your Phase 2 deployment is complete. The system is ready for:
- ✅ Multiple brokerage portfolio imports
- ✅ Real-time stock market data
- ✅ Live portfolio enrichment
- ✅ Advanced stock analysis

**Happy investing! 📈**

---

**Last Updated**: December 4, 2025  
**Version**: Phase 2.0  
**Status**: Production Ready
