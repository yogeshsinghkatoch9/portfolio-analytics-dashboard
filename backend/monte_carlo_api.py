"""
Monte Carlo API Endpoints
Provide portfolio forecasting via Monte Carlo simulation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from monte_carlo import get_simulator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SimulationRequest(BaseModel):
    holdings: List[Dict[str, Any]]
    years: int = 10
    num_simulations: Optional[int] = 1000
    confidence_levels: Optional[List[float]] = [0.05, 0.25, 0.50, 0.75, 0.95]


class SimulationResponse(BaseModel):
    metadata: Dict[str, Any]
    scenarios: Dict[str, float]
    percentiles: Dict[str, float]
    statistics: Dict[str, float]
    probabilities: Dict[str, float]
    time_series: Dict[str, Any]


@router.post('/monte-carlo/simulate', response_model=SimulationResponse)
async def run_monte_carlo_simulation(request: SimulationRequest):
    """
    Run Monte Carlo simulation on portfolio
    
    Generates forecast scenarios based on historical returns and volatility.
    Returns percentile outcomes, probabilities, and time series data.
    
    Example holdings format:
    ```json
    {
        "holdings": [
            {
                "ticker": "AAPL",
                "value": 50000,
                "annual_return": 0.12,
                "volatility": 0.20
            }
        ],
        "years": 10,
        "num_simulations": 1000
    }
    ```
    """
    try:
        if not request.holdings:
            raise HTTPException(status_code=400, detail="Holdings list cannot be empty")
        
        if request.years < 1 or request.years > 30:
            raise HTTPException(status_code=400, detail="Years must be between 1 and 30")
        
        if request.num_simulations < 100 or request.num_simulations > 10000:
            raise HTTPException(status_code=400, detail="Simulations must be between 100 and 10,000")
        
        # Get simulator
        simulator = get_simulator(request.num_simulations)
        
        # Run simulation
        results = simulator.simulate_portfolio(
            holdings=request.holdings,
            years=request.years,
            confidence_levels=request.confidence_levels or [0.05, 0.25, 0.50, 0.75, 0.95]
        )
        
        logger.info(f"Monte Carlo simulation complete: {request.years} years, {request.num_simulations} scenarios")
        
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Monte Carlo simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post('/monte-carlo/quick-forecast')
async def quick_forecast(request: SimulationRequest):
    """
    Quick forecast endpoint - returns simplified results faster
    
    Uses fewer simulations (100) for faster response
    """
    try:
        # Override to use fewer simulations for speed
        simulator = get_simulator(100)
        
        results = simulator.simulate_portfolio(
            holdings=request.holdings,
            years=request.years,
            confidence_levels=[0.05, 0.50, 0.95]  # Just key percentiles
        )
        
        # Return simplified response
        return {
            'initial_value': results['metadata']['initial_value'],
            'median_outcome': results['scenarios']['median'],
            'best_case': results['scenarios']['best_case'],
            'worst_case': results['scenarios']['worst_case'],
            'prob_gain': results['probabilities']['prob_gain'],
            'prob_loss': results['probabilities']['prob_loss']
        }
        
    except Exception as e:
        logger.error(f"Quick forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")
