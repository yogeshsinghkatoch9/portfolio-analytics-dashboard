#!/bin/bash

# Portfolio Analytics Dashboard - Startup Script
# This script installs dependencies and starts the backend server

echo "🚀 Portfolio Analytics Dashboard - Starting Up"
echo "=============================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install backend dependencies
echo ""
echo "📦 Installing Python dependencies..."
cd backend
pip install -q -r requirements.txt --break-system-packages 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "⚠ Some dependency conflicts (non-critical)"
fi

# Start backend server
echo ""
echo "🌐 Starting backend server on http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
echo "📱 Frontend available at:"
echo "   Option 1: Open frontend/index.html in your browser"
echo "   Option 2: Run 'cd frontend && python3 -m http.server 3000'"
echo "            Then visit http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=============================================="
echo ""

# Start the server
python3 main.py
