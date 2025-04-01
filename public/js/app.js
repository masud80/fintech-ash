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
    const authForm = document.getElementById('auth-form');
    if (user) {
        authStatus.textContent = `Signed in as ${user.email}`;
        loginBtn.classList.add('hidden');
        logoutBtn.classList.remove('hidden');
        tickerSection.classList.remove('hidden');
        // Hide the email and password fields
        document.getElementById('email').value = '';
        document.getElementById('password').value = '';
        authForm.classList.add('hidden');
    } else {
        authStatus.textContent = 'Please sign in to analyze stocks';
        loginBtn.classList.remove('hidden');
        logoutBtn.classList.add('hidden');
        tickerSection.classList.add('hidden');
        // Show the auth form
        authForm.classList.remove('hidden');
        
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
    
    if (data.financial_metrics) {
        html += `
            <div class="results-section">
                <h3 class="results-section-title">Financial Metrics</h3>
                <div class="metrics-grid">`;
        
        for (const [key, value] of Object.entries(data.financial_metrics)) {
            // Determine if the metric is positive, negative, or neutral
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
        
        // Split the analysis into sections based on numbering
        const sections = data.analysis_summary.split(/(?=\d+\.\s+\*\*)/);
        
        sections.forEach(section => {
            if (section.trim()) {
                // Extract and format risk title
                const titleMatch = section.match(/\*\*(.*?)\*\*/);
                const title = titleMatch ? titleMatch[1] : '';
                
                // Format the content, replacing ** with proper styling
                let content = section
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\d+\.\s+/, ''); // Remove numbering
                
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

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Make analyzeStock function available globally
window.analyzeStock = analyzeStock; 