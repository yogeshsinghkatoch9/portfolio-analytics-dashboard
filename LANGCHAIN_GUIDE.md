# LangChain Integration - Quick Start Guide

## 🚀 What You Got

Your portfolio analytics dashboard now has **supercharged AI capabilities** powered by LangChain:

### ✨ New Features

1. **Structured AI Responses** - Type-safe, validated outputs every time
2. **Conversation Memory** - AI remembers your chat history
3. **Historical Analysis (RAG)** - Query your portfolio history naturally
4. **Autonomous Agent** - AI that can use tools to answer complex questions
5. **7 New API Endpoints** - Enhanced functionality

---

## 📋 Prerequisites

**Required:**
- OpenAI API Key (set in `.env` as `OPENAI_API_KEY`)

**Optional:**
- Customize model: `OPENAI_MODEL=gpt-4` (default)
- Adjust temperature: `OPENAI_TEMPERATURE=0.7` (default)

---

## 🎯 Quick Examples

### Example 1: Get Structured Portfolio Analysis

**Endpoint:** `POST /api/ai/langchain/analyze`

```python
import requests

response = requests.post(
    "http://localhost:8000/api/ai/langchain/analyze",
    json={
        "user_id": 1,
        "portfolio_context": {
            "total_value": 500000,
            "holdings": [
                {"ticker": "AAPL", "value": 75000, "allocation": 15, "sector": "Technology"},
                {"ticker": "MSFT", "value": 60000, "allocation": 12, "sector": "Technology"}
            ],
            "sectors": {"Technology": 27, "Healthcare": 20},
            "risk_metrics": {"beta": 1.1, "sharpe_ratio": 1.5}
        }
    }
)

analysis = response.json()
print(f"Score: {analysis['score']}/100")
print(f"Sentiment: {analysis['sentiment']}")
print(f"Top Risk: {analysis['risks'][0]['description']}")
```

### Example 2: Chat with Memory

**Endpoint:** `POST /api/ai/langchain/chat`

```python
# First message
response1 = requests.post(
    "http://localhost:8000/api/ai/langchain/chat",
    json={
        "user_id": 1,
        "message": "What's my largest holding?",
        "portfolio_context": {...}
    }
)

# Follow-up (AI remembers context!)
response2 = requests.post(
    "http://localhost:8000/api/ai/langchain/chat",
    json={
        "user_id": 1,
        "message": "Should I reduce it?",  # AI knows "it" refers to largest holding
        "portfolio_context": {...}
    }
)
```

### Example 3: Query Portfolio History

**Endpoint:** `POST /api/ai/rag/query`

```python
response = requests.post(
    "http://localhost:8000/api/ai/rag/query",
    json={
        "user_id": 1,
        "query": "How has my tech allocation changed over the past 6 months?",
        "current_portfolio": {...}
    }
)

print(response.json()['answer'])
# Output: "Based on historical snapshots, your technology allocation 
#          has increased from 35% to 45% over the past 6 months..."
```

### Example 4: Use the Autonomous Agent

**Endpoint:** `POST /api/ai/agent/query`

```python
response = requests.post(
    "http://localhost:8000/api/ai/agent/query",
    json={
        "user_id": 1,
        "question": "What are my top 3 holdings and how are they performing today?",
        "portfolio_context": {...}
    }
)

result = response.json()
print(result['answer'])
print(f"Agent used {len(result['steps'])} tools")
```

---

## 🔧 Available Endpoints

| Endpoint | Purpose | Requires user_id |
|----------|---------|------------------|
| `/api/ai/langchain/analyze` | Structured portfolio analysis | ✅ |
| `/api/ai/langchain/chat` | Chat with memory | ✅ |
| `/api/ai/rag/query` | Query portfolio history | ✅ |
| `/api/ai/rag/compare` | Compare with history | ✅ |
| `/api/ai/agent/query` | Autonomous agent queries | ✅ |
| `/api/ai/agent/capabilities` | Get agent info | ❌ |
| `/api/ai/memory/{user_id}` | Clear user memory | ✅ |

---

## 🛠️ Agent Capabilities

The autonomous agent has 4 tools:

