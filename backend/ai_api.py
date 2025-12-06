from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ai_service import get_ai_service

# LangChain imports
from langchain_service import get_langchain_service
from portfolio_rag import get_portfolio_rag
from portfolio_agent import get_portfolio_agent

router = APIRouter()

class AnalyzeRequest(BaseModel):
    portfolio_context: Dict[str, Any]
    query: Optional[str] = None
    user_id: Optional[int] = None  # Added for LangChain features

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
    user_id: Optional[int] = None  # Added for memory management

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    follow_up_suggestions: Optional[List[str]] = []

class QuickInsightRequest(BaseModel):
    portfolio_context: Dict[str, Any]

class QuickInsightResponse(BaseModel):
    insight: str

# New LangChain-specific request/response models
class RAGQueryRequest(BaseModel):
    query: str
    user_id: int
    current_portfolio: Optional[Dict[str, Any]] = None

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    
class AgentQueryRequest(BaseModel):
    question: str
    user_id: int
    portfolio_context: Optional[Dict[str, Any]] = None

class AgentQueryResponse(BaseModel):
    answer: str
    steps: List[Dict[str, Any]]
    success: bool

class CompareHistoryRequest(BaseModel):
    user_id: int
    current_portfolio: Dict[str, Any]
    comparison_type: str = "performance"

class CompareHistoryResponse(BaseModel):
    summary: str
    changes: List[str]
    insights: List[str]


# ============================================================================
# EXISTING ENDPOINTS (Backward Compatible)
# ============================================================================

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


# ============================================================================
# NEW LANGCHAIN-POWERED ENDPOINTS
# ============================================================================

@router.post('/ai/langchain/analyze', response_model=AnalysisResponse)
async def analyze_portfolio_langchain(request: AnalyzeRequest):
    """
    Enhanced portfolio analysis using LangChain with structured outputs
    
    Features:
    - Structured Pydantic output parsing for type safety
    - Historical context from vector store (if user_id provided)
    - Automatic storage of analysis for future reference
    - More reliable and consistent responses
    """
    try:
        if not request.user_id:
            raise HTTPException(
                status_code=400, 
                detail="user_id required for LangChain analysis"
            )
        
        lc_service = get_langchain_service()
        
        if not lc_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="LangChain service unavailable - check OpenAI API key"
            )
        
        analysis = lc_service.generate_portfolio_analysis(
            portfolio_context=request.portfolio_context,
            user_query=request.query,
            user_id=request.user_id
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"LangChain analysis failed: {str(e)}"
        )

@router.post('/ai/langchain/chat', response_model=ChatResponse)
async def chat_with_langchain(request: ChatRequest):
    """
    Enhanced conversational AI with memory management
    
    Features:
    - Persistent conversation memory per user
    - Structured responses with follow-up suggestions
    - Better context retention across messages
    """
    try:
        if not request.user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id required for LangChain chat"
            )
        
        if not request.portfolio_context:
            return ChatResponse(
                response="Please provide portfolio context to get personalized insights.",
                sources=[],
                follow_up_suggestions=[]
            )
        
        lc_service = get_langchain_service()
        
        if not lc_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="LangChain service unavailable"
            )
        
        result = lc_service.chat(
            message=request.message,
            portfolio_context=request.portfolio_context,
            user_id=request.user_id
        )
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LangChain chat failed: {str(e)}"
        )

@router.post('/ai/rag/query', response_model=RAGQueryResponse)
async def query_portfolio_history(request: RAGQueryRequest):
    """
    Query portfolio history using RAG (Retrieval-Augmented Generation)
    
    Features:
    - Search historical portfolio snapshots
    - Context-aware answers based on past data
    - Source attribution for transparency
    
    Example queries:
    - "How has my tech allocation changed over time?"
    - "When was my portfolio value highest?"
    - "Show me periods with similar risk levels"
    """
    try:
        rag_service = get_portfolio_rag()
        
        if not rag_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="RAG service unavailable"
            )
        
        result = rag_service.query_portfolio_history(
            query=request.query,
            user_id=request.user_id,
            current_portfolio=request.current_portfolio
        )
        
        return RAGQueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {str(e)}"
        )

@router.post('/ai/rag/compare', response_model=CompareHistoryResponse)
async def compare_with_history(request: CompareHistoryRequest):
    """
    Compare current portfolio with historical snapshots
    
    Comparison types:
    - performance: Returns, gains/losses over time
    - allocation: Sector and asset allocation changes
    - risk: Risk metrics evolution
    """
    try:
        rag_service = get_portfolio_rag()
        
        if not rag_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="RAG service unavailable"
            )
        
        result = rag_service.compare_with_history(
            user_id=request.user_id,
            current_portfolio=request.current_portfolio,
            comparison_type=request.comparison_type
        )
        
        return CompareHistoryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Historical comparison failed: {str(e)}"
        )

@router.post('/ai/agent/query', response_model=AgentQueryResponse)
async def query_with_agent(request: AgentQueryRequest):
    """
    Query portfolio using autonomous AI agent
    
    The agent can:
    - Use multiple tools to answer complex questions
    - Fetch real-time market data
    - Calculate metrics on demand
    - Search historical patterns
    - Perform multi-step reasoning
    
    Example queries:
    - "What are my top holdings and how are they performing today?"
    - "Calculate my Sharpe ratio and compare it to the market"
    - "Find historical periods when my portfolio had similar characteristics"
    """
    try:
        agent = get_portfolio_agent()
        
        if not agent.is_available():
            raise HTTPException(
                status_code=503,
                detail="Agent service unavailable"
            )
        
        result = agent.query(
            question=request.question,
            user_id=request.user_id,
            portfolio_context=request.portfolio_context
        )
        
        return AgentQueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent query failed: {str(e)}"
        )

@router.get('/ai/agent/capabilities')
async def get_agent_capabilities():
    """Get agent capabilities and example queries"""
    try:
        agent = get_portfolio_agent()
        return agent.get_capabilities()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get capabilities: {str(e)}"
        )

@router.delete('/ai/memory/{user_id}')
async def clear_user_memory(user_id: int):
    """Clear conversation memory for a user"""
    try:
        lc_service = get_langchain_service()
        agent = get_portfolio_agent()
        
        lc_service.clear_conversation_memory(user_id)
        agent.clear_memory(user_id)
        
        return {"message": f"Memory cleared for user {user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear memory: {str(e)}"
        )
