import os
from contextlib import closing
from urllib.parse import urlparse
import socket

from flask_jwt_extended import JWTManager  # type: ignore
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore

from app.services.redis_client import get_redis_client

# Shared extension instances
jwt = JWTManager()
def _resolve_limiter_storage():
    default_storage = "memory://"
    storage_url = (
        os.environ.get("RATELIMIT_STORAGE_URL")
        or os.environ.get("RATELIMIT_STORAGE_URI")
        or os.environ.get("REDIS_URL")
    )

    if not storage_url:
        return default_storage, "missing configuration"

    if storage_url.startswith("memory://"):
        return storage_url, None

    if storage_url.startswith("redis://"):
        try:
            parsed = urlparse(storage_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            timeout = float(os.environ.get("REDIS_CONNECT_TIMEOUT", "1.0"))
            with closing(socket.create_connection((host, port), timeout=timeout)):
                pass
        except OSError as exc:
            return default_storage, f"Redis unavailable at {storage_url} ({exc})"

    return storage_url, None


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
        """Check if token is blacklisted"""
        jti = jwt_payload['jti']
        try:
            r = get_redis_client()
            return r.get(f"blacklist:{jti}") is not None
        except Exception:
            # If Redis is unavailable, fail open for availability (consider security trade-off)
            app.logger.error("Redis unavailable for token blacklist check")
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

