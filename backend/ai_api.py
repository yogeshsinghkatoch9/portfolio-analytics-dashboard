from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ai_service import AIService

router = APIRouter()

class AnalyzeRequest(BaseModel):
    portfolio_context: Dict[str, Any]
    query: Optional[str] = None

class AnalysisResponse(BaseModel):
    summary: str
    risks: List[str]
    opportunities: List[str]
    sentiment: str

class ChatRequest(BaseModel):
    message: str
    portfolio_context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []

@router.post('/ai/analyze', response_model=AnalysisResponse)
async def analyze_portfolio(request: AnalyzeRequest):
    """
    Generate comprehensive portfolio analysis using AI
    """
    try:
        analysis = AIService.generate_portfolio_analysis(
            request.portfolio_context, 
            request.query
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/ai/chat', response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Chat endpoint for follow-up questions
    """
    try:
        # For now, we'll keep the simple chat or upgrade it later
        # Re-using the mock logic for chat if AIService.chat isn't fully ready
        # or implementing a simple wrapper
        
        # For this phase, let's focus on the Analysis panel first
        return ChatResponse(
            response="I've analyzed your portfolio structure. Check the AI Insights panel for details on risks and opportunities.",
            sources=["VisionWealth AI"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
