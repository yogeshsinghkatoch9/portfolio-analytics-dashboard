// AI Integration Module
// Add AI-powered insights to the portfolio dashboard

// Initialize AI features after portfolio data is loaded
async function initializeAIInsights(portfolioData) {
    const aiSection = document.getElementById('aiInsightsSection');
    if (!aiSection) {
        console.warn('AI Insights section not found');
        return;
    }

    // Show the section
    aiSection.classList.remove('hidden');

    // Load AI analysis
    await loadAIAnalysis(portfolioData);
}

async function loadAIAnalysis(portfolioData) {
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

        // Call AI analyze endpoint
        const response = await fetch(`${API_URL}/api/v2/ai/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                portfolio_context: portfolioContext,
                query: "Provide comprehensive analysis with actionable recommendations"
            })
        });

        if (!response.ok) {
            throw new Error(`AI analysis failed: ${response.statusText}`);
        }

        const analysis = await response.json();

        // Display the analysis
        displayAIAnalysis(analysis);

        // Also get quick insight
        await loadQuickInsight(portfolioContext);

    } catch (error) {
        console.error('AI Analysis Error:', error);

        // Show error state
        aiLoading?.classList.add('hidden');
        aiError?.classList.remove('hidden');

        const errorMsg = document.getElementById('aiErrorMessage');
        if (errorMsg) {
            errorMsg.textContent = error.message || 'AI analysis unavailable';
        }
    }
}

async function loadQuickInsight(portfolioContext) {
    try {
        const response = await fetch(`${API_URL}/api/v2/ai/quick-insight`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portfolio_context: portfolioContext })
        });

        if (response.ok) {
            const data = await response.json();
            const insightElement = document.getElementById('quickInsight');
            if (insightElement) {
                insightElement.textContent = `"${data.insight}"`;
            }
        }
    } catch (error) {
        console.error('Quick insight failed:', error);
    }
}

function displayAIAnalysis(analysis) {
    const aiLoading = document.getElementById('aiLoading');
    const aiContent = document.getElementById('aiInsightsContent');

    // Hide loading, show content
    aiLoading?.classList.add('hidden');
    aiContent?.classList.remove('hidden');

    // Set score and sentiment
    const scoreElement = document.getElementById('portfolioScore');
    const sentimentElement = document.getElementById('portfolioSentiment');
    const recCountElement = document.getElementById('recommendationCount');

    if (scoreElement && analysis.score) {
        scoreElement.textContent = analysis.score;
        scoreElement.className = `text-3xl font-bold ${getScoreColor(analysis.score)}`;
    }

    if (sentimentElement && analysis.sentiment) {
        sentimentElement.textContent = analysis.sentiment;
        sentimentElement.className = `text-2xl font-bold ${getSentimentColor(analysis.sentiment)}`;
    }

    if (recCountElement && analysis.recommendations) {
        recCountElement.textContent = analysis.recommendations.length;
    }

    // Set summary
    const summaryElement = document.getElementById('aiSummary');
    if (summaryElement && analysis.summary) {
        summaryElement.textContent = analysis.summary;
    }

    // Set risks
    const risksElement = document.getElementById('aiRisks');
    if (risksElement && analysis.risks) {
        risksElement.innerHTML = analysis.risks.map(risk => `
            <li class="flex items-start">
                <svg class="w-5 h-5 text-red-500 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
                <span class="text-gray-700">${risk}</span>
            </li>
        `).join('');
    }

    // Set opportunities
    const opportunitiesElement = document.getElementById('aiOpportunities');
    if (opportunitiesElement && analysis.opportunities) {
        opportunitiesElement.innerHTML = analysis.opportunities.map(opp => `
            <li class="flex items-start">
                <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span class="text-gray-700">${opp}</span>
            </li>
        `).join('');
    }

    // Set recommendations
    const recommendationsElement = document.getElementById('aiRecommendations');
    if (recommendationsElement && analysis.recommendations) {
        recommendationsElement.innerHTML = analysis.recommendations.map((rec, index) => `
            <li class="text-gray-700 py-1">
                <span class="font-medium text-purple-600">Action ${index + 1}:</span> ${rec}
            </li>
        `).join('');
    }

    // Setup AI tabs
    setupAITabs();
}

function setupAITabs() {
    const tabs = document.querySelectorAll('.ai-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.aiTab;

            // Remove active from all tabs
            tabs.forEach(t => {
                t.classList.remove('text-purple-600', 'border-b-2', 'border-purple-600');
                t.classList.add('text-gray-500');
            });

            // Add active to clicked tab
            tab.classList.remove('text-gray-500');
            tab.classList.add('text-purple-600', 'border-b-2', 'border-purple-600');

            // Hide all content
            document.querySelectorAll('.ai-tab-content').forEach(content => {
                content.classList.add('hidden');
            });

            // Show target content
            const targetContent = document.getElementById(`ai-${targetTab}-content`);
            if (targetContent) {
                targetContent.classList.remove('hidden');
            }
        });
    });
}

function getScoreColor(score) {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
}

function getSentimentColor(sentiment) {
    const sentimentLower = sentiment.toLowerCase();
    if (sentimentLower.includes('bull')) return 'text-green-600';
    if (sentimentLower.includes('bear')) return 'text-red-600';
    return 'text-gray-600';
}

// Refresh AI analysis
document.getElementById('refreshAIBtn')?.addEventListener('click', async () => {
    if (portfolioData) {
        await loadAIAnalysis(portfolioData);
        Toast.success('AI analysis refreshed');
    }
});

// Export for use in main app
window.initializeAIInsights = initializeAIInsights;
