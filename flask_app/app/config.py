import os
from datetime import timedelta
from sqlalchemy.pool import StaticPool

def _prepare_database_url(url):
    """Prepare database URL with SSL for Supabase"""
    if not url:
        return None
    # Ensure SSL is enabled for Supabase (required)
    if 'supabase.co' in url and 'sslmode' not in url:
        # Add SSL parameters if not present
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}sslmode=require"
    return url

# Get database URL from environment
_raw_db_url = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DATABASE_URL')
_prepared_db_url = _prepare_database_url(_raw_db_url) if _raw_db_url else None

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Supabase Database Configuration
    # Supabase provides connection strings in format:
    # postgresql://postgres:[PASSWORD]@[PROJECT_REF].supabase.co:5432/postgres
    # For connection pooling (recommended): postgresql://postgres:[PASSWORD]@[PROJECT_REF].supabase.co:6543/postgres
    # SQLAlchemy is kept primarily for testing; in production Supabase client is used directly.
    # Fallback to in-memory SQLite when no DATABASE_URL is provided.
    SQLALCHEMY_DATABASE_URI = _prepared_db_url or 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Supabase connection pool settings
    # Use connection pooling for better performance with Supabase
    if _prepared_db_url and 'supabase.co' in _prepared_db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,  # Verify connections before using
            'pool_recycle': 300,    # Recycle connections after 5 minutes
            'pool_size': 5,         # Reduced for Supabase connection limits
            'max_overflow': 10,     # Additional connections beyond pool_size
            'connect_args': {
                'sslmode': 'require'  # Require SSL for Supabase
            }
        }
    elif _prepared_db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 10,
            'max_overflow': 20
        }
    else:
        # In-memory SQLite fallback for testing and local development without Supabase
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool
        }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = 'Strict'
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://redis:6379/0'
    
    # Encryption Configuration
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or None
    if not ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY environment variable must be set")
    
    # Security Settings
    BCRYPT_LOG_ROUNDS = 12
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = REDIS_URL
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 30  # Keep 30 days of logs
    
    # Application Settings
    ENV = os.environ.get('ENV', 'production')
    DEBUG = False
    TESTING = False
    
    # CORS Settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    LOG_LEVEL = 'INFO'
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_HTTPONLY = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    # Use in-memory SQLite for testing (bypass Supabase)
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    REDIS_URL = 'redis://localhost:6379/1'
    LOG_LEVEL = 'DEBUG'
    # Override database URL check for testing
    DATABASE_URL = SQLALCHEMY_DATABASE_URI

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}

