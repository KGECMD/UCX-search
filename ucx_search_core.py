"""
UCX Search Engine Core
Primary: Yep Search (web scraping - no API key needed)
Fallback: Tavily API
Privacy-focused, fast, and lightweight
"""

import os
import json
import time
import requests
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote, urljoin
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from functools import lru_cache
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CacheManager:
    """Simple in-memory cache for search results"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.Lock()
    
    def get_key(self, query: str, source: str) -> str:
        """Generate cache key from query"""
        content = f"{query.lower().strip()}_{source}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, source: str) -> Optional[Dict]:
        """Retrieve from cache if valid"""
        with self.lock:
            key = self.get_key(query, source)
            if key in self.cache:
                cached, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    logger.info(f"📦 Cache hit for: {query}")
                    return cached
                else:
                    del self.cache[key]
            return None
    
    def set(self, query: str, source: str, data: Dict) -> None:
        """Store in cache"""
        with self.lock:
            key = self.get_key(query, source)
            self.cache[key] = (data, time.time())
    
    def clear(self) -> None:
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()


class YepScraper:
    """High-performance Yep Search scraper - no API key required"""
    
    def __init__(self, cache_ttl: int = 3600):
        self.base_url = "https://yep.com/search"
        self.cache = CacheManager(ttl=cache_ttl)
        self.session = self._create_session()
        self.timeout = 10
        self.max_retries = 2
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        return session
    
    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Scrape search results from Yep.com - FAST & PRIVACY FOCUSED
        
        Args:
            query: Search query string
            num_results: Number of results to retrieve
            
        Returns:
            List of search result dictionaries
        """
        # Check cache first
        cached = self.cache.get(query, "yep")
        if cached:
            return cached[:num_results]
        
        try:
            logger.info(f"🔍 Scraping Yep for: '{query}'")
            start_time = time.time()
            
            params = {
                'q': quote(query),
                'type': 'web'
            }
            
            # Attempt with retries for resilience
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
                        logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying...")
                        time.sleep(1)
                    else:
                        raise
            
            results = self._parse_results(response.text)
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Found {len(results)} Yep results in {elapsed:.2f}s")
            
            # Cache results
            self.cache.set(query, "yep", results)
            
            return results[:num_results]
            
        except Exception as e:
            logger.warning(f"⚠️ Yep scraping failed: {e}")
            return []
    
    def _parse_results(self, html: str) -> List[Dict]:
        """
        Parse Yep HTML results with optimized BeautifulSoup
        
        Args:
            html: HTML content from Yep
            
        Returns:
            List of parsed results
        """
        results = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Try multiple parsing strategies for robustness
            result_items = soup.find_all('div', class_=lambda x: x and 'result' in x.lower())
            
            if not result_items:
                result_items = soup.find_all('article')
            
            if not result_items:
                result_items = soup.find_all('a', {'class': lambda x: x and 'link' in x.lower()})
            
            for item in result_items[:20]:  # Limit to avoid memory bloat
                try:
                    # Extract title
                    title_elem = item.find(['h2', 'h3', 'a', 'span'])
                    title = title_elem.get_text(strip=True) if title_elem else None
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Extract URL
                    link_elem = item.find('a', href=True)
                    if not link_elem:
                        link_elem = item.parent.find('a', href=True) if item.parent else None
                    
                    url = link_elem.get('href', '') if link_elem else None
                    
                    if not url or not url.startswith('http'):
                        if url and url.startswith('/'):
                            url = urljoin('https://yep.com', url)
                        else:
                            continue
                    
                    # Extract description
                    desc_elem = item.find(['p', 'span'], class_=lambda x: x and ('desc' in x.lower() or 'snippet' in x.lower()))
                    if not desc_elem:
                        desc_elem = item.find(['p', 'div'], string=lambda x: x and len(x.strip()) > 20)
                    
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Skip ads and spam
                    if any(skip in url.lower() for skip in ['ad.', '/ads/', 'sponsored', 'yep.com/search']):
                        continue
                    
                    # Validate result
                    if title and url and len(title) > 2:
                        result = {
                            'title': title[:200],
                            'url': url,
                            'description': description[:300] if description else "No description available",
                            'source': 'Yep',
                            'scraped_at': datetime.now().isoformat(),
                            'relevance': self._calculate_relevance(title, description)
                        }
                        results.append(result)
                
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
        
        # Sort by relevance
        results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return results
    
    def _calculate_relevance(self, title: str, description: str) -> float:
        """Calculate simple relevance score"""
        score = 0.0
        
        # Title length (longer = more substantial)
        score += min(len(title) / 100, 0.3)
        
        # Description exists
        if description and len(description) > 50:
            score += 0.4
        
        # General quality indicators
        if any(word in title.lower() for word in ['guide', 'tutorial', 'how', 'best']):
            score += 0.3
        
        return score


class TavilySearcher:
    """Fast Tavily API fallback searcher"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"
        self.timeout = 10
        self.cache = CacheManager(ttl=3600)
    
    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search using Tavily API with caching
        
        Args:
            query: Search query string
            num_results: Number of results to retrieve
            
        Returns:
            List of search results from Tavily
        """
        # Check cache
        cached = self.cache.get(query, "tavily")
        if cached:
            return cached[:num_results]
        
        try:
            logger.info(f"🔍 Searching Tavily for: '{query}'")
            start_time = time.time()
            
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": num_results,
                "include_answer": True,
                "include_raw_content": False
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
                    'title': result.get('title', 'Untitled'),
                    'url': result.get('url', ''),
                    'description': result.get('content', '')[:300],
                    'source': 'Tavily',
                    'score': result.get('score', 0.5),
                    'retrieved_at': datetime.now().isoformat(),
                    'relevance': result.get('score', 0.5)
                })
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Found {len(results)} Tavily results in {elapsed:.2f}s")
            
            # Cache results
            self.cache.set(query, "tavily", results)
            return results
            
        except Exception as e:
            logger.error(f"❌ Tavily error: {e}")
            return []


