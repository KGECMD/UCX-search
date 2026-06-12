"""
UCX Search Configuration Module
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ucx-search-secret-key')
    
    # Server
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Search
    TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')
    YEP_TIMEOUT = int(os.environ.get('YEP_TIMEOUT', 10))
    TAVILY_TIMEOUT = int(os.environ.get('TAVILY_TIMEOUT', 10))
    
    # Cache
    CACHE_TTL = int(os.environ.get('CACHE_TTL', 3600))  # 1 hour
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() == 'true'
    
    # Threading
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 3))
    ENABLE_THREADING = os.environ.get('ENABLE_THREADING', 'true').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'ucx_search.log')
    
    # Performance
    MAX_RESULTS = int(os.environ.get('MAX_RESULTS', 50))
    MIN_RESULTS = int(os.environ.get('MIN_RESULTS', 1))
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    RATE_LIMIT = int(os.environ.get('RATE_LIMIT', 100))  # requests per minute


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://yourdomain.com')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    CACHE_ENABLED = False


def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'production')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(env, ProductionConfig)
