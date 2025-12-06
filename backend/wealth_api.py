"""
Wealth API - Production-Ready Net Worth Calculation
Complete implementation with error handling, logging, and comprehensive endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import get_db, SessionLocal
from models import Portfolio, Holding, Watchlist, WatchlistItem
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class NetWorthResponse(BaseModel):
    """Response model for net worth calculations"""
    net_worth: float = Field(..., description="Total net worth (assets - liabilities)")
    total_assets: float = Field(..., description="Sum of all assets")
    total_liabilities: float = Field(..., description="Sum of all liabilities")
    currency: str = Field(default="USD", description="Currency code")
    breakdown: Dict[str, float] = Field(..., description="Breakdown by asset type")
    calculated_at: datetime = Field(..., description="Timestamp of calculation")
    portfolio_id: Optional[int] = Field(None, description="Portfolio ID if filtered")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Historical data")

    class Config:
        json_schema_extra = {
            "example": {
                "net_worth": 45000.00,
                "total_assets": 50000.00,
                "total_liabilities": 5000.00,
                "currency": "USD",
                "breakdown": {
                    "Stock": 30000.00,
                    "Bond": 15000.00,
                    "Real Estate": 5000.00,
                    "Liability": -5000.00
                },
                "calculated_at": "2024-12-05T10:30:00",
                "portfolio_id": None,
                "history": []
            }
        }


@router.get('/wealth/net-worth', response_model=NetWorthResponse, tags=["Wealth"])
def get_net_worth(
    portfolio_id: Optional[int] = Query(None, description="Filter by specific portfolio ID", ge=1),
    session: Session = Depends(get_db)
):
    """
    Calculate total net worth across all portfolios or a specific portfolio.
    
    **Net Worth Formula**: Total Assets - Total Liabilities
    """
    try:
        logger.info(f"Calculating net worth for portfolio_id={portfolio_id}")
        
        # Base query - filter out invalid holdings
        base_query = session.query(Holding).filter(
            Holding.quantity.isnot(None),
            Holding.price.isnot(None),
            Holding.quantity != 0
        )
        
        if portfolio_id is not None:
            base_query = base_query.filter(Holding.portfolio_id == portfolio_id)
        
        # Calculate assets
        assets_query = base_query.filter(
            func.coalesce(func.lower(Holding.asset_type), 'stock') != 'liability'
        ).with_entities(
            func.coalesce(Holding.asset_type, 'Stock').label('asset_type'),
            func.sum(Holding.quantity * Holding.price).label('total')
        ).group_by(Holding.asset_type)
        
        # Calculate liabilities
        liabilities_query = base_query.filter(
            func.lower(Holding.asset_type) == 'liability'
        ).with_entities(
            Holding.asset_type,
            func.sum(Holding.quantity * Holding.price).label('total')
        ).group_by(Holding.asset_type)
        
        breakdown = {}
        total_assets = 0.0
        total_liabilities = 0.0
        
        # Process assets
        for asset_type, total in assets_query:
            if total is not None:
                value = float(total)
                breakdown[asset_type] = round(value, 2)
                total_assets += value
        
        # Process liabilities
        for asset_type, total in liabilities_query:
            if total is not None:
                value = abs(float(total))
                breakdown[asset_type] = round(-value, 2)
                total_liabilities += value
        
        net_worth = total_assets - total_liabilities
        
        return NetWorthResponse(
            net_worth=round(net_worth, 2),
            total_assets=round(total_assets, 2),
            total_liabilities=round(total_liabilities, 2),
            currency='USD',
            breakdown=breakdown,
            calculated_at=datetime.utcnow(),
            portfolio_id=portfolio_id,
            history=[]
        )
        
    except Exception as e:
        logger.error(f"Error calculating net worth: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating net worth")


@router.get('/wealth/net-worth/summary', tags=["Wealth"])
def get_net_worth_summary(session: Session = Depends(get_db)):
    """Get quick net worth summary"""
    try:
        assets_total = session.query(
            func.sum(Holding.quantity * Holding.price)
        ).filter(
            Holding.quantity.isnot(None),
            Holding.price.isnot(None),
            func.coalesce(func.lower(Holding.asset_type), 'stock') != 'liability'
        ).scalar() or 0.0
        
        liabilities_total = session.query(
            func.sum(Holding.quantity * Holding.price)
        ).filter(
            Holding.quantity.isnot(None),
            Holding.price.isnot(None),
            func.lower(Holding.asset_type) == 'liability'
        ).scalar() or 0.0
        
        liabilities_total = abs(float(liabilities_total))
        assets_total = float(assets_total)
        
        return {
            "net_worth": round(assets_total - liabilities_total, 2),
            "total_assets": round(assets_total, 2),
            "total_liabilities": round(liabilities_total, 2),
            "currency": "USD",
            "calculated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error in summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating summary")


@router.get('/wealth/breakdown', tags=["Wealth"])
def get_asset_breakdown(
    portfolio_id: Optional[int] = Query(None, ge=1),
    session: Session = Depends(get_db)
):
    """Get detailed breakdown of assets by type"""
    try:
        base_query = session.query(Holding).filter(
            Holding.quantity.isnot(None),
            Holding.price.isnot(None)
        )
        
        if portfolio_id is not None:
            base_query = base_query.filter(Holding.portfolio_id == portfolio_id)
        
        breakdown_query = base_query.with_entities(
            func.coalesce(Holding.asset_type, 'Stock').label('asset_type'),
            func.count(Holding.id).label('count'),
            func.sum(Holding.quantity * Holding.price).label('total')
        ).group_by(Holding.asset_type)
        
        results = []
        grand_total = 0.0
        breakdown_data = []
        
        for asset_type, count, total in breakdown_query:
            if total is not None:
                value = float(total)
                is_liability = asset_type.lower() == 'liability'
                if is_liability:
                    value = -abs(value)
                
                breakdown_data.append({
                    'asset_type': asset_type,
                    'count': count,
                    'total': value,
                    'is_liability': is_liability
                })
                grand_total += abs(value)
        
        for item in breakdown_data:
            percentage = (abs(item['total']) / grand_total * 100) if grand_total > 0 else 0
            results.append({
                'asset_type': item['asset_type'],
                'count': item['count'],
                'total': round(item['total'], 2),
                'percentage': round(percentage, 2),
                'is_liability': item['is_liability']
            })
        
        results.sort(key=lambda x: abs(x['total']), reverse=True)
        
        return {
            "breakdown": results,
            "grand_total": round(grand_total, 2),
            "portfolio_id": portfolio_id,
            "currency": "USD",
            "calculated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error in breakdown: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating breakdown")
