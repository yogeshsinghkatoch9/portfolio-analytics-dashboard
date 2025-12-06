"""
Monte Carlo Simulation Engine for Portfolio Forecasting
Predicts portfolio outcomes using historical data and probability distributions
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributionType(str, Enum):
    """Types of probability distributions"""
    NORMAL = "normal"
    LOGNORMAL = "lognormal"
    STUDENT_T = "student_t"
    HISTORICAL = "historical"


class SimulationMethod(str, Enum):
    """Monte Carlo simulation methods"""
    GEOMETRIC_BROWNIAN = "geometric_brownian_motion"
    HISTORICAL_BOOTSTRAP = "historical_bootstrap"
    MEAN_REVERSION = "mean_reversion"


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation"""
    num_simulations: int = 1000
    years: int = 10
    time_step_months: int = 1
    distribution: DistributionType = DistributionType.NORMAL
    method: SimulationMethod = SimulationMethod.GEOMETRIC_BROWNIAN
    risk_free_rate: float = 0.03
    random_seed: Optional[int] = 42
    
    def validate(self):
        """Validate configuration parameters"""
        if self.num_simulations < 100:
            raise ValueError("num_simulations must be at least 100")
        if self.num_simulations > 100000:
            raise ValueError("num_simulations cannot exceed 100,000")
        if self.years < 1 or self.years > 50:
            raise ValueError("years must be between 1 and 50")


class PortfolioStats:
    """Container for portfolio statistics"""
    
    def __init__(self, initial_value: float, mean_return: float, volatility: float, sharpe_ratio: float, weights: np.ndarray):
        self.initial_value = initial_value
        self.mean_return = mean_return
        self.volatility = volatility
        self.sharpe_ratio = sharpe_ratio
        self.weights = weights
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'initial_value': self.initial_value,
            'mean_return': self.mean_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio
        }


