"""
Watchlist API - Production-Ready Implementation
Complete watchlist management with live prices and validation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import db
from datetime import datetime
import logging
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class WatchlistItemOut(BaseModel):
    """Response model for a single watchlist item"""
    id: int = Field(..., description="Unique identifier for the watchlist item")
    ticker: str = Field(..., description="Stock ticker symbol")
    added_at: datetime = Field(..., description="Timestamp when item was added")
    price: Optional[float] = Field(None, description="Current price (if fetched)")
    change_percent: Optional[float] = Field(None, description="Percent change (if fetched)")
    company_name: Optional[str] = Field(None, description="Company name (if available)")
    
    class Config:
        from_attributes = True


class WatchlistOut(BaseModel):
    """Response model for watchlist with items"""
    id: int = Field(..., description="Watchlist ID")
    name: str = Field(..., description="Watchlist name")
    items: List[WatchlistItemOut] = Field(default_factory=list, description="List of watchlist items")
    item_count: int = Field(..., description="Total number of items")
    created_at: Optional[datetime] = Field(None, description="When watchlist was created")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class WatchlistCreateRequest(BaseModel):
    """Request model for creating a watchlist"""
    name: str = Field(default="My Watchlist", min_length=1, max_length=100)
    
    @validator('name')
    def validate_name(cls, v):
        return v.strip()


class AddTickerRequest(BaseModel):
    """Request model for adding a ticker to watchlist"""
    ticker: str = Field(..., min_length=1, max_length=10)
    
    @validator('ticker')
    def validate_ticker(cls, v):
        return v.upper().strip()


class BulkAddTickersRequest(BaseModel):
    """Request model for adding multiple tickers at once"""
    tickers: List[str] = Field(..., min_items=1, max_items=50)
    
    @validator('tickers')
    def validate_tickers(cls, v):
        return [ticker.upper().strip() for ticker in v]


class WatchlistItemsWithPrices(BaseModel):
    """Response model for watchlist items with live prices"""
    items: List[WatchlistItemOut]
    last_updated: datetime
    failed_tickers: List[str] = Field(default_factory=list)


@router.post('/watchlist', response_model=WatchlistOut, tags=["Watchlist"])
def create_watchlist(
    request: WatchlistCreateRequest = WatchlistCreateRequest(),
    session: Session = Depends(db.get_session)
):
    """Create or get the default watchlist"""
    try:
        logger.info(f"Creating/fetching watchlist: {request.name}")
        
        watchlist = session.query(db.Watchlist).first()
        
        if not watchlist:
            watchlist = db.Watchlist(
                name=request.name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)
            logger.info(f"Created watchlist ID: {watchlist.id}")
        
        return _build_watchlist_response(watchlist, include_prices=False)
        
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error creating watchlist")


@router.get('/watchlist', response_model=WatchlistOut, tags=["Watchlist"])
def get_watchlist(
    include_prices: bool = Query(False, description="Fetch live prices"),
    session: Session = Depends(db.get_session)
):
    """Get the user's watchlist"""
    try:
        logger.info("Fetching watchlist")
        
        watchlist = session.query(db.Watchlist).first()
        
        if not watchlist:
            watchlist = db.Watchlist(
                name="My Watchlist",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)
        
        return _build_watchlist_response(watchlist, include_prices=include_prices)
        
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching watchlist")


