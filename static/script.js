// ============================================
// UCX Search v2.5 - Enhanced Frontend
// Features: Search, Chat, AI, Multi-type search
// ============================================

const THEMES = {};
let currentTheme = 'dark-midnight';
let currentMode = 'search';
let lastResults = null;
let chatMode = false;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadThemePreference();
});

function initializeApp() {
    fetch('/api/themes')
        .then(response => response.json())
        .then(data => Object.assign(THEMES, data))
        .catch(err => console.error('Failed to load themes:', err));
    
    document.getElementById('searchInput').focus();
}

function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') performSearch();
    });
    
    document.getElementById('chatInput')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendChatMessage();
    });
}

// ============================================
// MODE MANAGEMENT
// ============================================

function changeMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-content').forEach(el => {
        el.style.display = el.id === mode + 'Mode' ? 'block' : 'none';
    });
    
    if (mode === 'chat') {
        setTimeout(() => document.getElementById('chatInput')?.focus(), 100);
    } else {
        setTimeout(() => document.getElementById('searchInput')?.focus(), 100);
    }
}

// ============================================
// SEARCH FUNCTIONALITY
// ============================================

async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        showNotification('Please enter a search query', 'warning');
        return;
    }
    
    showLoading(true);
    document.getElementById('clearBtn').style.display = 'inline-block';
    
    try {
        const searchType = document.getElementById('searchType').value;
        const numResults = parseInt(document.getElementById('resultsCount').value);
        const useAI = document.getElementById('useAI').checked;
        
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                search_type: searchType,
                results: numResults,
                use_ai: useAI
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        lastResults = data;
        
        displayResults(data);
        showNotification(`Found ${data.total} results in ${data.execution_time.toFixed(2)}s`, 'success');
        
        if (data.ai_summary) {
            displayAISummary(data.ai_summary);
        }
        
    } catch (error) {
        console.error('Search error:', error);
        showNotification(`Search failed: ${error.message}`, 'error');
        displayError(error);
    } finally {
        showLoading(false);
    }
}

function displayResults(data) {
    const resultsContainer = document.getElementById('results');
    resultsContainer.innerHTML = '';
    
    if (!data.success || data.total === 0) {
        resultsContainer.innerHTML = `
            <div class="no-results">
                <div class="no-results-emoji">
                    ${data.search_type === 'images' ? '🖼️' : data.search_type === 'news' ? '📰' : '🔍'}
                </div>
                <p>No results found for "${escapeHtml(data.query)}"</p>
            </div>
        `;
        return;
    }
    
    const header = document.createElement('div');
    header.style.marginBottom = '1.5rem';
    header.style.paddingBottom = '1rem';
    header.style.borderBottom = '1px solid var(--border-color)';
    header.innerHTML = `
        <p style="color: var(--text-secondary); font-size: 0.9rem;">
            📊 <strong>${data.total}</strong> results from <strong>${data.source}</strong>
            • ⏱️ ${data.execution_time.toFixed(2)}s
        </p>
    `;
    resultsContainer.appendChild(header);
    
    data.results.forEach((result, index) => {
        const element = createResultElement(result, index + 1, data.search_type);
        resultsContainer.appendChild(element);
    });
}

function createResultElement(result, index, searchType) {
    const div = document.createElement('div');
    div.className = 'result-item';
    
    if (searchType === 'images') {
        div.innerHTML = `
            <div style="text-align: center;">
                <img src="${escapeHtml(result.thumbnail)}" alt="${escapeHtml(result.title)}" style="max-width: 100%; max-height: 200px; border-radius: 8px; margin-bottom: 1rem;">
                <h3 class="result-title">${escapeHtml(result.title)}</h3>
                <button class="option-btn" onclick="openResult('${escapeHtml(result.url)}', event)" style="margin-top: 0.5rem;">
                    View ↗
                </button>
            </div>
        `;
    } else if (searchType === 'news') {
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                <div style="flex: 1;">
                    <h3 class="result-title">${index}. ${escapeHtml(result.title)}</h3>
                    ${result.date ? `<p style="font-size: 0.85rem; color: var(--text-secondary);">📅 ${result.date}</p>` : ''}
                </div>
            </div>
            <p class="result-description">${escapeHtml(result.description)}</p>
            <button class="option-btn" onclick="openResult('${escapeHtml(result.url)}', event)">Read Full Article ↗</button>
        `;
    } else {
        const cleanUrl = new URL(result.url).hostname;
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                <div style="flex: 1;">
                    <h3 class="result-title">${index}. ${escapeHtml(result.title)}</h3>
                </div>
                <button class="option-btn" onclick="openResult('${escapeHtml(result.url)}', event)" style="margin-left: 1rem;">
                    Open ↗
                </button>
            </div>
            <div class="result-url" onclick="copyToClipboard('${escapeHtml(result.url)}', event)" title="Click to copy">
                🔗 ${escapeHtml(cleanUrl)}
            </div>
            <p class="result-description">${escapeHtml(result.description)}</p>
            <div class="result-meta">
                <span>📍 ${escapeHtml(result.source)}</span>
                ${result.ai_rank_score ? `<span>⭐ ${(result.ai_rank_score * 100).toFixed(0)}%</span>` : ''}
            </div>
        `;
    }
    
    return div;
}

