from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import random
import os

# Try importing simple AI clients if available, otherwise mock
try:
    import openai
except ImportError:
    openai = None

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    portfolio_context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []

def _generate_system_prompt(context: Dict[str, Any]) -> str:
    """
    Construct a prompt with portfolio context.
    """
    if not context:
        return "You are a helpful financial assistant called VisionWealth AI. The user has no portfolio loaded."
        
    holdings_summary = ""
    if 'holdings' in context:
        # Limit to top 5 for brevity in context
        sorted_holdings = sorted(context['holdings'], key=lambda h: h.get('value', 0), reverse=True)[:5]
        holdings_txt = ", ".join([f"{h['ticker']} (${h.get('value',0):,.0f})" for h in sorted_holdings])
        holdings_summary = f"Top Holdings: {holdings_txt}"

    prompt = f"""
    You are VisionWealth AI, an advanced wealth management assistant.
    
    CURRENT PORTFOLIO CONTEXT:
    Total Net Worth: ${context.get('net_worth', 0):,.2f}
    Daily Change: {context.get('daily_change_percent', 0):.2f}%
    {holdings_summary}
    
    User Question: {{user_message}}
    
    Answer the user's question concisely based on this context. 
    If they ask about specific stock performance, simulate a realistic financial analyst response.
    """
    return prompt

@router.post('/ai/chat', response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Chat endpoint. In production, this would call GPT-4 or Gemini.
    Here we prioritize a high-quality Mock experience if no key is found.
    """
    try:
        user_msg = request.message.lower()
        context = request.portfolio_context or {}
        
        # 1. Simple Keyword Handling (Mock Intelligence)
        response_text = ""
        
        if "dividend" in user_msg:
             response_text = f"Based on your portfolio, I assume you're interested in income. With your top holdings like {context.get('holdings', [{'ticker':'assets'}])[0].get('ticker')}, you likely have quarterly distributions. Shall I pull up the Dividend Calendar?"
             
        elif "risk" in user_msg or "safe" in user_msg:
            response_text = "Analyzing your risk profile... You have a mix across asset classes. To give a precise beta score, I'd need to run a deeper regression analysis, but visibly you have concentration in Tech."
            
        elif "worth" in user_msg or "value" in user_msg:
             val = context.get('net_worth', 0)
             response_text = f"Your current total Net Worth is **${val:,.2f}**. It looks like a solid foundation."
             
        elif "hello" in user_msg or "hi" in user_msg:
             response_text = "Hello! I am your AI Wealth Assistant. I have access to your live portfolio data. Ask me about your dividends, risk, or performance!"
             
        else:
             # Fallback generic financial advice style
             response_text = "That's an interesting question. In a full production environment, I would connect to a live LLM to answer detailed queries about market trends or specific tax implications. For now, try asking me about your 'dividends' or 'net worth' to demonstrate my context awareness."

        return ChatResponse(
            response=response_text,
            sources=["VisionWealth Portfolio Engine", "Market Data"]
        )
        
    except Exception as e:
        print(f"AI Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