class UCXSearch:
    """
    🚀 UCX Search Engine - Privacy-Focused, Fast, and Powerful
    Primary: Yep (no API key needed!)
    Fallback: Tavily API
    """
    
    def __init__(self, tavily_api_key: str, cache_ttl: int = 3600, enable_threading: bool = True):
        """
        Initialize UCX Search Engine
        
        Args:
            tavily_api_key: Your Tavily API key for fallback
            cache_ttl: Cache time-to-live in seconds
            enable_threading: Enable multi-threaded searching
        """
        self.yep_scraper = YepScraper(cache_ttl=cache_ttl)
        self.tavily_searcher = TavilySearcher(tavily_api_key)
        self.search_history = []
        self.enable_threading = enable_threading
        self.executor = ThreadPoolExecutor(max_workers=3) if enable_threading else None
    
    def search(self, query: str, num_results: int = 10, use_fallback: bool = True,
               parallel: bool = False) -> Dict:
        """
        Perform UCX search (Yep primary, Tavily fallback)
        
        Args:
            query: Search query string
            num_results: Number of results to retrieve
            use_fallback: Use Tavily if Yep fails
            parallel: Search both sources in parallel
            
        Returns:
            Dictionary containing search results and metadata
        """
        if not query or not query.strip():
            return {
                'success': False,
                'error': 'Query cannot be empty',
                'results': [],
                'total': 0,
                'source': 'None'
            }
        
        query = query.strip()
        start_time = time.time()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 UCX SEARCH: '{query}'")
        logger.info(f"{'='*60}")
        
        if parallel and self.enable_threading:
            results = self._parallel_search(query, num_results)
        else:
            # Try Yep first (primary method)
            results = self.yep_scraper.search(query, num_results)
            source_used = "Yep 🌐"
            
            # If Yep fails and fallback enabled, use Tavily
            if not results and use_fallback:
                logger.info("⚠️ Yep returned no results, switching to Tavily...")
                results = self.tavily_searcher.search(query, num_results)
                source_used = "Tavily 🔄"
        
        # Deduplicate and sort
        results = self._deduplicate_and_sort(results)
        
        elapsed = time.time() - start_time
        
        search_result = {
            'success': len(results) > 0,
            'query': query,
            'source': source_used if not parallel else "Yep + Tavily",
            'total': len(results),
            'results': results[:num_results],
            'timestamp': datetime.now().isoformat(),
            'execution_time': elapsed
        }
        
        self.search_history.append(search_result)
        return search_result
    
    def _parallel_search(self, query: str, num_results: int) -> List[Dict]:
        """Search both sources in parallel for speed"""
        results = []
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            yep_future = executor.submit(self.yep_scraper.search, query, num_results)
            tavily_future = executor.submit(self.tavily_searcher.search, query, num_results)
            
            try:
                yep_results = yep_future.result(timeout=15)
                results.extend(yep_results)
            except:
                pass
            
            try:
                tavily_results = tavily_future.result(timeout=15)
                results.extend(tavily_results)
            except:
                pass
        
        return results
    
    def _deduplicate_and_sort(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicates and sort by relevance"""
        seen = {}
        unique = []
        
        for result in results:
            url = result['url'].lower().split('?')[0]
            domain = url.split('/')[2] if len(url.split('/')) > 2 else url
            
            if domain not in seen:
                seen[domain] = True
                unique.append(result)
        
        # Sort by relevance
        unique.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return unique
    
    def display_results(self, search_result: Dict) -> None:
        """Pretty print search results"""
        if not search_result['success']:
            print(f"❌ Search failed: {search_result.get('error', 'Unknown error')}")
            return
        
        print(f"\n{'='*70}")
        print(f"📊 UCX Search Results")
        print(f"{'='*70}")
        print(f"Query: {search_result['query']}")
        print(f"Source: {search_result['source']}")
        print(f"Results: {search_result['total']} | Time: {search_result.get('execution_time', 0):.2f}s")
        print(f"{'-'*70}\n")
        
        for i, result in enumerate(search_result['results'], 1):
            print(f"{i}. {result['title']}")
            print(f"   🔗 {result['url'][:60]}...")
            print(f"   📝 {result['description'][:80]}...")
            print(f"   ⭐ {result['source']}")
            print()
    
    def save_results(self, search_result: Dict, filename: str = None) -> str:
        """Save results to JSON"""
        if not filename:
            query_safe = search_result['query'].replace(' ', '_')[:30]
            filename = f"ucx_results_{query_safe}_{int(time.time())}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(search_result, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Results saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
            return None
    
    def get_history(self) -> List[Dict]:
        """Get search history"""
        return self.search_history
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self.yep_scraper.cache.clear()
        self.tavily_searcher.cache.clear()
        logger.info("✅ Cache cleared")
    
    def __del__(self):
        """Cleanup thread executor"""
        if self.executor:
            self.executor.shutdown(wait=False)
