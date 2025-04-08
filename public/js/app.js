// Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyDTVrNzD-YYFnvqakAk1LysPe8jPrpyScc",
  authDomain: "fintech-ash-80b97.firebaseapp.com",
  projectId: "fintech-ash-80b97",
  storageBucket: "fintech-ash-80b97.appspot.com",
  messagingSenderId: "972685478512",
  appId: "1:972685478512:web:34d1aa305be183112702b5",
  measurementId: "G-FHFL400HD3"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const analytics = firebase.analytics();
const db = firebase.firestore();

let currentAnalysisListener = null;

// Ticker List Functionality
const NASDAQ_TICKERS = [
    { symbol: 'AAPL', name: 'Apple Inc.' },
    { symbol: 'MSFT', name: 'Microsoft Corporation' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.' },
    { symbol: 'AMZN', name: 'Amazon.com Inc.' },
    { symbol: 'NVDA', name: 'NVIDIA Corporation' },
    { symbol: 'META', name: 'Meta Platforms Inc.' },
    { symbol: 'TSLA', name: 'Tesla Inc.' },
    { symbol: 'NFLX', name: 'Netflix Inc.' },
    { symbol: 'AMD', name: 'Advanced Micro Devices.' },
    { symbol: 'INTC', name: 'Intel Corporation' },
    // Add more tickers as needed
];

// Update the METRIC_DEFINITIONS to match the exact keys we receive
const METRIC_DEFINITIONS = {
    'Current Price': 'The current market price of the stock.',
    'Market Cap': 'Total value of all outstanding shares of the company.',
    'Forward P/E': 'Forward Price-to-Earnings ratio, comparing current share price to predicted earnings per share.',
    'Trailing P/E': 'Trailing Price-to-Earnings ratio, comparing current share price to historical earnings per share.',
    'Dividend Yield': 'Annual dividend payments as a percentage of the stock price.',
    'Beta': 'Measure of stock\'s volatility compared to the overall market. Beta > 1 means more volatile than market.',
    '52 Week High': 'Highest price of the stock over the past 52 weeks.',
    '52 Week Low': 'Lowest price of the stock over the past 52 weeks.',
    'Volume': 'Number of shares traded during the current session.',
    'Average Volume': 'Average number of shares traded daily.',
    'Return on Equity': 'Net income as a percentage of shareholder equity, measuring profitability.',
    'Profit Margins': 'Net profit as a percentage of revenue, indicating profit efficiency.',
    'Revenue Growth': 'Year-over-year increase in company\'s revenue.',
    'Debt to Equity': 'Total debt relative to equity, measuring financial leverage.',
    'Quick Ratio': 'Liquid assets relative to liabilities, measuring short-term solvency.',
    'Current Ratio': 'Current assets relative to current liabilities, measuring short-term solvency.',
    'SMA50': '50-day Simple Moving Average, average closing price over last 50 trading days.',
    'SMA200': '200-day Simple Moving Average, average closing price over last 200 trading days.',
    'RSI': 'Relative Strength Index, momentum indicator measuring speed and magnitude of price changes.',
    'Volatility': 'Statistical measure of stock price variation over time, annualized.',
    'Industry': 'The business sector in which the company operates.',
    'Full Time Employees': 'Total number of full-time employees in the company.',
    'Recommendation': 'Analyst consensus recommendation for the stock.'
};

// Initialize ticker list
function initializeTickerList() {
    const tickerList = document.getElementById('ticker-list');
    const tickerSearch = document.getElementById('ticker-search');
    const togglePanel = document.querySelector('.toggle-panel');
    const tickerPanel = document.querySelector('.ticker-list-panel');

    // Populate initial list
    renderTickerList(NASDAQ_TICKERS);

    // Search functionality
    tickerSearch.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredTickers = NASDAQ_TICKERS.filter(ticker => 
            ticker.symbol.toLowerCase().includes(searchTerm) || 
            ticker.name.toLowerCase().includes(searchTerm)
        );
        renderTickerList(filteredTickers);
    });

    // Mobile toggle functionality
    togglePanel?.addEventListener('click', () => {
        tickerPanel.classList.toggle('active');
    });

    // Close panel when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && 
            !tickerPanel.contains(e.target) && 
            !togglePanel.contains(e.target)) {
            tickerPanel.classList.remove('active');
        }
    });
}

