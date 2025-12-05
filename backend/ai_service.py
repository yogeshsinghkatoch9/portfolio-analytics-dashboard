"""
AI Service for VisionWealth
Handles interactions with OpenAI API for portfolio analysis
"""

import os
import openai
from typing import Dict, Any, List, Optional
import json

# Configure OpenAI
# In production, this comes from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

class AIService:
    @staticmethod
    def generate_portfolio_analysis(portfolio_context: Dict[str, Any], user_query: str = None) -> Dict[str, Any]:
        """
        Generate AI insights for a portfolio
        """
        if not OPENAI_API_KEY:
            return {
                "summary": "AI configuration missing. Please add OPENAI_API_KEY.",
                "risks": [],
                "opportunities": []
            }

        # Construct context for the AI
        holdings = portfolio_context.get('holdings', [])
        # Limit holdings to top 20 to avoid token limits
        top_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)[:20]
        
        holdings_str = "\n".join([
            f"- {h.get('ticker', 'Unknown')}: ${h.get('value', 0):,.2f} ({h.get('allocation', 0):.1f}%) - {h.get('sector', 'N/A')}" 
            for h in top_holdings
        ])
        
        total_value = portfolio_context.get('total_value', 0)
        daily_change = portfolio_context.get('daily_change_pct', 0)
        
        system_prompt = """
        You are VisionWealth AI, an expert financial analyst for a high-net-worth portfolio dashboard.
        Your goal is to provide concise, actionable, and professional investment insights.
        
        Analyze the provided portfolio data and return a JSON response with:
        1. "summary": A 2-3 sentence executive summary of the portfolio's status and performance.
        2. "risks": A list of 2-3 potential risks (concentration, sector exposure, volatility).
        3. "opportunities": A list of 2-3 potential opportunities or observations (dividend income, diversification).
        4. "sentiment": One of "Bullish", "Bearish", or "Neutral".
        
        Tone: Professional, objective, institutional-grade.
        """
        
        user_prompt = f"""
        PORTFOLIO METRICS:
        Total Value: ${total_value:,.2f}
        Daily Change: {daily_change:.2f}%
        
        TOP HOLDINGS:
        {holdings_str}
        
        USER QUERY: {user_query if user_query else "Analyze my portfolio structure and risk."}
        
        Provide the analysis in JSON format.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Use GPT-4 for better financial analysis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON from response (handle potential markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content)
            
        except Exception as e:
            print(f"AI Analysis Error: {e}")
            # Fallback response
            return {
                "summary": "Unable to generate detailed analysis at this moment.",
                "risks": ["AI Service currently unavailable"],
                "opportunities": [],
                "sentiment": "Neutral"
            }

    @staticmethod
    def chat(message: str, portfolio_context: Dict[str, Any]) -> str:
        """
        Chat with the AI about the portfolio
        """
        # Similar logic but returns text string for chat interface
        # ... (simplified for now)
        return "Chat functionality coming in next update."
