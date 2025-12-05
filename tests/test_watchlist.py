
import pytest
from backend.watchlist_api import create_watchlist, add_watchlist_item, remove_watchlist_item
from backend.db import get_session, Base, engine

# Re-init db for testing if needed, though we rely on main DB for simplicity in this env
# Ideally use a test DB. For now, we test the logic.

def test_watchlist_workflow():
    # Use a fresh session context
    session = next(get_session())
    
    # 1. Create/Get Watchlist
    w_out = create_watchlist(session=session)
    assert w_out.name == "My Watchlist"
    
    # 2. Add Item
    w_out = add_watchlist_item("AAPL", session=session)
    # Check if item exists in list
    assert any(i.ticker == "AAPL" for i in w_out.items)
    
    # 3. Add Another
    w_out = add_watchlist_item("MSFT", session=session)
    assert any(i.ticker == "MSFT" for i in w_out.items)
    assert len(w_out.items) >= 2
    
    # 4. Remove Item
    w_out = remove_watchlist_item("AAPL", session=session)
    assert not any(i.ticker == "AAPL" for i in w_out.items)
    assert any(i.ticker == "MSFT" for i in w_out.items)
    
    print("\nWatchlist Test Passed. Items remaining:", [i.ticker for i in w_out.items])

if __name__ == "__main__":
    test_watchlist_workflow()
