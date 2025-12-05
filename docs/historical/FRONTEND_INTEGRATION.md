"""
Frontend Integration Guide - Phase 2
JavaScript functions and examples for integrating live market data
and smart file import into the HTML dashboard
"""

# =============================================================================
# PHASE 2 FRONTEND INTEGRATION - JavaScript Code Snippets
# =============================================================================

# Add these functions to your frontend JavaScript (in index.html <script> section)

# 1. SMART FILE IMPORT FUNCTION
function smartImportFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Show loading state
    showLoadingSpinner('Processing file...');
    
    fetch('http://localhost:8000/api/v2/import/smart', {
        method: 'POST',
        body: formData,
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingSpinner();
        
        if (data.success) {
            // Display import metadata
            console.log('File format detected:', data.metadata.format);
            console.log('Auto-mapped columns:', data.metadata.auto_mapped_columns);
            console.log('Holdings imported:', data.metadata.total_holdings);
            
            // Show warnings if any
            if (data.warnings.length > 0) {
                showWarnings(data.warnings);
            }
            
            // Process holdings data
            processHoldingsData(data.holdings);
            
            // Enrich with live data
            enrichWithLiveData(data.holdings);
        } else {
            showError('Import failed: ' + data.errors.join(', '));
        }
    })
    .catch(error => {
        hideLoadingSpinner();
        showError('Error: ' + error.message);
    });
}

# 2. ENRICH PORTFOLIO WITH LIVE DATA
function enrichPortfolioWithLiveData(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showLoadingSpinner('Fetching live market data...');
    
    fetch('http://localhost:8000/api/v2/portfolio/enrich-live-data', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingSpinner();
        
        if (data.success) {
            // Display portfolio with live prices
            displayLivePortfolio(data.portfolio);
            
            // Display summary
            displayLiveSummary(data.summary);
            
            // Display market movers
            displayMarketMovers(data.market_movers);
            
            // Show last update time
            showUpdateTime(data.timestamp);
        } else {
            showError('Failed to enrich portfolio');
        }
    })
    .catch(error => showError('Error: ' + error.message));
}

