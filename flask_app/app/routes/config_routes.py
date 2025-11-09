from flask import Blueprint, request, jsonify  # type: ignore
from flask_jwt_extended import get_jwt_identity, get_jwt  # type: ignore
from datetime import datetime

from app.db.supabase_client import get_supabase_client
from app.services.rbac import has_permission, requires_any_permission, requires_permissions
from app.services.session_manager import get_session_manager
from app.utils.encryption import get_encryption_service
from app.utils.logger import log_security_event
from app.utils.validation import sanitize_input, validate_config_data

config_bp = Blueprint('config', __name__)
session_manager = get_session_manager()


def _ensure_active_session(claims, user_id):
    session_id = claims.get('session_id')
    if not session_manager.ensure_active_session(session_id, user_id):
        session_manager.revoke_session(session_id)
        return False
    return True


@config_bp.route('', methods=['GET'])
@requires_any_permission('config:read', 'config:read:own')
def list_configs():
    """List all configuration data for current user (admin sees all)"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        if not _ensure_active_session(claims, user_id):
            return jsonify({'error': 'Session expired'}), 401
        is_admin = has_permission(claims.get('role'), 'config:read')
        username = claims.get('username')
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)

        client = get_supabase_client()
        q = client.table('config_data').select('id, user_id, name, description, version, created_at, updated_at, created_by, updated_by, is_deleted').eq('is_deleted', False)
        if not is_admin:
            q = q.eq('user_id', user_id)
        start = (page - 1) * per_page
        end = start + per_page - 1
        q = q.order('created_at', desc=True).range(start, end)
        resp = q.execute()
        items = getattr(resp, 'data', []) or []
        count_q = client.table('config_data').select('id', count='exact').eq('is_deleted', False)
        if not is_admin:
            count_q = count_q.eq('user_id', user_id)
        count_resp = count_q.execute()
        total = getattr(count_resp, 'count', None) or len(items)
        pages = (total + per_page - 1) // per_page if total is not None else None
        result = {
            'configs': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }
        log_security_event('config_list', 'Listed configurations', 'info', 'success', {'count': len(items)}, user_id, username)
        return jsonify(result), 200
        
    except Exception as exc:
        log_security_event('config_list', f'Error listing configs: {str(exc)}', 'error', 'failure')
        return jsonify({'error': 'Failed to list configurations'}), 500

@config_bp.route('/<int:config_id>', methods=['GET'])
@requires_any_permission('config:read', 'config:read:own')
def get_config(config_id):
    """Get specific configuration data"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        if not _ensure_active_session(claims, user_id):
            return jsonify({'error': 'Session expired'}), 401
        is_admin = has_permission(claims.get('role'), 'config:read')
        username = claims.get('username')

        client = get_supabase_client()
        resp = client.table('config_data').select('*').eq('id', config_id).limit(1).execute()
        recs = getattr(resp, 'data', []) or []
        if not recs:
            return jsonify({'error': 'Configuration not found'}), 404
        cfg = recs[0]
        if cfg.get('is_deleted'):
            return jsonify({'error': 'Configuration not found'}), 404
        if not is_admin and cfg.get('user_id') != user_id:
            log_security_event('config_access', f'Unauthorized access attempt to config {config_id}', 'warning', 'failure', {'config_id': config_id}, user_id, username)
            return jsonify({'error': 'Unauthorized'}), 403
        encryption_service = get_encryption_service()
        decrypted_data = encryption_service.decrypt(
            cfg.get('encrypted_data'),
            cfg.get('data_hash'),
            cfg.get('iv'),
            cfg.get('key_version'),
            cfg.get('encryption_algorithm'),
        )
        result = {
            'id': cfg.get('id'),
            'user_id': cfg.get('user_id'),
            'name': cfg.get('name'),
            'description': cfg.get('description'),
            'version': cfg.get('version'),
            'created_at': cfg.get('created_at'),
            'updated_at': cfg.get('updated_at'),
            'created_by': cfg.get('created_by'),
            'updated_by': cfg.get('updated_by'),
            'is_deleted': cfg.get('is_deleted'),
            'data': decrypted_data
        }
        log_security_event('config_read', f'Accessed configuration: {cfg.get("name")}', 'info', 'success', {'config_id': config_id}, user_id, username)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': f'Decryption failed: {str(e)}'}), 500
    except Exception as e:
        log_security_event('config_read', f'Error reading config: {str(e)}', 'error', 'failure', {'config_id': config_id})
        return jsonify({'error': 'Failed to read configuration'}), 500