// Render ticker list
function renderTickerList(tickers) {
    const tickerList = document.getElementById('ticker-list');
    tickerList.innerHTML = tickers.map(ticker => `
        <div class="ticker-item" onclick="selectTicker('${ticker.symbol}')">
            <span class="ticker-symbol">${ticker.symbol}</span>
            <span class="ticker-name">${ticker.name}</span>
        </div>
    `).join('');
}

// Select ticker
function selectTicker(symbol) {
    const tickerInput = document.getElementById('ticker');
    tickerInput.value = symbol;
    
    // Close panel on mobile after selection
    if (window.innerWidth <= 768) {
        document.querySelector('.ticker-list-panel').classList.remove('active');
    }
}

// Initialize ticker list when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTickerList);

// Make selectTicker function available globally
window.selectTicker = selectTicker;

// DOM Elements
const loginBtn = document.getElementById('login-btn');
const headerLogoutBtn = document.getElementById('header-logout-btn');
const authStatus = document.getElementById('auth-status');
const tickerSection = document.getElementById('ticker-section');

// Function to listen for analysis updates
function listenForAnalysisUpdates(documentId) {
    // Clean up any existing listener
    if (currentAnalysisListener) {
        currentAnalysisListener();
    }

    currentAnalysisListener = db.collection('analysis_results')
        .doc(documentId)
        .onSnapshot((doc) => {
            if (doc.exists) {
                const data = doc.data();
                if (data.status === 'completed') {
                    document.getElementById('result-content').innerHTML = formatResults(data.result);
                    document.getElementById('result').classList.add('active');
                    document.getElementById('loading').classList.remove('active');
                    // Clean up the listener
                    currentAnalysisListener();
                    currentAnalysisListener = null;
                } else if (data.status === 'error') {
                    showError(data.error_message || 'Analysis failed');
                    document.getElementById('loading').classList.remove('active');
                    // Clean up the listener
                    currentAnalysisListener();
                    currentAnalysisListener = null;
                }
            }
        }, (error) => {
            console.error('Error listening to analysis updates:', error);
            showError('Error receiving analysis updates');
            document.getElementById('loading').classList.remove('active');
            // Clean up the listener
            currentAnalysisListener();
            currentAnalysisListener = null;
        });
}

// Update auth state change handler
auth.onAuthStateChanged(user => {
    console.log('Auth state changed:', user ? 'User signed in' : 'User signed out');
    const authForm = document.getElementById('auth-form');
    const loginBtn = document.getElementById('login-btn');
    const headerLogoutBtn = document.getElementById('header-logout-btn');
    const tickerSection = document.getElementById('ticker-section');
    const resultSection = document.getElementById('result');
    const loadingSection = document.getElementById('loading');
    const visualizationsSection = document.getElementById('visualizations');
    
    if (user) {
        console.log('User email:', user.email);
        authStatus.textContent = `Signed in as ${user.email}`;
        loginBtn.classList.add('hidden');
        headerLogoutBtn.classList.remove('hidden');
        authForm.classList.add('hidden');
        tickerSection.classList.remove('hidden');
        // Hide the email and password fields
        document.getElementById('email').value = '';
        document.getElementById('password').value = '';
    } else {
        console.log('No user signed in');
        authStatus.textContent = 'Please sign in to analyze stocks';
        loginBtn.classList.remove('hidden');
        headerLogoutBtn.classList.add('hidden');
        authForm.classList.remove('hidden');
        tickerSection.classList.add('hidden');
        
        // Clear analysis results
        if (resultSection) {
            resultSection.classList.remove('active');
            if (resultSection.querySelector('#result-content')) {
                resultSection.querySelector('#result-content').innerHTML = '';
            }
        }
        
        // Clear visualizations
        if (visualizationsSection) {
            visualizationsSection.innerHTML = '';
        }
        
        // Hide loading indicator if visible
        if (loadingSection) {
            loadingSection.classList.remove('active');
        }
        
        // Clean up any existing listener
        if (currentAnalysisListener) {
            currentAnalysisListener();
            currentAnalysisListener = null;
        }
    }
});

loginBtn.onclick = async () => {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (!email || !password) {
        showError('Please enter both email and password');
        return;
    }

    try {
        await auth.signInWithEmailAndPassword(email, password);
    } catch (error) {
        showError(error.message);
    }
};

headerLogoutBtn.onclick = () => auth.signOut();

