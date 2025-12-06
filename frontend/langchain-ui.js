// LangChain AI Integration Module
// Enhanced AI features with conversation memory, RAG, and autonomous agents

// Configuration
const LANGCHAIN_ENABLED = true;
let currentUserId = null;

// Get user ID from session
function getCurrentUserId() {
    if (currentUserId) return currentUserId;

    // Try to get from localStorage or session
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    currentUserId = user.id || 1; // Default to 1 for demo
    return currentUserId;
}

// ============================================================================
// ENHANCED AI ANALYSIS (with LangChain)
// ============================================================================

async function loadLangChainAnalysis(portfolioData) {
    const userId = getCurrentUserId();
    const aiLoading = document.getElementById('aiLoading');
    const aiContent = document.getElementById('aiInsightsContent');
    const aiError = document.getElementById('aiError');

    // Show loading
    aiLoading?.classList.remove('hidden');
    aiContent?.classList.add('hidden');
    aiError?.classList.add('hidden');

    try {
        // Prepare portfolio context
        const portfolioContext = {
            holdings: portfolioData.holdings || [],
            total_value: portfolioData.totalValue || 0,
            daily_change_pct: portfolioData.dailyChange || 0,
            risk_metrics: {
                beta: portfolioData.beta,
                sharpe_ratio: portfolioData.sharpeRatio,
                volatility: portfolioData.volatility
            },
            sectors: portfolioData.sectors || {}
        };

        // Use LangChain endpoint for structured analysis
        const response = await fetch(`${API_URL}/api/ai/langchain/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                user_id: userId,
                portfolio_context: portfolioContext,
                query: "Provide comprehensive analysis with specific, actionable recommendations"
            })
        });

        if (!response.ok) {
            throw new Error(`AI analysis failed: ${response.statusText}`);
        }

        const analysis = await response.json();

        // Display the enhanced analysis
        displayLangChainAnalysis(analysis);

        // Store for later use
        window.currentAnalysis = analysis;

    } catch (error) {
        console.error('LangChain Analysis Error:', error);

        // Show error state
        aiLoading?.classList.add('hidden');
        aiError?.classList.remove('hidden');

        const errorMsg = document.getElementById('aiErrorMessage');
        if (errorMsg) {
            errorMsg.textContent = error.message || 'AI analysis unavailable';
        }
    }
}

function displayLangChainAnalysis(analysis) {
    const aiLoading = document.getElementById('aiLoading');
    const aiContent = document.getElementById('aiInsightsContent');

    // Hide loading, show content
    aiLoading?.classList.add('hidden');
    aiContent?.classList.remove('hidden');

    // Set score and sentiment
    const scoreElement = document.getElementById('portfolioScore');
    const sentimentElement = document.getElementById('portfolioSentiment');

    if (scoreElement && analysis.score) {
        scoreElement.textContent = analysis.score;
        scoreElement.className = `text-3xl font-bold ${getScoreColor(analysis.score)}`;
    }

    if (sentimentElement && analysis.sentiment) {
        sentimentElement.textContent = analysis.sentiment;
        sentimentElement.className = `text-2xl font-bold ${getSentimentColor(analysis.sentiment)}`;
    }

    // Set summary
    const summaryElement = document.getElementById('aiSummary');
    if (summaryElement && analysis.summary) {
        summaryElement.textContent = analysis.summary;
    }

    // Enhanced: Display structured risks with severity
    const risksElement = document.getElementById('aiRisks');
    if (risksElement && analysis.risks) {
        risksElement.innerHTML = analysis.risks.map(risk => {
            const riskData = typeof risk === 'object' ? risk : { description: risk, severity: 'Medium' };
            const severityColor = getSeverityColor(riskData.severity);

            return `
                <li class="flex items-start p-2 rounded hover:bg-gray-50">
                    <svg class="w-5 h-5 ${severityColor} mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                    <div class="flex-1">
                        <span class="text-sm font-medium ${severityColor}">${riskData.severity}</span>
                        <p class="text-gray-700">${riskData.description}</p>
                        ${riskData.impact ? `<p class="text-sm text-gray-500 mt-1">Impact: ${riskData.impact}</p>` : ''}
                    </div>
                </li>
            `;
        }).join('');
    }

    // Enhanced: Display opportunities with actions
    const opportunitiesElement = document.getElementById('aiOpportunities');
    if (opportunitiesElement && analysis.opportunities) {
        opportunitiesElement.innerHTML = analysis.opportunities.map(opp => {
            const oppData = typeof opp === 'object' ? opp : { description: opp };

            return `
                <li class="flex items-start p-2 rounded hover:bg-gray-50">
                    <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    <div class="flex-1">
                        <p class="text-gray-700">${oppData.description}</p>
                        ${oppData.potential_benefit ? `<p class="text-sm text-green-600 mt-1">✓ ${oppData.potential_benefit}</p>` : ''}
                        ${oppData.action_required ? `<p class="text-sm text-gray-600 mt-1">→ ${oppData.action_required}</p>` : ''}
                    </div>
                </li>
            `;
        }).join('');
    }

    // Enhanced: Prioritized recommendations
    const recommendationsElement = document.getElementById('aiRecommendations');
    if (recommendationsElement && analysis.recommendations) {
        recommendationsElement.innerHTML = analysis.recommendations.map((rec, index) => {
            const recData = typeof rec === 'object' ? rec : { action: rec, priority: index + 1 };
            const priorityBadge = getPriorityBadge(recData.priority);

            return `
                <li class="text-gray-700 py-2 border-b border-gray-100 last:border-0">
                    <div class="flex items-start">
                        ${priorityBadge}
                        <div class="flex-1 ml-3">
                            <p class="font-medium text-gray-900">${recData.action}</p>
                            ${recData.rationale ? `<p class="text-sm text-gray-600 mt-1">Why: ${recData.rationale}</p>` : ''}
                            ${recData.expected_impact ? `<p class="text-sm text-green-600 mt-1">Impact: ${recData.expected_impact}</p>` : ''}
                        </div>
                    </div>
                </li>
            `;
        }).join('');
    }
}

// ============================================================================
// AI CHAT INTERFACE (with Memory)
// ============================================================================

class AIChatInterface {
    constructor() {
        this.messages = [];
        this.isProcessing = false;
        this.initializeUI();
    }

    initializeUI() {
        const chatBtn = document.getElementById('openAIChat');
        if (chatBtn) {
            chatBtn.addEventListener('click', () => this.open());
        }
    }

    open() {
        // Create chat modal if doesn't exist
        if (!document.getElementById('aiChatModal')) {
            this.createModal();
        }
        document.getElementById('aiChatModal').classList.remove('hidden');
        this.loadHistory();
    }

    close() {
        document.getElementById('aiChatModal')?.classList.add('hidden');
    }

    createModal() {
        const modal = document.createElement('div');
        modal.id = 'aiChatModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 hidden flex items-center justify-center';
        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl h-3/4 flex flex-col">
                <!-- Header -->
                <div class="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-4 rounded-t-lg flex justify-between items-center">
                    <div>
                        <h3 class="text-xl font-bold">AI Portfolio Assistant</h3>
                        <p class="text-sm opacity-90">Powered by LangChain</p>
                    </div>
                    <button onclick="aiChat.close()" class="text-white hover:text-gray-200">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>

                <!-- Messages -->
                <div id="chatMessages" class="flex-1 overflow-y-auto p-4 space-y-4">
                    <div class="text-center text-gray-500 text-sm">
                        Start a conversation about your portfolio
                    </div>
                </div>

                <!-- Input -->
                <div class="border-t p-4">
                    <div class="flex space-x-2">
                        <input
                            type="text"
                            id="chatInput"
                            class="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                            placeholder="Ask about your portfolio..."
                            onkeypress="if(event.key==='Enter') aiChat.send()"
                        />
                        <button
                            onclick="aiChat.send()"
                            class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50"
                            id="chatSendBtn"
                        >
                            Send
                        </button>
                    </div>
                    <div class="mt-2 text-xs text-gray-500">
                        Tip: Try "What's my largest holding?" or "Should I rebalance?"
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    loadHistory() {
        // Load last few messages from memory
        const messagesDiv = document.getElementById('chatMessages');
        if (this.messages.length > 0) {
            messagesDiv.innerHTML = this.messages.map(msg => this.formatMessage(msg)).join('');
        }
    }

    async send() {
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('chatSendBtn');
        const message = input.value.trim();

        if (!message || this.isProcessing) return;

        this.isProcessing = true;
        sendBtn.disabled = true;
        input.value = '';

        // Add user message
        this.addMessage({ role: 'user', content: message });

        // Show typing indicator
        this.showTyping();

        try {
            const userId = getCurrentUserId();
            const portfolioData = window.portfolioData || {};

            const response = await fetch(`${API_URL}/api/ai/langchain/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAuthToken()}`
                },
                body: JSON.stringify({
                    user_id: userId,
                    message: message,
                    portfolio_context: {
                        total_value: portfolioData.totalValue || 0,
                        holdings: portfolioData.holdings || [],
                        sectors: portfolioData.sectors || {},
                        daily_change_pct: portfolioData.dailyChange || 0
                    }
                })
            });

            if (!response.ok) throw new Error('Chat failed');

            const data = await response.json();

            // Remove typing indicator
            document.getElementById('typingIndicator')?.remove();

            // Add AI response
            this.addMessage({
                role: 'assistant',
                content: data.response,
                suggestions: data.follow_up_suggestions
            });

        } catch (error) {
            console.error('Chat error:', error);
            document.getElementById('typingIndicator')?.remove();
            this.addMessage({
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.'
            });
        } finally {
            this.isProcessing = false;
            sendBtn.disabled = false;
        }
    }

    addMessage(msg) {
        this.messages.push(msg);
        const messagesDiv = document.getElementById('chatMessages');
        messagesDiv.innerHTML += this.formatMessage(msg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    formatMessage(msg) {
        if (msg.role === 'user') {
            return `
                <div class="flex justify-end">
                    <div class="bg-purple-600 text-white rounded-lg px-4 py-2 max-w-md">
                        ${msg.content}
                    </div>
                </div>
            `;
        } else {
            const suggestions = msg.suggestions ? `
                <div class="mt-2 space-y-1">
                    ${msg.suggestions.map(s => `
                        <button 
                            onclick="document.getElementById('chatInput').value='${s}'" 
                            class="text-xs text-purple-600 hover:underline block"
                        >
                            💡 ${s}
                        </button>
                    `).join('')}
                </div>
            ` : '';

            return `
                <div class="flex justify-start">
                    <div class="bg-gray-100 text-gray-900 rounded-lg px-4 py-2 max-w-md">
                        ${msg.content}
                        ${suggestions}
                    </div>
                </div>
            `;
        }
    }

    showTyping() {
        const messagesDiv = document.getElementById('chatMessages');
        const typing = document.createElement('div');
        typing.id = 'typingIndicator';
        typing.className = 'flex justify-start';
        typing.innerHTML = `
            <div class="bg-gray-100 text-gray-900 rounded-lg px-4 py-2">
                <div class="flex space-x-1">
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                </div>
            </div>
        `;
        messagesDiv.appendChild(typing);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

// Initialize chat
const aiChat = new AIChatInterface();
window.aiChat = aiChat;

// ============================================================================
// RAG HISTORICAL QUERIES
// ============================================================================

async function queryPortfolioHistory(question) {
    const userId = getCurrentUserId();
    const resultsDiv = document.getElementById('ragResults');

    if (resultsDiv) {
        resultsDiv.innerHTML = '<div class="text-center py-4"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto"></div></div>';
    }

    try {
        const response = await fetch(`${API_URL}/api/ai/rag/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                user_id: userId,
                query: question,
                current_portfolio: window.portfolioData
            })
        });

        if (!response.ok) throw new Error('RAG query failed');

        const data = await response.json();

        // Display results
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div class="bg-white rounded-lg p-4 shadow">
                    <h4 class="font-bold text-gray-900 mb-2">Answer:</h4>
                    <p class="text-gray-700 mb-4">${data.answer}</p>
                    ${data.sources && data.sources.length > 0 ? `
                        <h5 class="text-sm font-medium text-gray-600 mb-2">Sources:</h5>
                        <ul class="text-sm text-gray-500 space-y-1">
                            ${data.sources.map(s => `
                                <li>• ${new Date(s.timestamp).toLocaleDateString()} - $${s.total_value?.toLocaleString()}</li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </div>
            `;
        }

    } catch (error) {
        console.error('RAG query error:', error);
        if (resultsDiv) {
            resultsDiv.innerHTML = `<div class="text-red-600">Error: ${error.message}</div>`;
        }
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getScoreColor(score) {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
}

function getSentimentColor(sentiment) {
    const sentimentLower = sentiment?.toLowerCase() || '';
    if (sentimentLower.includes('bull')) return 'text-green-600';
    if (sentimentLower.includes('bear')) return 'text-red-600';
    return 'text-gray-600';
}

function getSeverityColor(severity) {
    const sev = severity?.toLowerCase() || 'medium';
    if (sev === 'high') return 'text-red-500';
    if (sev === 'low') return 'text-yellow-500';
    return 'text-orange-500';
}

function getPriorityBadge(priority) {
    const colors = {
        1: 'bg-red-100 text-red-800',
        2: 'bg-orange-100 text-orange-800',
        3: 'bg-yellow-100 text-yellow-800',
        4: 'bg-blue-100 text-blue-800',
        5: 'bg-gray-100 text-gray-800'
    };
    const color = colors[priority] || colors[3];
    return `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${color}">${priority}</span>`;
}

function getAuthToken() {
    return localStorage.getItem('authToken') || '';
}

// Export functions
window.loadLangChainAnalysis = loadLangChainAnalysis;
window.queryPortfolioHistory = queryPortfolioHistory;
window.getCurrentUserId = getCurrentUserId;