@config_bp.route('', methods=['POST'])
@requires_any_permission('config:write', 'config:write:own')
def create_config():
    """Create new configuration data"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        if not _ensure_active_session(claims, user_id):
            return jsonify({'error': 'Session expired'}), 401
        username = claims.get('username')
        # Permission decorator already ensures caller has write rights; optional for auditing
        has_permission(claims.get('role'), 'config:write')
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = sanitize_input(data.get('name', ''), max_length=255)
        description = sanitize_input(data.get('description', ''), max_length=1000) if data.get('description') else None
        config_data = data.get('data')
        
        # Validation
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        if not config_data:
            return jsonify({'error': 'Configuration data is required'}), 400
        
        is_valid, error_msg = validate_config_data(config_data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        client = get_supabase_client()
        dup = client.table('config_data').select('id').eq('user_id', user_id).eq('name', name).eq('is_deleted', False).limit(1).execute()
        if getattr(dup, 'data', None):
            return jsonify({'error': 'Configuration with this name already exists'}), 409
        encryption_service = get_encryption_service()
        encrypted_payload = encryption_service.encrypt(config_data)
        payload = {
            'user_id': user_id,
            'name': name,
            'description': description,
            'encrypted_data': encrypted_payload.ciphertext,
            'data_hash': encrypted_payload.data_hash,
            'iv': encrypted_payload.iv,
            'key_version': encrypted_payload.key_version,
            'encryption_algorithm': encrypted_payload.algorithm,
            'version': 1,
            'created_by': username,
            'updated_by': username,
            'is_deleted': False
        }
        resp = client.table('config_data').insert(payload).execute()
        if getattr(resp, 'error', None):
            log_security_event('config_create', f'Error creating config: {str(resp.error)}', 'error', 'failure')
            return jsonify({'error': 'Failed to create configuration'}), 500
        created = (resp.data or [{}])[0]
        result = {
            'id': created.get('id'),
            'user_id': user_id,
            'name': name,
            'description': description,
            'version': 1,
            'created_at': created.get('created_at'),
            'updated_at': created.get('updated_at'),
            'created_by': username,
            'updated_by': username,
            'is_deleted': False
        }
        log_security_event('config_create', f'Created configuration: {name}', 'info', 'success', {'config_id': result['id'], 'name': name}, user_id, username)
        return jsonify({'message': 'Configuration created successfully', 'config': result}), 201
        
    except Exception as exc:
        log_security_event('config_create', f'Error creating config: {str(exc)}', 'error', 'failure')
        return jsonify({'error': 'Failed to create configuration'}), 500

@config_bp.route('/<int:config_id>', methods=['PUT'])
@requires_any_permission('config:write', 'config:write:own')
def update_config(config_id):
    """Update configuration data"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        if not _ensure_active_session(claims, user_id):
            return jsonify({'error': 'Session expired'}), 401
        is_admin = has_permission(claims.get('role'), 'config:write')
        username = claims.get('username')
        
        client = get_supabase_client()
        resp = client.table('config_data').select('*').eq('id', config_id).limit(1).execute()
        recs = getattr(resp, 'data', []) or []
        if not recs:
            return jsonify({'error': 'Configuration not found'}), 404
        config = recs[0]
        if config.get('is_deleted'):
            return jsonify({'error': 'Configuration not found'}), 404
        if not is_admin and config.get('user_id') != user_id:
            log_security_event('config_update', f'Unauthorized update attempt to config {config_id}', 'warning', 'failure', {'config_id': config_id}, user_id, username)
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        update = {}
        if 'name' in data:
            update['name'] = sanitize_input(data['name'], max_length=255)
        if 'description' in data:
            update['description'] = sanitize_input(data.get('description', ''), max_length=1000) if data.get('description') else None
        if 'data' in data:
            cfg_data = data['data']
            is_valid, error_msg = validate_config_data(cfg_data)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            encryption_service = get_encryption_service()
            encrypted_payload = encryption_service.encrypt(cfg_data)
            update['encrypted_data'] = encrypted_payload.ciphertext
            update['data_hash'] = encrypted_payload.data_hash
            update['iv'] = encrypted_payload.iv
            update['key_version'] = encrypted_payload.key_version
            update['encryption_algorithm'] = encrypted_payload.algorithm
            update['version'] = (config.get('version') or 1) + 1
        update['updated_by'] = username
        update['updated_at'] = datetime.utcnow().isoformat()
        resp = client.table('config_data').update(update).eq('id', config_id).execute()
        if getattr(resp, 'error', None):
            log_security_event('config_update', f'Error updating config: {str(resp.error)}', 'error', 'failure', {'config_id': config_id})
            return jsonify({'error': 'Failed to update configuration'}), 500
        out = client.table('config_data').select('id, user_id, name, description, version, created_at, updated_at, created_by, updated_by, is_deleted').eq('id', config_id).limit(1).execute()
        item = (getattr(out, 'data', []) or [{}])[0]
        log_security_event('config_update', f'Updated configuration: {item.get("name")}', 'info', 'success', {'config_id': config_id, 'version': item.get('version')}, user_id, username)
        return jsonify({'message': 'Configuration updated successfully', 'config': item}), 200
        
    except ValueError as e:
        return jsonify({'error': f'Encryption failed: {str(e)}'}), 500
    except Exception as e:
        log_security_event('config_update', f'Error updating config: {str(e)}', 'error', 'failure', {'config_id': config_id})
        return jsonify({'error': 'Failed to update configuration'}), 500

