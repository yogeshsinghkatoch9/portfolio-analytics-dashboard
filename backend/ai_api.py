from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ai_service import get_ai_service

router = APIRouter()

class AnalyzeRequest(BaseModel):
    portfolio_context: Dict[str, Any]
    query: Optional[str] = None

class AnalysisResponse(BaseModel):
    summary: str
    risks: List[str]
    opportunities: List[str]
    recommendations: Optional[List[str]] = []
    sentiment: str
    score: Optional[int] = None

class ChatRequest(BaseModel):
    message: str
    portfolio_context: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []

class QuickInsightRequest(BaseModel):
    portfolio_context: Dict[str, Any]

class QuickInsightResponse(BaseModel):
    insight: str

@router.post('/ai/analyze', response_model=AnalysisResponse)
async def analyze_portfolio(request: AnalyzeRequest):
    """
    Generate comprehensive portfolio analysis using OpenAI GPT-4
    
    Returns detailed insights including:
    - Executive summary
    - Risk assessment
    - Opportunities
    - Specific recommendations
    - Overall sentiment and score
    """
    try:
        ai_service = get_ai_service()
        analysis = ai_service.generate_portfolio_analysis(
            request.portfolio_context, 
            request.query
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@router.post('/ai/chat', response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Interactive chat about portfolio
    
    Supports conversation history for context-aware responses
    """
    try:
        ai_service = get_ai_service()
        
        if not request.portfolio_context:
            return ChatResponse(
                response="Please provide portfolio context to get personalized insights.",
                sources=[]
            )
        
        response_text = ai_service.chat(
            request.message,
            request.portfolio_context,
            request.conversation_history
        )
        
        return ChatResponse(
            response=response_text,
            sources=["OpenAI GPT-4", "Portfolio Data"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.post('/ai/quick-insight', response_model=QuickInsightResponse)
async def get_quick_insight(request: QuickInsightRequest):
    """
    Generate a quick one-sentence insight about the portfolio
    
    Fast endpoint for dashboard widgets
    """
    try:
        ai_service = get_ai_service()
        insight = ai_service.generate_quick_insight(request.portfolio_context)
        return QuickInsightResponse(insight=insight)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {str(e)}")
