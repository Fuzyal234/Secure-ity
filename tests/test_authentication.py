"""
Unit and integration tests for authentication and RBAC
Tests login, register, JWT tokens, and role-based access
"""
import json
from datetime import datetime, timedelta

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token, decode_token

from app import create_app, db
from app.models.user import User
from app.services.session_manager import get_session_manager


@pytest.fixture
def app():
    """Create test application"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create admin user for testing"""
    with app.app_context():
        user = User(
            username='admin_test',
            email='admin@test.com',
            role='admin',
            is_active=True
        )
        user.set_password('AdminPassword123!')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def regular_user(app):
    """Create regular user for testing"""
    with app.app_context():
        user = User(
            username='user_test',
            email='user@test.com',
            role='user',
            is_active=True
        )
        user.set_password('UserPassword123!')
        db.session.add(user)
        db.session.commit()
        return user


class TestUserRegistration:
    """Test user registration endpoint"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'NewPassword123!'
        }
        
        response = client.post('/api/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 201
        result = json.loads(response.data)
        assert result['message'] == 'User registered successfully'
        assert result['user']['username'] == 'newuser'
        assert result['user']['role'] == 'user'  # Default role
        assert 'password' not in result['user']  # Password not in response
    
    def test_register_duplicate_username(self, client, regular_user):
        """Test registration with duplicate username"""
        data = {
            'username': regular_user.username,
            'email': 'different@test.com',
            'password': 'Password123!'
        }
        
        response = client.post('/api/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 409
        result = json.loads(response.data)
        assert 'already exists' in result['error'].lower()
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        data = {
            'username': 'weakuser',
            'email': 'weak@test.com',
            'password': 'short'  # Too short
        }
        
        response = client.post('/api/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        result = json.loads(response.data)
        assert 'password' in result['error'].lower()
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        data = {
            'username': 'incomplete'
            # Missing email and password
        }
        
        response = client.post('/api/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400


class TestUserLogin:
    """Test user login endpoint"""
    
    def test_login_success(self, client, regular_user):
        """Test successful login"""
        data = {
            'username': regular_user.username,
            'password': 'UserPassword123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert 'access_token' in result
        assert 'refresh_token' in result
        assert result['user']['username'] == regular_user.username
        assert 'session' in result
        assert 'id' in result['session']
    
    def test_login_invalid_credentials(self, client, regular_user):
        """Test login with invalid password"""
        data = {
            'username': regular_user.username,
            'password': 'WrongPassword123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 401
        result = json.loads(response.data)
        assert 'invalid' in result['error'].lower()
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        data = {
            'username': 'nonexistent',
            'password': 'Password123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 401
    
    def test_login_inactive_account(self, client, app):
        """Test login with inactive account"""
        with app.app_context():
            user = User(
                username='inactive',
                email='inactive@test.com',
                role='user',
                is_active=False
            )
            user.set_password('Password123!')
            db.session.add(user)
            db.session.commit()
        
        data = {
            'username': 'inactive',
            'password': 'Password123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 403
        result = json.loads(response.data)
        assert 'inactive' in result['error'].lower()
    
    def test_login_account_locked(self, client, app):
        """Test login with locked account"""
        with app.app_context():
            user = User(
                username='locked',
                email='locked@test.com',
                role='user',
                is_active=True,
                locked_until=datetime.utcnow() + timedelta(minutes=30)
            )
            user.set_password('Password123!')
            db.session.add(user)
            db.session.commit()
        
        data = {
            'username': 'locked',
            'password': 'Password123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 403
        result = json.loads(response.data)
        assert 'locked' in result['error'].lower()
    
    def test_login_failed_attempts_lockout(self, client, regular_user):
        """Test account lockout after 5 failed attempts"""
        # Make 5 failed login attempts
        for _ in range(5):
            data = {
                'username': regular_user.username,
                'password': 'WrongPassword123!'
            }
            client.post('/api/auth/login',
                       data=json.dumps(data),
                       content_type='application/json')
        
        # Account should now be locked
        with client.application.app_context():
            user = User.query.filter_by(username=regular_user.username).first()
            assert user.is_locked()
        
        # Try to login with correct password - should fail
        data = {
            'username': regular_user.username,
            'password': 'UserPassword123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 403


class TestJWTTokens:
    """Test JWT token functionality"""
    
    def test_token_contains_claims(self, client, admin_user):
        """Test that JWT token contains correct claims"""
        data = {
            'username': admin_user.username,
            'password': 'AdminPassword123!'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        token = result['access_token']
        
        # Decode token to check claims
        decoded = decode_token(token)
        assert decoded['sub'] == admin_user.id
        assert decoded['role'] == 'admin'
        assert decoded['username'] == admin_user.username
        assert 'session_id' in decoded
    
    def test_token_expiration(self, client, regular_user, app):
        """Test that tokens expire correctly"""
        # Create session and token with short expiration
        session_manager = get_session_manager()
        session_info = session_manager.create_session(
            user_id=regular_user.id,
            username=regular_user.username,
            request=None,
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        with app.app_context():
            from flask_jwt_extended import create_access_token
            token = create_access_token(
                identity=regular_user.id,
                expires_delta=timedelta(seconds=1),
                additional_claims={
                    "role": regular_user.role,
                    "username": regular_user.username,
                    "session_id": session_info.session_id,
                },
            )
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Try to use expired token
        response = client.get('/api/auth/me',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 401
        session_manager.revoke_session(session_info.session_id)
    
    def test_refresh_token(self, client, regular_user):
        """Test token refresh endpoint"""
        # Login to get tokens
        data = {
            'username': regular_user.username,
            'password': 'UserPassword123!'
        }
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps(data),
                                   content_type='application/json')
        refresh_token = json.loads(login_response.data)['refresh_token']
        
        # Refresh access token
        response = client.post('/api/auth/refresh',
                             headers={'Authorization': f'Bearer {refresh_token}'})
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert 'access_token' in result
        assert decode_token(result['access_token'])['session_id'] == decode_token(refresh_token)['session_id']


class TestRBAC:
    """Test Role-Based Access Control"""
    
    def test_admin_access_config_audit(self, client, admin_user):
        """Test that admin can access config audit endpoint"""
        # Login as admin
        data = {
            'username': admin_user.username,
            'password': 'AdminPassword123!'
        }
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps(data),
                                   content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # Access admin-only endpoint
        response = client.get('/api/config/audit',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
    
    def test_user_cannot_access_config_audit(self, client, regular_user):
        """Test that regular user cannot access admin endpoints"""
        # Login as regular user
        data = {
            'username': regular_user.username,
            'password': 'UserPassword123!'
        }
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps(data),
                                   content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # Try to access admin-only endpoint
        response = client.get('/api/config/audit',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 403
        result = json.loads(response.data)
        assert 'access' in result['error'].lower()
    
    def test_user_can_only_access_own_configs(self, client, app, regular_user, admin_user):
        """Test that users can only see their own configs"""
        # Create configs for both users
        with app.app_context():
            from app.models.config_data import ConfigData
            from app.utils.encryption import get_encryption_service
            
            encryption_service = get_encryption_service()
            encrypted_payload = encryption_service.encrypt({"key": "value"})
            
            # Admin's config
            admin_config = ConfigData(
                user_id=admin_user.id,
                name='admin_config',
                encrypted_data=encrypted_payload.ciphertext,
                data_hash=encrypted_payload.data_hash,
                iv=encrypted_payload.iv,
                key_version=encrypted_payload.key_version,
                encryption_algorithm=encrypted_payload.algorithm,
                created_by=admin_user.username,
                updated_by=admin_user.username
            )
            
            # User's config
            user_config = ConfigData(
                user_id=regular_user.id,
                name='user_config',
                encrypted_data=encrypted_payload.ciphertext,
                data_hash=encrypted_payload.data_hash,
                iv=encrypted_payload.iv,
                key_version=encrypted_payload.key_version,
                encryption_algorithm=encrypted_payload.algorithm,
                created_by=regular_user.username,
                updated_by=regular_user.username
            )
            
            db.session.add_all([admin_config, user_config])
            db.session.commit()
        
        # Login as regular user
        data = {
            'username': regular_user.username,
            'password': 'UserPassword123!'
        }
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps(data),
                                   content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # List configs - should only see own
        response = client.get('/api/config',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result['configs']) == 1
        assert result['configs'][0]['name'] == 'user_config'
    
    def test_admin_can_access_all_configs(self, client, app, admin_user, regular_user):
        """Test that admin can see all configs"""
        # Create configs (same as above)
        with app.app_context():
            from app.models.config_data import ConfigData
            from app.utils.encryption import get_encryption_service
            
            encryption_service = get_encryption_service()
            encrypted_payload = encryption_service.encrypt({"key": "value"})
            
            admin_config = ConfigData(
                user_id=admin_user.id,
                name='admin_config',
                encrypted_data=encrypted_payload.ciphertext,
                data_hash=encrypted_payload.data_hash,
                iv=encrypted_payload.iv,
                key_version=encrypted_payload.key_version,
                encryption_algorithm=encrypted_payload.algorithm,
                created_by=admin_user.username,
                updated_by=admin_user.username
            )
            
            user_config = ConfigData(
                user_id=regular_user.id,
                name='user_config',
                encrypted_data=encrypted_payload.ciphertext,
                data_hash=encrypted_payload.data_hash,
                iv=encrypted_payload.iv,
                key_version=encrypted_payload.key_version,
                encryption_algorithm=encrypted_payload.algorithm,
                created_by=regular_user.username,
                updated_by=regular_user.username
            )
            
            db.session.add_all([admin_config, user_config])
            db.session.commit()
        
        # Login as admin
        data = {
            'username': admin_user.username,
            'password': 'AdminPassword123!'
        }
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps(data),
                                   content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # List configs - should see all
        response = client.get('/api/config',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result['configs']) == 2


class TestUnauthorizedAccess:
    """Test unauthorized access attempts"""
    
    def test_protected_route_without_token(self, client):
        """Test accessing protected route without token"""
        response = client.get('/api/config')
        assert response.status_code == 401
    
    def test_protected_route_with_invalid_token(self, client):
        """Test accessing protected route with invalid token"""
        response = client.get('/api/config',
                           headers={'Authorization': 'Bearer invalid_token_12345'})
        assert response.status_code == 422  # Unprocessable entity
    
    def test_protected_route_with_expired_token(self, client, app, regular_user):
        """Test accessing protected route with expired token"""
        with app.app_context():
            from flask_jwt_extended import create_access_token
            from datetime import timedelta
            
            token = create_access_token(
                identity=regular_user.id,
                expires_delta=timedelta(seconds=-1)  # Already expired
            )
        
        response = client.get('/api/config',
                           headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 401
    
    def test_user_cannot_access_other_user_config(self, client, app, regular_user, admin_user):
        """Test that user cannot access another user's config"""
        # Create config for admin
        with app.app_context():
            from app.models.config_data import ConfigData
            from app.utils.encryption import get_encryption_service
            
            encryption_service = get_encryption_service()
            encrypted_payload = encryption_service.encrypt({"key": "value"})
            
            admin_config = ConfigData(
                user_id=admin_user.id,
                name='admin_only_config',
                encrypted_data=encrypted_payload.ciphertext,
                data_hash=encrypted_payload.data_hash,
                iv=encrypted_payload.iv,
                key_version=encrypted_payload.key_version,
                encryption_algorithm=encrypted_payload.algorithm,
                created_by=admin_user.username,
                updated_by=admin_user.username
            )
            
            db.session.add(admin_config)
            db.session.commit()
            config_id = admin_config.id
        
        # Login as regular user
        data = {
            'username': regular_user.username,
            'password': 'UserPassword123!'
        }
        
        login_response = client.post('/api/auth/login',
                                   data=json.dumps(data),
                                   content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # Try to access admin's config
        response = client.get(f'/api/config/{config_id}',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 403
        result = json.loads(response.data)
        assert 'unauthorized' in result['error'].lower()

