"""
UCX Search Engine Core - Enhanced Version
Features: Yep scraping, Tavily fallback, AI summaries, Image/News search, Smart ranking
Bug fixes: Better error handling, improved caching, thread safety
"""

import os
import json
import time
import requests
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin
from datetime import datetime
from bs4 import BeautifulSoup
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CacheManager:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def get_key(self, query: str, source: str, search_type: str = 'web') -> str:
        """Generate cache key from query"""
        content = f"{query.lower().strip()}_{source}_{search_type}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, source: str, search_type: str = 'web') -> Optional[list]:
        """Retrieve from cache if valid"""
        try:
            with self.lock:
                key = self.get_key(query, source, search_type)
                if key in self.cache:
                    cached, timestamp = self.cache[key]
                    if time.time() - timestamp < self.ttl:
                        logger.debug(f"📦 Cache hit for: {query}")
                        return cached
                    else:
                        del self.cache[key]
                return None
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    def set(self, query: str, source: str, data: list, search_type: str = 'web') -> None:
        """Store in cache"""
        try:
            with self.lock:
                key = self.get_key(query, source, search_type)
                self.cache[key] = (data, time.time())
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def clear(self) -> None:
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()


class AIEnhancer:
    """AI-powered enhancements for search results"""
    
    @staticmethod
    def generate_summary(results: List[Dict], max_length: int = 200) -> str:
        """Generate AI-style summary from search results"""
        if not results:
            return "No results available for summary."
        
        try:
            # Extract unique keywords from titles and descriptions
            titles = [r['title'] for r in results[:3]]
            descriptions = [r['description'][:100] for r in results[:3]]
            
            # Create intelligent summary
            summary_parts = []
            
            # Top result context
            if results:
                top = results[0]
                summary_parts.append(f"Based on search results, the top finding is about: {top['title'][:80]}...")
            
            # Common themes
            all_text = ' '.join(titles + descriptions).lower()
            keywords = re.findall(r'\b[a-z]{4,}\b', all_text)
            top_keywords = list(set(keywords))[:3]
            
            if top_keywords:
                summary_parts.append(f"\nKey topics: {', '.join(top_keywords[:3])}")
            
            summary_parts.append(f"\nFound {len(results)} highly relevant results from {results[0]['source']}")
            
            return '\n'.join(summary_parts)[:max_length]
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Unable to generate summary at this time."
    
    @staticmethod
    def rank_by_relevance(results: List[Dict], query: str) -> List[Dict]:
        """Advanced relevance ranking based on query match"""
        query_words = set(query.lower().split())
        
        for result in results:
            score = 0.0
            title_lower = result['title'].lower()
            desc_lower = result['description'].lower()
            
            # Title matching
            for word in query_words:
                if word in title_lower:
                    score += 0.5
            
            # Description matching
            for word in query_words:
                if word in desc_lower:
                    score += 0.2
            
            # Domain reputation bonus
            trusted_domains = ['wikipedia.org', 'github.com', 'stackoverflow.com', 'arxiv.org']
            if any(domain in result['url'] for domain in trusted_domains):
                score += 0.3
            
            # Length bonus (substantial content)
            if len(result['description']) > 150:
                score += 0.1
            
            result['ai_rank_score'] = min(score, 1.0)
        
        return sorted(results, key=lambda x: x.get('ai_rank_score', 0), reverse=True)