# 3. GET LIVE STOCK QUOTE
function getStockQuote(ticker) {
    return fetch(`http://localhost:8000/api/v2/market/quote/${ticker}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                return data;
            } else {
                console.error('Quote fetch failed:', data.error);
                return null;
            }
        })
        .catch(error => {
            console.error('Error fetching quote:', error);
            return null;
        });
}

# 4. GET BATCH QUOTES FOR MULTIPLE TICKERS
function getStockQuotes(tickers) {
    return fetch('http://localhost:8000/api/v2/market/quotes/batch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tickers: tickers })
    })
    .then(response => response.json())
    .then(data => data.quotes)
    .catch(error => {
        console.error('Error fetching batch quotes:', error);
        return {};
    });
}

# 5. DISPLAY LIVE PORTFOLIO TABLE
function displayLivePortfolio(holdings) {
    const tableBody = document.getElementById('live-portfolio-table');
    tableBody.innerHTML = ''; // Clear existing rows
    
    holdings.forEach(holding => {
        const row = document.createElement('tr');
        
        // Determine color based on gain/loss
        const gainColor = holding.live_gain_loss_pct >= 0 ? '#10b981' : '#ef4444';
        
        row.innerHTML = `
            <td class="px-4 py-2">${holding.ticker}</td>
            <td class="px-4 py-2">${holding.company_name}</td>
            <td class="px-4 py-2">${holding.quantity}</td>
            <td class="px-4 py-2 font-semibold">$${holding.live_price.toFixed(2)}</td>
            <td class="px-4 py-2">$${holding.live_value.toFixed(2)}</td>
            <td class="px-4 py-2" style="color: ${gainColor}">
                $${holding.live_gain_loss.toFixed(2)} 
                (${holding.live_gain_loss_pct.toFixed(2)}%)
            </td>
            <td class="px-4 py-2 text-sm">${holding.sector}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

# 6. DISPLAY MARKET MOVERS
function displayMarketMovers(movers) {
    // Display gainers
    const gainersContainer = document.getElementById('gainers-list');
    gainersContainer.innerHTML = '';
    
    movers.gainers.forEach(gainer => {
        const card = document.createElement('div');
        card.className = 'bg-green-50 border-l-4 border-green-500 p-4 mb-2';
        card.innerHTML = `
            <div class="flex justify-between">
                <div>
                    <h4 class="font-semibold text-green-900">${gainer.ticker}</h4>
                    <p class="text-sm text-green-700">${gainer.company_name}</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-green-600">+${gainer.live_change_pct.toFixed(2)}%</p>
                    <p class="text-sm text-green-600">$${gainer.live_price.toFixed(2)}</p>
                </div>
            </div>
        `;
        gainersContainer.appendChild(card);
    });
    
    // Display losers
    const losersContainer = document.getElementById('losers-list');
    losersContainer.innerHTML = '';
    
    movers.losers.forEach(loser => {
        const card = document.createElement('div');
        card.className = 'bg-red-50 border-l-4 border-red-500 p-4 mb-2';
        card.innerHTML = `
            <div class="flex justify-between">
                <div>
                    <h4 class="font-semibold text-red-900">${loser.ticker}</h4>
                    <p class="text-sm text-red-700">${loser.company_name}</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-red-600">${loser.live_change_pct.toFixed(2)}%</p>
                    <p class="text-sm text-red-600">$${loser.live_price.toFixed(2)}</p>
                </div>
            </div>
        `;
        losersContainer.appendChild(card);
    });
}

# 7. TICKER SEARCH WITH AUTOCOMPLETE
function searchTicker(query) {
    if (query.length < 1) {
        return Promise.resolve([]);
    }
    
    return fetch(`http://localhost:8000/api/v2/market/search/${query}`)
        .then(response => response.json())
        .then(data => data.results || [])
        .catch(error => {
            console.error('Search error:', error);
            return [];
        });
}

# 8. DISPLAY TICKER DETAILS
function showTickerDetails(ticker) {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    
    // Show loading
    modal.innerHTML = '<div class="bg-white p-8 rounded-lg"><p>Loading...</p></div>';
    document.body.appendChild(modal);
    
    // Fetch ticker analysis
    fetch(`http://localhost:8000/api/v2/market/ticker/${ticker}/analysis`)
        .then(response => response.json())
        .then(data => {
            modal.innerHTML = `
                <div class="bg-white p-8 rounded-lg max-w-2xl max-h-96 overflow-y-auto">
                    <div class="flex justify-between items-start">
                        <div>
                            <h2 class="text-2xl font-bold">${data.company_name}</h2>
                            <p class="text-gray-500">${data.symbol}</p>
                        </div>
                        <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                                class="text-gray-500 hover:text-gray-700">✕</button>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4 mt-6">
                        <div class="border-l-2 border-blue-500 pl-4">
                            <p class="text-gray-500 text-sm">Price</p>
                            <p class="text-2xl font-bold">$${data.current_price.toFixed(2)}</p>
                        </div>
                        <div class="border-l-2 border-blue-500 pl-4">
                            <p class="text-gray-500 text-sm">Sector</p>
                            <p class="text-lg font-semibold">${data.sector}</p>
                        </div>
                        <div class="border-l-2 border-green-500 pl-4">
                            <p class="text-gray-500 text-sm">P/E Ratio</p>
                            <p class="text-lg font-semibold">${data.pe_ratio.toFixed(2)}</p>
                        </div>
                        <div class="border-l-2 border-green-500 pl-4">
                            <p class="text-gray-500 text-sm">Dividend Yield</p>
                            <p class="text-lg font-semibold">${(data.dividend_yield * 100).toFixed(2)}%</p>
                        </div>
                        <div class="border-l-2 border-purple-500 pl-4">
                            <p class="text-gray-500 text-sm">52W High</p>
                            <p class="text-lg font-semibold">$${data['52w_high'].toFixed(2)}</p>
                        </div>
                        <div class="border-l-2 border-purple-500 pl-4">
                            <p class="text-gray-500 text-sm">52W Low</p>
                            <p class="text-lg font-semibold">$${data['52w_low'].toFixed(2)}</p>
                        </div>
                    </div>
                    
                    <div class="mt-6 p-4 bg-gray-50 rounded">
                        <p class="text-sm font-semibold mb-2">Recommendation: <span class="text-blue-600">${data.recommendation.toUpperCase()}</span></p>
                        <p class="text-sm">Target Price: $${data.target_price.toFixed(2)}</p>
                        <p class="text-sm">Analyst Count: ${data.analyst_count}</p>
                        <p class="text-sm">1Y Return: ${data.year_return_pct.toFixed(2)}%</p>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            modal.innerHTML = `<div class="bg-white p-8 rounded-lg"><p>Error: ${error.message}</p></div>`;
        });
}

# 9. DISPLAY HISTORICAL CHART
function displayHistoricalChart(ticker, period = '1y', interval = '1d') {
    fetch(`http://localhost:8000/api/v2/market/historical/${ticker}?period=${period}&interval=${interval}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Format data for Chart.js
                const dates = data.data.map(d => d.Date.split('T')[0]);
                const closes = data.data.map(d => d.Close);
                const ma20 = data.data.map(d => d.MA_20);
                const ma50 = data.data.map(d => d.MA_50);
                
                // Create Chart.js chart
                const ctx = document.getElementById('priceChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [
                            {
                                label: 'Price',
                                data: closes,
                                borderColor: '#3b82f6',
                                tension: 0.1,
                                fill: false
                            },
                            {
                                label: '20-Day MA',
                                data: ma20,
                                borderColor: '#f59e0b',
                                borderDash: [5, 5],
                                fill: false
                            },
                            {
                                label: '50-Day MA',
                                data: ma50,
                                borderColor: '#ef4444',
                                borderDash: [10, 5],
                                fill: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: `${ticker} - ${period.toUpperCase()} (${data.data_points} days)`
                            },
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        },
                        scales: {
                            y: {
                                title: {
                                    display: true,
                                    text: 'Price ($)'
                                }
                            }
                        }
                    }
                });
            }
        });
}