@config_bp.route('/<int:config_id>', methods=['DELETE'])
@requires_any_permission('config:delete', 'config:delete:own')
def delete_config(config_id):
    """Soft delete configuration data"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        if not _ensure_active_session(claims, user_id):
            return jsonify({'error': 'Session expired'}), 401
        is_admin = has_permission(claims.get('role'), 'config:delete')
        username = claims.get('username')
        
        client = get_supabase_client()
        resp = client.table('config_data').select('id, user_id, name, is_deleted').eq('id', config_id).limit(1).execute()
        recs = getattr(resp, 'data', []) or []
        if not recs:
            return jsonify({'error': 'Configuration not found'}), 404
        cfg = recs[0]
        if cfg.get('is_deleted'):
            return jsonify({'error': 'Configuration already deleted'}), 404
        if not is_admin and cfg.get('user_id') != user_id:
            log_security_event('config_delete', f'Unauthorized delete attempt to config {config_id}', 'warning', 'failure', {'config_id': config_id}, user_id, username)
            return jsonify({'error': 'Unauthorized'}), 403
        delete_resp = client.table('config_data').delete().eq('id', config_id).execute()
        if getattr(delete_resp, 'error', None):
            log_security_event('config_delete', f'Error deleting config: {str(delete_resp.error)}', 'error', 'failure', {'config_id': config_id})
            return jsonify({'error': 'Failed to delete configuration'}), 500
        log_security_event('config_delete', f'Permanently deleted configuration: {cfg.get("name")}', 'info', 'success', {'config_id': config_id}, user_id, username)
        return jsonify({'message': 'Configuration deleted successfully'}), 200
        
    except Exception as e:
        log_security_event('config_delete', f'Error deleting config: {str(e)}', 'error', 'failure', {'config_id': config_id})
        return jsonify({'error': 'Failed to delete configuration'}), 500

@config_bp.route('/audit', methods=['GET'])
@requires_permissions('config:audit')
def get_config_audit():
    """Get audit log for configuration changes (admin only)"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        if not _ensure_active_session(claims, user_id):
            return jsonify({'error': 'Session expired'}), 401
        
        from app.services.security_audit import SecurityAuditService
        
        hours = request.args.get('hours', 24, type=int)
        config_id = request.args.get('config_id', type=int)
        
        audit_service = SecurityAuditService()
        
        if config_id:
            events = audit_service.get_config_changes(config_id=config_id, hours=hours)
        else:
            events = audit_service.get_config_changes(hours=hours)
        
        return jsonify({
            'events': events,
            'count': len(events)
        }), 200
        
    except Exception as exc:
        log_security_event('config_audit', f'Error fetching audit log: {str(exc)}', 'error', 'failure')
        return jsonify({'error': 'Failed to get audit log'}), 500

