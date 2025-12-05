from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
import db
from datetime import datetime
import json

router = APIRouter()


class HoldingIn(BaseModel):
    ticker: str
    quantity: float = 0.0
    price: float = 0.0
    cost_basis: Optional[float] = 0.0
    asset_type: str = 'Stock'
    currency: str = 'USD'
    metadata: Optional[dict] = Field(default_factory=dict)


class PortfolioIn(BaseModel):
    name: Optional[str] = 'My Portfolio'
    holdings: List[HoldingIn]


class HoldingOut(BaseModel):
    id: int
    ticker: str
    quantity: float
    price: float
    cost_basis: float
    asset_type: str
    currency: str
    metadata: dict


class PortfolioOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    holdings: List[HoldingOut]


@router.post('/portfolio', response_model=PortfolioOut)
def create_portfolio(payload: PortfolioIn, session: Session = Depends(db.get_session)):
    p = db.Portfolio(name=payload.name)
    session.add(p)
    session.flush()

    for h in payload.holdings:
        holding = db.Holding(
            portfolio_id=p.id,
            ticker=h.ticker.upper(),
            quantity=h.quantity,
            price=h.price,
            cost_basis=h.cost_basis or 0.0,
            asset_type=h.asset_type,
            currency=h.currency,
            meta_json=json.dumps(h.metadata or {})
        )
        session.add(holding)

    session.commit()
    session.refresh(p)

    return _portfolio_out(p)


@router.get('/portfolio', response_model=List[PortfolioOut])
def list_portfolios(session: Session = Depends(db.get_session)):
    items = session.query(db.Portfolio).all()
    return [_portfolio_out(p) for p in items]


@router.get('/portfolio/{portfolio_id}', response_model=PortfolioOut)
def get_portfolio(portfolio_id: int, session: Session = Depends(db.get_session)):
    p = session.get(db.Portfolio, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail='Portfolio not found')
    return _portfolio_out(p)


@router.delete('/portfolio/{portfolio_id}')
def delete_portfolio(portfolio_id: int, session: Session = Depends(db.get_session)):
    p = session.get(db.Portfolio, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail='Portfolio not found')
    session.delete(p)
    session.commit()
    return {'success': True, 'id': portfolio_id}


@router.post('/portfolio/{portfolio_id}/holdings', response_model=PortfolioOut)
def add_holding(portfolio_id: int, holding: HoldingIn, session: Session = Depends(db.get_session)):
    p = session.get(db.Portfolio, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail='Portfolio not found')
        
    h = db.Holding(
        portfolio_id=p.id,
        ticker=holding.ticker.upper(),
        quantity=holding.quantity,
        price=holding.price,
        cost_basis=holding.cost_basis or 0.0,
        asset_type=holding.asset_type,
        currency=holding.currency,
        meta_json=json.dumps(holding.metadata or {})
    )
    session.add(h)
    session.commit()
    session.refresh(p)
    return _portfolio_out(p)


@router.put('/portfolio/{portfolio_id}/holdings/{holding_id}', response_model=PortfolioOut)
def update_holding(portfolio_id: int, holding_id: int, holding: HoldingIn, session: Session = Depends(db.get_session)):
    p = session.get(db.Portfolio, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail='Portfolio not found')
        
    h = session.get(db.Holding, holding_id)
    if not h or h.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail='Holding not found')
        
    # Update fields
    h.ticker = holding.ticker.upper()
    h.quantity = holding.quantity
    h.price = holding.price
    h.cost_basis = holding.cost_basis or 0.0
    h.asset_type = holding.asset_type
    h.currency = holding.currency
    h.meta_json = json.dumps(holding.metadata or {})
    
    session.commit()
    session.refresh(p)
    return _portfolio_out(p)


@router.delete('/portfolio/{portfolio_id}/holdings/{holding_id}', response_model=PortfolioOut)
def delete_holding(portfolio_id: int, holding_id: int, session: Session = Depends(db.get_session)):
    p = session.get(db.Portfolio, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail='Portfolio not found')
        
    h = session.get(db.Holding, holding_id)
    if not h or h.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail='Holding not found')
        
    session.delete(h)
    session.commit()
    session.refresh(p)
    return _portfolio_out(p)


def _portfolio_out(p: db.Portfolio):
    return PortfolioOut(
        id=p.id,
        name=p.name,
        created_at=p.created_at,
        updated_at=p.updated_at,
        holdings=[
            HoldingOut(
                id=h.id,
                ticker=h.ticker,
                quantity=h.quantity,
                price=h.price,
                cost_basis=h.cost_basis or 0.0,
                asset_type=h.asset_type,
                currency=h.currency,
                metadata=json.loads(h.meta_json or '{}')
            ) for h in p.holdings
        ]
    )
