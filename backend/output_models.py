"""
Pydantic Models for Structured LangChain Outputs
Ensures type-safe and validated AI responses
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from enum import Enum


class RiskLevel(str, Enum):
    """Risk severity levels"""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class MarketSentiment(str, Enum):
    """Market sentiment options"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class RiskItem(BaseModel):
    """Individual risk assessment"""
    description: str = Field(..., description="Specific risk description")
    severity: RiskLevel = Field(..., description="Risk severity level")
    impact: str = Field(..., description="Potential impact on portfolio")
    
    class Config:
        use_enum_values = True


class Opportunity(BaseModel):
    """Investment opportunity"""
    description: str = Field(..., description="Opportunity description")
    potential_benefit: str = Field(..., description="Expected benefit")
    action_required: str = Field(..., description="Specific action to take")


class Recommendation(BaseModel):
    """Actionable recommendation"""
    priority: int = Field(..., ge=1, le=5, description="Priority level (1=highest)")
    action: str = Field(..., description="Specific action to take")
    rationale: str = Field(..., description="Why this recommendation matters")
    expected_impact: str = Field(..., description="Expected outcome")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Priority must be between 1 and 5')
        return v


class PortfolioAnalysis(BaseModel):
    """Complete portfolio analysis output"""
    summary: str = Field(
        ..., 
        description="2-3 sentence executive summary of portfolio health",
        min_length=50,
        max_length=500
    )
    risks: List[RiskItem] = Field(
        ..., 
        description="List of identified risks",
        min_items=1,
        max_items=5
    )
    opportunities: List[Opportunity] = Field(
        ..., 
        description="List of opportunities for improvement",
        min_items=1,
        max_items=4
    )
    recommendations: List[Recommendation] = Field(
        ..., 
        description="Prioritized list of recommendations",
        min_items=2,
        max_items=6
    )
    sentiment: MarketSentiment = Field(
        ..., 
        description="Overall market sentiment for this portfolio"
    )
    score: int = Field(
        ..., 
        ge=1, 
        le=100, 
        description="Overall portfolio health score (1-100)"
    )
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "summary": "Well-diversified portfolio with strong tech exposure. Consider rebalancing to reduce concentration risk in top 3 holdings.",
                "risks": [
                    {
                        "description": "High concentration in technology sector (45%)",
                        "severity": "High",
                        "impact": "Vulnerable to tech sector downturns"
                    }
                ],
                "opportunities": [
                    {
                        "description": "Underweight in healthcare sector",
                        "potential_benefit": "Better diversification and defensive positioning",
                        "action_required": "Allocate 10-15% to healthcare ETFs or stocks"
                    }
                ],
                "recommendations": [
                    {
                        "priority": 1,
                        "action": "Reduce top 3 holdings from 60% to 40% of portfolio",
                        "rationale": "Excessive concentration risk",
                        "expected_impact": "Lower volatility and better risk-adjusted returns"
                    }
                ],
                "sentiment": "Neutral",
                "score": 72
            }
        }


class QuickInsight(BaseModel):
    """Quick one-line insight"""
    insight: str = Field(
        ..., 
        description="Concise, actionable insight about the portfolio",
        min_length=20,
        max_length=200
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence level in this insight"
    )


class ChatResponse(BaseModel):
    """Conversational chat response"""
    response: str = Field(..., description="Natural language response to user query")
    follow_up_suggestions: Optional[List[str]] = Field(
        None, 
        description="Suggested follow-up questions",
        max_items=3
    )
    data_points_referenced: Optional[List[str]] = Field(
        None,
        description="Portfolio data points used in the response"
    )
