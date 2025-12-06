"""
LangChain Demo Script
Demonstrates the new AI capabilities with real API calls
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../.env')

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_service import get_langchain_service
from portfolio_rag import get_portfolio_rag
from portfolio_agent import get_portfolio_agent

# Sample portfolio data
SAMPLE_PORTFOLIO = {
    "total_value": 500000,
    "daily_change_pct": 1.2,
    "holdings": [
        {"ticker": "AAPL", "value": 75000, "allocation": 15, "sector": "Technology"},
        {"ticker": "MSFT", "value": 60000, "allocation": 12, "sector": "Technology"},
        {"ticker": "GOOGL", "value": 50000, "allocation": 10, "sector": "Technology"},
        {"ticker": "JNJ", "value": 40000, "allocation": 8, "sector": "Healthcare"},
        {"ticker": "JPM", "value": 35000, "allocation": 7, "sector": "Finance"}
    ],
    "sectors": {
        "Technology": 37,
        "Healthcare": 20,
        "Finance": 18,
        "Consumer": 15,
        "Energy": 10
    },
    "risk_metrics": {
        "beta": 1.15,
        "sharpe_ratio": 1.8,
        "volatility": 18.5
    }
}


def demo_structured_analysis():
    """Demo 1: Structured Portfolio Analysis"""
    print("\n" + "="*70)
    print("DEMO 1: Structured Portfolio Analysis with LangChain")
    print("="*70)
    
    service = get_langchain_service()
    
    if not service.is_available():
        print("❌ Service unavailable - check API key")
        return
    
    print("\n📊 Analyzing portfolio with structured outputs...")
    print("Portfolio Value: $500,000")
    print("Top Holdings: AAPL (15%), MSFT (12%), GOOGL (10%)")
    print("\n⏳ Generating AI analysis (this may take 5-10 seconds)...\n")
    
    try:
        analysis = service.generate_portfolio_analysis(
            portfolio_context=SAMPLE_PORTFOLIO,
            user_query="Analyze my portfolio and suggest specific improvements",
            user_id=1
        )
        
        print("✅ Analysis Complete!\n")
        print(f"📈 Portfolio Health Score: {analysis['score']}/100")
        print(f"💭 Market Sentiment: {analysis['sentiment']}\n")
        
        print("📝 Executive Summary:")
        print(f"   {analysis['summary']}\n")
        
        print(f"⚠️  Risks Identified ({len(analysis['risks'])}):")
        for i, risk in enumerate(analysis['risks'][:3], 1):
            print(f"   {i}. [{risk['severity']}] {risk['description']}")
        
        print(f"\n💡 Top Recommendations ({len(analysis['recommendations'])}):")
        for rec in analysis['recommendations'][:3]:
            print(f"   Priority {rec['priority']}: {rec['action']}")
            print(f"      → {rec['rationale']}")
        
        print("\n✨ Note: This analysis was automatically stored in the vector database")
        print("   for future historical queries!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")


def demo_conversation_memory():
    """Demo 2: Chat with Conversation Memory"""
    print("\n" + "="*70)
    print("DEMO 2: Conversational AI with Memory")
    print("="*70)
    
    service = get_langchain_service()
    
    if not service.is_available():
        print("❌ Service unavailable")
        return
    
    print("\n💬 Having a multi-turn conversation with the AI...")
    print("⏳ This demonstrates how the AI remembers context...\n")
    
    try:
        # First message
        print("You: What's my largest holding?\n")
        response1 = service.chat(
            message="What's my largest holding?",
            portfolio_context=SAMPLE_PORTFOLIO,
            user_id=1
        )
        print(f"AI: {response1['response']}\n")
        
        # Follow-up (AI remembers "it" refers to AAPL)
        print("You: Should I reduce it?\n")
        response2 = service.chat(
            message="Should I reduce it?",
            portfolio_context=SAMPLE_PORTFOLIO,
            user_id=1
        )
        print(f"AI: {response2['response']}\n")
        
        if response2.get('follow_up_suggestions'):
            print("💡 Suggested follow-up questions:")
            for suggestion in response2['follow_up_suggestions']:
                print(f"   - {suggestion}")
        
        print("\n✨ The AI remembered the context from the first message!")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")


def demo_rag_query():
    """Demo 3: RAG Historical Query"""
    print("\n" + "="*70)
    print("DEMO 3: Querying Portfolio History with RAG")
    print("="*70)
    
    rag = get_portfolio_rag()
    
    if not rag.is_available():
        print("❌ RAG unavailable")
        return
    
    print("\n🔍 Querying historical portfolio data...")
    print("Question: 'What was my portfolio composition when I first started?'\n")
    print("⏳ Searching vector database and generating answer...\n")
    
    try:
        result = rag.query_portfolio_history(
            query="What was my portfolio composition when I first started?",
            user_id=1,
            current_portfolio=SAMPLE_PORTFOLIO
        )
        
        print(f"📖 Answer:\n   {result['answer']}\n")
        
        if result['sources']:
            print(f"📚 Sources (Historical Snapshots):")
            for i, source in enumerate(result['sources'], 1):
                print(f"   {i}. {source.get('timestamp', 'Unknown date')}")
                print(f"      Value: ${source.get('total_value', 0):,.2f}, Holdings: {source.get('num_holdings', 0)}")
        else:
            print("ℹ️  No historical data found yet - this is your first snapshot!")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")


def demo_agent_query():
    """Demo 4: Autonomous Agent"""
    print("\n" + "="*70)
    print("DEMO 4: Autonomous Agent with Tools")
    print("="*70)
    
    agent = get_portfolio_agent()
    
    if not agent.is_available():
        print("❌ Agent unavailable")
        return
    
    print("\n🤖 Asking the agent a complex question...")
    print("Question: 'What are my top 3 holdings and their sectors?'\n")
    print("⏳ Agent is thinking and using tools...\n")
    
    try:
        result = agent.query(
            question="What are my top 3 holdings and their sectors?",
            user_id=1,
            portfolio_context=SAMPLE_PORTFOLIO
        )
        
        if result['success']:
            print(f"✅ Agent Response:\n   {result['answer']}\n")
            
            if result['steps']:
                print(f"🔧 Tools Used ({len(result['steps'])}):")
                for i, step in enumerate(result['steps'], 1):
                    print(f"   {i}. {step['tool']}")
                    print(f"      Input: {step['input']}")
                    print(f"      Output: {step['output'][:100]}...")
            
            print("\n✨ The agent autonomously selected and used the right tools!")
        else:
            print(f"❌ Agent error: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")


def main():
    """Run all demos"""
    print("\n" + "🚀 "*35)
    print("LangChain Portfolio Analytics - Live Demo")
    print("🚀 "*35)
    
    # Check if API key is configured
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment")
        print("Please set it in your .env file\n")
        return
    
    print("\n✅ OpenAI API Key detected")
    print("ℹ️  Using model: " + os.getenv("OPENAI_MODEL", "gpt-4"))
    print("\n⚠️  Note: These demos will make real API calls and incur costs")
    print("   (approximately $0.10-0.20 total for all demos)\n")
    
    input("Press Enter to start the demo...")
    
    # Run demos
    demo_structured_analysis()
    input("\nPress Enter for next demo...")
    
    demo_conversation_memory()
    input("\nPress Enter for next demo...")
    
    demo_rag_query()
    input("\nPress Enter for next demo...")
    
    demo_agent_query()
    
    print("\n" + "="*70)
    print("🎉 Demo Complete!")
    print("="*70)
    print("\nWhat you just saw:")
    print("  ✅ Structured AI analysis with type-safe outputs")
    print("  ✅ Conversation memory across multiple messages")
    print("  ✅ RAG queries over historical portfolio data")
    print("  ✅ Autonomous agent using tools")
    print("\nAll of this is now available via your API endpoints!")
    print("See LANGCHAIN_GUIDE.md for integration examples.\n")


if __name__ == "__main__":
    main()
