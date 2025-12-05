from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import db
from typing import Dict, List, Any
from pydantic import BaseModel

router = APIRouter()

class NetWorthResponse(BaseModel):
    net_worth: float
    total_assets: float
    total_liabilities: float
    currency: str
    breakdown: Dict[str, float]
    history: List[Dict[str, Any]] = []

@router.get('/wealth/net-worth', response_model=NetWorthResponse)
def get_net_worth(session: Session = Depends(db.get_session)):
    """
    Calculate total net worth across all portfolios.
    Net Worth = Sum(Assets) + Sum(Liabilities) 
    (Note: Liabilities should be stored as negative values or handled by asset_type)
    For this implementation, we assume 'Liability' asset_type has positive quantity but we treat it as debt.
    Actually, let's assume 'Liability' means the value is a debt.
    """
    holdings = session.query(db.Holding).all()
    
    total_assets = 0.0
    total_liabilities = 0.0
    breakdown = {}
    
    for h in holdings:
        # Calculate current value
        # If manual asset, price might be total value and quantity 1
        val = h.quantity * h.price
        
        atype = h.asset_type or 'Stock'
        
        if atype.lower() == 'liability':
            total_liabilities += abs(val)
        else:
            total_assets += val
            
        # Add to breakdown
        breakdown[atype] = breakdown.get(atype, 0.0) + val
        
    net_worth = total_assets - total_liabilities
    
    # In a real app we would track history in a separate table.
    # For now return empty history.
    
    return NetWorthResponse(
        net_worth=round(net_worth, 2),
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        currency='USD',
        breakdown={k: round(v, 2) for k, v in breakdown.items()}
    )
