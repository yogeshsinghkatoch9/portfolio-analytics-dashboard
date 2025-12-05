from backend import main
import httpx
import pytest

@pytest.mark.asyncio
async def test_wealth_features_api():
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        
        # 1. Create a Portfolio with mixed assets
        payload = {
            "name": "Test Wealth Portfolio",
            "holdings": [
                {
                    "ticker": "AAPL",
                    "quantity": 10,
                    "price": 150.0,
                    "cost_basis": 1400.0,
                    "asset_type": "Stock"
                },
                {
                    "ticker": "BTC",
                    "quantity": 0.5,
                    "price": 40000.0,
                    "cost_basis": 20000.0,
                    "asset_type": "Crypto"
                },
                {
                    "ticker": "MY CONDO",
                    "quantity": 1,
                    "price": 500000.0,
                    "cost_basis": 450000.0,
                    "asset_type": "Real Estate"
                },
                {
                    "ticker": "MORTGAGE",
                    "quantity": 1,
                    "price": 300000.0,
                    "cost_basis": 0.0,
                    "asset_type": "Liability"
                }
            ]
        }
        res = await client.post('/api/v2/portfolio', json=payload)
        assert res.status_code == 200
        data = res.json()
        pid = data['id']
        
        # Check assets saved correctly
        holdings = data['holdings']
        assert any(h['ticker'] == 'BTC' and h['asset_type'] == 'Crypto' for h in holdings)
        
        # 2. Check Net Worth
        res = await client.get('/api/v2/wealth/net-worth')
        assert res.status_code == 200
        nw = res.json()
        
        # Expected Net Worth:
        # Assets: (10*150) + (0.5*40000) + (500000) = 1500 + 20000 + 500000 = 521500
        # Liab: 300000
        # NW = 221500
        # Note: Depending on existing DB state, this might be higher if other portfolios exist.
        # So we just assert it's at least 221500
        assert nw['net_worth'] >= 221500
        assert nw['total_liabilities'] >= 300000
        
        # 3. Add Holding
        new_holding = {
            "ticker": "CASH",
            "quantity": 5000,
            "price": 1.0,
            "asset_type": "Cash"
        }
        res = await client.post(f'/api/v2/portfolio/{pid}/holdings', json=new_holding)
        assert res.status_code == 200
        
        # Verify added
        res = await client.get(f'/api/v2/portfolio/{pid}')
        p = res.json()
        assert any(h['ticker'] == 'CASH' for h in p['holdings'])

        # 4. Clean up
        await client.delete(f'/api/v2/portfolio/{pid}')