async function analyzeStock() {
    const ticker = document.getElementById('ticker').value.trim().toUpperCase();
    if (!ticker) return showError('Please enter a ticker symbol');

    const user = firebase.auth().currentUser;
    if (!user) return showError('You must be signed in to analyze stocks.');

    const token = await user.getIdToken();

    document.getElementById('loading').classList.add('active');
    document.getElementById('result').classList.remove('active');
    document.getElementById('error').classList.add('hidden');

    const loadingText = document.querySelector('#loading span');
    loadingText.textContent = 'Starting analysis...';

    try {
        analytics.logEvent('analyze_stock', { ticker });

        const response = await fetch('/api/analyze_stock_endpoint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ ticker })
        });

        const data = await response.json();
        console.log('Response from backend:', data); // Debug log

        if (!response.ok) {
            throw new Error(data.error || 'An error occurred during analysis');
        }

        console.log('Status from response:', data.status); // Debug log
        console.log('Document ID:', data.document_id); // Debug log
        
        if(data.status === 'completed'){ // if the analysis was already completed within the last 24 hours
            console.log('Entering completed branch'); // Debug log
            console.log('Result data:', data.result); // Debug log
            document.getElementById('result-content').innerHTML = formatResults(data.result);
            document.getElementById('result').classList.add('active');
            document.getElementById('loading').classList.remove('active');
        }
        else if(data.status === 'error') {
            throw new Error(data.error_message || 'Analysis failed');
        }
        else {
            console.log('Entering in-progress branch'); // Debug log
            loadingText.textContent = 'Analysis in progress...';
            // Start listening for updates
            listenForAnalysisUpdates(data.document_id);
        }
      
    } catch (error) {
        console.error('Analysis error:', error); // Debug log
        showError(error.message || 'An unexpected error occurred. Please try again.');
        analytics.logEvent('analyze_stock_error', { ticker, error: error.message });
        document.getElementById('loading').classList.remove('active');
    }
}

// Update the getMetricKey function
function getMetricKey(key) {
    // First try direct match
    if (METRIC_DEFINITIONS[key]) {
        return key;
    }
    
    // Try common variations
    const variations = {
        'Market Cap (B)': 'Market Cap',
        'Market Cap (M)': 'Market Cap',
        'Forward PE': 'Forward P/E',
        'Trailing PE': 'Trailing P/E',
        'Dividend Yield (%)': 'Dividend Yield',
        '52-Week High': '52 Week High',
        '52-Week Low': '52 Week Low',
        'Avg Volume': 'Average Volume',
        'ROE': 'Return on Equity',
        'Debt/Equity': 'Debt to Equity',
        'Employees': 'Full Time Employees',
        'Recommendation Key': 'Recommendation'
    };

    return variations[key] || key;
}

// Modify the metric card creation part in formatResults
function formatResults(data) {
    let html = '<div class="results-container">';
    
    // Clear previous visualizations
    document.getElementById('visualizations').innerHTML = '';
    
    // Handle quantitative data
    if (data.quantitative_data) {
        // Create visualizations for financial metrics
        createFinancialVisualizations(data.quantitative_data);
        
        html += `
            <div class="results-section">
                <h3 class="results-section-title">Financial Metrics</h3>
                <div class="metrics-grid">`;
        
        for (const [key, value] of Object.entries(data.quantitative_data)) {
            let metricClass = 'neutral-metric';
            if (typeof value === 'string' && value.includes('%')) {
                const numericValue = parseFloat(value);
                if (numericValue > 0) metricClass = 'positive-metric';
                if (numericValue < 0) metricClass = 'negative-metric';
            }
            
            const metricKey = getMetricKey(key);
            const definition = METRIC_DEFINITIONS[metricKey] || `No definition available for ${key}`;
            
            html += `
                <div class="metric-card" data-tooltip="${definition}">
                    <div class="metric-label">${key}</div>
                    <div class="metric-value ${metricClass}">${value}</div>
                </div>`;
        }
        html += '</div></div>';
    }

    // Handle analysis data
    if (data.analysis) {
        // Data Analysis Section
       /*  if (data.analysis.data_analysis) {
            html += `
                <div class="results-section">
                    <h3 class="results-section-title">Quantitative Analysis</h3>
                    <div class="analysis-content">
                        ${formatAnalysisSection(data.analysis.data_analysis)}
                    </div>
                </div>`;
        } */

        // Trading Strategy Section
        if (data.analysis.trading_strategy) {
            html += `
                <div class="results-section">
                    <h3 class="results-section-title">Trading Strategy</h3>
                    <div class="analysis-content">
                        ${formatStrategySection(data.analysis.trading_strategy)}
                    </div>
                </div>`;
        }

        // Execution Plan Section
        if (data.analysis.execution_plan) {
            html += `
                <div class="results-section">
                    <h3 class="results-section-title">Execution Plan</h3>
                    <div class="analysis-content">
                        ${formatExecutionSection(data.analysis.execution_plan)}
                    </div>
                </div>`;
        }

        // Risk Assessment Section
        if (data.analysis.risk_assessment) {
            html += `
                <div class="results-section">
                    <h3 class="results-section-title">Risk Assessment</h3>
                    <div class="analysis-content">
                        ${formatRiskSection(data.analysis.risk_assessment)}
                    </div>
                </div>`;
        }
    }
    
    html += '</div>';
    return html;
}

