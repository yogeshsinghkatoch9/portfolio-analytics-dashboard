from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import db
from datetime import datetime

router = APIRouter()

class WatchlistItemOut(BaseModel):
    id: int
    ticker: str
    added_at: datetime
    price: float = 0.0
    change_percent: float = 0.0

class WatchlistOut(BaseModel):
    id: int
    name: str
    items: List[WatchlistItemOut]

# Create (or get default) Watchlist
@router.post('/watchlist', response_model=WatchlistOut)
def create_watchlist(name: str = "My Watchlist", session: Session = Depends(db.get_session)):
    # Simple logic: Single user, so check if one exists or create
    w = session.query(db.Watchlist).first()
    if not w:
        w = db.Watchlist(name=name)
        session.add(w)
        session.commit()
        session.refresh(w)
    return _watchlist_out(w)

@router.get('/watchlist', response_model=WatchlistOut)
def get_watchlist(session: Session = Depends(db.get_session)):
    w = session.query(db.Watchlist).first()
    if not w:
        w = db.Watchlist(name="My Watchlist")
        session.add(w)
        session.commit()
        session.refresh(w)
    return _watchlist_out(w)

@router.post('/watchlist/items', response_model=WatchlistOut)
def add_watchlist_item(ticker: str, session: Session = Depends(db.get_session)):
    w = session.query(db.Watchlist).first()
    if not w:
        w = db.Watchlist(name="My Watchlist")
        session.add(w)
        session.commit()
        session.refresh(w)
        
    ticker = ticker.upper().strip()
    
    # Check if exists
    exists = session.query(db.WatchlistItem).filter_by(watchlist_id=w.id, ticker=ticker).first()
    if not exists:
        item = db.WatchlistItem(watchlist_id=w.id, ticker=ticker)
        session.add(item)
        session.commit()
        session.refresh(w)
        
    return _watchlist_out(w)

@router.delete('/watchlist/items/{ticker}', response_model=WatchlistOut)
def remove_watchlist_item(ticker: str, session: Session = Depends(db.get_session)):
    w = session.query(db.Watchlist).first()
    if not w:
        raise HTTPException(status_code=404, detail="Watchlist not found")
        
    ticker = ticker.upper().strip()
    item = session.query(db.WatchlistItem).filter_by(watchlist_id=w.id, ticker=ticker).first()
    
    if item:
        session.delete(item)
        session.commit()
        session.refresh(w)
        
    return _watchlist_out(w)

def _watchlist_out(w: db.Watchlist):
    # Fetch real-time prices for items
    import yfinance as yf
    
    items_out = []
    tickers = [i.ticker for i in w.items]
    
    prices = {}
    if tickers:
        try:
            # Batch fetch
            # yfinance download is fastest for batch
            # We just need last price and % change
            # But download returns history. Ticker object might be better for rich info but slower.
            # Let's use download for speed on just 'Adj Close' for today? No, we need change.
            # Tickers with fast_info is best.
            pass # We'll do simple fetch one by one or optimized batch if needed.
                 # Optimization: Use existing batch endpoint logic or simple loop for now (watchlist usually small)
        except:
            pass
            
    # For now, let's use a simple helper or just return structure and let frontend fetch live data?
    # Better: Return structure, Frontend calls /api/market/quotes for live data.
    # This keeps API fast.
    
    for i in w.items:
        items_out.append(WatchlistItemOut(
            id=i.id,
            ticker=i.ticker,
            added_at=i.added_at,
            price=0, # Frontend will fetch
            change_percent=0 # Frontend will fetch
        ))
        
    return WatchlistOut(
        id=w.id,
        name=w.name,
        items=items_out
    )