class MonteCarloSimulator:
    """Advanced Monte Carlo simulation for portfolio forecasting"""
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.config.validate()
        
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)
        
        logger.info(f"Initialized Monte Carlo: {self.config.num_simulations} simulations, {self.config.years} years")
    
    def simulate_portfolio(
        self, holdings: List[Dict[str, Any]], years: Optional[int] = None,
        confidence_levels: List[float] = [0.05, 0.25, 0.50, 0.75, 0.95],
        contributions: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Run Monte Carlo simulation for portfolio"""
        if years:
            self.config.years = years
        
        logger.info(f"Starting simulation: {self.config.num_simulations} scenarios over {self.config.years} years")
        
        try:
            start_time = datetime.now()
            
            portfolio_stats = self._calculate_portfolio_stats(holdings)
            
            if portfolio_stats.initial_value <= 0:
                raise ValueError("Portfolio initial value must be positive")
            
            # Run simulations
            simulation_paths = self._run_gbm_simulations(portfolio_stats, contributions)
            
            # Calculate results
            percentiles = self._calculate_percentiles(simulation_paths, confidence_levels)
            stats = self._calculate_statistics(simulation_paths, portfolio_stats.initial_value)
            probabilities = self._calculate_probabilities(simulation_paths, portfolio_stats.initial_value)
            risk_metrics = self._calculate_risk_metrics(simulation_paths, portfolio_stats.initial_value)
            time_series = self._prepare_time_series(simulation_paths)
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'metadata': {
                    'num_simulations': self.config.num_simulations,
                    'years': self.config.years,
                    'method': self.config.method.value,
                    'initial_value': portfolio_stats.initial_value,
                    'mean_annual_return': portfolio_stats.mean_return,
                    'annual_volatility': portfolio_stats.volatility,
                    'simulation_time_seconds': elapsed_time,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'scenarios': {
                    'best_case': float(np.max(simulation_paths[:, -1])),
                    'worst_case': float(np.min(simulation_paths[:, -1])),
                    'median': float(np.median(simulation_paths[:, -1])),
                    'mean': float(np.mean(simulation_paths[:, -1]))
                },
                'percentiles': percentiles,
                'statistics': stats,
                'probabilities': probabilities,
                'risk_metrics': risk_metrics,
                'time_series': time_series,
                'portfolio_stats': portfolio_stats.to_dict()
            }
            
            logger.info(f"Simulation complete in {elapsed_time:.2f}s. Median: ${result['scenarios']['median']:,.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}", exc_info=True)
            raise
    
    def _calculate_portfolio_stats(self, holdings: List[Dict]) -> PortfolioStats:
        """Calculate portfolio statistics"""
        if not holdings:
            raise ValueError("Holdings list cannot be empty")
        
        total_value = sum(h.get('value', 0) for h in holdings)
        
        if total_value <= 0:
            raise ValueError("Portfolio has zero or negative value")
        
        weights = np.array([h.get('value', 0) / total_value for h in holdings])
        returns = np.array([h.get('annual_return', 0.08) for h in holdings])
        volatilities = np.array([h.get('volatility', 0.15) for h in holdings])
        
        portfolio_return = np.dot(weights, returns)
        portfolio_variance = np.dot(weights ** 2, volatilities ** 2)
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        sharpe_ratio = (portfolio_return - self.config.risk_free_rate) / portfolio_volatility
        
        return PortfolioStats(total_value, portfolio_return, portfolio_volatility, sharpe_ratio, weights)
    
    def _run_gbm_simulations(self, stats: PortfolioStats, contributions: Optional[Dict[str, float]] = None) -> np.ndarray:
        """Run Geometric Brownian Motion simulations"""
        months = self.config.years * 12
        dt = 1 / 12
        
        paths = np.zeros((self.config.num_simulations, months + 1))
        paths[:, 0] = stats.initial_value
        
        period_return = stats.mean_return * dt
        period_vol = stats.volatility * np.sqrt(dt)
        
        monthly_contribution = contributions.get('monthly_amount', 0) if contributions else 0
        
        shocks = np.random.standard_normal((self.config.num_simulations, months))
        
        for t in range(1, months + 1):
            returns = period_return + period_vol * shocks[:, t - 1]
            paths[:, t] = paths[:, t - 1] * (1 + returns)
            
            if monthly_contribution > 0:
                paths[:, t] += monthly_contribution
        
        return paths
    
    def _calculate_percentiles(self, paths: np.ndarray, confidence_levels: List[float]) -> Dict[str, float]:
        """Calculate percentile outcomes"""
        final_values = paths[:, -1]
        
        percentiles = {}
        for level in confidence_levels:
            percentiles[f'p{int(level * 100)}'] = float(np.percentile(final_values, level * 100))
        
        return percentiles
    
    def _calculate_statistics(self, paths: np.ndarray, initial_value: float) -> Dict[str, float]:
        """Calculate statistical measures"""
        final_values = paths[:, -1]
        returns = (final_values - initial_value) / initial_value
        years = self.config.years
        annualized_returns = (final_values / initial_value) ** (1 / years) - 1
        
        return {
            'mean_final_value': float(np.mean(final_values)),
            'median_final_value': float(np.median(final_values)),
            'std_final_value': float(np.std(final_values)),
            'min_final_value': float(np.min(final_values)),
            'max_final_value': float(np.max(final_values)),
            'mean_total_return': float(np.mean(returns)),
            'median_total_return': float(np.median(returns)),
            'mean_annualized_return': float(np.mean(annualized_returns)),
            'median_annualized_return': float(np.median(annualized_returns))
        }
    
    def _calculate_risk_metrics(self, paths: np.ndarray, initial_value: float) -> Dict[str, float]:
        """Calculate risk metrics"""
        final_values = paths[:, -1]
        returns = (final_values - initial_value) / initial_value
        
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        cvar_95 = np.mean(returns[returns <= var_95])
        cvar_99 = np.mean(returns[returns <= var_99])
        
        max_drawdowns = []
        for path in paths:
            running_max = np.maximum.accumulate(path)
            drawdowns = (path - running_max) / running_max
            max_drawdowns.append(np.min(drawdowns))
        
        return {
            'value_at_risk_95': float(var_95),
            'value_at_risk_99': float(var_99),
            'conditional_var_95': float(cvar_95),
            'conditional_var_99': float(cvar_99),
            'mean_max_drawdown': float(np.mean(max_drawdowns)),
            'worst_drawdown': float(np.min(max_drawdowns))
        }
    
    def _calculate_probabilities(self, paths: np.ndarray, initial_value: float) -> Dict[str, float]:
        """Calculate probability of outcomes"""
        final_values = paths[:, -1]
        
        return {
            'prob_gain': float(np.sum(final_values > initial_value) / self.config.num_simulations),
            'prob_loss': float(np.sum(final_values < initial_value) / self.config.num_simulations),
            'prob_double': float(np.sum(final_values >= initial_value * 2) / self.config.num_simulations),
            'prob_triple': float(np.sum(final_values >= initial_value * 3) / self.config.num_simulations),
            'prob_10pct_gain': float(np.sum(final_values >= initial_value * 1.1) / self.config.num_simulations),
            'prob_25pct_gain': float(np.sum(final_values >= initial_value * 1.25) / self.config.num_simulations)
        }
    
    def _prepare_time_series(self, paths: np.ndarray) -> Dict[str, Any]:
        """Prepare time series visualization data"""
        sample_size = min(100, self.config.num_simulations)
        sample_indices = np.random.choice(self.config.num_simulations, size=sample_size, replace=False)
        
        percentile_bands = {
            'p5': np.percentile(paths, 5, axis=0).tolist(),
            'p25': np.percentile(paths, 25, axis=0).tolist(),
            'p50': np.percentile(paths, 50, axis=0).tolist(),
            'p75': np.percentile(paths, 75, axis=0).tolist(),
            'p95': np.percentile(paths, 95, axis=0).tolist(),
            'mean': np.mean(paths, axis=0).tolist()
        }
        
        return {
            'sample_paths': paths[sample_indices].tolist(),
            'percentile_bands': percentile_bands,
            'num_samples': sample_size
        }


def get_simulator(num_simulations: int = 1000, config: Optional[SimulationConfig] = None) -> MonteCarloSimulator:
    """Get Monte Carlo simulator instance"""
    if config is None:
        config = SimulationConfig(num_simulations=num_simulations)
    
    return MonteCarloSimulator(config)


def quick_simulate(portfolio_value: float, annual_return: float = 0.08, volatility: float = 0.15, years: int = 10, num_simulations: int = 1000) -> Dict[str, Any]:
    """Quick simulation with minimal inputs"""
    holdings = [{
        'value': portfolio_value,
        'annual_return': annual_return,
        'volatility': volatility
    }]
    
    simulator = get_simulator(num_simulations=num_simulations)
    return simulator.simulate_portfolio(holdings, years=years)
