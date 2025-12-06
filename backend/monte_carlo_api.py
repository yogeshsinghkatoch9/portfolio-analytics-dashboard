"""
Monte Carlo Simulation API Endpoints
Provides portfolio forecasting via Monte Carlo simulation with comprehensive options
"""

from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from monte_carlo import (
    get_simulator,
    MonteCarloSimulator,
    SimulationConfig,
    DistributionType,
    SimulationMethod,
    quick_simulate
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class HoldingInput(BaseModel):
    """Model for a single portfolio holding"""
    ticker: str = Field(..., min_length=1, max_length=10)
    value: float = Field(..., gt=0)
    annual_return: Optional[float] = Field(0.08, ge=-1, le=2)
    volatility: Optional[float] = Field(0.15, ge=0, le=2)
    asset_type: Optional[str] = None
    
    @validator('ticker')
    def validate_ticker(cls, v):
        return v.upper().strip()


class ContributionsInput(BaseModel):
    """Model for regular contributions"""
    monthly_amount: float = Field(..., ge=0)
    annual_increase: float = Field(0.0, ge=0, le=0.2)


class SimulationRequest(BaseModel):
    """Request model for Monte Carlo simulation"""
    holdings: List[HoldingInput] = Field(..., min_items=1, max_items=100)
    years: int = Field(10, ge=1, le=50)
    num_simulations: int = Field(1000, ge=100, le=100000)
    confidence_levels: List[float] = Field([0.05, 0.25, 0.50, 0.75, 0.95])
    method: Optional[SimulationMethod] = Field(SimulationMethod.GEOMETRIC_BROWNIAN)
    distribution: Optional[DistributionType] = Field(DistributionType.NORMAL)
    contributions: Optional[ContributionsInput] = None
    risk_free_rate: Optional[float] = Field(0.03, ge=0, le=0.2)
    
    @validator('confidence_levels')
    def validate_confidence_levels(cls, v):
        if not all(0 <= level <= 1 for level in v):
            raise ValueError("Confidence levels must be between 0 and 1")
        return sorted(v)


class QuickForecastRequest(BaseModel):
    """Simplified request for quick forecast"""
    portfolio_value: float = Field(..., gt=0)
    annual_return: float = Field(0.08, ge=-1, le=2)
    volatility: float = Field(0.15, ge=0, le=2)
    years: int = Field(10, ge=1, le=50)


class QuickForecastResponse(BaseModel):
    """Simplified response for quick forecast"""
    initial_value: float
    median_outcome: float
    best_case: float
    worst_case: float
    prob_gain: float
    prob_loss: float
    prob_double: float
    expected_return: float


# Main Endpoints

@router.post('/monte-carlo/simulate', tags=["Monte Carlo"], status_code=200)
async def run_monte_carlo_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """
    Run comprehensive Monte Carlo simulation for portfolio forecasting.
    
    **Features**:
    - Multiple simulation methods (GBM, Bootstrap, Mean Reversion)
    - Various distribution types (Normal, Student-t, Historical)
    - Support for regular contributions with annual increases
    - Comprehensive risk metrics (VaR, CVaR, Sharpe, Sortino)
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting simulation: {request.num_simulations} paths, {request.years} years")
        
        if not request.holdings:
            raise HTTPException(status_code=400, detail="Holdings list cannot be empty")
        
        config = SimulationConfig(
            num_simulations=request.num_simulations,
            years=request.years,
            method=request.method,
            distribution=request.distribution,
            risk_free_rate=request.risk_free_rate
        )
        
        simulator = MonteCarloSimulator(config)
        
        holdings_data = [h.dict() for h in request.holdings]
        
        contributions_data = None
        if request.contributions:
            contributions_data = {
                'monthly_amount': request.contributions.monthly_amount,
                'annual_increase': request.contributions.annual_increase,
                'years': request.years
            }
        
        results = simulator.simulate_portfolio(
            holdings=holdings_data,
            years=request.years,
            confidence_levels=request.confidence_levels,
            contributions=contributions_data
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Simulation complete in {elapsed:.2f}s. Median: ${results['scenarios']['median']:,.2f}")
        
        background_tasks.add_task(_log_simulation_analytics, request.num_simulations, request.years, len(holdings_data), elapsed)
        
        return results
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post('/monte-carlo/quick-forecast', response_model=QuickForecastResponse, tags=["Monte Carlo"])
async def quick_forecast(request: QuickForecastRequest):
    """Run a fast portfolio forecast with simplified inputs and outputs"""
    try:
        logger.info(f"Quick forecast: ${request.portfolio_value:,.2f}, {request.years} years")
        
        results = quick_simulate(
            portfolio_value=request.portfolio_value,
            annual_return=request.annual_return,
            volatility=request.volatility,
            years=request.years,
            num_simulations=500
        )
        
        response = QuickForecastResponse(
            initial_value=results['metadata']['initial_value'],
            median_outcome=results['scenarios']['median'],
            best_case=results['scenarios']['best_case'],
            worst_case=results['scenarios']['worst_case'],
            prob_gain=results['probabilities']['prob_gain'],
            prob_loss=results['probabilities']['prob_loss'],
            prob_double=results['probabilities']['prob_double'],
            expected_return=results['statistics']['mean_annualized_return']
        )
        
        logger.info(f"Quick forecast complete. Median: ${response.median_outcome:,.2f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Quick forecast failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@router.get('/monte-carlo/simple', response_model=QuickForecastResponse, tags=["Monte Carlo"])
async def simple_forecast(
    portfolio_value: float = Query(..., gt=0),
    annual_return: float = Query(0.08, ge=-1, le=2),
    volatility: float = Query(0.15, ge=0, le=2),
    years: int = Query(10, ge=1, le=50)
):
    """Run a simple forecast using query parameters (GET request)"""
    try:
        results = quick_simulate(
            portfolio_value=portfolio_value,
            annual_return=annual_return,
            volatility=volatility,
            years=years,
            num_simulations=500
        )
        
        return QuickForecastResponse(
            initial_value=results['metadata']['initial_value'],
            median_outcome=results['scenarios']['median'],
            best_case=results['scenarios']['best_case'],
            worst_case=results['scenarios']['worst_case'],
            prob_gain=results['probabilities']['prob_gain'],
            prob_loss=results['probabilities']['prob_loss'],
            prob_double=results['probabilities']['prob_double'],
            expected_return=results['statistics']['mean_annualized_return']
        )
        
    except Exception as e:
        logger.error(f"Simple forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/monte-carlo/compare', tags=["Monte Carlo"])
async def compare_scenarios(scenarios: List[SimulationRequest] = Body(..., min_items=2, max_items=5)):
    """Compare multiple simulation scenarios side-by-side"""
    try:
        if len(scenarios) < 2 or len(scenarios) > 5:
            raise HTTPException(status_code=400, detail="2-5 scenarios required")
        
        logger.info(f"Comparing {len(scenarios)} scenarios")
        
        results = []
        
        for i, scenario in enumerate(scenarios):
            config = SimulationConfig(
                num_simulations=scenario.num_simulations,
                years=scenario.years,
                method=scenario.method,
                distribution=scenario.distribution
            )
            
            simulator = MonteCarloSimulator(config)
            holdings_data = [h.dict() for h in scenario.holdings]
            
            result = simulator.simulate_portfolio(holdings=holdings_data, years=scenario.years, confidence_levels=scenario.confidence_levels)
            result['scenario_id'] = i + 1
            results.append(result)
        
        comparison = {
            'scenarios': results,
            'summary': {
                'best_median': max(r['scenarios']['median'] for r in results),
                'worst_median': min(r['scenarios']['median'] for r in results)
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/monte-carlo/methods', tags=["Monte Carlo"])
async def get_simulation_methods():
    """Get information about available simulation methods and distributions"""
    return {
        'simulation_methods': [
            {
                'id': SimulationMethod.GEOMETRIC_BROWNIAN.value,
                'name': 'Geometric Brownian Motion',
                'description': 'Classic Black-Scholes model',
                'use_case': 'General purpose forecasting'
            },
            {
                'id': SimulationMethod.HISTORICAL_BOOTSTRAP.value,
                'name': 'Historical Bootstrap',
                'description': 'Samples from historical returns',
                'use_case': 'When historical data available'
            },
            {
                'id': SimulationMethod.MEAN_REVERSION.value,
                'name': 'Mean Reversion',
                'description': 'Ornstein-Uhlenbeck process',
                'use_case': 'Markets with mean reversion'
            }
        ],
        'distributions': [
            {'id': DistributionType.NORMAL.value, 'name': 'Normal (Gaussian)'},
            {'id': DistributionType.STUDENT_T.value, 'name': 'Student-t'},
            {'id': DistributionType.LOGNORMAL.value, 'name': 'Log-Normal'}
        ],
        'default_config': {
            'num_simulations': 1000,
            'years': 10,
            'method': SimulationMethod.GEOMETRIC_BROWNIAN.value
        }
    }


@router.get('/monte-carlo/health', tags=["Monte Carlo"])
async def check_health():
    """Health check for Monte Carlo simulation service"""
    try:
        test_start = datetime.now()
        
        test_result = quick_simulate(
            portfolio_value=100000,
            annual_return=0.08,
            volatility=0.15,
            years=5,
            num_simulations=100
        )
        
        test_time = (datetime.now() - test_start).total_seconds()
        
        return {
            'status': 'healthy',
            'service': 'Monte Carlo Simulation',
            'test_simulation_time': f"{test_time:.3f}s",
            'max_simulations': 100000,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


# Helper Functions

async def _log_simulation_analytics(num_simulations: int, years: int, holdings_count: int, elapsed_time: float):
    """Log simulation analytics for monitoring (background task)"""
    try:
        logger.info(f"Simulation Analytics - Simulations: {num_simulations}, Years: {years}, Holdings: {holdings_count}, Time: {elapsed_time:.2f}s")
    except Exception as e:
        logger.warning(f"Failed to log analytics: {e}")