// Helper function to format analysis section
function formatAnalysisSection(analysis) {
    let html = '<div class="analysis-grid">';
    
    const sections = {
        'Fundamental Metrics': analysis.fundamental_metrics,
        'Technical Indicators': analysis.technical_indicators,
        'Financial Metrics': analysis.financial_metrics,
        'Risk Metrics': analysis.risk_metrics
    };

    for (const [title, metrics] of Object.entries(sections)) {
        if (metrics) {
            html += `
                <div class="analysis-subsection">
                    <h4 class="subsection-title">${title}</h4>
                    <div class="metrics-list">`;
            
            for (const [key, value] of Object.entries(metrics)) {
                if (value !== null) {
                    const formattedValue = typeof value === 'number' ? 
                        value.toFixed(2) : value;
                    html += `
                        <div class="metric-item">
                            <span class="metric-name">${formatMetricName(key)}</span>
                            <span class="metric-value">${formattedValue}</span>
                        </div>`;
                }
            }
            
            html += '</div></div>';
        }
    }
    
    html += '</div>';
    return html;
}

// Helper function to format strategy section
function formatStrategySection(strategy) {
    if (!strategy.trading_strategy) return 'No trading strategy available';
    
    const ts = strategy.trading_strategy;
    let html = '<div class="strategy-grid">';

    // Technical Analysis
    if (ts.technical_analysis) {
        html += `
            <div class="strategy-subsection">
                <h4>Technical Analysis</h4>
                <div class="metrics-list">`;
        for (const [key, value] of Object.entries(ts.technical_analysis)) {
            if (value !== null) {
                html += `
                    <div class="metric-item">
                        <span class="metric-name">${formatMetricName(key)}</span>
                        <span class="metric-value">${typeof value === 'number' ? value.toFixed(2) : value}</span>
                    </div>`;
            }
        }
        html += '</div></div>';
    }

    // Entry Points
    if (ts.entry_points) {
        html += `
            <div class="strategy-subsection">
                <h4>Entry Points</h4>
                <div class="entry-points">
                    <div class="entry-point">
                        <h5>Primary Entry</h5>
                        <p>Price Range: ${ts.entry_points.primary.price_range}</p>
                        <p>Conditions: ${ts.entry_points.primary.conditions}</p>
                    </div>
                    <div class="entry-point">
                        <h5>Secondary Entry</h5>
                        <p>Price Target: $${ts.entry_points.secondary.price_target}</p>
                        <p>Conditions: ${ts.entry_points.secondary.conditions}</p>
                    </div>
                </div>
            </div>`;
    }

    // Position Sizing
    if (ts.position_sizing) {
        html += `
            <div class="strategy-subsection">
                <h4>Position Sizing</h4>
                <p>Recommended Size: ${ts.position_sizing.recommended_size}</p>
                <div class="entry-breakdown">
                    <h5>Entry Breakdown</h5>
                    <ul>
                        <li>First Entry: ${ts.position_sizing.entry_breakdown.first_entry.percentage}% - ${ts.position_sizing.entry_breakdown.first_entry.conditions}</li>
                        <li>Second Entry: ${ts.position_sizing.entry_breakdown.second_entry.percentage}% - ${ts.position_sizing.entry_breakdown.second_entry.conditions}</li>
                        <li>Third Entry: ${ts.position_sizing.entry_breakdown.third_entry.percentage}% - ${ts.position_sizing.entry_breakdown.third_entry.conditions}</li>
                    </ul>
                </div>
            </div>`;
    }

    html += '</div>';
    return html;
}

