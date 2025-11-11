from flask import Blueprint, jsonify  # type: ignore

from app.db.supabase_client import SupabaseConfigError, get_supabase_client

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    errors_detected = False
    degraded = False

    status = {'database': 'unknown'}
    
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
    
    # Stateless mode: no Redis health

    status['status'] = 'healthy'
    if degraded:
        status['status'] = 'degraded'
    if errors_detected:
        status['status'] = 'unhealthy'

    return jsonify(status), 200

