"""
UCX Search Web UI - Beautiful, Privacy-Focused Interface
20+ Themes, Fast, and Privacy-First
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from ucx_search_core import UCXSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize UCX Search
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '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')
ucx_search = UCXSearch(tavily_api_key=TAVILY_API_KEY)

# Theme configuration
THEMES = {
    'dark-midnight': {'name': 'Dark Midnight', 'primary': '#0f0f0f', 'accent': '#00d4ff'},
    'dark-slate': {'name': 'Dark Slate', 'primary': '#1a1a2e', 'accent': '#16c784'},
    'dark-coal': {'name': 'Dark Coal', 'primary': '#2b2b2b', 'accent': '#6366f1'},
    'light-minimal': {'name': 'Light Minimal', 'primary': '#ffffff', 'accent': '#3b82f6'},
    'light-cream': {'name': 'Light Cream', 'primary': '#faf8f3', 'accent': '#d97706'},
    'neon-cyan': {'name': 'Neon Cyan', 'primary': '#0a0e27', 'accent': '#00ffff'},
    'neon-purple': {'name': 'Neon Purple', 'primary': '#1a0033', 'accent': '#ff00ff'},
    'neon-green': {'name': 'Neon Green', 'primary': '#0d1b0f', 'accent': '#00ff00'},
    'forest-green': {'name': 'Forest Green', 'primary': '#0f2818', 'accent': '#4ade80'},
    'ocean-blue': {'name': 'Ocean Blue', 'primary': '#0a1628', 'accent': '#06b6d4'},
    'sunset-orange': {'name': 'Sunset Orange', 'primary': '#1a0800', 'accent': '#fb923c'},
    'cherry-red': {'name': 'Cherry Red', 'primary': '#1a0505', 'accent': '#ef4444'},
    'lavender-purple': {'name': 'Lavender', 'primary': '#2d1b4e', 'accent': '#a78bfa'},
    'steel-gray': {'name': 'Steel Gray', 'primary': '#18202f', 'accent': '#9ca3af'},
    'golden-amber': {'name': 'Golden Amber', 'primary': '#1f1810', 'accent': '#fbbf24'},
    'teal-turquoise': {'name': 'Teal', 'primary': '#0d2b2b', 'accent': '#14b8a6'},
    'rose-pink': {'name': 'Rose Pink', 'primary': '#1f0a15', 'accent': '#ec4899'},
    'lime-bright': {'name': 'Lime', 'primary': '#0f1a00', 'accent': '#84cc16'},
    'indigo-deep': {'name': 'Indigo', 'primary': '#0f0a1f', 'accent': '#6366f1'},
    'zinc-neutral': {'name': 'Zinc', 'primary': '#09090b', 'accent': '#a1a1aa'},
}

@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html', themes=THEMES)

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for search"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        num_results = min(int(data.get('results', 10)), 50)
        parallel = data.get('parallel', False)
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        # Perform search
        results = ucx_search.search(query, num_results=num_results, parallel=parallel)
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def api_history():
    """Get search history"""
    history = ucx_search.get_history()
    return jsonify({'history': history[-10:]})  # Last 10 searches

@app.route('/api/clear-cache', methods=['POST'])
def api_clear_cache():
    """Clear search cache"""
    ucx_search.clear_cache()
    return jsonify({'status': 'Cache cleared'})

@app.route('/api/export', methods=['POST'])
def api_export():
    """Export search results"""
    try:
        data = request.get_json()
        results = data.get('results', {})
        
        filename = ucx_search.save_results(results)
        return jsonify({'filename': filename, 'status': 'Exported'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/themes', methods=['GET'])
def api_themes():
    """Get available themes"""
    return jsonify(THEMES)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