@router.post('/watchlist/items', response_model=WatchlistOut, tags=["Watchlist"])
def add_watchlist_item(
    request: AddTickerRequest,
    session: Session = Depends(db.get_session)
):
    """Add a ticker to the watchlist"""
    try:
        logger.info(f"Adding ticker: {request.ticker}")
        
        watchlist = session.query(db.Watchlist).first()
        if not watchlist:
            watchlist = db.Watchlist(
                name="My Watchlist",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)
        
        # Validate ticker
        if not _validate_ticker(request.ticker):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {request.ticker}")
        
        # Check duplicate
        existing = session.query(db.WatchlistItem).filter_by(
            watchlist_id=watchlist.id,
            ticker=request.ticker
        ).first()
        
        if existing:
            logger.info(f"Ticker {request.ticker} already exists")
            return _build_watchlist_response(watchlist, include_prices=False)
        
        # Add new item
        new_item = db.WatchlistItem(
            watchlist_id=watchlist.id,
            ticker=request.ticker,
            added_at=datetime.utcnow()
        )
        session.add(new_item)
        watchlist.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(watchlist)
        
        logger.info(f"Added {request.ticker} to watchlist")
        
        return _build_watchlist_response(watchlist, include_prices=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error adding ticker")


@router.post('/watchlist/items/bulk', response_model=WatchlistOut, tags=["Watchlist"])
def add_watchlist_items_bulk(
    request: BulkAddTickersRequest,
    session: Session = Depends(db.get_session)
):
    """Add multiple tickers at once"""
    try:
        logger.info(f"Bulk adding {len(request.tickers)} tickers")
        
        watchlist = session.query(db.Watchlist).first()
        if not watchlist:
            watchlist = db.Watchlist(
                name="My Watchlist",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)
        
        existing_tickers = {
            item.ticker for item in 
            session.query(db.WatchlistItem).filter_by(watchlist_id=watchlist.id).all()
        }
        
        added_count = 0
        for ticker in request.tickers:
            if ticker in existing_tickers:
                continue
            
            if not _validate_ticker(ticker):
                logger.warning(f"Invalid ticker: {ticker}")
                continue
            
            new_item = db.WatchlistItem(
                watchlist_id=watchlist.id,
                ticker=ticker,
                added_at=datetime.utcnow()
            )
            session.add(new_item)
            existing_tickers.add(ticker)
            added_count += 1
        
        watchlist.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(watchlist)
        
        logger.info(f"Bulk add complete: {added_count} added")
        
        return _build_watchlist_response(watchlist, include_prices=False)
        
    except Exception as e:
        logger.error(f"Error in bulk add: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error adding tickers")


@router.delete('/watchlist/items/{ticker}', response_model=WatchlistOut, tags=["Watchlist"])
def remove_watchlist_item(ticker: str, session: Session = Depends(db.get_session)):
    """Remove a ticker from the watchlist"""
    try:
        ticker = ticker.upper().strip()
        logger.info(f"Removing ticker: {ticker}")
        
        watchlist = session.query(db.Watchlist).first()
        if not watchlist:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        item = session.query(db.WatchlistItem).filter_by(
            watchlist_id=watchlist.id,
            ticker=ticker
        ).first()
        
        if item:
            session.delete(item)
            watchlist.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(watchlist)
            logger.info(f"Removed {ticker}")
        
        return _build_watchlist_response(watchlist, include_prices=False)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error removing ticker")


@router.delete('/watchlist/items', response_model=WatchlistOut, tags=["Watchlist"])
def clear_watchlist(session: Session = Depends(db.get_session)):
    """Remove all items from watchlist"""
    try:
        logger.info("Clearing watchlist")
        
        watchlist = session.query(db.Watchlist).first()
        if not watchlist:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        
        session.query(db.WatchlistItem).filter_by(watchlist_id=watchlist.id).delete()
        watchlist.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(watchlist)
        
        return _build_watchlist_response(watchlist, include_prices=False)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing watchlist: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error clearing watchlist")


@router.get('/watchlist/prices', response_model=WatchlistItemsWithPrices, tags=["Watchlist"])
def get_watchlist_with_prices(session: Session = Depends(db.get_session)):
    """Get watchlist items with live price data"""
    try:
        logger.info("Fetching watchlist with prices")
        
        watchlist = session.query(db.Watchlist).first()
        if not watchlist or not watchlist.items:
            return WatchlistItemsWithPrices(
                items=[],
                last_updated=datetime.utcnow(),
                failed_tickers=[]
            )
        
        tickers = [item.ticker for item in watchlist.items]
        price_data = _fetch_prices_batch(tickers)
        
        items_out = []
        failed_tickers = []
        
        for item in watchlist.items:
            data = price_data.get(item.ticker)
            
            if data:
                items_out.append(WatchlistItemOut(
                    id=item.id,
                    ticker=item.ticker,
                    added_at=item.added_at,
                    price=data.get('price'),
                    change_percent=data.get('change_percent'),
                    company_name=data.get('company_name')
                ))
            else:
                failed_tickers.append(item.ticker)
                items_out.append(WatchlistItemOut(
                    id=item.id,
                    ticker=item.ticker,
                    added_at=item.added_at
                ))
        
        return WatchlistItemsWithPrices(
            items=items_out,
            last_updated=datetime.utcnow(),
            failed_tickers=failed_tickers
        )
        
    except Exception as e:
        logger.error(f"Error fetching prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching prices")


# Helper Functions

def _build_watchlist_response(watchlist: db.Watchlist, include_prices: bool = False) -> WatchlistOut:
    """Build watchlist response with optional price data"""
    items_out = []
    
    if include_prices and watchlist.items:
        tickers = [item.ticker for item in watchlist.items]
        price_data = _fetch_prices_batch(tickers)
        
        for item in watchlist.items:
            data = price_data.get(item.ticker, {})
            items_out.append(WatchlistItemOut(
                id=item.id,
                ticker=item.ticker,
                added_at=item.added_at,
                price=data.get('price'),
                change_percent=data.get('change_percent'),
                company_name=data.get('company_name')
            ))
    else:
        for item in watchlist.items:
            items_out.append(WatchlistItemOut(
                id=item.id,
                ticker=item.ticker,
                added_at=item.added_at
            ))
    
    return WatchlistOut(
        id=watchlist.id,
        name=watchlist.name,
        items=items_out,
        item_count=len(items_out),
        created_at=getattr(watchlist, 'created_at', None),
        updated_at=getattr(watchlist, 'updated_at', None)
    )


def _validate_ticker(ticker: str) -> bool:
    """Validate if ticker exists using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return 'symbol' in info or 'shortName' in info
    except Exception as e:
        logger.warning(f"Validation failed for {ticker}: {e}")
        return False


def _fetch_prices_batch(tickers: List[str]) -> Dict[str, Dict]:
    """Fetch prices for multiple tickers in batch"""
    price_data = {}
    
    if not tickers:
        return price_data
    
    try:
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                previous_close = info.get('previousClose')
                
                change_percent = None
                if current_price and previous_close and previous_close > 0:
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                
                price_data[ticker] = {
                    'price': round(current_price, 2) if current_price else None,
                    'change_percent': round(change_percent, 2) if change_percent else None,
                    'company_name': info.get('shortName') or info.get('longName')
                }
                
            except Exception as e:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                price_data[ticker] = {'price': None, 'change_percent': None, 'company_name': None}
        
    except Exception as e:
        logger.error(f"Batch fetch failed: {e}", exc_info=True)
    
    return price_data
