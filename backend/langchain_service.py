"""
LangChain-Enhanced AI Service for Portfolio Analytics
Provides advanced AI capabilities with structured outputs, conversation memory, and RAG
"""

import os
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain.memory import ConversationBufferMemory

from langchain_config import get_langchain_config
from output_models import (
    PortfolioAnalysis, 
    QuickInsight, 
    ChatResponse,
    RiskItem,
    Opportunity,
    Recommendation
)
from vector_store_manager import get_vector_store

logger = logging.getLogger(__name__)


class LangChainAIService:
    """Enhanced AI service using LangChain for portfolio analytics"""
    
    def __init__(self):
        """Initialize LangChain AI service"""
        self.config = get_langchain_config()
        self.vector_store = get_vector_store()
        
        # Initialize LLM
        try:
            self.llm = self.config.get_llm()
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.available = False
        
        # Initialize parsers
        self.portfolio_parser = PydanticOutputParser(pydantic_object=PortfolioAnalysis)
        self.insight_parser = PydanticOutputParser(pydantic_object=QuickInsight)
        self.chat_parser = PydanticOutputParser(pydantic_object=ChatResponse)
        
        # Conversation memories (keyed by user_id)
        self.memories: Dict[int, ConversationBufferMemory] = {}
        
        logger.info("LangChain AI Service initialized")
    
    def is_available(self) -> bool:
        """Check if AI service is configured and available"""
        return self.available and self.config.is_configured()
    
    def generate_portfolio_analysis(
        self,
        portfolio_context: Dict[str, Any],
        user_query: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI insights for a portfolio using structured outputs
        
        Args:
            portfolio_context: Portfolio data including holdings, metrics
            user_query: Optional specific question from user
            user_id: Optional user ID for storing analysis
            
        Returns:
            Dictionary with structured analysis (summary, risks, opportunities, recommendations)
        """
        if not self.is_available():
            return self._fallback_response("AI service unavailable - OpenAI API key not configured")
        
        try:
            # Prepare portfolio data
            portfolio_data_str = self._format_portfolio_data(portfolio_context)
            
            # Get historical context if user_id provided
            historical_context = ""
            if user_id:
                historical_context = self._get_historical_context(user_id, portfolio_context)
            
            # Create prompt with format instructions
            system_template = """You are an expert portfolio analyst and financial advisor.
Your goal is to provide professional, actionable investment insights.

Analyze the portfolio and provide a comprehensive analysis.

{format_instructions}

Be specific, quantitative when possible, and prioritize actionable insights."""

            human_template = """PORTFOLIO ANALYSIS REQUEST

{portfolio_data}

{historical_context}

USER QUERY: {user_query}

Provide analysis in the specified JSON format."""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                ("human", human_template)
            ])
            
            # Create chain with structured output
            chain = prompt | self.llm | self.portfolio_parser
            
            # Execute chain
            result = chain.invoke({
                "format_instructions": self.portfolio_parser.get_format_instructions(),
                "portfolio_data": portfolio_data_str,
                "historical_context": historical_context,
                "user_query": user_query or "Provide a comprehensive portfolio analysis with specific recommendations."
            })
            
            # Convert Pydantic model to dict
            analysis_dict = result.dict()
            
            # Store snapshot in vector store
            if user_id:
                try:
                    self.vector_store.add_portfolio_snapshot(
                        user_id=user_id,
                        portfolio_data=portfolio_context,
                        analysis=analysis_dict
                    )
                except Exception as e:
                    logger.warning(f"Failed to store portfolio snapshot: {e}")
            
            logger.info(f"Generated structured AI analysis for portfolio value ${portfolio_context.get('total_value', 0):,.0f}")
            return analysis_dict
            
        except Exception as e:
            logger.error(f"AI Analysis Error: {e}")
            return self._fallback_response(str(e))
    
    def generate_quick_insight(
        self,
        portfolio_context: Dict[str, Any]
    ) -> str:
        """
        Generate a quick one-sentence insight using structured output
        
        Args:
            portfolio_context: Portfolio data
            
        Returns:
            Quick insight string
        """
        if not self.is_available():
            return "AI insights unavailable - configure API key"
        
        try:
            holdings_count = len(portfolio_context.get('holdings', []))
            total_value = portfolio_context.get('total_value', 0)
            top_sector = self._get_top_sector(portfolio_context.get('sectors', {}))
            
            prompt = PromptTemplate(
                template="""Generate ONE concise, actionable insight about this portfolio:
- {holdings_count} holdings worth ${total_value:,.0f}
- Top sector: {top_sector}
- Beta: {beta}

{format_instructions}

Make it specific and actionable. No fluff.""",
                input_variables=["holdings_count", "total_value", "top_sector", "beta"],
                partial_variables={"format_instructions": self.insight_parser.get_format_instructions()}
            )
            
            chain = prompt | self.llm | self.insight_parser
            
            result = chain.invoke({
                "holdings_count": holdings_count,
                "total_value": total_value,
                "top_sector": top_sector,
                "beta": portfolio_context.get('risk_metrics', {}).get('beta', 'N/A')
            })
            
            return result.insight
            
        except Exception as e:
            logger.error(f"Quick insight generation failed: {e}")
            return f"Portfolio of {len(portfolio_context.get('holdings', []))} holdings worth ${portfolio_context.get('total_value', 0):,.0f}"
    
    def chat(
        self,
        message: str,
        portfolio_context: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Interactive chat about the portfolio with conversation memory
        
        Args:
            message: User's question
            portfolio_context: Current portfolio data
            user_id: User ID for conversation memory
            
        Returns:
            ChatResponse with answer and follow-up suggestions
        """
        if not self.is_available():
            return {
                "response": "AI chat unavailable - please configure OpenAI API key",
                "follow_up_suggestions": [],
                "data_points_referenced": []
            }
        
        try:
            # Get or create memory for this user
            if user_id not in self.memories:
                self.memories[user_id] = self.config.get_conversation_memory()
            
            memory = self.memories[user_id]
            
            # Create portfolio context string
            portfolio_summary = f"""Portfolio Value: ${portfolio_context.get('total_value', 0):,.2f}
Holdings: {len(portfolio_context.get('holdings', []))}
Top Holding: {portfolio_context.get('holdings', [{}])[0].get('ticker', 'N/A') if portfolio_context.get('holdings') else 'None'}
Daily Change: {portfolio_context.get('daily_change_pct', 0):+.2f}%"""
            
            # Create prompt
            prompt = self.config.get_chat_prompt()
            
            # Create chain with memory
            chain = (
                RunnablePassthrough.assign(
                    chat_history=lambda x: memory.load_memory_variables({})["chat_history"]
                )
                | prompt
                | self.llm
                | self.chat_parser
            )
            
            # Execute
            result = chain.invoke({
                "portfolio_context": portfolio_summary,
                "input": message
            })
            
            # Save to memory
            memory.save_context(
                {"input": message},
                {"output": result.response}
            )
            
            return result.dict()
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "response": "I'm having trouble processing your request. Please try again.",
                "follow_up_suggestions": [],
                "data_points_referenced": []
            }
    
    def clear_conversation_memory(self, user_id: int):
        """Clear conversation memory for a user"""
        if user_id in self.memories:
            self.memories[user_id].clear()
            logger.info(f"Cleared conversation memory for user {user_id}")
    
    def _format_portfolio_data(self, portfolio_context: Dict[str, Any]) -> str:
        """Format portfolio data for prompt"""
        holdings = portfolio_context.get('holdings', [])
        top_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)[:15]
        
        holdings_str = "\n".join([
            f"- {h.get('ticker', 'Unknown')}: ${h.get('value', 0):,.2f} ({h.get('allocation', 0):.1f}%) - Sector: {h.get('sector', 'N/A')}" 
            for h in top_holdings
        ])
        
        total_value = portfolio_context.get('total_value', 0)
        daily_change = portfolio_context.get('daily_change_pct', 0)
        risk_metrics = portfolio_context.get('risk_metrics', {})
        
        return f"""PORTFOLIO METRICS:
- Total Value: ${total_value:,.2f}
- Daily Change: {daily_change:+.2f}%
- Number of Holdings: {len(holdings)}
- Beta: {risk_metrics.get('beta', 'N/A')}
- Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A')}
- Volatility: {risk_metrics.get('volatility', 'N/A')}

TOP HOLDINGS:
{holdings_str}

SECTOR ALLOCATION:
{self._format_sectors(portfolio_context.get('sectors', {}))}"""
    
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
    
    def _get_historical_context(self, user_id: int, current_portfolio: Dict[str, Any]) -> str:
        """Get historical context from vector store"""
        try:
            # Search for similar past portfolios
            query = f"Portfolio with {len(current_portfolio.get('holdings', []))} holdings, value ${current_portfolio.get('total_value', 0):,.0f}"
            similar_docs = self.vector_store.search_similar_portfolios(
                query=query,
                user_id=user_id,
                k=3
            )
            
            if not similar_docs:
                return ""
            
            context_parts = ["HISTORICAL CONTEXT (Previous Portfolio States):"]
            for i, doc in enumerate(similar_docs[:2], 1):
                timestamp = doc.metadata.get('timestamp', 'Unknown')
                context_parts.append(f"\n{i}. Snapshot from {timestamp}:")
                context_parts.append(doc.page_content[:300] + "...")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Failed to retrieve historical context: {e}")
            return ""
    
    def _fallback_response(self, error_msg: str = "") -> Dict[str, Any]:
        """Fallback response when AI fails"""
        return {
            "summary": "AI analysis temporarily unavailable. Please try again.",
            "risks": [
                {
                    "description": "Service experiencing technical difficulties",
                    "severity": "Medium",
                    "impact": "Unable to provide AI insights"
                }
            ],
            "opportunities": [],
            "recommendations": [
                {
                    "priority": 1,
                    "action": "Retry analysis in a moment",
                    "rationale": "Temporary service interruption",
                    "expected_impact": "Access to AI insights"
                }
            ],
            "sentiment": "Neutral",
            "score": 50,
            "error": error_msg
        }


# Global instance
_langchain_service_instance: Optional[LangChainAIService] = None


def get_langchain_service() -> LangChainAIService:
    """Get or create singleton LangChain AI service instance"""
    global _langchain_service_instance
    if _langchain_service_instance is None:
        _langchain_service_instance = LangChainAIService()
    return _langchain_service_instance
