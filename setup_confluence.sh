#!/bin/bash

# Confluence Sync - Quick Start Script

echo "🚀 Confluence Sync Setup"
echo "========================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your Confluence credentials:"
    echo "   - CONFLUENCE_URL"
    echo "   - CONFLUENCE_EMAIL"
    echo "   - CONFLUENCE_API_TOKEN"
    echo "   - CONFLUENCE_SPACE_KEY"
    echo ""
    echo "Run this script again after editing .env"
    exit 1
fi

# Check if dependencies are installed
echo "📦 Installing dependencies..."
pip install -q -r confluence_requirements.txt

# Test connection
echo ""
echo "🔌 Testing Confluence connection..."
python confluence_sync.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Check Confluence - your docs should be there!"
echo "   2. Edit docs/prd.md to customize your PRD"
echo "   3. Add more docs to sync in confluence_sync.py"
echo "   4. Push to GitHub to enable auto-sync"
