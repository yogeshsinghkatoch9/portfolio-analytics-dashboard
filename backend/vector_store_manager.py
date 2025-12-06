"""
Vector Store Manager for Portfolio History
Manages ChromaDB for storing and retrieving portfolio snapshots
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_config import get_langchain_config
import logging

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages vector storage for portfolio history and analysis"""
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize vector store manager
        
        Args:
            persist_directory: Directory to persist vector store data
        """
        self.config = get_langchain_config()
        self.persist_directory = persist_directory or self.config.vector_store_dir
        
        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embeddings
        self.embeddings = self.config.get_embeddings()
        
        # Initialize vector store
        self.vector_store = None
        self._initialize_vector_store()
        
        logger.info(f"Vector store initialized at {self.persist_directory}")
    
    def _initialize_vector_store(self):
        """Initialize or load existing vector store"""
        try:
            self.vector_store = Chroma(
                client=self.client,
                collection_name=self.config.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise
    
    def add_portfolio_snapshot(
        self,
        user_id: int,
        portfolio_data: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a portfolio snapshot to the vector store
        
        Args:
            user_id: User ID
            portfolio_data: Portfolio data including holdings, metrics
            analysis: Optional AI analysis results
            
        Returns:
            Document ID
        """
        try:
            # Create document content
            content = self._create_snapshot_content(portfolio_data, analysis)
            
            # Create metadata
            metadata = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "total_value": portfolio_data.get("total_value", 0),
                "num_holdings": len(portfolio_data.get("holdings", [])),
                "snapshot_type": "portfolio_analysis"
            }
            
            # Add sector information if available
            if "sectors" in portfolio_data:
                top_sector = max(
                    portfolio_data["sectors"].items(),
                    key=lambda x: x[1],
                    default=("Unknown", 0)
                )
                metadata["top_sector"] = top_sector[0]
                metadata["top_sector_allocation"] = top_sector[1]
            
            # Create document
            document = Document(
                page_content=content,
                metadata=metadata
            )
            
            # Add to vector store
            ids = self.vector_store.add_documents([document])
            
            logger.info(f"Added portfolio snapshot for user {user_id}: {ids[0]}")
            return ids[0]
            
        except Exception as e:
            logger.error(f"Error adding portfolio snapshot: {e}")
            raise
    
    def _create_snapshot_content(
        self,
        portfolio_data: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create searchable content from portfolio data
        
        Args:
            portfolio_data: Portfolio data
            analysis: Optional analysis results
            
        Returns:
            Formatted content string
        """
        content_parts = []
        
        # Portfolio summary
        content_parts.append(f"Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}")
        content_parts.append(f"Number of Holdings: {len(portfolio_data.get('holdings', []))}")
        
        # Holdings information
        holdings = portfolio_data.get('holdings', [])
        if holdings:
            top_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)[:5]
            content_parts.append("\nTop Holdings:")
            for h in top_holdings:
                content_parts.append(
                    f"- {h.get('ticker', 'Unknown')}: ${h.get('value', 0):,.2f} "
                    f"({h.get('allocation', 0):.1f}%) - {h.get('sector', 'N/A')}"
                )
        
        # Sector allocation
        sectors = portfolio_data.get('sectors', {})
        if sectors:
            content_parts.append("\nSector Allocation:")
            sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
            for sector, allocation in sorted_sectors:
                content_parts.append(f"- {sector}: {allocation:.1f}%")
        
        # Risk metrics
        risk_metrics = portfolio_data.get('risk_metrics', {})
        if risk_metrics:
            content_parts.append("\nRisk Metrics:")
            for metric, value in risk_metrics.items():
                content_parts.append(f"- {metric}: {value}")
        
        # Analysis summary if available
        if analysis:
            content_parts.append("\nAI Analysis Summary:")
            content_parts.append(analysis.get('summary', 'No summary available'))
            
            if 'risks' in analysis:
                content_parts.append("\nIdentified Risks:")
                for risk in analysis['risks'][:3]:
                    if isinstance(risk, dict):
                        content_parts.append(f"- {risk.get('description', risk)}")
                    else:
                        content_parts.append(f"- {risk}")
        
        return "\n".join(content_parts)
    
    def search_similar_portfolios(
        self,
        query: str,
        user_id: Optional[int] = None,
        k: int = 5
    ) -> List[Document]:
        """
        Search for similar portfolio snapshots
        
        Args:
            query: Search query
            user_id: Optional user ID filter
            k: Number of results to return
            
        Returns:
            List of similar documents
        """
        try:
            # Build filter
            filter_dict = {}
            if user_id is not None:
                filter_dict["user_id"] = user_id
            
            # Perform similarity search
            if filter_dict:
                results = self.vector_store.similarity_search(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=k)
            
            logger.info(f"Found {len(results)} similar portfolios for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching portfolios: {e}")
            return []
    
    def get_user_history(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Document]:
        """
        Get portfolio history for a specific user
        
        Args:
            user_id: User ID
            limit: Maximum number of snapshots to return
            
        Returns:
            List of portfolio snapshots
        """
        try:
            # Query with user filter
            results = self.vector_store.get(
                where={"user_id": user_id},
                limit=limit
            )
            
            # Convert to documents
            documents = []
            if results and 'documents' in results:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if 'metadatas' in results else {}
                    documents.append(Document(
                        page_content=doc,
                        metadata=metadata
                    ))
            
            logger.info(f"Retrieved {len(documents)} snapshots for user {user_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving user history: {e}")
            return []
    
    def delete_user_data(self, user_id: int) -> int:
        """
        Delete all portfolio data for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of documents deleted
        """
        try:
            # Get collection
            collection = self.client.get_collection(self.config.collection_name)
            
            # Delete with filter
            collection.delete(where={"user_id": user_id})
            
            logger.info(f"Deleted portfolio data for user {user_id}")
            return 1  # ChromaDB doesn't return count
            
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            return 0
    
    def reset_store(self):
        """Reset the entire vector store (use with caution!)"""
        try:
            self.client.reset()
            self._initialize_vector_store()
            logger.warning("Vector store has been reset")
        except Exception as e:
            logger.error(f"Error resetting vector store: {e}")
            raise


# Global instance
_vector_store_instance: Optional[VectorStoreManager] = None


def get_vector_store() -> VectorStoreManager:
    """Get or create singleton vector store instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreManager()
    return _vector_store_instance