function displayAISummary(summary) {
    const summaryDiv = document.getElementById('aiSummary');
    const content = document.getElementById('summaryContent');
    
    if (summary) {
        content.innerHTML = `<p>${summary.replace(/\n/g, '<br>')}</p>`;
        summaryDiv.style.display = 'block';
    }
}

function toggleSummary() {
    const content = document.getElementById('summaryContent');
    const btn = event.target;
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        btn.textContent = '−';
    } else {
        content.style.display = 'none';
        btn.textContent = '+';
    }
}

function displayError(error) {
    const resultsContainer = document.getElementById('results');
    resultsContainer.innerHTML = `
        <div class="no-results">
            <div class="no-results-emoji">❌</div>
            <p><strong>Search Error:</strong></p>
            <p style="font-size: 0.9rem;">${escapeHtml(error.message)}</p>
        </div>
    `;
}

// ============================================
// CHAT FUNCTIONALITY
// ============================================

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message
    addChatMessage(message, 'user');
    input.value = '';
    
    try {
        const searchEnabled = document.getElementById('chatSearch').checked;
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                search: searchEnabled
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        addChatMessage(data.response, 'bot');
        
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage(`Sorry, I encountered an error: ${error.message}`, 'bot');
    }
}

function addChatMessage(message, role) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}-message`;
    messageDiv.innerHTML = `<p>${message.replace(/\n/g, '<br>')}</p>`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function handleChatKeypress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

// ============================================
// THEME & UTILITY
// ============================================

function changeTheme(theme) {
    currentTheme = theme;
    document.body.className = theme;
    localStorage.setItem('ucxTheme', theme);
    showNotification(`Theme: ${theme.replace('-', ' ').toUpperCase()}`, 'success');
}

function loadThemePreference() {
    const saved = localStorage.getItem('ucxTheme') || 'dark-midnight';
    currentTheme = saved;
    document.body.className = saved;
    document.getElementById('themeSelect').value = saved;
}

function updateSearchType() {
    const searchType = document.getElementById('searchType').value;
    if (searchType === 'images') {
        document.getElementById('resultsCount').value = 20;
    } else {
        document.getElementById('resultsCount').value = 10;
    }
}

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'flex' : 'none';
}

function clearResults() {
    document.getElementById('searchInput').value = '';
    document.getElementById('results').innerHTML = '';
    document.getElementById('aiSummary').style.display = 'none';
    document.getElementById('clearBtn').style.display = 'none';
    document.getElementById('searchInput').focus();
}

async function exportResults() {
    if (!lastResults) {
        showNotification('No results to export', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(lastResults)
        });
        
        const data = await response.json();
        showNotification(`Exported to ${data.filename}`, 'success');
    } catch (error) {
        showNotification(`Export failed: ${error.message}`, 'error');
    }
}

function openResult(url, event) {
    event.stopPropagation();
    window.open(url, '_blank');
}

function copyToClipboard(text, event) {
    event.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
        showNotification('URL copied! 📋', 'success');
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed; bottom: 2rem; right: 2rem; padding: 1rem 1.5rem;
        background: ${getNotificationColor(type)}; color: white; border-radius: 8px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3); z-index: 3000;
        animation: slideIn 0.3s ease-out; font-weight: 500;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function getNotificationColor(type) {
    const colors = {
        'success': '#10b981',
        'error': '#ef4444',
        'warning': '#f59e0b',
        'info': '#3b82f6'
    };
    return colors[type] || colors.info;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleHistory() {
    const sidebar = document.getElementById('historySidebar');
    sidebar.style.display = sidebar.style.display === 'none' ? 'flex' : 'none';
}

function closeHistory() {
    document.getElementById('historySidebar').style.display = 'none';
}

function showAbout() { document.getElementById('aboutModal').style.display = 'block'; }
function showFeatures() { document.getElementById('featuresModal').style.display = 'block'; }
function showPrivacy() { document.getElementById('privacyModal').style.display = 'block'; }
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

window.onclick = (e) => {
    if (e.target.classList.contains('modal')) e.target.style.display = 'none';
};

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
        document.getElementById('searchInput').select();
    }
    if (e.key === 'Escape') {
        closeHistory();
        document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
    }
});