// Helper function to format execution section
function formatExecutionSection(execution) {
    if (!execution.execution_plan) return 'No execution plan available';
    
    const plan = execution.execution_plan;
    let html = '<div class="execution-grid">';

    // Entry Execution
    if (plan.entry_execution) {
        html += `
            <div class="execution-subsection">
                <h4>Entry Execution</h4>
                <div class="tranches">`;
        
        ['tranche_1', 'tranche_2', 'tranche_3'].forEach(tranche => {
            const t = plan.entry_execution[tranche];
            if (t) {
                html += `
                    <div class="tranche">
                        <h5>${formatMetricName(tranche)}</h5>
                        <p>Price Target: $${t.price_target}</p>
                        <p>Order Type: ${t.order_type}</p>
                        <p>Size: ${t.size}</p>
                        <p>Timing: ${t.timing}</p>
                        <p>Validity: ${t.validity}</p>
                    </div>`;
            }
        });
        
        html += '</div></div>';
    }

    // Execution Considerations
    if (plan.execution_considerations) {
        const ec = plan.execution_considerations;
        html += `
            <div class="execution-subsection">
                <h4>Execution Considerations</h4>
                <div class="considerations">
                    <div class="consideration">
                        <h5>Liquidity Analysis</h5>
                        <p>Average Daily Volume: ${ec.liquidity_analysis.avg_daily_volume}</p>
                        <p>Max Order Size: ${ec.liquidity_analysis.recommended_max_order_size}</p>
                        <p>Expected Slippage: ${ec.liquidity_analysis.expected_slippage}</p>
                    </div>
                    <div class="consideration">
                        <h5>Timing Optimization</h5>
                        <p>Preferred Hours: ${ec.timing_optimization.preferred_trading_hours}</p>
                        <p>Avoid Periods: ${ec.timing_optimization.avoid_periods.join(', ')}</p>
                    </div>
                    <div class="consideration">
                        <h5>Cost Analysis</h5>
                        <p>Commission: ${ec.cost_analysis.estimated_commission}</p>
                        <p>Slippage Cost: ${ec.cost_analysis.expected_slippage_cost}</p>
                        <p>Total Cost: ${ec.cost_analysis.total_cost_estimate}</p>
                    </div>
                </div>
            </div>`;
    }

    html += '</div>';
    return html;
}

