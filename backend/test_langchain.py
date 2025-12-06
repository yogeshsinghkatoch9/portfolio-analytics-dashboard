"""
Test script for LangChain integration
Verifies all components are working correctly
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from langchain_config import get_langchain_config
        print("✓ langchain_config imported")
        
        from output_models import PortfolioAnalysis, QuickInsight, ChatResponse
        print("✓ output_models imported")
        
        from vector_store_manager import get_vector_store
        print("✓ vector_store_manager imported")
        
        from langchain_service import get_langchain_service
        print("✓ langchain_service imported")
        
        from portfolio_rag import get_portfolio_rag
        print("✓ portfolio_rag imported")
        
        from portfolio_tools import get_portfolio_tools
        print("✓ portfolio_tools imported")
        
        from portfolio_agent import get_portfolio_agent
        print("✓ portfolio_agent imported")
        
        print("\n✅ All imports successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}\n")
        return False


def test_configuration():
    """Test configuration setup"""
    print("Testing configuration...")
    
    try:
        from langchain_config import get_langchain_config
        
        config = get_langchain_config()
        print(f"✓ Config initialized")
        print(f"  - API Key configured: {config.is_configured()}")
        print(f"  - Model: {config.model}")
        print(f"  - Temperature: {config.temperature}")
        print(f"  - Embedding model: {config.embedding_model}")
        
        if config.is_configured():
            llm = config.get_llm()
            print(f"✓ LLM instance created: {type(llm).__name__}")
            
            embeddings = config.get_embeddings()
            print(f"✓ Embeddings instance created: {type(embeddings).__name__}")
        else:
            print("⚠️  OpenAI API key not configured - some features will be unavailable")
        
        print("\n✅ Configuration test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_output_models():
    """Test Pydantic output models"""
    print("Testing output models...")
    
    try:
        from output_models import PortfolioAnalysis, RiskItem, Opportunity, Recommendation
        
        # Test creating a valid analysis
        analysis = PortfolioAnalysis(
            summary="Test portfolio with good diversification across multiple sectors including technology, healthcare, and finance. Overall risk profile is moderate.",
            risks=[
                RiskItem(
                    description="High tech concentration",
                    severity="High",
                    impact="Vulnerable to tech sector downturns"
                )
            ],
            opportunities=[
                Opportunity(
                    description="Underweight in healthcare",
                    potential_benefit="Better diversification",
                    action_required="Allocate 10% to healthcare"
                )
            ],
            recommendations=[
                Recommendation(
                    priority=1,
                    action="Reduce tech allocation",
                    rationale="Too concentrated",
                    expected_impact="Lower volatility"
                ),
                Recommendation(
                    priority=2,
                    action="Add healthcare exposure",
                    rationale="Improve diversification",
                    expected_impact="Better risk-adjusted returns"
                )
            ],
            sentiment="Neutral",
            score=75
        )
        
        print(f"✓ PortfolioAnalysis model created")
        print(f"  - Summary: {analysis.summary[:50]}...")
        print(f"  - Risks: {len(analysis.risks)}")
        print(f"  - Score: {analysis.score}")
        
        # Test validation
        try:
            invalid = PortfolioAnalysis(
                summary="Too short",  # Should fail min_length
                risks=[],  # Should fail min_items
                opportunities=[],
                recommendations=[],
                sentiment="Invalid",  # Should fail enum
                score=150  # Should fail max value
            )
            print("❌ Validation should have failed!")
            return False
        except Exception:
            print("✓ Validation working correctly")
        
        print("\n✅ Output models test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Output models test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test vector store initialization"""
    print("Testing vector store...")
    
    try:
        from vector_store_manager import get_vector_store
        
        vector_store = get_vector_store()
        print(f"✓ Vector store initialized")
        print(f"  - Persist directory: {vector_store.persist_directory}")
        print(f"  - Collection name: {vector_store.config.collection_name}")
        
        # Test adding a sample snapshot
        sample_portfolio = {
            "total_value": 100000,
            "holdings": [
                {"ticker": "AAPL", "value": 15000, "allocation": 15, "sector": "Technology"},
                {"ticker": "MSFT", "value": 12000, "allocation": 12, "sector": "Technology"}
            ],
            "sectors": {"Technology": 27, "Healthcare": 20, "Finance": 15},
            "risk_metrics": {"beta": 1.1, "sharpe_ratio": 1.5}
        }
        
        doc_id = vector_store.add_portfolio_snapshot(
            user_id=999,  # Test user
            portfolio_data=sample_portfolio,
            analysis={"summary": "Test analysis"}
        )
        
        print(f"✓ Added test snapshot: {doc_id}")
        
        # Test search
        results = vector_store.search_similar_portfolios(
            query="Technology portfolio",
            user_id=999,
            k=1
        )
        
        print(f"✓ Search returned {len(results)} results")
        
        # Cleanup
        vector_store.delete_user_data(999)
        print(f"✓ Cleaned up test data")
        
        print("\n✅ Vector store test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Vector store test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_services():
    """Test service initialization"""
    print("Testing services...")
    
    try:
        from langchain_service import get_langchain_service
        from portfolio_rag import get_portfolio_rag
        from portfolio_agent import get_portfolio_agent
        
        lc_service = get_langchain_service()
        print(f"✓ LangChain service initialized")
        print(f"  - Available: {lc_service.is_available()}")
        
        rag_service = get_portfolio_rag()
        print(f"✓ RAG service initialized")
        print(f"  - Available: {rag_service.is_available()}")
        
        agent = get_portfolio_agent()
        print(f"✓ Agent initialized")
        print(f"  - Available: {agent.is_available()}")
        
        if agent.is_available():
            capabilities = agent.get_capabilities()
            print(f"  - Tools: {len(capabilities['tools'])}")
        
        print("\n✅ Services test passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Services test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("LangChain Integration Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_configuration()))
    results.append(("Output Models", test_output_models()))
    results.append(("Vector Store", test_vector_store()))
    results.append(("Services", test_services()))
    
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:20} {status}")
    
    print()
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! LangChain integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
