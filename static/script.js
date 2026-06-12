// ============================================
// UCX Search - Frontend JavaScript
// Privacy-First, Lightning-Fast UI
// ============================================

const THEMES = {};
let currentTheme = 'dark-midnight';
let lastResults = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadThemePreference();
});

function initializeApp() {
    // Load available themes
    fetch('/api/themes')
        .then(response => response.json())
        .then(data => {
            Object.assign(THEMES, data);
        })
        .catch(err => console.error('Failed to load themes:', err));
    
    // Focus on search input
    document.getElementById('searchInput').focus();
}

function setupEventListeners() {
    // Search on Enter key
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Clear history on load
    updateHistory();
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
        const numResults = parseInt(document.getElementById('resultsCount').value);
        const parallel = document.getElementById('parallelSearch').checked;
        
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                results: numResults,
                parallel: parallel
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        lastResults = data;
        
        displayResults(data);
        showNotification(`Found ${data.total} results in ${data.execution_time.toFixed(2)}s`, 'success');
        
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
                <div class="no-results-emoji">🔍</div>
                <p>No results found for "${escapeHtml(data.query)}"</p>
                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.5rem;">
                    Tip: Try different keywords or enable Fast Mode for fallback search
                </p>
            </div>
        `;
        return;
    }
    
    // Add results header
    const header = document.createElement('div');
    header.style.marginBottom = '1.5rem';
    header.style.paddingBottom = '1rem';
    header.style.borderBottom = '1px solid var(--border-color)';
    header.innerHTML = `
        <div>
            <p style="color: var(--text-secondary); font-size: 0.9rem;">
                📊 <strong>${data.total}</strong> results from <strong>${data.source}</strong>
                • ⏱️ ${data.execution_time.toFixed(2)}s
            </p>
        </div>
    `;
    resultsContainer.appendChild(header);
    
    // Display results
    data.results.forEach((result, index) => {
        const resultElement = createResultElement(result, index + 1);
        resultsContainer.appendChild(resultElement);
    });
}

function createResultElement(result, index) {
    const div = document.createElement('div');
    div.className = 'result-item';
    
    const cleanUrl = new URL(result.url).hostname;
    const timeStr = new Date(result.retrieved_at || result.scraped_at).toLocaleDateString();
    
    div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
            <div style="flex: 1;">
                <h3 class="result-title">${index}. ${escapeHtml(result.title)}</h3>
            </div>
            <button class="option-btn" onclick="openResult('${escapeHtml(result.url)}', event)" style="margin-left: 1rem; padding: 0.5rem 1rem; font-size: 0.85rem;">
                Open ↗
            </button>
        </div>
        <div class="result-url" onclick="copyToClipboard('${escapeHtml(result.url)}', event)" title="Click to copy">
            🔗 ${escapeHtml(cleanUrl)}
        </div>
        <div class="result-description">
            ${escapeHtml(result.description)}
        </div>
        <div class="result-meta">
            <span class="result-source">📍 ${escapeHtml(result.source)}</span>
            <span class="result-time">📅 ${timeStr}</span>
            ${result.score ? `<span>⭐ ${(result.score * 100).toFixed(0)}%</span>` : ''}
        </div>
    `;
    
    return div;
}

function openResult(url, event) {
    event.stopPropagation();
    window.open(url, '_blank');
}

function copyToClipboard(text, event) {
    event.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
        showNotification('URL copied to clipboard! 📋', 'success');
    });
}

function displayError(error) {
    const resultsContainer = document.getElementById('results');
    resultsContainer.innerHTML = `
        <div class="no-results">
            <div class="no-results-emoji">❌</div>
            <p><strong>Search Error:</strong></p>
            <p style="font-size: 0.9rem; color: var(--text-secondary);">${escapeHtml(error.message)}</p>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 1rem;">
                This might be a temporary issue. Please try again or enable Fast Mode for fallback to Tavily.
            </p>
        </div>
    `;
}

// ============================================
// THEME MANAGEMENT
// ============================================

function changeTheme(theme) {
    currentTheme = theme;
    document.body.className = theme;
    localStorage.setItem('ucxTheme', theme);
    showNotification(`Theme changed to ${theme}`, 'success');
}

function loadThemePreference() {
    const saved = localStorage.getItem('ucxTheme') || 'dark-midnight';
    currentTheme = saved;
    document.body.className = saved;
    document.getElementById('themeSelect').value = saved;
}

// ============================================
// HISTORY MANAGEMENT
// ============================================

async function updateHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        displayHistory(data.history);
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function displayHistory(history) {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';
    
    if (history.length === 0) {
        historyList.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 1rem;">No search history yet</p>';
        return;
    }
    
    history.reverse().forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div onclick="repeatSearch('${escapeHtml(item.query)}')" style="cursor: pointer;">
                <strong>${escapeHtml(item.query.substring(0, 25))}${item.query.length > 25 ? '...' : ''}</strong>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">
                    ${item.total} results
                </div>
            </div>
        `;
        historyList.appendChild(historyItem);
    });
}

function repeatSearch(query) {
    document.getElementById('searchInput').value = query;
    closeHistory();
    performSearch();
}

function toggleHistory() {
    const sidebar = document.getElementById('historySidebar');
    if (sidebar.style.display === 'none') {
        updateHistory();
        sidebar.style.display = 'flex';
    } else {
        closeHistory();
    }
}

function closeHistory() {
    document.getElementById('historySidebar').style.display = 'none';
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'flex' : 'none';
}

function clearResults() {
    document.getElementById('searchInput').value = '';
    document.getElementById('results').innerHTML = '';
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
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(lastResults)
        });
        
        const data = await response.json();
        showNotification(`Results exported to ${data.filename}`, 'success');
    } catch (error) {
        showNotification(`Export failed: ${error.message}`, 'error');
    }
}

function showNotification(message, type = 'info') {
    // Create temporary notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${getNotificationColor(type)};
        color: white;
        border-radius: 8px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        z-index: 3000;
        animation: slideIn 0.3s ease-out;
        font-weight: 500;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Auto-remove
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

function showAbout() {
    document.getElementById('aboutModal').style.display = 'block';
}

function showPrivacy() {
    document.getElementById('privacyModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = event.target;
    if (modal.classList.contains('modal')) {
        modal.style.display = 'none';
    }
};

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + L: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
        document.getElementById('searchInput').select();
    }
    
    // Ctrl/Cmd + K: Focus search (common shortcut)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }
    
    // Escape: Clear search or close modals
    if (e.key === 'Escape') {
        closeHistory();
        document.querySelectorAll('.modal').forEach(m => {
            if (m.style.display !== 'none') {
                m.style.display = 'none';
            }
        });
    }
});
