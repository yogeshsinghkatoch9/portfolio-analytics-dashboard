"""
Portfolio Query Agent
Autonomous agent that can answer complex portfolio questions using tools
"""

import logging
from typing import Dict, Any, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

from langchain_config import get_langchain_config
from portfolio_tools import get_portfolio_tools

logger = logging.getLogger(__name__)


class PortfolioAgent:
    """Autonomous agent for portfolio analysis and queries"""
    
    def __init__(self):
        """Initialize portfolio agent"""
        self.config = get_langchain_config()
        
        try:
            self.llm = self.config.get_llm(temperature=0.2)  # Lower temp for more focused responses
            self.tools = get_portfolio_tools()
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            self.available = False
        
        # Create agent
        if self.available:
            self.agent_executor = self._create_agent()
        
        # Conversation memories per user
        self.memories: Dict[int, ConversationBufferMemory] = {}
        
        logger.info("Portfolio agent initialized")
    
    def _create_agent(self) -> AgentExecutor:
        """Create the ReAct agent"""
        
        # Define the prompt template
        template = """You are a helpful financial advisor AI assistant with access to portfolio analysis tools.
Answer the user's question about their portfolio using the available tools when needed.

You have access to the following tools:
{tools}

Tool Names: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Previous conversation:
{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)
        
        # Create the agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        return agent_executor
    
    def is_available(self) -> bool:
        """Check if agent is available"""
        return self.available
    
    def query(
        self,
        question: str,
        user_id: int,
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the agent with a question
        
        Args:
            question: User's question
            user_id: User ID for context
            portfolio_context: Optional current portfolio data
            
        Returns:
            Dictionary with answer and reasoning steps
        """
        if not self.is_available():
            return {
                "answer": "Agent unavailable - OpenAI API key not configured",
                "steps": [],
                "error": "Service unavailable"
            }
        
        try:
            # Get or create memory for user
            if user_id not in self.memories:
                self.memories[user_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=False
                )
            
            memory = self.memories[user_id]
            
            # Add portfolio context to question if provided
            enhanced_question = question
            if portfolio_context:
                context_str = f"\nCurrent Portfolio Context: User {user_id}, Value: ${portfolio_context.get('total_value', 0):,.2f}, Holdings: {len(portfolio_context.get('holdings', []))}"
                enhanced_question = question + context_str
            
            # Execute agent
            result = self.agent_executor.invoke({
                "input": enhanced_question,
                "chat_history": memory.load_memory_variables({}).get("chat_history", "")
            })
            
            # Save to memory
            memory.save_context(
                {"input": question},
                {"output": result["output"]}
            )
            
            # Extract intermediate steps
            steps = []
            if "intermediate_steps" in result:
                for action, observation in result["intermediate_steps"]:
                    steps.append({
                        "tool": action.tool,
                        "input": action.tool_input,
                        "output": observation
                    })
            
            logger.info(f"Agent query completed for user {user_id}: {question[:50]}...")
            
            return {
                "answer": result["output"],
                "steps": steps,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Agent query error: {e}")
            return {
                "answer": f"I encountered an error processing your question: {str(e)}",
                "steps": [],
                "error": str(e),
                "success": False
            }
    
    def clear_memory(self, user_id: int):
        """Clear conversation memory for a user"""
        if user_id in self.memories:
            self.memories[user_id].clear()
            logger.info(f"Cleared agent memory for user {user_id}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities description"""
        return {
            "description": "Autonomous portfolio analysis agent",
            "tools": [
                {
                    "name": "query_portfolio",
                    "description": "Query portfolio holdings, sectors, metrics, and performance"
                },
                {
                    "name": "fetch_market_data",
                    "description": "Fetch real-time market data for stocks"
                },
                {
                    "name": "calculate_metrics",
                    "description": "Calculate portfolio risk and performance metrics"
                },
                {
                    "name": "search_history",
                    "description": "Search historical portfolio data for patterns"
                }
            ],
            "example_queries": [
                "What are my top 5 holdings?",
                "How has my technology sector allocation changed over time?",
                "Calculate my portfolio's Sharpe ratio",
                "What's the current price of AAPL?",
                "Show me periods when my portfolio had similar risk levels"
            ]
        }


# Global instance
_agent_instance: Optional[PortfolioAgent] = None


def get_portfolio_agent() -> PortfolioAgent:
    """Get or create singleton agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = PortfolioAgent()
    return _agent_instance