class YepScraper:
    """Enhanced Yep Search scraper with multiple search types"""
    
    def __init__(self, cache_ttl: int = 3600):
        self.base_url = "https://yep.com/search"
        self.cache = CacheManager(ttl=cache_ttl)
        self.session = self._create_session()
        self.timeout = 12
        self.max_retries = 3
        self.ai_enhancer = AIEnhancer()
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        })
        return session
    
    def search(self, query: str, search_type: str = 'web', num_results: int = 10) -> List[Dict]:
        """
        Search Yep with support for multiple search types
        
        Args:
            query: Search query
            search_type: 'web', 'news', 'images'
            num_results: Number of results to return
        """
        # Check cache first
        cached = self.cache.get(query, "yep", search_type)
        if cached:
            return cached[:num_results]
        
        try:
            logger.info(f"🔍 Scraping Yep ({search_type}): '{query}'")
            start_time = time.time()
            
            params = {
                'q': quote(query),
                'type': search_type
            }
            
            response = None
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(
                        self.base_url,
                        params=params,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt < self.max_retries - 1:
                        logger.debug(f"⚠️ Attempt {attempt + 1} failed, retrying...")
                        time.sleep(0.5 * (attempt + 1))
                    else:
                        raise
            
            if search_type == 'images':
                results = self._parse_image_results(response.text)
            elif search_type == 'news':
                results = self._parse_news_results(response.text)
            else:
                results = self._parse_web_results(response.text)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Found {len(results)} results in {elapsed:.2f}s")
            
            # Apply AI ranking
            results = self.ai_enhancer.rank_by_relevance(results, query)
            
            # Cache results
            self.cache.set(query, "yep", results, search_type)
            
            return results[:num_results]
        
        except Exception as e:
            logger.error(f"❌ Yep scraping error: {e}")
            return []
    
    def _parse_web_results(self, html: str) -> List[Dict]:
        """Parse web search results"""
        results = []
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Multiple selector strategies
            selectors = [
                ('div[data-testid="result"]', 'h2', 'p'),
                ('article', 'h3', 'p'),
                ('div.result', 'h2', 'span.description'),
            ]
            
            for item_selector, title_selector, desc_selector in selectors:
                items = soup.select(item_selector)
                if items:
                    for item in items[:20]:
                        try:
                            title_elem = item.select_one(title_selector)
                            link_elem = item.find('a', href=True)
                            desc_elem = item.select_one(desc_selector)
                            
                            title = title_elem.get_text(strip=True) if title_elem else None
                            url = link_elem.get('href', '') if link_elem else None
                            description = desc_elem.get_text(strip=True) if desc_elem else ""
                            
                            if title and url and len(title) > 3:
                                if not url.startswith('http'):
                                    url = urljoin(self.base_url, url)
                                
                                if not any(skip in url.lower() for skip in ['ad.', '/ads/', 'sponsored']):
                                    results.append({
                                        'title': title[:200],
                                        'url': url,
                                        'description': description[:300] or "No description available",
                                        'source': 'Yep',
                                        'type': 'web',
                                        'scraped_at': datetime.now().isoformat(),
                                    })
                        except Exception as e:
                            logger.debug(f"Error parsing item: {e}")
                            continue
                    
                    if results:
                        break
        
        except Exception as e:
            logger.error(f"Web parsing error: {e}")
        
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict]:
        """Parse news search results"""
        results = []
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # News-specific selectors
            items = soup.select('article, div.news-item, div[class*="news"]')
            
            for item in items[:20]:
                try:
                    title_elem = item.find(['h2', 'h3'])
                    link_elem = item.find('a', href=True)
                    desc_elem = item.find(['p', 'span'], class_=lambda x: x and 'desc' in x.lower() if x else False)
                    date_elem = item.find(['time', 'span'], class_=lambda x: x and 'date' in x.lower() if x else False)
                    
                    title = title_elem.get_text(strip=True) if title_elem else None
                    url = link_elem.get('href', '') if link_elem else None
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    date = date_elem.get_text(strip=True) if date_elem else ""
                    
                    if title and url:
                        if not url.startswith('http'):
                            url = urljoin(self.base_url, url)
                        
                        results.append({
                            'title': title[:200],
                            'url': url,
                            'description': description[:300] or "No description available",
                            'date': date,
                            'source': 'Yep',
                            'type': 'news',
                            'scraped_at': datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing news item: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"News parsing error: {e}")
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict]:
        """Parse image search results"""
        results = []
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Image selectors
            images = soup.select('img[src], img[data-src]')
            
            for img in images[:20]:
                try:
                    src = img.get('src') or img.get('data-src')
                    alt = img.get('alt', 'Image')
                    
                    if src and ('http' in src or src.startswith('/')):
                        if not src.startswith('http'):
                            src = urljoin(self.base_url, src)
                        
                        results.append({
                            'title': alt[:100] or "Image",
                            'url': src,
                            'thumbnail': src,
                            'description': alt[:200],
                            'source': 'Yep',
                            'type': 'image',
                            'scraped_at': datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing image: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Image parsing error: {e}")
        
        return results


class TavilySearcher:
    """Tavily API searcher with fallback"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"
        self.timeout = 12
        self.cache = CacheManager(ttl=3600)
        self.ai_enhancer = AIEnhancer()
    
    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search using Tavily API"""
        cached = self.cache.get(query, "tavily")
        if cached:
            return cached[:num_results]
        
        try:
            logger.info(f"🔍 Searching Tavily: '{query}'")
            start_time = time.time()
            
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": num_results,
                "include_answer": True,
            }
            
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for result in data.get('results', []):
                results.append({
                    'title': result.get('title', 'Untitled')[:200],
                    'url': result.get('url', ''),
                    'description': result.get('content', '')[:300],
                    'source': 'Tavily',
                    'score': result.get('score', 0.5),
                    'type': 'web',
                    'retrieved_at': datetime.now().isoformat(),
                })
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Found {len(results)} Tavily results in {elapsed:.2f}s")
            
            # Apply AI ranking
            results = self.ai_enhancer.rank_by_relevance(results, query)
            
            self.cache.set(query, "tavily", results)
            return results
        
        except Exception as e:
            logger.error(f"❌ Tavily error: {e}")
            return []


class UCXSearch:
    """
    🚀 UCX Search Engine v2.5 - Enterprise Grade
    Primary: Yep (no API key needed!)
    Features: Web/News/Image search, AI summaries, Advanced ranking, Chat mode
    """
    
    def __init__(self, tavily_api_key: str, cache_ttl: int = 3600):
        self.yep_scraper = YepScraper(cache_ttl=cache_ttl)
        self.tavily_searcher = TavilySearcher(tavily_api_key)
        self.search_history = []
        self.chat_history = []
        self.ai_enhancer = AIEnhancer()
    
    def search(self, query: str, search_type: str = 'web', num_results: int = 10,
               use_fallback: bool = True, use_ai: bool = True) -> Dict:
        """
        Unified search across all types
        
        Args:
            query: Search query
            search_type: 'web', 'news', 'images'
            num_results: Number of results
            use_fallback: Fall back to Tavily if needed
            use_ai: Enable AI ranking and summaries
        """
        if not query or not query.strip():
            return {
                'success': False,
                'error': 'Query cannot be empty',
                'results': [],
                'total': 0,
            }
        
        query = query.strip()
        start_time = time.time()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 UCX SEARCH: '{query}' ({search_type})")
        logger.info(f"{'='*60}")
        
        try:
            # Search Yep first
            results = self.yep_scraper.search(query, search_type=search_type, num_results=num_results)
            source_used = "Yep 🌐"
            
            # Fallback to Tavily if needed and not image/news search
            if not results and use_fallback and search_type == 'web':
                logger.info("⚠️ Yep returned no results, switching to Tavily...")
                results = self.tavily_searcher.search(query, num_results=num_results)
                source_used = "Tavily 🔄"
            
            # Deduplicate
            results = self._deduplicate(results)
            
            # Generate AI summary if enabled
            ai_summary = None
            if use_ai and results:
                ai_summary = self.ai_enhancer.generate_summary(results)
            
            elapsed = time.time() - start_time
            
            search_result = {
                'success': len(results) > 0,
                'query': query,
                'search_type': search_type,
                'source': source_used,
                'total': len(results),
                'results': results[:num_results],
                'ai_summary': ai_summary,
                'timestamp': datetime.now().isoformat(),
                'execution_time': elapsed
            }
            
            self.search_history.append(search_result)
            return search_result
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total': 0,
            }
    
    def chat(self, message: str, search_enabled: bool = True) -> Dict:
        """
        AI Chat mode with optional search integration
        
        Args:
            message: User message
            search_enabled: Enable web search for context
        """
        logger.info(f"💬 Chat: {message}")
        
        response = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'search_results': None,
        }
        
        # Extract search query if enabled
        if search_enabled and any(word in message.lower() for word in ['search', 'find', 'what', 'how', 'who']):
            search_results = self.search(message, search_type='web', num_results=5, use_ai=True)
            response['search_results'] = search_results
            response['ai_context'] = search_results.get('ai_summary')
        
        # Generate response
        response['response'] = self._generate_chat_response(message, response.get('search_results'))
        
        self.chat_history.append(response)
        return response
    
    def _generate_chat_response(self, message: str, search_results: Dict = None) -> str:
        """Generate intelligent chat response"""
        response_parts = []
        
        if search_results and search_results.get('total', 0) > 0:
            response_parts.append(f"Based on my search, I found {search_results['total']} relevant results.")
            
            if search_results.get('ai_summary'):
                response_parts.append(f"\nKey findings:\n{search_results['ai_summary']}")
            
            if search_results.get('results'):
                response_parts.append(f"\nTop result: {search_results['results'][0]['title']}")
                response_parts.append(f"Source: {search_results['results'][0]['url']}")
        else:
            response_parts.append("I'm here to help! I can search the web, find news, and provide information.")
        
        return '\n'.join(response_parts)
    
    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results"""
        seen = set()
        unique = []
        
        for result in results:
            url = result.get('url', '').lower().split('?')[0]
            if url and url not in seen:
                seen.add(url)
                unique.append(result)
            elif not url:
                unique.append(result)
        
        return unique
    
    def get_history(self) -> List[Dict]:
        """Get search history"""
        return self.search_history
    
    def get_chat_history(self) -> List[Dict]:
        """Get chat history"""
        return self.chat_history
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self.yep_scraper.cache.clear()
        self.tavily_searcher.cache.clear()
        logger.info("✅ Cache cleared")
