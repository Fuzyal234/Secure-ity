from flask_jwt_extended import JWTManager  # type: ignore
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore

# Shared extension instances
jwt = JWTManager()
def _resolve_limiter_storage():
    # Stateless default: always in-memory rate limit storage
    return "memory://", None


RATE_LIMIT_STORAGE_URI, RATE_LIMIT_FALLBACK_REASON = _resolve_limiter_storage()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=RATE_LIMIT_STORAGE_URI,
)

def setup_jwt_callbacks(jwt, app):
    """Setup JWT callbacks for token blacklisting"""
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Stateless mode: no server-side blacklist, always allow."""
        return False
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token'}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'error': 'Authorization token required'}, 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return {'error': 'Fresh token required'}, 401

