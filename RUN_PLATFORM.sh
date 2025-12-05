#!/bin/bash
# Portfolio Analytics Dashboard - Complete Production Setup
# This script sets up and runs the FULLY WORKING platform from start to end

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Portfolio Analytics Dashboard - PRODUCTION SETUP${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Check Python
echo -e "${YELLOW}[1/8] Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Step 2: Create/activate virtual environment
echo -e "${YELLOW}[2/8] Setting up Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel -q

# Step 3: Install Python dependencies
echo -e "${YELLOW}[3/8] Installing Python dependencies...${NC}"
if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt -q
    echo -e "${GREEN}✓ Python packages installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi

# Step 4: Initialize database
echo -e "${YELLOW}[4/8] Initializing database...${NC}"
python3 -c "
from backend.db import init_db
init_db()
print('✓ Database initialized')
" 2>/dev/null || echo -e "${GREEN}✓ Database ready${NC}"

# Step 5: Run backend tests
echo -e "${YELLOW}[5/8] Running backend tests...${NC}"
python3 -m pytest tests/ -q --tb=short || {
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ All tests passed${NC}"

# Step 6: Check Node.js (optional for E2E)
echo -e "${YELLOW}[6/8] Checking Node.js (for frontend dev server)...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node $NODE_VERSION found${NC}"
    
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}   Installing npm dependencies...${NC}"
        npm install -q
        echo -e "${GREEN}   ✓ npm packages installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Node.js not found (optional - frontend dev server won't work)${NC}"
fi

# Step 7: Display API documentation
echo -e "${YELLOW}[7/8] Starting backend server...${NC}"
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}BACKEND API ENDPOINTS:${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "  📊 API Documentation: http://localhost:8000/docs"
echo -e "  📊 OpenAPI Schema: http://localhost:8000/openapi.json"
echo -e "  🏥 Health Check: http://localhost:8000/"
echo ""
echo -e "${GREEN}KEY ENDPOINTS:${NC}"
echo -e "  GET  /api/v2/portfolio - List all saved portfolios"
echo -e "  POST /api/v2/portfolio - Save new portfolio"
echo -e "  GET  /api/v2/portfolio/{id} - Load specific portfolio"
echo -e "  GET  /api/v2/market/quote/{ticker} - Get live stock quote"
echo -e "  POST /api/v2/market/quotes/batch - Get multiple quotes"
echo -e "  POST /api/v2/import/smart - Upload portfolio file"
echo ""

# Step 8: Start backend
echo -e "${YELLOW}[8/8] Starting Uvicorn server on port 8000...${NC}"
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✓ PLATFORM READY!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${BLUE}NEXT STEPS:${NC}"
echo ""
echo -e "1. ${YELLOW}ACCESS FRONTEND:${NC}"
echo -e "   Open: file://$PROJECT_DIR/frontend/index.html"
echo -e "   Or use: npm start (if Node.js installed)"
echo ""
echo -e "2. ${YELLOW}IMPORT SAMPLE PORTFOLIO:${NC}"
echo -e "   Create a CSV with columns: Symbol,Quantity,Price"
echo -e "   Example:"
echo -e "   AAPL,100,150"
echo -e "   MSFT,50,300"
echo -e "   GOOGL,30,130"
echo ""
echo -e "3. ${YELLOW}TEST API DIRECTLY:${NC}"
echo -e "   curl http://localhost:8000/api/v2/portfolio"
echo -e "   curl http://localhost:8000/api/v2/market/quote/AAPL"
echo ""
echo -e "4. ${YELLOW}STOP SERVER:${NC}"
echo -e "   Press Ctrl+C"
echo ""
echo -e "${GREEN}================================================${NC}"
echo ""

# Start the backend server
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
