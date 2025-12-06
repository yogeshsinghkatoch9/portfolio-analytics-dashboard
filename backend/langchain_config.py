"""
LangChain Configuration Module
Handles initialization and configuration for LangChain components
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import logging

logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Vector store configuration
VECTOR_STORE_DIR = os.getenv("VECTOR_STORE_DIR", "./data/vector_store")
COLLECTION_NAME = "portfolio_history"


class LangChainConfig:
    """Central configuration for LangChain components"""
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
        self.embedding_model = EMBEDDING_MODEL
        self.vector_store_dir = VECTOR_STORE_DIR
        self.collection_name = COLLECTION_NAME
        
    def is_configured(self) -> bool:
        """Check if LangChain is properly configured"""
        return self.api_key is not None
    
    def get_llm(self, temperature: Optional[float] = None) -> ChatOpenAI:
        """
        Get configured LLM instance
        
        Args:
            temperature: Override default temperature
            
        Returns:
            ChatOpenAI instance
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key not configured")
        
        return ChatOpenAI(
            model=self.model,
            temperature=temperature or self.temperature,
            api_key=self.api_key
        )
    
    def get_embeddings(self) -> OpenAIEmbeddings:
        """
        Get configured embeddings instance
        
        Returns:
            OpenAIEmbeddings instance
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key not configured")
        
        return OpenAIEmbeddings(
            model=self.embedding_model,
            api_key=self.api_key
        )
    
    def get_conversation_memory(
        self, 
        memory_type: str = "buffer",
        max_token_limit: int = 2000
    ) -> ConversationBufferMemory:
        """
        Get configured conversation memory
        
        Args:
            memory_type: Type of memory ("buffer" or "summary")
            max_token_limit: Maximum tokens for summary memory
            
        Returns:
            Conversation memory instance
        """
        if memory_type == "summary":
            return ConversationSummaryMemory(
                llm=self.get_llm(temperature=0.3),
                max_token_limit=max_token_limit,
                return_messages=True
            )
        else:
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
    
    def get_portfolio_analysis_prompt(self) -> ChatPromptTemplate:
        """
        Get prompt template for portfolio analysis
        
        Returns:
            ChatPromptTemplate for portfolio analysis
        """
        system_template = """You are an expert portfolio analyst and financial advisor.
Your goal is to provide professional, actionable investment insights suitable for both 
individual investors and financial professionals.

Analyze the portfolio data provided and give specific, quantitative recommendations.
Focus on:
1. Risk assessment and concentration issues
2. Sector diversification opportunities
3. Performance optimization strategies
4. Market sentiment and timing considerations

Be direct, specific, and prioritize actionable insights."""

        human_template = """PORTFOLIO ANALYSIS REQUEST

{portfolio_data}

USER QUERY: {user_query}

Provide a comprehensive analysis with specific recommendations."""

        return ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", human_template)
        ])
    
    def get_chat_prompt(self) -> ChatPromptTemplate:
        """
        Get prompt template for conversational chat
        
        Returns:
            ChatPromptTemplate with message history
        """
        system_template = """You are a helpful financial advisor assistant.
You have access to the user's portfolio data and can answer questions about their investments.

Portfolio Context:
{portfolio_context}

Answer questions conversationally but professionally. Provide specific insights when possible."""

        return ChatPromptTemplate.from_messages([
            ("system", system_template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])


# Global configuration instance
_config_instance: Optional[LangChainConfig] = None


def get_langchain_config() -> LangChainConfig:
    """Get or create singleton LangChain configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = LangChainConfig()
        logger.info("LangChain configuration initialized")
    return _config_instance
