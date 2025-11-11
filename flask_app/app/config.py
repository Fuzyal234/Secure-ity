import os
from datetime import timedelta

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
    
    # Database
    # This application uses Supabase (see app/db/supabase_client.py).
    # No SQLAlchemy configuration is used in stateless mode.
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=15)
    JWT_ALGORITHM = 'HS256'
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = 'Strict'
    
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
    
    # Rate Limiting (stateless default: in-memory)
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
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
    LOG_LEVEL = 'DEBUG'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}

