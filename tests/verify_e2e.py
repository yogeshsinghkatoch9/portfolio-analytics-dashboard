
import asyncio
import httpx
from backend.db import init_db
import os

# Configuration
BASE_URL = "http://localhost:8000"

async def verify_e2e():
    print("🚀 Starting End-to-End Platform Verification...")
    
    # Ensure DB is ready (assuming server is running, or we use direct DB access, 
    # but for E2E we should hit endpoints. We'll assume the user has the server running or we can start it?)
    # Since I cannot easily verify if the server is running, I will write this as a test that *can* be run against a live server,
    # or I will verify using direct function calls if I want to be self-contained. 
    # Given the previous pattern, I'll use direct function calls or TestClient which is safer.
    
    # Use AsyncClient for better compatibility with modern FastAPI/httpx
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    
    # Init DB to ensure tables exist
    from backend.db import init_db
    init_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("1. Creating a fresh portfolio...")
        # Create Portfolio
        res = await client.post("/api/v2/portfolio", json={"name": "E2E Test Portfolio", "holdings": []})
        if res.status_code != 200:
            print(f"❌ Failed to create portfolio: {res.text}")
        assert res.status_code == 200
        pid = res.json()['id']
        print(f"   ✅ Portfolio created via API (ID: {pid})")
        
        print("2. Adding Assets...")
        # Add Stock (AAPL)
        item_stock = {
            "ticker": "AAPL",
            "quantity": 10,
            "price": 150.0,
            "cost_basis": 1400.0,
            "metadata": {"type": "Stock"}
        }
        res = await client.post(f"/api/v2/portfolio/{pid}/holdings", json=item_stock)
        if res.status_code != 200:
             print(f"❌ Failed to add stock: {res.text}")
        assert res.status_code == 200
        
        # Add Crypto (BTC-USD) - Testing Multi-Asset
        item_crypto = {
            "ticker": "BTC-USD",
            "quantity": 0.5,
            "price": 30000.0,
            "cost_basis": 15000.0,
            "metadata": {"type": "Crypto"}
        }
        res = await client.post(f"/api/v2/portfolio/{pid}/holdings", json=item_crypto)
        assert res.status_code == 200
        print("   ✅ Assets (Stock + Crypto) added")
        
        print("3. Verifying Analytics...")
        res = await client.get(f"/api/v2/portfolio/{pid}/analytics")
        assert res.status_code == 200
        data = res.json()
        
        # Check Net Worth
        # AAPL: 10 * 150 = 1500
        # BTC: 0.5 * 30000 = 15000
        # Total: 16500
        summary = data.get('summary', {})
        print(f"   📊 Net Worth reported: ${summary.get('total_value')}")
        assert summary.get('total_value') == 16500.0
        print("   ✅ Net Worth calculation correct")
        
        # Check Deep Analytics (Phase 5)
        analytics = data.get('analytics', {})
        
        # Sector Allocation
        sectors = analytics.get('sector_allocation', {}).get('sectors', [])
        print(f"   Sector Data: {len(sectors)} sectors found")
        assert 'sector_allocation' in analytics
        
        # Risk Metrics
        risk = analytics.get('advanced_risk', {}).get('metrics', {})
        print(f"   Risk Metrics: Beta={risk.get('beta')}, Sharpe={risk.get('sharpe')}")
        assert 'beta' in risk
        assert 'sharpe' in risk
        print("   ✅ Deep Analytics fields present")
        
        print("4. Testing AI Chat...")
        # Test Chat context
        chat_payload = {
            "message": "What is my net worth?",
            "portfolio_context": {
                "net_worth": summary.get('total_value'),
                "total_value": summary.get('total_value'), # Keeping both just in case
                "holdings": [{"ticker": "AAPL", "value": 1500}, {"ticker": "BTC-USD", "value": 15000}]
            }
        }
        res = await client.post("/api/v2/ai/chat", json=chat_payload)
        assert res.status_code == 200
        reply = res.json()['response']
        print(f"   🤖 AI Reply: {reply[:50]}...")
        assert "16,500" in reply or "16500" in reply
        print("   ✅ AI Context awareness verified")
        
        print("🎉 All Systems Go!")

if __name__ == "__main__":
    asyncio.run(verify_e2e())
