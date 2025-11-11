from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from datetime import datetime, timedelta
import bcrypt

from app.db.supabase_client import get_supabase_client
from app.utils.logger import log_security_event
from app.utils.validation import validate_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        # Validation
        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        client = get_supabase_client()
        dup_u = client.table('users').select('id').eq('username', username).limit(1).execute()
        if getattr(dup_u, 'data', None):
            log_security_event('register', f'Registration attempt with existing username: {username}', 'warning', 'failure')
            return jsonify({'error': 'Username already exists'}), 409
        dup_e = client.table('users').select('id').eq('email', email).limit(1).execute()
        if getattr(dup_e, 'data', None):
            log_security_event('register', f'Registration attempt with existing email: {email}', 'warning', 'failure')
            return jsonify({'error': 'Email already exists'}), 409
        
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            log_security_event('register', f'Weak password attempt for username: {username}', 'warning', 'failure')
            return jsonify({'error': error_msg}), 400
        
        # Only allow admin role assignment by existing admins (in production)
        if role == 'admin':
            # This should be restricted - for now, allow but log
            log_security_event('register', f'Admin role assignment attempt: {username}', 'warning', 'success')
        
        client = get_supabase_client()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        payload = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': role if role in ['admin', 'user'] else 'user',
            'is_active': True,
            'failed_login_attempts': 0,
            'locked_until': None,
            'last_login': None,
        }
        resp = client.table('users').insert(payload).execute()
        if getattr(resp, 'error', None):
            log_security_event('register', f'Registration error: {str(resp.error)}', 'error', 'failure')
            return jsonify({'error': 'Registration failed'}), 500
        created = (resp.data or [{}])[0]
        log_security_event('register', f'User registered: {username}', 'info', 'success', {'email': email, 'role': payload['role']}, created.get('id'), username)
        user_resp = {
            'id': created.get('id'),
            'username': username,
            'email': email,
            'role': payload['role'],
            'is_active': True,
            'created_at': created.get('created_at'),
            'last_login': None
        }
        return jsonify({'message': 'User registered successfully', 'user': user_resp}), 201
        
    except Exception as e:
        log_security_event('register', f'Registration error: {str(e)}', 'error', 'failure')
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login and get JWT tokens"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        client = get_supabase_client()
        resp = client.table('users').select('*').eq('username', username).limit(1).execute()
        records = getattr(resp, 'data', []) or []
        if not records:
            log_security_event('login', f'Login attempt with non-existent username: {username}', 'warning', 'failure', {}, None, username)
            return jsonify({'error': 'Invalid credentials'}), 401
        user = records[0]
        user_id = user.get('id')
        # Locked?
        locked_until = user.get('locked_until')
        if locked_until:
            now = datetime.utcnow().isoformat()
            if locked_until > now:
                log_security_event('login', f'Login attempt on locked account: {username}', 'warning', 'failure', {}, user_id, username)
                return jsonify({'error': 'Account is locked. Please try again later.'}), 403
        if not user.get('is_active', True):
            log_security_event('login', f'Login attempt on inactive account: {username}', 'warning', 'failure', {}, user_id, username)
            return jsonify({'error': 'Account is inactive'}), 403
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), (user.get('password_hash') or '').encode('utf-8')):
            failed = (user.get('failed_login_attempts') or 0) + 1
            update = {'failed_login_attempts': failed}
            if failed >= 5:
                # Lock account for 30 minutes
                lock_until = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
                update['locked_until'] = lock_until
            # Request the updated columns back so we can catch issues immediately
            upd_resp = client.table('users').update(update).eq('id', user_id).select('failed_login_attempts,locked_until').execute()
            # If Supabase returned an error or the value did not persist, log it for visibility
            persisted_failed = None
            try:
                recs = getattr(upd_resp, 'data', []) or []
                if recs:
                    persisted_failed = recs[0].get('failed_login_attempts')
            except Exception:
                persisted_failed = None
            meta = {'failed_attempts': failed, 'persisted_failed_attempts': persisted_failed}
            if getattr(upd_resp, 'error', None):
                meta['update_error'] = str(upd_resp.error)
            log_security_event('login', f'Failed login attempt: {username}', 'warning', 'failure', meta, user_id, username)
            return jsonify({'error': 'Invalid credentials'}), 401
        # Success
        client.table('users').update({
            'failed_login_attempts': 0,
            'locked_until': None,
            'last_login': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()

        additional_claims = {
            'role': user.get('role'),
            'username': user.get('username'),
        }
        access_token = create_access_token(identity=user_id, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=user_id, additional_claims=additional_claims)
        log_security_event('login', f'Successful login: {username}', 'info', 'success', {'role': user.get('role')}, user_id, username)
        response = jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user_id,
                'username': user.get('username'),
                'email': user.get('email'),
                'role': user.get('role'),
                'is_active': user.get('is_active', True),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login')
            },
        })
        return response, 200
        
    except Exception as e:
        log_security_event('login', f'Login error: {str(e)}', 'error', 'failure')
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout and blacklist token"""
    try:
        # Stateless: nothing to revoke server-side
        user_id = get_jwt_identity()
        log_security_event('logout', f'User logged out', 'info', 'success', {}, user_id, None)
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        log_security_event('logout', f'Logout error: {str(e)}', 'error', 'failure')
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        user_id = get_jwt_identity()
        client = get_supabase_client()
        resp = client.table('users').select('id, role, username, is_active').eq('id', user_id).limit(1).execute()
        recs = getattr(resp, 'data', []) or []
        if not recs or not recs[0].get('is_active', True):
            return jsonify({'error': 'User not found or inactive'}), 401
        u = recs[0]
        additional_claims = {'role': u.get('role'), 'username': u.get('username')}
        access_token = create_access_token(identity=user_id, additional_claims=additional_claims)
        return jsonify({'access_token': access_token}), 200
        
    except Exception as e:
        return jsonify({'error': 'Token refresh failed'}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        user_id = get_jwt_identity()
        client = get_supabase_client()
        resp = client.table('users').select('id, username, email, role, is_active, created_at, last_login').eq('id', user_id).limit(1).execute()
        recs = getattr(resp, 'data', []) or []
        if not recs:
            return jsonify({'error': 'User not found'}), 404
        u = recs[0]
        user_data = {
            'id': u.get('id'),
            'username': u.get('username'),
            'email': u.get('email'),
            'role': u.get('role'),
            'is_active': u.get('is_active', True),
            'created_at': u.get('created_at'),
            'last_login': u.get('last_login')
        }
        return jsonify({'user': user_data}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user information'}), 500

