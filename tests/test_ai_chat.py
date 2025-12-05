
import pytest
from backend.ai_api import chat_with_ai, ChatRequest

@pytest.mark.asyncio
async def test_ai_chat_direct():
    # Test "dividend" query
    context = {
        "net_worth": 50000,
        "daily_change_percent": 1.5,
        "holdings": [{"ticker": "AAPL", "value": 10000}, {"ticker": "MSFT", "value": 8000}]
    }
    req = ChatRequest(
        message="how are my dividends?",
        portfolio_context=context
    )
    
    response = await chat_with_ai(req)
    assert response.response
    msg = response.response.lower()
    assert "dividend" in msg or "income" in msg
    
    # Test "net worth" query
    req.message = "what is my net worth?"
    response = await chat_with_ai(req)
    assert "$50,000.00" in response.response

@pytest.mark.asyncio
async def test_ai_chat_no_context():
    req = ChatRequest(message="hello")
    response = await chat_with_ai(req)
    # The mock response is "Hello! I am your AI Wealth Assistant..."
    assert "AI Wealth Assistant" in response.response
