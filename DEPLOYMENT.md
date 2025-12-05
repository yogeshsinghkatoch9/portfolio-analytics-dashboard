# Deployment Guide

## Quick Deployment Options

### Option 1: Local Development (Fastest)

**Start Backend:**
```bash
./start.sh
```

**Start Frontend:**
Open `frontend/index.html` in your browser, or:
```bash
cd frontend
python3 -m http.server 3000
```

Visit: `http://localhost:3000`

---

### Option 2: Docker Compose (Recommended for Production)

**Prerequisites:**
- Docker
- Docker Compose

**Deploy:**
```bash
docker-compose up -d
```

**Access:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

**Stop:**
```bash
docker-compose down
```

**View Logs:**
```bash
docker-compose logs -f
```

---

### Option 3: Railway (Backend Hosting)

**Prerequisites:**
- Railway account (free tier available)
- Railway CLI

**Steps:**

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
# or
curl -fsSL https://railway.app/install.sh | sh
```

2. **Login:**
```bash
railway login
```

3. **Create project:**
```bash
railway init
```

4. **Deploy backend:**
```bash
cd backend
railway up
```

5. **Get backend URL:**
```bash
railway domain
```

6. **Update frontend:**
Edit `frontend/index.html` and change:
```javascript
const API_URL = 'https://your-app.railway.app';
```

**Environment Variables:**
Railway automatically detects Python and installs dependencies.

**Custom Start Command (if needed):**
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

### Option 4: Vercel (Frontend Hosting)

**Prerequisites:**
- Vercel account
- Vercel CLI

**Steps:**

1. **Install Vercel CLI:**
```bash
npm install -g vercel
```

2. **Deploy frontend:**
```bash
cd frontend
vercel deploy --prod
```

3. **Configure:**
Create `vercel.json`:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

4. **Update API URL:**
Edit `index.html`:
```javascript
const API_URL = 'https://your-backend.railway.app';
```

---

### Option 5: Render (Full Stack)

**Backend:**

1. Create new Web Service on Render
2. Connect your Git repository
3. Configure:
   - **Build Command:** `cd backend && pip install -r requirements.txt`
   - **Start Command:** `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3

**Frontend:**

1. Create new Static Site on Render
2. Configure:
   - **Build Command:** `echo "No build needed"`
   - **Publish Directory:** `frontend`

3. Update API URL in `frontend/index.html`

---

### Option 6: AWS EC2 (Full Control)

**1. Launch EC2 Instance:**
- Ubuntu 22.04 LTS
- t2.micro (free tier)
- Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)

**2. SSH into instance:**
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

**3. Install dependencies:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3 python3-pip nginx

# Install Docker (optional)
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

**4. Deploy application:**
```bash
# Clone repository
git clone your-repo.git
cd portfolio-analytics

# Using Docker Compose
docker-compose up -d

# OR Manual setup
cd backend
pip3 install -r requirements.txt
nohup python3 main.py &

# Setup Nginx for frontend
sudo cp frontend/* /var/www/html/
```

**5. Configure Nginx:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**6. Setup SSL (optional):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

### Option 7: Heroku

**Backend:**

1. Create `Procfile`:
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

2. Create `runtime.txt`:
```
python-3.11.5
```

3. Deploy:
```bash
heroku login
heroku create your-app-name
git push heroku main
```

**Frontend:**
Deploy to Netlify or Vercel, update API URL

---

## Production Checklist

### Security
- [ ] Change CORS origins in `backend/main.py`
- [ ] Add API rate limiting
- [ ] Enable HTTPS
- [ ] Add authentication (if needed)
- [ ] Sanitize file uploads
- [ ] Set up monitoring

### Performance
- [ ] Enable gzip compression
- [ ] Set up CDN for frontend assets
- [ ] Configure caching headers
- [ ] Optimize chart rendering
- [ ] Add database for persistence (if needed)

