import os

import redis  # type: ignore
from flask import Blueprint, jsonify, current_app  # type: ignore

from app.db.supabase_client import SupabaseConfigError, get_supabase_client

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    errors_detected = False
    degraded = False

    status = {
        'database': 'unknown',
        'redis': 'unknown',
    }
    
    # Check Supabase
    try:
        client = get_supabase_client()
        resp = client.table('users').select('id').limit(1).execute()
        if getattr(resp, 'error', None):
            raise RuntimeError(str(resp.error))
        status['database'] = 'connected'
    except SupabaseConfigError:
        status['database'] = 'not_configured'
        degraded = True
    except Exception as e:
        status['database'] = f'error: {str(e)}'
        degraded = True
    
    effective_storage = current_app.config.get('RATELIMIT_EFFECTIVE_STORAGE_URI')
    redis_url = None
    if effective_storage and effective_storage.startswith('redis://'):
        redis_url = effective_storage
    else:
        redis_url = os.environ.get('REDIS_URL')

    if not redis_url or redis_url.startswith('memory://'):
        status['redis'] = 'not_configured'
        degraded = True
    else:
        try:
            redis_password = os.environ.get('REDIS_PASSWORD')
            if redis_password and 'redis://' in redis_url:
                if '@' not in redis_url or redis_url.count('@') == 0:
                    redis_url = redis_url.replace('redis://', f'redis://:{redis_password}@')
                elif redis_url.count('@') == 1 and not redis_url.split('://')[1].split('@')[0]:
                    redis_url = redis_url.replace('redis://@', f'redis://:{redis_password}@')

            r = redis.from_url(redis_url)
            r.ping()
            status['redis'] = 'connected'
        except Exception as e:
            status['redis'] = f'error: {str(e)}'
            degraded = True

    status['status'] = 'healthy'
    if degraded:
        status['status'] = 'degraded'
    if errors_detected:
        status['status'] = 'unhealthy'

    return jsonify(status), 200

