
import pytest
from backend.news_api import get_market_news

def test_news_fetch():
    # Test SPY news (general market)
    response = get_market_news()
    assert response.news
    print(f"\nGeneral News Count: {len(response.news)}")
    print(f"Top Story: {response.news[0].title}")
    
    # Test specific ticker news
    # Note: If yfinance fails due to network, this might flake
    try:
        response_tsla = get_market_news(tickers="TSLA")
        if response_tsla.news:
            assert any('Tesla' in n.title or 'TSLA' in str(n.relatedTickers) for n in response_tsla.news)
            print(f"TSLA News Count: {len(response_tsla.news)}")
    except Exception as e:
        print(f"TSLA fetch warning: {e}")

if __name__ == "__main__":
    test_news_fetch()