### Backend Configuration
```python
# In main.py, update CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Frontend Configuration
```javascript
// In index.html, update:
const API_URL = process.env.API_URL || 'https://your-backend.com';
```

---

## Environment Variables

### Backend (.env)
```bash
# Optional configurations
MAX_FILE_SIZE_MB=10
ENABLE_CORS=true
ALLOWED_ORIGINS=https://your-frontend.com
LOG_LEVEL=info
```

### Frontend
```javascript
// Update in index.html
const CONFIG = {
    API_URL: 'https://your-backend.com',
    MAX_FILE_SIZE_MB: 10,
    ENABLE_ANALYTICS: false
};
```

---

## Monitoring & Logs

### Docker Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Railway Logs
```bash
railway logs
```

### System Logs (Linux)
```bash
# Backend logs
tail -f nohup.out

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## Scaling Considerations

### Horizontal Scaling
- Use load balancer (AWS ELB, Nginx)
- Deploy multiple backend instances
- Share session state via Redis

### Vertical Scaling
- Increase instance size
- Optimize Pandas operations
- Add caching layer

### Database (Optional)
If you need to store portfolio history:
```bash
# Add PostgreSQL
docker-compose.yml:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: portfolio
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure_password
```

---

## Backup & Disaster Recovery

### Backup uploaded files (if stored):
```bash
# Create backup
tar -czf portfolio-backup-$(date +%Y%m%d).tar.gz /path/to/uploads

# Automated backup (cron)
0 2 * * * tar -czf /backups/portfolio-$(date +\%Y\%m\%d).tar.gz /app/uploads
```

### Database backup (if using):
```bash
# PostgreSQL
pg_dump portfolio > portfolio_backup.sql

# Automated
0 2 * * * pg_dump portfolio > /backups/portfolio-$(date +\%Y\%m\%d).sql
```

---

## Cost Estimates

### Free Tier Options:
- **Vercel** (Frontend): Free for personal projects
- **Railway** (Backend): $5/month starter plan
- **Render** (Full stack): Free tier available
- **Total**: $0-5/month

### Production:
- **AWS EC2** (t3.small): ~$15/month
- **AWS RDS** (optional): ~$15/month
- **CloudFlare** (CDN): Free
- **Total**: $15-30/month

---

## CI/CD Pipeline

### GitHub Actions Workflows

The repository includes automated CI/CD workflows:

**1. Playwright E2E Tests (`.github/workflows/playwright-e2e.yml`)**

Runs on every push to `main`/`master` and on pull requests:

- Installs Python dependencies and creates a virtual environment
- Starts the backend API (uvicorn on port 8000)
- Installs Node dependencies and Playwright browsers
- Starts the frontend dev server (live-server on port 5173)
- Runs Playwright E2E tests with HTML reporting
- Uploads test report as an artifact for review

**Key Commands in Workflow:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000

npm ci
npm run install:playwright
npm start
npx playwright test --reporter=html
```

**Artifacts:**
- `playwright-report/` — HTML report of test results (30 days retention)
- Backend logs: `backend_uvicorn.log`
- Frontend logs: `frontend_dev.log`

### Local CI Testing

To test locally before pushing:

```bash
# Backend
source .venv/bin/activate
python -m pytest tests/ -v

# Frontend + E2E
npm install
npm run install:playwright
# (start backend in another terminal)
npx playwright test --ui
```

### Extending CI

To add more workflows or jobs:

1. Create new workflow files in `.github/workflows/`
2. Use `actions/setup-python`, `actions/setup-node` for dependencies
3. Reference `.github/workflows/playwright-e2e.yml` as a template

---

## Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Verify environment variables
3. Test API: `curl http://localhost:8000/health`
4. Check CORS configuration
5. Verify file upload limits

---

## Next Steps After Deployment

1. Test with sample portfolio file
2. Set up monitoring (Sentry, New Relic)
3. Configure automated backups
4. Set up CI/CD pipeline
5. Add user authentication (if needed)
6. Enable analytics (optional)

---

**Need help?** Check the main README.md or create an issue.
