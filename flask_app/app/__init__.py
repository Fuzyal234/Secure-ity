import logging
import os

from flask import Flask
from flask_cors import CORS

from app.extensions import (
    RATE_LIMIT_FALLBACK_REASON,
    RATE_LIMIT_STORAGE_URI,
    jwt,
    limiter,
    setup_jwt_callbacks,
)

_rate_limit_warning_emitted = False

def create_app(config_name=None):
    """Application factory pattern"""
    # Determine static folder path - React build output
    # In container, React build will be at /app/frontend/dist
    # In development, check if dist exists, otherwise use frontend source
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_dist = os.path.join(base_dir, 'frontend', 'dist')
    frontend_path = os.path.join(base_dir, 'frontend')
    
    # Check if React build exists
    if os.path.exists(frontend_dist):
        static_folder = frontend_dist
    elif os.path.exists(os.path.join(base_dir, 'frontend')):
        static_folder = frontend_path
    else:
        # Try absolute path in container
        static_folder = '/app/frontend/dist'
        if not os.path.exists(static_folder):
            static_folder = '/app/frontend'
    
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    
    # Load configuration
    config_name = config_name or os.environ.get('ENV', 'production')
    from .config import config
    app.config.from_object(config[config_name])
    
    # Configure rate limit storage before initializing extensions
    app.config["RATELIMIT_STORAGE_URL"] = RATE_LIMIT_STORAGE_URI
    app.config["RATELIMIT_STORAGE_URI"] = RATE_LIMIT_STORAGE_URI

    # Initialize extensions
    jwt.init_app(app)
    limiter.init_app(app)

    app.config["RATELIMIT_EFFECTIVE_STORAGE_URI"] = RATE_LIMIT_STORAGE_URI

    global _rate_limit_warning_emitted
    if RATE_LIMIT_FALLBACK_REASON and not _rate_limit_warning_emitted:
        logging.getLogger("app.rate_limit").info(
            "Rate limiter falling back to in-memory storage: %s",
            RATE_LIMIT_FALLBACK_REASON,
        )
        _rate_limit_warning_emitted = True
    
    # Setup JWT callbacks
    setup_jwt_callbacks(jwt, app)
    
    # CORS configuration
    if app.config.get('CORS_ORIGINS'):
        CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    else:
        CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    
    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.config_routes import config_bp
    from app.routes.health_routes import health_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(health_bp, url_prefix='')
    
    # Serve React app - SPA routing
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        # Don't interfere with API routes
        if path.startswith('api/'):
            return None
        
        # Serve static files if they exist
        try:
            return app.send_static_file(path)
        except Exception:
            # For SPA routing, serve index.html for all non-API routes
            try:
                return app.send_static_file('index.html')
            except Exception:
                return "Frontend not found. Please build the React app first.", 404
    
    # Setup logging
    from app.utils.logger import setup_logging
    setup_logging(app)
    
    # Security headers middleware
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    return app

