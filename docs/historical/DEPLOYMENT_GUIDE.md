# Portfolio Analytics Dashboard - Deployment Guide

## Quick Start (Local Development)

### Prerequisites
- Python 3.9+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Steps

1. **Navigate to project directory**:
```bash
cd "/Users/yogeshsinghkatoch/Desktop/New Project/portfolio-analytics-dashboard"
```

2. **Install backend dependencies**:
```bash
pip3 install --user -r backend/requirements.txt
```

3. **Start the backend server**:
```bash
python3 backend/main.py
```

Server will start on `http://0.0.0.0:8000`

4. **Open the frontend**:
Open `frontend/index.html` in your browser, or navigate to:
```
file:///Users/yogeshsinghkatoch/Desktop/New%20Project/portfolio-analytics-dashboard/frontend/index.html
```

---

## Docker Deployment

### Build and Run with Docker Compose

1. **Update `docker-compose.yml`** (already configured):
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./backend:/app
    restart: unless-stopped

  frontend:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./frontend:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
    restart: unless-stopped
```

2. **Build and start containers**:
```bash
docker-compose up -d
```

3. **Access the application**:
- Frontend: `http://localhost`
- Backend API: `http://localhost:8000`

4. **Stop containers**:
```bash
docker-compose down
```

---

## Cloud Deployment Options

### Option 1: Heroku (Free Tier Available)

1. **Install Heroku CLI**:
```bash
brew tap heroku/brew && brew install heroku
```

2. **Login to Heroku**:
```bash
heroku login
```

3. **Create Heroku app**:
```bash
heroku create your-portfolio-app
```

4. **Deploy**:
```bash
git init
git add .
git commit -m "Deploy portfolio dashboard"
git push heroku main
```

5. **Open your app**:
```bash
heroku open
```

**Note**: For Heroku, you'll need to create a `Procfile`:
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

### Option 2: AWS EC2

1. **Launch EC2 Instance** (Ubuntu 22.04 LTS recommended):
   - Instance type: t2.micro (free tier)
   - Security group: Allow ports 22, 80, 8000

2. **SSH into instance**:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

3. **Install dependencies**:
```bash
sudo apt update
sudo apt install python3-pip nginx -y
```

4. **Clone/upload your code**:
```bash
scp -i your-key.pem -r portfolio-analytics-dashboard ubuntu@your-ec2-ip:~/
```

5. **Install Python dependencies**:
```bash
cd portfolio-analytics-dashboard
pip3 install -r backend/requirements.txt
```

6. **Setup systemd service** (`/etc/systemd/system/portfolio-api.service`):
```ini
[Unit]
Description=Portfolio Analytics API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/portfolio-analytics-dashboard/backend
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

7. **Start service**:
```bash
sudo systemctl enable portfolio-api
sudo systemctl start portfolio-api
```

8. **Configure Nginx** (`/etc/nginx/sites-available/portfolio`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /home/ubuntu/portfolio-analytics-dashboard/frontend;
        index index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

9. **Enable site and restart Nginx**:
```bash
sudo ln -s /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

### Option 3: DigitalOcean App Platform

1. **Create DigitalOcean account** and install `doctl`

2. **Create app spec** (`app.yaml`):
```yaml
name: portfolio-analytics
services:
  - name: backend
    github:
      repo: your-username/portfolio-analytics
      branch: main
      deploy_on_push: true
    source_dir: /backend
    run_command: python main.py
    http_port: 8000
    instance_count: 1
    instance_size_slug: basic-xxs

  - name: frontend
    github:
      repo: your-username/portfolio-analytics
      branch: main
    source_dir: /frontend
    static_sites:
      - output_dir: /
```

3. **Deploy**:
```bash
doctl apps create --spec app.yaml
```

---

## Environment Configuration

Create `.env` file in backend directory:

```env
# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
ENABLE_CORS=true

# Cache Configuration
CACHE_TTL=300

# Logging
LOG_LEVEL=info

# Optional: API Keys (if you add premium features)
# ALPHA_VANTAGE_API_KEY=your_key_here
# IEX_CLOUD_API_KEY=your_key_here
```

Load with `python-dotenv` in `main.py`:
```python
from dotenv import load_dotenv
import os

load_dotenv()

API_PORT = int(os.getenv('API_PORT', 8000))
```

---

## Production Optimizations

### 1. Enable HTTPS

**With Let's Encrypt (free)**:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. Add Rate Limiting

Install `slowapi`:
```bash
pip install slowapi
```

Update `main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/upload-portfolio")
@limiter.limit("10/minute")
async def upload_portfolio(request: Request, file: UploadFile = File(...)):
    # ... existing code
```

### 3. Add Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### 4. Database Integration (Optional)

For persistent storage, add PostgreSQL:

```bash
pip install psycopg2-binary sqlalchemy
```

---

## Monitoring & Maintenance

### Health Checks

The API includes a health check endpoint:
```bash
curl http://localhost:8000/health
```

### Log Monitoring

```bash
# View logs
tail -f app.log

# Docker logs
docker-compose logs -f backend
```

### Backup Strategy

1. **Code**: Use Git for version control
2. **User Data**: If storing portfolios, backup database regularly
3. **Configuration**: Keep `.env` files in secure location

---

## Troubleshooting

### Backend won't start

**Issue**: `ModuleNotFoundError`
**Solution**: Install missing dependencies
```bash
pip3 install --user -r backend/requirements.txt
```

**Issue**: Port 8000 already in use
**Solution**: Kill existing process or change port

```bash
lsof -ti:8000 | xargs kill -9
# OR change port in main.py
```

### Frontend can't connect to API

**Issue**: CORS errors
**Solution**: Ensure backend has CORS middleware enabled

**Issue**: Wrong API_URL
**Solution**: Update API_URL in `index.html` to match your deployment

### Charts not rendering

**Issue**: Chart.js not loading
**Solution**: Check browser console, ensure CDN is accessible

---

## Security Checklist

- [ ] Enable HTTPS in production
- [ ] Add rate limiting
- [ ] Validate file uploads (size, type)
- [ ] Sanitize user inputs
- [ ] Keep dependencies updated
- [ ] Use environment variables for secrets
- [ ] Enable firewall rules
- [ ] Regular security audits

---

## Performance Tips

1. **Enable Gzip compression** in Nginx
2. **Cache static files** with appropriate headers
3. **Use CDN** for Chart.js and Tailwind
4. **Minimize API calls** by caching quote data
5. **Lazy load charts** only when tabs are viewed

---

## Next Steps

1. **Custom Domain**: Point your domain to deployment
2. **SSL Certificate**: Enable HTTPS
3. **Monitoring**: Add APM like New Relic or DataDog
4. **Backup**: Schedule regular backups
5. **CI/CD**: Set up automated deployment pipeline
6. **Testing**: Add automated E2E tests

---

## Support

For issues:
1. Check logs first
2. Verify all dependencies are installed
3. Test with sample portfolio file
4. Check browser console for errors

**API Documentation**: Available at `http://localhost:8000/docs` (FastAPI Swagger UI)
