"""
Monte Carlo Simulation Engine
Predict portfolio outcomes using historical data and probability distributions
"""

import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """Monte Carlo simulation for portfolio forecasting"""
    
    def __init__(self, num_simulations: int = 1000):
        """
        Initialize Monte Carlo simulator
        
        Args:
            num_simulations: Number of simulation paths to generate
        """
        self.num_simulations = num_simulations
        np.random.seed(42)  # For reproducibility
    
    def simulate_portfolio(
        self,
        holdings: List[Dict],
        years: int = 10,
        confidence_levels: List[float] = [0.05, 0.25, 0.50, 0.75, 0.95]
    ) -> Dict:
        """
        Run Monte Carlo simulation for portfolio
        
       Args:
            holdings: List of portfolio holdings with ticker, value, returns data
            years: Number of years to simulate forward
            confidence_levels: Percentiles to calculate (0.05 = 5th percentile)
            
        Returns:
            Dictionary with simulation results including scenarios, percentiles, statistics
        """
        logger.info(f"Starting Monte Carlo simulation: {self.num_simulations} scenarios over {years} years")
        
        try:
            # Calculate portfolio-level statistics
            portfolio_stats = self._calculate_portfolio_stats(holdings)
            
            # Run simulations
            simulation_paths = self._run_simulations(
                portfolio_stats['initial_value'],
                portfolio_stats['mean_return'],
                portfolio_stats['volatility'],
                years
            )
            
            # Calculate percentiles
            percentiles = self._calculate_percentiles(simulation_paths, confidence_levels)
            
            # Calculate statistics
            stats = self._calculate_statistics(simulation_paths)
            
            # Probability of outcomes
            probabilities = self._calculate_probabilities(
                simulation_paths,
                portfolio_stats['initial_value']
            )
            
            result = {
                'metadata': {
                    'num_simulations': self.num_simulations,
                    'years': years,
                    'initial_value': portfolio_stats['initial_value'],
                    'mean_annual_return': portfolio_stats['mean_return'],
                    'annual_volatility': portfolio_stats['volatility']
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
                'time_series': self._prepare_time_series(simulation_paths, years)
            }
            
            logger.info(f"Simulation complete. Median outcome: ${result['scenarios']['median']:,.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {e}")
            raise
    
    def _calculate_portfolio_stats(self, holdings: List[Dict]) -> Dict:
        """Calculate portfolio-level mean return and volatility"""
        total_value = sum(h.get('value', 0) for h in holdings)
        
        if total_value == 0:
            raise ValueError("Portfolio has zero value")
        
        # Weighted average of returns and volatilities
        portfolio_return = 0.0
        portfolio_variance = 0.0
        
        for holding in holdings:
            weight = holding.get('value', 0) / total_value
            
            # Use historical or assumed returns
            annual_return = holding.get('annual_return', 0.08)  # Default 8%
            volatility = holding.get('volatility', 0.15)  # Default 15%
            
            portfolio_return += weight * annual_return
            portfolio_variance += (weight * volatility) ** 2  # Simplified - assumes uncorrelated
        
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        return {
            'initial_value': total_value,
            'mean_return': portfolio_return,
            'volatility': portfolio_volatility
        }
    
    def _run_simulations(
        self,
        initial_value: float,
        mean_return: float,
        volatility: float,
        years: int
    ) -> np.ndarray:
        """
        Run Monte Carlo simulations using geometric Brownian motion
        
        Returns:
            Array of shape (num_simulations, years * 12) with monthly values
        """
        months = years * 12
        dt = 1/12  # Monthly time step
        
        # Initialize array for all paths
        paths = np.zeros((self.num_simulations, months + 1))
        paths[:, 0] = initial_value
        
        # Convert annual to monthly parameters
        monthly_return = mean_return / 12
        monthly_vol = volatility / np.sqrt(12)
        
        # Generate random returns
        for t in range(1, months + 1):
            # Generate random shocks
            z = np.random.standard_normal(self.num_simulations)
            
            # Geometric Brownian Motion formula
            returns = monthly_return * dt + monthly_vol * np.sqrt(dt) * z
            paths[:, t] = paths[:, t-1] * (1 + returns)
        
        return paths
    
    def _calculate_percentiles(
        self,
        paths: np.ndarray,
        confidence_levels: List[float]
    ) -> Dict:
        """Calculate percentile outcomes"""
        final_values = paths[:, -1]
        
        percentiles = {}
        for level in confidence_levels:
            percentile_value = np.percentile(final_values, level * 100)
            percentiles[f'p{int(level * 100)}'] = float(percentile_value)
        
        return percentiles
    
    def _calculate_statistics(self, paths: np.ndarray) -> Dict:
        """Calculate statistical measures"""
        final_values = paths[:, -1]
        initial_value = paths[0, 0]
        
        returns = (final_values - initial_value) / initial_value
        
        return {
            'mean_final_value': float(np.mean(final_values)),
            'median_final_value': float(np.median(final_values)),
            'std_final_value': float(np.std(final_values)),
            'mean_return': float(np.mean(returns)),
            'median_return': float(np.median(returns)),
            'std_return': float(np.std(returns)),
            'var_95': float(np.percentile(returns, 5)),  # Value at Risk
            'cvar_95': float(np.mean(returns[returns <= np.percentile(returns, 5)]))  # Conditional VaR
        }
    
    def _calculate_probabilities(self, paths: np.ndarray, initial_value: float) -> Dict:
        """Calculate probability of different outcomes"""
        final_values = paths[:, -1]
        
        return {
            'prob_gain': float(np.sum(final_values > initial_value) / self.num_simulations),
            'prob_loss': float(np.sum(final_values < initial_value) / self.num_simulations),
            'prob_double': float(np.sum(final_values >= initial_value * 2) / self.num_simulations),
            'prob_half': float(np.sum(final_values <= initial_value * 0.5) / self.num_simulations),
            'prob_10pct_gain': float(np.sum(final_values >= initial_value * 1.1) / self.num_simulations),
            'prob_10pct_loss': float(np.sum(final_values <= initial_value * 0.9) / self.num_simulations)
        }
    
    def _prepare_time_series(self, paths: np.ndarray, years: int) -> Dict:
        """Prepare time series data for visualization"""
        months = years * 12
        
        # Sample some paths for visualization (don't return all 1000)
        sample_indices = np.random.choice(self.num_simulations, size=min(50, self.num_simulations), replace=False)
        sample_paths = paths[sample_indices]
        
        # Calculate percentile bands over time
        p5 = np.percentile(paths, 5, axis=0)
        p25 = np.percentile(paths, 25, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p75 = np.percentile(paths, 75, axis=0)
        p95 = np.percentile(paths, 95, axis=0)
        
        # Generate time labels
        time_labels = [f"Month {i}" for i in range(months + 1)]
        
        return {
            'time_labels': time_labels,
            'sample_paths': sample_paths.tolist(),
            'percentile_bands': {
                'p5': p5.tolist(),
                'p25': p25.tolist(),
                'p50': p50.tolist(),
                'p75': p75.tolist(),
                'p95': p95.tolist()
            }
        }


# Global instance
_monte_carlo_simulator = None

def get_simulator(num_simulations: int = 1000) -> MonteCarloSimulator:
    """Get or create Monte Carlo simulator instance"""
    global _monte_carlo_simulator
    if _monte_carlo_simulator is None or _monte_carlo_simulator.num_simulations != num_simulations:
        _monte_carlo_simulator = MonteCarloSimulator(num_simulations)
    return _monte_carlo_simulator
