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

// DOM Elements
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
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
    const logoutBtn = document.getElementById('logout-btn');
    const tickerSection = document.getElementById('ticker-section');
    
    if (user) {
        console.log('User email:', user.email);
        authStatus.textContent = `Signed in as ${user.email}`;
        loginBtn.classList.add('hidden');
        logoutBtn.classList.remove('hidden');
        authForm.classList.add('hidden');
        tickerSection.classList.remove('hidden');
        // Hide the email and password fields
        document.getElementById('email').value = '';
        document.getElementById('password').value = '';
    } else {
        console.log('No user signed in');
        authStatus.textContent = 'Please sign in to analyze stocks';
        loginBtn.classList.remove('hidden');
        logoutBtn.classList.add('hidden');
        authForm.classList.remove('hidden');
        tickerSection.classList.add('hidden');
        
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

logoutBtn.onclick = () => auth.signOut();

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

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'An error occurred');
        }

        const data = await response.json();
        console.log('Response from backend:', data); // Debug log
        console.log('Status from response:', data.status); // Debug log
        console.log('Document ID:',  data.document_id); // Debug log
        
        if(data.status === 'completed'){ // if the analysis was already completed within the last 24 hours
            console.log('Entering completed branch'); // Debug log
            console.log('Result data:', data.result); // Debug log
            document.getElementById('result-content').innerHTML = formatResults(data.result);
            document.getElementById('result').classList.add('active');
            document.getElementById('loading').classList.remove('active');
        }
        else {
            console.log('Entering in-progress branch'); // Debug log
            loadingText.textContent = 'Analysis in progress...';
            // Start listening for updates
            listenForAnalysisUpdates(data.document_id);
        }
      
    } catch (error) {
        showError(error.message);
        analytics.logEvent('analyze_stock_error', { ticker, error: error.message });
        document.getElementById('loading').classList.remove('active');
    }
}

function formatResults(data) {
    let html = '<div class="results-container">';
    
    // Clear previous visualizations
    document.getElementById('visualizations').innerHTML = '';
    
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
            
            html += `
                <div class="metric-card">
                    <div class="metric-label">${key}</div>
                    <div class="metric-value ${metricClass}">${value}</div>
                </div>`;
        }
        html += '</div></div>';
    }
    
    if (data.analysis_summary) {
        html += `
            <div class="results-section">
                <h3 class="results-section-title">Analysis Summary</h3>
                <div class="analysis-content">`;
        
        const sections = data.analysis_summary.split(/(?=\d+\.\s+\*\*)/);
        
        sections.forEach(section => {
            if (section.trim()) {
                const titleMatch = section.match(/\*\*(.*?)\*\*/);
                const title = titleMatch ? titleMatch[1] : '';
                
                let content = section
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\d+\.\s+/, '');
                
                html += `
                    <div class="analysis-card">
                        ${content}
                    </div>`;
            }
        });
        html += '</div></div>';
    }
    
    html += '</div>';
    return html;
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
        const gaugeChart = document.createElement('canvas');
        gaugeChart.id = 'gaugeChart';
        visualizationsContainer.appendChild(gaugeChart);
        
        new Chart(gaugeChart.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(profitabilityData).filter(key => profitabilityData[key] !== null),
                datasets: [{
                    data: Object.values(profitabilityData).filter(val => val !== null),
                    backgroundColor: ['#10B981', '#3B82F6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: 'Profitability Metrics (%)'
                    }
                }
            }
        });
    }

    // Prepare technical data
    const technicalData = {
        'RSI': safeParseNumber(metrics['RSI']),
        'Beta': safeParseNumber(metrics['Beta']),
        'Volatility': safeParseNumber(metrics['Volatility'], '%')
    };

    if (hasValidData(technicalData)) {
        const barChart = document.createElement('canvas');
        barChart.id = 'barChart';
        visualizationsContainer.appendChild(barChart);
        
        const validLabels = Object.keys(technicalData).filter(key => technicalData[key] !== null);
        const validData = validLabels.map(label => technicalData[label]);

        new Chart(barChart.getContext('2d'), {
            type: 'bar',
            data: {
                labels: validLabels,
                datasets: [{
                    label: 'Technical Indicators',
                    data: validData,
                    backgroundColor: validLabels.map((_, i) => 
                        ['#10B981', '#3B82F6', '#EF4444'][i % 3]
                    ),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Technical Analysis Metrics'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { display: false }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // Prepare price data
    const priceData = {
        'Current Price': safeParseNumber(metrics['Current Price'], '$'),
        'SMA50': safeParseNumber(metrics['SMA50'], '$'),
        'SMA200': safeParseNumber(metrics['SMA200'], '$')
    };

    if (hasValidData(priceData)) {
        const lineChart = document.createElement('canvas');
        lineChart.id = 'lineChart';
        visualizationsContainer.appendChild(lineChart);
        
        const validLabels = Object.keys(priceData).filter(key => priceData[key] !== null);
        const validData = validLabels.map(label => priceData[label]);

        new Chart(lineChart.getContext('2d'), {
            type: 'line',
            data: {
                labels: validLabels,
                datasets: [{
                    label: 'Price Indicators ($)',
                    data: validData,
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Price Analysis'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { display: false }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // Prepare valuation data
    const valuationData = {
        'Forward P/E': safeParseNumber(metrics['Forward P/E']),
        'Market Cap (B)': safeParseNumber(metrics['Market Cap']?.replace(/[^0-9.-]/g, '')) / 1e9,
        'Beta': safeParseNumber(metrics['Beta'])
    };

    if (hasValidData(valuationData)) {
        const radarChart = document.createElement('canvas');
        radarChart.id = 'radarChart';
        visualizationsContainer.appendChild(radarChart);
        
        const validLabels = Object.keys(valuationData).filter(key => valuationData[key] !== null);
        const validData = validLabels.map(label => valuationData[label]);

        new Chart(radarChart.getContext('2d'), {
            type: 'radar',
            data: {
                labels: validLabels,
                datasets: [{
                    label: 'Valuation Metrics',
                    data: validData,
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: '#3B82F6',
                    borderWidth: 2,
                    pointBackgroundColor: '#3B82F6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Valuation Analysis'
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        ticks: { display: false }
                    }
                }
            }
        });
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
}

// Make analyzeStock function available globally
window.analyzeStock = analyzeStock; 