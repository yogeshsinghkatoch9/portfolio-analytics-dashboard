"""
AI Service for Portfolio Analytics
Handles interactions with OpenAI API for portfolio analysis
Updated for OpenAI API v1.0+
"""

import os
from openai import OpenAI
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

# Configure OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
    
    def is_available(self) -> bool:
        """Check if AI service is configured"""
        return self.client is not None
    
    def generate_portfolio_analysis(
        self, 
        portfolio_context: Dict[str, Any], 
        user_query: str = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI insights for a portfolio
        
        Args:
            portfolio_context: Portfolio data including holdings, metrics
            user_query: Optional specific question from user
            
        Returns:
            Dictionary with summary, risks, opportunities, recommendations
        """
        if not self.is_available():
            return {
                "summary": "AI analysis unavailable - OpenAI API key not configured",
                "risks": ["Configure OPENAI_API_KEY environment variable to enable AI insights"],
                "opportunities": [],
                "recommendations": [],
                "sentiment": "Neutral"
            }

        try:
            # Prepare portfolio data
            holdings = portfolio_context.get('holdings', [])
            top_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)[:15]
            
            holdings_str = "\n".join([
                f"- {h.get('ticker', 'Unknown')}: ${h.get('value', 0):,.2f} ({h.get('allocation', 0):.1f}%) - Sector: {h.get('sector', 'N/A')}" 
                for h in top_holdings
            ])
            
            total_value = portfolio_context.get('total_value', 0)
            daily_change = portfolio_context.get('daily_change_pct', 0)
            risk_metrics = portfolio_context.get('risk_metrics', {})
            
            # Enhanced system prompt
            system_prompt = """You are an expert portfolio analyst and financial advisor.
Your goal is to provide professional, actionable investment insights suitable for both 
individual investors and financial professionals.

Analyze the portfolio and return a JSON response with:
1. "summary": 2-3 sentence executive summary highlighting key characteristics
2. "risks": List of 3-4 specific risks with severity (High/Medium/Low)
3. "opportunities": List of 2-3 actionable opportunities for improvement
4. "recommendations": List of 3-5 specific, prioritized actions to optimize the portfolio
5. "sentiment": Overall market outlook - "Bullish", "Bearish", or "Neutral"
6. "score": Overall portfolio health score from 1-100

Be specific, quantitative when possible, and prioritize actionable insights."""

            user_prompt = f"""PORTFOLIO ANALYSIS REQUEST

PORTFOLIO METRICS:
- Total Value: ${total_value:,.2f}
- Daily Change: {daily_change:+.2f}%
- Number of Holdings: {len(holdings)}
- Beta: {risk_metrics.get('beta', 'N/A')}
- Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A')}
- Volatility: {risk_metrics.get('volatility', 'N/A')}

TOP HOLDINGS:
{holdings_str}

SECTOR ALLOCATION:
{self._format_sectors(portfolio_context.get('sectors', {}))}

USER QUERY: {user_query if user_query else "Provide a comprehensive portfolio analysis with specific recommendations."}

Return analysis as valid JSON matching the requested format."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            logger.info(f"Generated AI analysis for portfolio value ${total_value:,.0f}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._fallback_response("JSON parsing error")
        except Exception as e:
            logger.error(f"AI Analysis Error: {e}")
            return self._fallback_response(str(e))
    
    def generate_quick_insight(
        self,
        portfolio_context: Dict[str, Any]
    ) -> str:
        """Generate a quick one-sentence insight"""
        if not self.is_available():
            return "AI insights unavailable - configure API key"
        
        try:
            holdings_count = len(portfolio_context.get('holdings', []))
            total_value = portfolio_context.get('total_value', 0)
            top_sector = self._get_top_sector(portfolio_context.get('sectors', {}))
            
            prompt = f"""Generate ONE concise sentence highlighting the most important insight about this portfolio:
- {holdings_count} holdings worth ${total_value:,.0f}
- Top sector: {top_sector}
- Beta: {portfolio_context.get('risk_metrics', {}).get('beta', 'N/A')}

Make it actionable and specific. No fluff."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Quick insight generation failed: {e}")
            return f"Portfolio of {len(portfolio_context.get('holdings', []))} holdings"
    
    def chat(
        self, 
        message: str, 
        portfolio_context: Dict[str, Any],
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Interactive chat about the portfolio
        
        Args:
            message: User's question
            portfolio_context: Current portfolio data
            conversation_history: Previous messages for context
            
        Returns:
            AI response as string
        """
        if not self.is_available():
            return "AI chat unavailable - please configure OpenAI API key"
        
        try:
            system_msg = f"""You are a helpful financial advisor assistant. 
You have access to the user's portfolio data:
- Total Value: ${portfolio_context.get('total_value', 0):,.2f}
- Holdings: {len(portfolio_context.get('holdings', []))}
- Top holding: {portfolio_context.get('holdings', [{}])[0].get('ticker', 'N/A') if portfolio_context.get('holdings') else 'None'}

Answer questions about their portfolio, provide insights, and offer guidance.
Be conversational but professional."""

            messages = [{"role": "system", "content": system_msg}]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-5:])  # Last 5 messages
            
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return "I'm having trouble processing your request. Please try again."
    
    def _format_sectors(self, sectors: Dict[str, float]) -> str:
        """Format sector allocation for prompt"""
        if not sectors:
            return "No sector data available"
        
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"- {sector}: {weight:.1f}%" for sector, weight in sorted_sectors[:5]])
    
    def _get_top_sector(self, sectors: Dict[str, float]) -> str:
        """Get the sector with highest allocation"""
        if not sectors:
            return "Diversified"
        return max(sectors, key=sectors.get)
    
    def _fallback_response(self, error_msg: str = "") -> Dict[str, Any]:
        """Fallback response when AI fails"""
        return {
            "summary": "AI analysis temporarily unavailable. Please try again.",
            "risks": ["Service experiencing technical difficulties"],
            "opportunities": [],
            "recommendations": ["Retry analysis in a moment"],
            "sentiment": "Neutral",
            "score": 50,
            "error": error_msg
        }


# Global instance
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Get or create singleton AI service instance"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