# 10. UPDATE QUOTE DISPLAY
function updateQuoteDisplay(ticker, elementId) {
    getStockQuote(ticker).then(quote => {
        if (quote) {
            const element = document.getElementById(elementId);
            const isPositive = quote.change_pct >= 0;
            const color = isPositive ? '#10b981' : '#ef4444';
            const arrow = isPositive ? '↑' : '↓';
            
            element.innerHTML = `
                <div class="text-lg font-semibold">$${quote.price.toFixed(2)}</div>
                <div style="color: ${color}; font-size: 0.875rem;">
                    ${arrow} ${Math.abs(quote.change).toFixed(2)} (${Math.abs(quote.change_pct).toFixed(2)}%)
                </div>
                <div class="text-xs text-gray-500">Vol: ${(quote.volume / 1000000).toFixed(1)}M</div>
            `;
        }
    });
}

# 11. LIVE UPDATE TICKER (Auto-refresh)
function startLiveUpdates(ticker, elementId, interval = 60000) {
    // Update immediately
    updateQuoteDisplay(ticker, elementId);
    
    // Update every interval (default 1 minute)
    return setInterval(() => {
        updateQuoteDisplay(ticker, elementId);
    }, interval);
}

# 12. STOP LIVE UPDATES
function stopLiveUpdates(updateIntervalId) {
    clearInterval(updateIntervalId);
}

# =============================================================================
# HTML INTEGRATION EXAMPLES
# =============================================================================

# In your index.html, add these sections:

# 1. LIVE PORTFOLIO TABLE
<div class="mt-8">
    <h2 class="text-xl font-bold mb-4">Live Portfolio</h2>
    <table class="w-full border-collapse border border-gray-200">
        <thead class="bg-gray-100">
            <tr>
                <th class="border px-4 py-2">Ticker</th>
                <th class="border px-4 py-2">Company</th>
                <th class="border px-4 py-2">Qty</th>
                <th class="border px-4 py-2">Live Price</th>
                <th class="border px-4 py-2">Live Value</th>
                <th class="border px-4 py-2">Gain/Loss</th>
                <th class="border px-4 py-2">Sector</th>
            </tr>
        </thead>
        <tbody id="live-portfolio-table">
            <!-- Populated by displayLivePortfolio() -->
        </tbody>
    </table>
</div>

# 2. MARKET MOVERS SECTION
<div class="grid grid-cols-2 gap-4 mt-8">
    <div>
        <h3 class="text-lg font-bold mb-4 text-green-600">Top Gainers</h3>
        <div id="gainers-list">
            <!-- Populated by displayMarketMovers() -->
        </div>
    </div>
    <div>
        <h3 class="text-lg font-bold mb-4 text-red-600">Top Losers</h3>
        <div id="losers-list">
            <!-- Populated by displayMarketMovers() -->
        </div>
    </div>
</div>

# 3. TICKER SEARCH
<div class="mt-8">
    <input type="text" id="tickerSearch" placeholder="Search stock..."
           class="w-full px-4 py-2 border border-gray-300 rounded"
           onkeyup="searchTickers(this.value)">
    <div id="searchResults" class="mt-2">
        <!-- Search results shown here -->
    </div>
</div>

# 4. PRICE CHART
<div class="mt-8">
    <h2 class="text-xl font-bold mb-4">Price Chart</h2>
    <canvas id="priceChart"></canvas>
</div>

# 5. QUICK QUOTE TICKER
<div class="grid grid-cols-4 gap-4 mt-8">
    <div class="bg-blue-50 p-4 rounded" id="quote-AAPL">Loading...</div>
    <div class="bg-blue-50 p-4 rounded" id="quote-MSFT">Loading...</div>
    <div class="bg-blue-50 p-4 rounded" id="quote-GOOGL">Loading...</div>
    <div class="bg-blue-50 p-4 rounded" id="quote-AMZN">Loading...</div>
</div>

<script>
    // Start live updates for major indices
    startLiveUpdates('AAPL', 'quote-AAPL');
    startLiveUpdates('MSFT', 'quote-MSFT');
    startLiveUpdates('GOOGL', 'quote-GOOGL');
    startLiveUpdates('AMZN', 'quote-AMZN');
</script>
"""