1. **query_portfolio** - Get holdings, sectors, metrics, performance
2. **fetch_market_data** - Real-time stock quotes and info
3. **calculate_metrics** - Sharpe ratio, beta, volatility, diversification
4. **search_history** - Find historical patterns

**Example Questions:**
- "What are my top 5 holdings?"
- "Calculate my portfolio's Sharpe ratio"
- "What's the current price of AAPL?"
- "Find periods when my portfolio had similar risk levels"
- "How has my healthcare sector allocation changed?"

---

## 📊 Data Storage

### Vector Store (ChromaDB)
- **Location:** `./data/vector_store/`
- **Purpose:** Stores portfolio snapshots for RAG
- **Auto-created:** Yes, on first use
- **Per-user:** Yes, filtered by user_id

### What Gets Stored
Every time you call `/api/ai/langchain/analyze`, the system automatically stores:
- Portfolio snapshot (holdings, sectors, metrics)
- AI analysis results
- Timestamp and metadata

This enables historical queries like:
- "How has my portfolio changed?"
- "When was my allocation most diversified?"
- "Show me similar periods"

---

## 🧪 Testing

Run the test suite:

```bash
cd backend
python test_langchain.py
```

**Expected Results:**
- ✅ Imports: All modules load correctly
- ✅ Configuration: Settings initialized
- ✅ Output Models: Pydantic validation works
- ⚠️  Vector Store: Requires OpenAI API key
- ⚠️  Services: Requires OpenAI API key

---

## 🔐 Security Notes

1. **API Key:** Never commit your OpenAI API key to git
2. **User Isolation:** All data is filtered by user_id
3. **Memory Management:** Clear user memory with DELETE endpoint
4. **Data Cleanup:** Use `vector_store.delete_user_data(user_id)` to remove user data

---

## 💡 Pro Tips

### 1. Use Structured Analysis for Reliability
The LangChain endpoint (`/api/ai/langchain/analyze`) is more reliable than the original because it uses Pydantic validation.

### 2. Clear Memory When Needed
If conversations get off-track:
```python
requests.delete(f"http://localhost:8000/api/ai/memory/{user_id}")
```

### 3. Monitor Token Usage
LangChain features use more tokens due to:
- Structured output instructions
- Historical context retrieval
- Agent reasoning steps

### 4. Batch Historical Queries
RAG queries are slower (vector search + LLM). Use for:
- ✅ Historical analysis
- ✅ Pattern finding
- ❌ Real-time dashboards (use regular analysis instead)

---

## 🐛 Troubleshooting

### "OpenAI API key not configured"
**Solution:** Add `OPENAI_API_KEY=sk-proj-...` to your `.env` file

### "user_id required"
**Solution:** LangChain endpoints need `user_id` for memory and history

### "Vector store unavailable"
**Solution:** Ensure `./data/vector_store/` directory is writable

### Agent gives wrong answers
**Solution:** Tools are currently returning mock data. Connect them to your real database/APIs.

---

## 📈 Performance Expectations

| Feature | Response Time | Token Usage |
|---------|---------------|-------------|
| Structured Analysis | ~3-5s | ~1500 tokens |
| Chat (with memory) | ~2-3s | ~800 tokens |
| RAG Query | ~5-8s | ~2000 tokens |
| Agent Query | ~5-10s | ~1500-3000 tokens |

*Times assume GPT-4. Use GPT-3.5-turbo for faster/cheaper responses.*

---

## 🎓 Learning Resources

- [LangChain Docs](https://python.langchain.com/docs/get_started/introduction)
- [Pydantic Models](https://docs.pydantic.dev/)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [ReAct Agents](https://python.langchain.com/docs/modules/agents/agent_types/react)

---

## ✅ Next Steps

1. **Set your OpenAI API key** in `.env`
2. **Test the endpoints** using the examples above
3. **Connect real data** to the agent tools
4. **Build frontend UI** for the new features
5. **Monitor costs** and optimize as needed

---

## 📞 Support

If you encounter issues:
1. Check the test suite: `python test_langchain.py`
2. Review logs for error messages
3. Verify API key is set correctly
4. Ensure all dependencies are installed

Happy analyzing! 🚀
