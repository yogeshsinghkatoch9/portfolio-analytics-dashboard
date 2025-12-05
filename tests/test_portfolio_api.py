from backend import main
import httpx
import pytest


@pytest.mark.asyncio
async def test_portfolio_crud_cycle():
    payload = {
        "name": "CI Test Portfolio",
        "holdings": [
            {"ticker": "AAPL", "quantity": 10, "price": 150.0, "cost_basis": 140.0, "metadata": {"note": "test"}},
            {"ticker": "MSFT", "quantity": 5, "price": 300.0}
        ]
    }

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        # Create
        res = await client.post('/api/v2/portfolio', json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data['name'] == 'CI Test Portfolio'
        pid = data['id']

        # List
        res = await client.get('/api/v2/portfolio')
        assert res.status_code == 200
        items = res.json()
        assert any(p['id'] == pid for p in items)

        # Get single
        res = await client.get(f'/api/v2/portfolio/{pid}')
        assert res.status_code == 200
        p = res.json()
        assert p['id'] == pid
        assert len(p['holdings']) >= 2

        # Delete
        res = await client.delete(f'/api/v2/portfolio/{pid}')
        assert res.status_code == 200
        d = res.json()
        assert d.get('success') is True

        # Verify deletion
        res = await client.get(f'/api/v2/portfolio/{pid}')
        assert res.status_code == 404
