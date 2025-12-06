"""
RAG (Retrieval-Augmented Generation) Implementation for Portfolio Analytics
Enables context-aware analysis using historical portfolio data
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from langchain_config import get_langchain_config
from vector_store_manager import get_vector_store

logger = logging.getLogger(__name__)


class PortfolioRAG:
    """RAG system for portfolio historical analysis"""
    
    def __init__(self):
        """Initialize RAG system"""
        self.config = get_langchain_config()
        self.vector_store = get_vector_store()
        
        try:
            self.llm = self.config.get_llm()
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize RAG LLM: {e}")
            self.available = False
        
        logger.info("Portfolio RAG system initialized")
    
    def is_available(self) -> bool:
        """Check if RAG is available"""
        return self.available
    
    def query_portfolio_history(
        self,
        query: str,
        user_id: int,
        current_portfolio: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Query portfolio history using RAG
        
        Args:
            query: User's question about portfolio history
            user_id: User ID
            current_portfolio: Optional current portfolio data for context
            
        Returns:
            Dictionary with answer and sources
        """
        if not self.is_available():
            return {
                "answer": "RAG system unavailable - OpenAI API key not configured",
                "sources": []
            }
        
        try:
            # Create retriever
            retriever = self.vector_store.vector_store.as_retriever(
                search_kwargs={
                    "k": 5,
                    "filter": {"user_id": user_id}
                }
            )
            
            # Create prompt template
            template = """You are a financial advisor analyzing a client's portfolio history.
Use the following historical portfolio snapshots to answer the question.
If you don't know the answer based on the provided context, say so.

Current Portfolio Context (if available):
{current_context}

Historical Portfolio Snapshots:
{context}

Question: {question}

Provide a detailed answer with specific references to the historical data.
Include dates and specific metrics when available.

Answer:"""

            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question", "current_context"]
            )
            
            # Create current context string
            current_context = ""
            if current_portfolio:
                current_context = f"""Total Value: ${current_portfolio.get('total_value', 0):,.2f}
Holdings: {len(current_portfolio.get('holdings', []))}
Top Sector: {self._get_top_sector(current_portfolio.get('sectors', {}))}"""
            
            # Create QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt}
            )
            
            # Execute query
            result = qa_chain.invoke({
                "query": query,
                "current_context": current_context
            })
            
            # Extract sources
            sources = []
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    sources.append({
                        "timestamp": doc.metadata.get("timestamp", "Unknown"),
                        "total_value": doc.metadata.get("total_value", 0),
                        "num_holdings": doc.metadata.get("num_holdings", 0)
                    })
            
            logger.info(f"RAG query executed for user {user_id}: {query[:50]}...")
            
            return {
                "answer": result["result"],
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": []
            }
    
    def compare_with_history(
        self,
        user_id: int,
        current_portfolio: Dict[str, Any],
        comparison_type: str = "performance"
    ) -> Dict[str, Any]:
        """
        Compare current portfolio with historical snapshots
        
        Args:
            user_id: User ID
            current_portfolio: Current portfolio data
            comparison_type: Type of comparison (performance, allocation, risk)
            
        Returns:
            Comparison analysis
        """
        if not self.is_available():
            return {
                "summary": "RAG comparison unavailable",
                "changes": [],
                "insights": []
            }
        
        try:
            # Get historical snapshots
            history = self.vector_store.get_user_history(user_id, limit=5)
            
            if not history:
                return {
                    "summary": "No historical data available for comparison",
                    "changes": [],
                    "insights": ["This is your first portfolio snapshot"]
                }
            
            # Create comparison prompt
            current_data = self._format_portfolio_summary(current_portfolio)
            historical_data = "\n\n".join([
                f"Snapshot {i+1} ({doc.metadata.get('timestamp', 'Unknown')}):\n{doc.page_content[:200]}"
                for i, doc in enumerate(history[:3])
            ])
            
            prompt = f"""Compare the current portfolio with historical snapshots.
Focus on: {comparison_type}

CURRENT PORTFOLIO:
{current_data}

HISTORICAL SNAPSHOTS:
{historical_data}

Provide:
1. A brief summary of key changes
2. List of specific changes (3-5 items)
3. Insights about trends or patterns (2-3 items)

Format as JSON with keys: summary, changes (array), insights (array)"""

            response = self.llm.invoke(prompt)
            
            # Parse response
            import json
            try:
                result = json.loads(response.content)
            except:
                # Fallback if not valid JSON
                result = {
                    "summary": response.content[:200],
                    "changes": ["See detailed analysis above"],
                    "insights": []
                }
            
            logger.info(f"Historical comparison completed for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Historical comparison error: {e}")
            return {
                "summary": "Error performing comparison",
                "changes": [],
                "insights": []
            }
    
    def find_similar_periods(
        self,
        user_id: int,
        current_portfolio: Dict[str, Any],
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find historical periods similar to current portfolio state
        
        Args:
            user_id: User ID
            current_portfolio: Current portfolio data
            k: Number of similar periods to find
            
        Returns:
            List of similar periods with metadata
        """
        try:
            # Create query from current portfolio
            query = self._format_portfolio_summary(current_portfolio)
            
            # Search for similar snapshots
            similar_docs = self.vector_store.search_similar_portfolios(
                query=query,
                user_id=user_id,
                k=k
            )
            
            # Format results
            results = []
            for doc in similar_docs:
                results.append({
                    "timestamp": doc.metadata.get("timestamp", "Unknown"),
                    "total_value": doc.metadata.get("total_value", 0),
                    "num_holdings": doc.metadata.get("num_holdings", 0),
                    "top_sector": doc.metadata.get("top_sector", "Unknown"),
                    "similarity_score": "High"  # ChromaDB doesn't return scores by default
                })
            
            logger.info(f"Found {len(results)} similar periods for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar periods: {e}")
            return []
    
    def _format_portfolio_summary(self, portfolio: Dict[str, Any]) -> str:
        """Format portfolio data for prompts"""
        return f"""Total Value: ${portfolio.get('total_value', 0):,.2f}
Number of Holdings: {len(portfolio.get('holdings', []))}
Top Sector: {self._get_top_sector(portfolio.get('sectors', {}))}
Daily Change: {portfolio.get('daily_change_pct', 0):+.2f}%
Beta: {portfolio.get('risk_metrics', {}).get('beta', 'N/A')}"""
    
    def _get_top_sector(self, sectors: Dict[str, float]) -> str:
        """Get top sector by allocation"""
        if not sectors:
            return "Diversified"
        return max(sectors, key=sectors.get)


# Global instance
_rag_instance: Optional[PortfolioRAG] = None


def get_portfolio_rag() -> PortfolioRAG:
    """Get or create singleton RAG instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = PortfolioRAG()
    return _rag_instance
