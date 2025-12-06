# Frontend Integration Instructions

## Quick Start - Add LangChain to Your Dashboard

### Step 1: Add JavaScript File

The `langchain-ui.js` file is already created. Just add it to your `index.html`:

```html
<!-- Add before closing </body> tag -->
<script src="langchain-ui.js"></script>
```

### Step 2: Add UI Components

Copy the components from `langchain-components.html` into your `index.html`.

**Where to add:**
- Find your existing AI section (or create a new section in the main content area)
- Replace or enhance with the new LangChain components

**What you get:**
1. **Floating Chat Button** - Bottom right corner, opens AI assistant
2. **Enhanced AI Analysis Panel** - Shows structured insights with priority/severity
3. **Historical Query Interface** - Ask questions about past performance
4. **AI/Standard Toggle** - Switch between LangChain and regular AI

### Step 3: Update API Configuration

Make sure your `API_URL` variable points to your backend:

```javascript
const API_URL = 'http://localhost:8000';  // or your backend URL
```

### Step 4: Test

1. Start your backend server
2. Load the dashboard
3. You should see:
   - Floating purple chat button (bottom right)
   - "Use Enhanced AI" button in AI section
   - Historical query panel

---

## Features Overview

### 1. **Enhanced AI Analysis** ⭐
Click "Use Enhanced AI" to get LangChain-powered analysis with:
- Structured risks (with severity levels)
- Opportunities (with actionable  steps)
- Prioritized recommendations
- Portfolio score and sentiment

### 2. **AI Chat Assistant** 💬
Click the floating chat button to:
- Ask questions about your portfolio
- Get AI responses with memory
- See suggested follow-up questions

**Example questions:**
- "What's my largest holding?"
- "Should I rebalance?"
- "How risky is my portfolio?"

### 3. **Historical Queries** 🔍
Use the Portfolio History panel to:
- Ask about past performance
- Find patterns in historical data
- Compare current vs. past allocation

**Quick buttons:**
- Tech allocation changes
- Highest value period
- Similar risk periods

---

## Customization

### Colors

The LangChain UI uses these Tailwind classes:
- Primary: `purple-600`
- Accent: `blue-600`
- Chat bubbles: `purple-600` (user), `gray-100` (AI)

Change in `langchain-ui.js` and `langchain-components.html`.

### API Endpoints

All endpoints are in `langchain-ui.js`:
- `/api/ai/langchain/analyze` - Enhanced analysis
- `/api/ai/langchain/chat` - Chat with memory
- `/api/ai/rag/query` - Historical queries

### User ID

The system uses `localStorage` to get user ID:
```javascript
const user = JSON.parse(localStorage.getItem('user') || '{}');
const userId = user.id;
```

Make sure you're storing user data after login!

---

## Full Integration Example

Here's how to integrate into your existing dashboard:

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <!-- Your existing dashboard content -->
    <div id="dashboard">
        <!-- ... existing content ... -->
    </div>

    <!-- ADD THIS: LangChain Features -->
    <div class="max-w-7xl mx-auto px-4 py-6">
        <!-- Copy AI Analysis Panel from langchain-components.html -->
        <!-- Copy Historical Query Panel from langchain-components.html -->
    </div>

    <!-- ADD THIS: Floating Chat Button -->
    <!-- Copy from langchain-components.html -->

    <!-- Your existing scripts -->
    <script src="auth.js"></script>
    
    <!-- ADD THIS: LangChain Scripts -->
    <script src="langchain-ui.js"></script>
    <script>
        // Configure API URL
        const API_URL = 'http://localhost:8000';
        
        // When portfolio loads, trigger LangChain analysis
        window.addEventListener('portfolioLoaded', async (event) => {
            await loadLangChainAnalysis(event.detail);
        });
    </script>
</body>
</html>
```

---

## Triggering Analysis

### Auto-trigger on Portfolio Load

```javascript
// Dispatch custom event when portfolio data is ready
const event = new CustomEvent('portfolioLoaded', { 
    detail: portfolioData 
});
window.dispatchEvent(event);
```

### Manual Trigger

```javascript
// Call directly
await loadLangChainAnalysis(portfolioData);
```

### On Button Click

```javascript
document.getElementById('analyzeBtn').addEventListener('click', async () => {
    await loadLangChainAnalysis(window.portfolioData);
});
```

---

## Troubleshooting

### Chat not opening
- Check console for errors
- Verify `aiChat` is defined: `console.log(window.aiChat)`
- Make sure `langchain-ui.js` loaded after DOM

### Analysis not loading
- Check API_URL is correct
- Verify user_id is being sent
- Check browser console for API errors
- Confirm backend is running

### No historical data
- RAG needs stored snapshots
- First analysis creates snapshot
- Run analysis a few times to build history

---

## Next Steps

1. **Copy components** from `langchain-components.html` to `index.html`
2. **Add script tag** for `langchain-ui.js`
3. **Test chat** - click floating button
4. **Test analysis** - click "Use Enhanced AI"
5. **Try RAG queries** - ask about portfolio history

**That's it!** Your dashboard now has advanced LangChain AI features. 🎉
