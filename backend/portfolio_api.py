"""
Portfolio Management API for VisionWealth
Handles portfolio and holdings CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import db
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class HoldingIn(BaseModel):
    """Request model for creating/updating a holding"""
    ticker: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(0.0, ge=0)
    price: float = Field(0.0, ge=0)
    cost_basis: Optional[float] = Field(0.0, ge=0)
    asset_type: str = Field('Stock')
    currency: str = Field('USD', min_length=3, max_length=3)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('ticker')
    def validate_ticker(cls, v):
        return v.upper().strip()
    
    @validator('currency')
    def validate_currency(cls, v):
        return v.upper().strip()


class PortfolioIn(BaseModel):
    """Request model for creating a portfolio"""
    name: str = Field('My Portfolio', min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    holdings: List[HoldingIn] = Field(default_factory=list)
    
    @validator('name')
    def validate_name(cls, v):
        return v.strip()


class PortfolioUpdateIn(BaseModel):
    """Request model for updating portfolio metadata"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('name')
    def validate_name(cls, v):
        if v:
            return v.strip()
        return v


class HoldingOut(BaseModel):
    """Response model for a holding"""
    id: int
    ticker: str
    quantity: float
    price: float
    cost_basis: float
    asset_type: str
    currency: str
    metadata: Dict[str, Any]
    current_value: float
    gain_loss: float
    gain_loss_pct: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PortfolioOut(BaseModel):
    """Response model for a portfolio"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    holdings: List[HoldingOut]
    total_value: float
    total_cost_basis: float
    total_gain_loss: float
    total_gain_loss_pct: float
    holdings_count: int


class PortfolioSummary(BaseModel):
    """Summary model for portfolio list view"""
    id: int
    name: str
    description: Optional[str] = None
    total_value: float
    total_gain_loss: float
    total_gain_loss_pct: float
    holdings_count: int
    created_at: datetime
    updated_at: datetime


class BulkHoldingOperation(BaseModel):
    """Model for bulk operations on holdings"""
    holding_ids: List[int] = Field(..., min_items=1, max_items=100)


# Portfolio Endpoints

@router.post('/portfolio', response_model=PortfolioOut, tags=["Portfolio"], status_code=201)
def create_portfolio(payload: PortfolioIn, session: Session = Depends(db.get_session)):
    """Create a new portfolio with optional initial holdings"""
    try:
        logger.info(f"Creating portfolio: {payload.name}")
        
        portfolio = db.Portfolio(
            name=payload.name,
            description=payload.description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(portfolio)
        session.flush()
        
        for holding_data in payload.holdings:
            holding = db.Holding(
                portfolio_id=portfolio.id,
                ticker=holding_data.ticker.upper(),
                quantity=holding_data.quantity,
                price=holding_data.price,
                cost_basis=holding_data.cost_basis or 0.0,
                asset_type=holding_data.asset_type,
                currency=holding_data.currency,
                meta_json=json.dumps(holding_data.metadata or {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(holding)
        
        session.commit()
        session.refresh(portfolio)
        
        logger.info(f"Portfolio created with ID: {portfolio.id}")
        
        return _build_portfolio_response(portfolio)
        
    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail="Portfolio with this name may already exist")
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating portfolio: {str(e)}")


@router.get('/portfolio', response_model=List[PortfolioSummary], tags=["Portfolio"])
def list_portfolios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    session: Session = Depends(db.get_session)
):
    """List all portfolios with summary information"""
    try:
        logger.info(f"Listing portfolios (skip={skip}, limit={limit})")
        
        query = session.query(db.Portfolio)
        
        if sort_order == "desc":
            query = query.order_by(getattr(db.Portfolio, sort_by).desc())
        else:
            query = query.order_by(getattr(db.Portfolio, sort_by).asc())
        
        portfolios = query.offset(skip).limit(limit).all()
        
        summaries = []
        for portfolio in portfolios:
            summary = _calculate_portfolio_summary(portfolio)
            summaries.append(PortfolioSummary(**summary))
        
        logger.info(f"Returned {len(summaries)} portfolios")
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error listing portfolios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving portfolios")


@router.get('/portfolio/{portfolio_id}', response_model=PortfolioOut, tags=["Portfolio"])
def get_portfolio(
    portfolio_id: int,
    include_metadata: bool = Query(True),
    session: Session = Depends(db.get_session)
):
    """Get detailed information about a specific portfolio"""
    try:
        logger.info(f"Retrieving portfolio {portfolio_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        return _build_portfolio_response(portfolio, include_metadata=include_metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving portfolio")


@router.put('/portfolio/{portfolio_id}', response_model=PortfolioOut, tags=["Portfolio"])
def update_portfolio(portfolio_id: int, payload: PortfolioUpdateIn, session: Session = Depends(db.get_session)):
    """Update portfolio metadata"""
    try:
        logger.info(f"Updating portfolio {portfolio_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        if payload.name is not None:
            portfolio.name = payload.name
        if payload.description is not None:
            portfolio.description = payload.description
        
        portfolio.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(portfolio)
        
        logger.info(f"Portfolio {portfolio_id} updated")
        
        return _build_portfolio_response(portfolio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error updating portfolio")


@router.delete('/portfolio/{portfolio_id}', tags=["Portfolio"])
def delete_portfolio(portfolio_id: int, session: Session = Depends(db.get_session)):
    """Delete a portfolio and all its holdings"""
    try:
        logger.info(f"Deleting portfolio {portfolio_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        holdings_count = len(portfolio.holdings)
        
        session.delete(portfolio)
        session.commit()
        
        logger.info(f"Portfolio {portfolio_id} deleted ({holdings_count} holdings)")
        
        return {
            'success': True,
            'id': portfolio_id,
            'holdings_deleted': holdings_count,
            'message': f"Portfolio and {holdings_count} holdings deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting portfolio: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error deleting portfolio")


# Holdings Endpoints

@router.post('/portfolio/{portfolio_id}/holdings', response_model=PortfolioOut, tags=["Holdings"], status_code=201)
def add_holding(portfolio_id: int, holding: HoldingIn, session: Session = Depends(db.get_session)):
    """Add a new holding to a portfolio"""
    try:
        logger.info(f"Adding holding {holding.ticker} to portfolio {portfolio_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        existing = session.query(db.Holding).filter(
            db.Holding.portfolio_id == portfolio_id,
            db.Holding.ticker == holding.ticker.upper()
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Holding with ticker {holding.ticker} already exists")
        
        new_holding = db.Holding(
            portfolio_id=portfolio.id,
            ticker=holding.ticker.upper(),
            quantity=holding.quantity,
            price=holding.price,
            cost_basis=holding.cost_basis or 0.0,
            asset_type=holding.asset_type,
            currency=holding.currency,
            meta_json=json.dumps(holding.metadata or {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(new_holding)
        portfolio.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(portfolio)
        
        logger.info(f"Holding {holding.ticker} added successfully")
        
        return _build_portfolio_response(portfolio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding holding: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error adding holding")


@router.post('/portfolio/{portfolio_id}/holdings/bulk', response_model=PortfolioOut, tags=["Holdings"])
def add_holdings_bulk(portfolio_id: int, holdings: List[HoldingIn], session: Session = Depends(db.get_session)):
    """Add multiple holdings at once"""
    try:
        if len(holdings) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 holdings can be added at once")
        
        logger.info(f"Bulk adding {len(holdings)} holdings to portfolio {portfolio_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        existing_tickers = {h.ticker for h in session.query(db.Holding.ticker).filter(db.Holding.portfolio_id == portfolio_id).all()}
        
        added_count = 0
        skipped_count = 0
        
        for holding_data in holdings:
            ticker = holding_data.ticker.upper()
            
            if ticker in existing_tickers:
                logger.warning(f"Skipping duplicate ticker: {ticker}")
                skipped_count += 1
                continue
            
            new_holding = db.Holding(
                portfolio_id=portfolio.id,
                ticker=ticker,
                quantity=holding_data.quantity,
                price=holding_data.price,
                cost_basis=holding_data.cost_basis or 0.0,
                asset_type=holding_data.asset_type,
                currency=holding_data.currency,
                meta_json=json.dumps(holding_data.metadata or {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(new_holding)
            existing_tickers.add(ticker)
            added_count += 1
        
        portfolio.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(portfolio)
        
        logger.info(f"Bulk add complete: {added_count} added, {skipped_count} skipped")
        
        return _build_portfolio_response(portfolio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk add: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error adding holdings")


@router.put('/portfolio/{portfolio_id}/holdings/{holding_id}', response_model=PortfolioOut, tags=["Holdings"])
def update_holding(portfolio_id: int, holding_id: int, holding: HoldingIn, session: Session = Depends(db.get_session)):
    """Update an existing holding"""
    try:
        logger.info(f"Updating holding {holding_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        existing_holding = session.get(db.Holding, holding_id)
        
        if not existing_holding or existing_holding.portfolio_id != portfolio_id:
            raise HTTPException(status_code=404, detail=f"Holding {holding_id} not found")
        
        existing_holding.ticker = holding.ticker.upper()
        existing_holding.quantity = holding.quantity
        existing_holding.price = holding.price
        existing_holding.cost_basis = holding.cost_basis or 0.0
        existing_holding.asset_type = holding.asset_type
        existing_holding.currency = holding.currency
        existing_holding.meta_json = json.dumps(holding.metadata or {})
        existing_holding.updated_at = datetime.utcnow()
        
        portfolio.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(portfolio)
        
        logger.info(f"Holding {holding_id} updated")
        
        return _build_portfolio_response(portfolio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating holding: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error updating holding")


@router.delete('/portfolio/{portfolio_id}/holdings/{holding_id}', response_model=PortfolioOut, tags=["Holdings"])
def delete_holding(portfolio_id: int, holding_id: int, session: Session = Depends(db.get_session)):
    """Delete a holding from a portfolio"""
    try:
        logger.info(f"Deleting holding {holding_id}")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        holding = session.get(db.Holding, holding_id)
        
        if not holding or holding.portfolio_id != portfolio_id:
            raise HTTPException(status_code=404, detail=f"Holding {holding_id} not found")
        
        ticker = holding.ticker
        
        session.delete(holding)
        portfolio.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(portfolio)
        
        logger.info(f"Holding {ticker} deleted")
        
        return _build_portfolio_response(portfolio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting holding: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error deleting holding")


@router.delete('/portfolio/{portfolio_id}/holdings', tags=["Holdings"])
def delete_holdings_bulk(portfolio_id: int, operation: BulkHoldingOperation, session: Session = Depends(db.get_session)):
    """Delete multiple holdings at once"""
    try:
        logger.info(f"Bulk deleting {len(operation.holding_ids)} holdings")
        
        portfolio = session.get(db.Portfolio, portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
        
        deleted_count = session.query(db.Holding).filter(
            db.Holding.id.in_(operation.holding_ids),
            db.Holding.portfolio_id == portfolio_id
        ).delete(synchronize_session=False)
        
        portfolio.updated_at = datetime.utcnow()
        
        session.commit()
        
        logger.info(f"Deleted {deleted_count} holdings")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'requested_count': len(operation.holding_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail="Error deleting holdings")


# Helper Functions

def _build_portfolio_response(portfolio: db.Portfolio, include_metadata: bool = True) -> PortfolioOut:
    """Build comprehensive portfolio response with calculations"""
    
    holdings_out = []
    total_value = 0.0
    total_cost_basis = 0.0
    
    for holding in portfolio.holdings:
        current_value = holding.quantity * holding.price
        cost_value = holding.quantity * (holding.cost_basis or 0.0)
        gain_loss = current_value - cost_value
        gain_loss_pct = (gain_loss / cost_value * 100) if cost_value > 0 else 0.0
        
        metadata = {}
        if include_metadata:
            try:
                metadata = json.loads(holding.meta_json or '{}')
            except:
                metadata = {}
        
        holdings_out.append(HoldingOut(
            id=holding.id,
            ticker=holding.ticker,
            quantity=holding.quantity,
            price=holding.price,
            cost_basis=holding.cost_basis or 0.0,
            asset_type=holding.asset_type,
            currency=holding.currency,
            metadata=metadata,
            current_value=round(current_value, 2),
            gain_loss=round(gain_loss, 2),
            gain_loss_pct=round(gain_loss_pct, 2),
            created_at=getattr(holding, 'created_at', None),
            updated_at=getattr(holding, 'updated_at', None)
        ))
        
        total_value += current_value
        total_cost_basis += cost_value
    
    total_gain_loss = total_value - total_cost_basis
    total_gain_loss_pct = (total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
    
    return PortfolioOut(
        id=portfolio.id,
        name=portfolio.name,
        description=getattr(portfolio, 'description', None),
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
        holdings=holdings_out,
        total_value=round(total_value, 2),
        total_cost_basis=round(total_cost_basis, 2),
        total_gain_loss=round(total_gain_loss, 2),
        total_gain_loss_pct=round(total_gain_loss_pct, 2),
        holdings_count=len(holdings_out)
    )


def _calculate_portfolio_summary(portfolio: db.Portfolio) -> Dict[str, Any]:
    """Calculate portfolio summary for list view"""
    
    total_value = 0.0
    total_cost_basis = 0.0
    
    for holding in portfolio.holdings:
        current_value = holding.quantity * holding.price
        cost_value = holding.quantity * (holding.cost_basis or 0.0)
        
        total_value += current_value
        total_cost_basis += cost_value
    
    total_gain_loss = total_value - total_cost_basis
    total_gain_loss_pct = (total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
    
    return {
        'id': portfolio.id,
        'name': portfolio.name,
        'description': getattr(portfolio, 'description', None),
        'total_value': round(total_value, 2),
        'total_gain_loss': round(total_gain_loss, 2),
        'total_gain_loss_pct': round(total_gain_loss_pct, 2),
        'holdings_count': len(portfolio.holdings),
        'created_at': portfolio.created_at,
        'updated_at': portfolio.updated_at
    }