// Helper function to format risk section
function formatRiskSection(risk) {
    if (typeof risk === 'string') {
        try {
            risk = JSON.parse(risk);
        } catch (e) {
            return risk; // Return as is if parsing fails
        }
    }

    // Get the risk assessment object
    const riskAssessment = risk.risk_assessment || risk;
    if (!riskAssessment) return 'No risk assessment data available';

    let html = '<div class="risk-grid">';

    // Portfolio Impact Section
    if (riskAssessment.portfolio_impact) {
        const portfolioImpact = riskAssessment.portfolio_impact;
        const concentrationRisk = portfolioImpact.concentration_risk || {};
        const riskMetrics = portfolioImpact.risk_metrics || {};

        html += `
            <div class="risk-subsection">
                <h4>Portfolio Impact</h4>
                <div class="risk-content">
                    <div class="subsection-group">
                        <h5>Concentration Risk</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">Max Recommended Allocation</span>
                                <span class="metric-value">${concentrationRisk.max_recommended_allocation || 'N/A'}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Sector Exposure Limit</span>
                                <span class="metric-value">${concentrationRisk.sector_exposure_limit || 'N/A'}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Portfolio Correlation</span>
                                <span class="metric-value">${concentrationRisk.correlation_with_portfolio || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="subsection-group">
                        <h5>Risk Metrics</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">VaR (95%)</span>
                                <span class="metric-value">${riskMetrics.var_95 || 'N/A'}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Expected Shortfall</span>
                                <span class="metric-value">${riskMetrics.expected_shortfall || 'N/A'}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Sharpe Ratio</span>
                                <span class="metric-value">${riskMetrics.sharpe_ratio || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    // Position Risk Analysis Section
    if (riskAssessment.position_risk_analysis) {
        const pra = riskAssessment.position_risk_analysis;
        html += `
            <div class="risk-subsection">
                <h4>Position Risk Analysis</h4>
                <div class="risk-content">
                    <div class="subsection-group">
                        <h5>Liquidity Risk</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">Execution Risk</span>
                                <span class="metric-value">${pra.liquidity_risk.execution_risk}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Daily Volume Ratio</span>
                                <span class="metric-value">${pra.liquidity_risk.daily_volume_ratio}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Average Spread</span>
                                <span class="metric-value">${pra.liquidity_risk.avg_spread}</span>
                            </div>
                        </div>
                    </div>
                    <div class="subsection-group">
                        <h5>Maximum Position Loss</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">Amount at Risk</span>
                                <span class="metric-value">${pra.max_position_loss.amount_at_risk}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Dollar Risk per Share</span>
                                <span class="metric-value">$${pra.max_position_loss.dollar_risk_per_share}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Position Sizing</span>
                                <span class="metric-value">${pra.max_position_loss.position_sizing_recommendation}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    // Market Risk Factors Section
    if (riskAssessment.market_risk_factors) {
        const mrf = riskAssessment.market_risk_factors;
        html += `
            <div class="risk-subsection">
                <h4>Market Risk Factors</h4>
                <div class="risk-content">
                    <div class="metric-item">
                        <span class="metric-name">Beta</span>
                        <span class="metric-value">${mrf.beta}</span>
                    </div>
                    <div class="subsection-group">
                        <h5>Sector Exposure</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">Sector</span>
                                <span class="metric-value">${mrf.sector_exposure.sector}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Sector Correlation</span>
                                <span class="metric-value">${mrf.sector_exposure.correlation_to_sector}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Cyclicality</span>
                                <span class="metric-value">${mrf.sector_exposure.sector_cyclicality}</span>
                            </div>
                        </div>
                    </div>
                    <div class="subsection-group">
                        <h5>Volatility Metrics</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">Historical Volatility</span>
                                <span class="metric-value">${mrf.volatility_metrics.historical_volatility}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Volatility Trend</span>
                                <span class="metric-value">${mrf.volatility_metrics.volatility_trend}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Risk Level</span>
                                <span class="metric-value">${mrf.volatility_metrics.risk_level}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    // Risk Mitigation Strategies Section
    if (riskAssessment.risk_mitigation_strategies) {
        const rms = riskAssessment.risk_mitigation_strategies;
        const monitoring = rms.monitoring_requirements || {};
        const riskIndicators = monitoring.risk_indicators || [];
        const alertLevels = monitoring.alert_levels || {};
        const technicalLevels = monitoring.technical_levels || [];
        const hedgingRecommendations = rms.hedging_recommendations || [];
        const positionManagement = rms.position_management || {};

        html += `
            <div class="risk-subsection">
                <h4>Risk Mitigation Strategies</h4>
                <div class="risk-content">
                    <div class="subsection-group">
                        <h5>Monitoring Requirements</h5>
                        <div class="monitoring-section">
                            <div class="risk-indicators">
                                <h6>Risk Indicators</h6>
                                <ul>
                                    ${riskIndicators.map(indicator => 
                                        `<li>${indicator}</li>`).join('') || '<li>No risk indicators available</li>'}
                                </ul>
                            </div>
                            <div class="alert-levels">
                                <h6>Alert Levels</h6>
                                <ul>
                                    <li>Volatility: ${alertLevels.volatility_alerts || 'N/A'}</li>
                                    <li>Volume: ${alertLevels.volume_alerts || 'N/A'}</li>
                                    <li>Price Levels: ${(alertLevels.price_alerts || []).join(', ') || 'N/A'}</li>
                                </ul>
                            </div>
                            <div class="technical-levels">
                                <h6>Technical Levels</h6>
                                <ul>
                                    ${technicalLevels.map(level => 
                                        `<li>${level}</li>`).join('') || '<li>No technical levels available</li>'}
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="subsection-group">
                        <h5>Hedging Recommendations</h5>
                        <ul class="hedging-list">
                            ${hedgingRecommendations.map(rec => 
                                `<li>${rec}</li>`).join('') || '<li>No hedging recommendations available</li>'}
                        </ul>
                    </div>
                    <div class="subsection-group">
                        <h5>Position Management</h5>
                        <div class="risk-metrics">
                            <div class="metric-item">
                                <span class="metric-name">Rebalancing</span>
                                <span class="metric-value">${positionManagement.rebalancing_frequency || 'N/A'}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Stop Adjustment</span>
                                <span class="metric-value">${positionManagement.stop_adjustment || 'N/A'}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-name">Position Scaling</span>
                                <span class="metric-value">${positionManagement.position_scaling || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    html += '</div>';
    return html;
}

// Helper function to format generic risk content
function formatRiskContent(content) {
    if (typeof content === 'string') return content;
    if (typeof content === 'object') {
        let html = '<div class="risk-metrics">';
        for (const [key, value] of Object.entries(content)) {
            if (value !== null && value !== undefined) {
                html += `
                    <div class="metric-item">
                        <span class="metric-name">${formatMetricName(key)}</span>
                        <span class="metric-value">${value}</span>
                    </div>`;
            }
        }
        html += '</div>';
        return html;
    }
    return '';
}

// Helper function to format metric names
function formatMetricName(name) {
    return name
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function createFinancialVisualizations(metrics) {
    // Early return if no metrics are available
    if (!metrics || typeof metrics !== 'object') {
        console.warn('No valid metrics data available for visualization');
        return;
    }

    const visualizationsContainer = document.getElementById('visualizations');
    visualizationsContainer.innerHTML = ''; // Clear existing visualizations

    // Helper function to safely parse numeric values
    const safeParseNumber = (value, removeSymbol = '') => {
        if (!value || typeof value !== 'string') return null;
        const cleanValue = value.replace(removeSymbol, '').replace('%', '').trim();
        const parsed = parseFloat(cleanValue);
        return isNaN(parsed) ? null : parsed;
    };

    // Helper function to check if we have enough valid data for a chart
    const hasValidData = (dataObject) => {
        const validValues = Object.values(dataObject).filter(val => val !== null);
        return validValues.length > 0;
    };

    // Prepare profitability data
    const profitabilityData = {
        'Return on Equity': safeParseNumber(metrics['Return on Equity'], '%'),
        'Profit Margins': safeParseNumber(metrics['Profit Margins'], '%')
    };

    if (hasValidData(profitabilityData)) {
        const gaugeChart = document.createElement('div');
        gaugeChart.id = 'gaugeChart';
        gaugeChart.style.height = '300px';
        visualizationsContainer.appendChild(gaugeChart);
        
        const options = {
            series: Object.values(profitabilityData).filter(val => val !== null),
            chart: {
                type: 'radialBar',
                height: 300,
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800,
                    animateGradually: {
                        enabled: true,
                        delay: 150
                    },
                    dynamicAnimation: {
                        enabled: true,
                        speed: 350
                    }
                }
            },
            plotOptions: {
                radialBar: {
                    hollow: {
                        size: '70%',
                        margin: 0
                    },
                    track: {
                        strokeWidth: '67%',
                        background: '#f2f2f2'
                    },
                    dataLabels: {
                        name: {
                            offsetY: -10,
                            color: '#888',
                            fontSize: '13px'
                        },
                        value: {
                            color: '#111',
                            fontSize: '30px',
                            show: true,
                            formatter: function (val) {
                                return val + '%';
                            }
                        }
                    }
                }
            },
            labels: Object.keys(profitabilityData).filter(key => profitabilityData[key] !== null),
            colors: ['#10B981', '#3B82F6'],
            stroke: {
                lineCap: 'round'
            }
        };

        new ApexCharts(gaugeChart, options).render();
    }

    // Prepare technical data
    const technicalData = {
        'RSI': safeParseNumber(metrics['RSI']),
        'Beta': safeParseNumber(metrics['Beta']),
        'Volatility': safeParseNumber(metrics['Volatility'], '%')
    };

    if (hasValidData(technicalData)) {
        const barChart = document.createElement('div');
        barChart.id = 'barChart';
        barChart.style.height = '300px';
        visualizationsContainer.appendChild(barChart);
        
        const validLabels = Object.keys(technicalData).filter(key => technicalData[key] !== null);
        const validData = validLabels.map(label => technicalData[label]);

        const options = {
            series: [{
                name: 'Technical Indicators',
                data: validData
            }],
            chart: {
                type: 'bar',
                height: 300,
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800,
                    animateGradually: {
                        enabled: true,
                        delay: 150
                    },
                    dynamicAnimation: {
                        enabled: true,
                        speed: 350
                    }
                }
            },
            plotOptions: {
                bar: {
                    borderRadius: 4,
                    horizontal: false,
                    columnWidth: '40%',
                    distributed: true,
                    dataLabels: {
                        position: 'top'
                    },
                    colors: {
                        ranges: [{
                            from: 0,
                            to: 100,
                            color: '#10B981'
                        }]
                    }
                }
            },
            dataLabels: {
                enabled: true,
                formatter: function (val) {
                    return val.toFixed(2);
                }
            },
            xaxis: {
                categories: validLabels,
                labels: {
                    style: {
                        colors: '#888'
                    }
                }
            },
            yaxis: {
                title: {
                    text: 'Value'
                }
            },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return val.toFixed(2);
                    }
                }
            }
        };

        new ApexCharts(barChart, options).render();
    }

    // Prepare price data
    const priceData = {
        'Current Price': safeParseNumber(metrics['Current Price'], '$'),
        'SMA50': safeParseNumber(metrics['SMA50'], '$'),
        'SMA200': safeParseNumber(metrics['SMA200'], '$')
    };

    if (hasValidData(priceData)) {
        const lineChart = document.createElement('div');
        lineChart.id = 'lineChart';
        lineChart.style.height = '300px';
        visualizationsContainer.appendChild(lineChart);
        
        const validLabels = Object.keys(priceData).filter(key => priceData[key] !== null);
        const validData = validLabels.map(label => priceData[label]);

        const options = {
            series: [{
                name: 'Price Indicators ($)',
                data: validData
            }],
            chart: {
                type: 'line',
                height: 300,
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800,
                    animateGradually: {
                        enabled: true,
                        delay: 150
                    },
                    dynamicAnimation: {
                        enabled: true,
                        speed: 350
                    }
                },
                toolbar: {
                    show: true
                }
            },
            stroke: {
                curve: 'smooth',
                width: 3
            },
            grid: {
                borderColor: '#f1f1f1',
                padding: {
                    top: 0,
                    right: 0,
                    bottom: 0,
                    left: 0
                }
            },
            xaxis: {
                categories: validLabels,
                labels: {
                    style: {
                        colors: '#888'
                    }
                }
            },
            yaxis: {
                title: {
                    text: 'Price ($)'
                }
            },
            markers: {
                size: 5,
                colors: '#10B981',
                strokeWidth: 0,
                hover: {
                    size: 7
                }
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.7,
                    opacityTo: 0.9,
                    stops: [0, 90, 100]
                }
            },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return '$' + val.toFixed(2);
                    }
                }
            }
        };

        new ApexCharts(lineChart, options).render();
    }

    // Prepare valuation data
    const valuationData = {
        'Forward P/E': safeParseNumber(metrics['Forward P/E']),
        'Market Cap (B)': safeParseNumber(metrics['Market Cap']?.replace(/[^0-9.-]/g, '')) / 1e9,
        'Beta': safeParseNumber(metrics['Beta'])
    };

    if (hasValidData(valuationData)) {
        const radarChart = document.createElement('div');
        radarChart.id = 'radarChart';
        radarChart.style.height = '300px';
        visualizationsContainer.appendChild(radarChart);
        
        const validLabels = Object.keys(valuationData).filter(key => valuationData[key] !== null);
        const validData = validLabels.map(label => valuationData[label]);

        const options = {
            series: [{
                name: 'Valuation Metrics',
                data: validData
            }],
            chart: {
                height: 300,
                type: 'radar',
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800,
                    animateGradually: {
                        enabled: true,
                        delay: 150
                    },
                    dynamicAnimation: {
                        enabled: true,
                        speed: 350
                    }
                }
            },
            title: {
                text: 'Valuation Analysis'
            },
            xaxis: {
                categories: validLabels
            },
            yaxis: {
                show: false
            },
            plotOptions: {
                radar: {
                    size: 140,
                    polygons: {
                        strokeColors: '#e2e8f0',
                        fill: {
                            colors: ['#f8fafc', '#f1f5f9', '#e2e8f0']
                        }
                    }
                }
            },
            colors: ['#3B82F6'],
            markers: {
                size: 4,
                colors: ['#fff'],
                strokeColors: '#3B82F6',
                strokeWidth: 2,
                hover: {
                    size: 6
                }
            },
            tooltip: {
                y: {
                    formatter: function (val) {
                        return val.toFixed(2);
                    }
                }
            }
        };

        new ApexCharts(radarChart, options).render();
    }

    // Add a message if no charts were created
    if (visualizationsContainer.children.length === 0) {
        const noDataMessage = document.createElement('div');
        noDataMessage.className = 'no-data-message';
        noDataMessage.textContent = 'No valid quantitative data available for visualization';
        visualizationsContainer.appendChild(noDataMessage);
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    document.getElementById('loading').classList.remove('active');
    document.getElementById('result').classList.remove('active');
}

// Make analyzeStock function available globally
window.analyzeStock = analyzeStock; 