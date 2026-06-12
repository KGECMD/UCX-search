"""
UCX Search - Initialize Package
"""

__version__ = "2.0.0"
__author__ = "KGECMD"
__description__ = "Privacy-First Search Engine - Yep + Tavily"

from ucx_search_core import UCXSearch, YepScraper, TavilySearcher, CacheManager

__all__ = ['UCXSearch', 'YepScraper', 'TavilySearcher', 'CacheManager']
