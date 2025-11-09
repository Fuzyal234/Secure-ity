"""
Unit tests for AES-256 encryption service
Tests encryption, decryption, and integrity verification
"""
import os
import pytest

from app.utils.encryption import EncryptionService, EncryptedPayload, get_encryption_service


class TestEncryptionService:
    """Test encryption service functionality"""
    
    def test_generate_key(self):
        """Test key generation"""
        key = EncryptionService.generate_key()
        assert key is not None
        assert len(key) == 44  # Fernet key is base64 encoded, 44 chars
        assert isinstance(key, str)
    
    def test_encrypt_decrypt_success(self):
        """Test successful encryption and decryption"""
        # Generate a test key
        test_key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=test_key, key_version="test-key")
        
        # Test data
        test_data = {
            "username": "testuser",
            "password": "TestPassword123!",
            "api_key": "secret-api-key-12345",
            "nested": {
                "value": "nested_data"
            }
        }
        
        # Encrypt
        encrypted_payload = service.encrypt(test_data)
        assert isinstance(encrypted_payload, EncryptedPayload)
        assert encrypted_payload.ciphertext is not None
        assert len(encrypted_payload.data_hash) == 64  # SHA-256 hex digest length
        assert encrypted_payload.ciphertext != str(test_data)  # Should be different
        
        # Decrypt
        decrypted_data = service.decrypt(
            encrypted_payload.ciphertext,
            encrypted_payload.data_hash,
            encrypted_payload.iv,
            encrypted_payload.key_version,
            encrypted_payload.algorithm,
        )
        
        assert decrypted_data == test_data
        assert decrypted_data["username"] == "testuser"
        assert decrypted_data["nested"]["value"] == "nested_data"
    
    def test_encrypt_decrypt_without_hash(self):
        """Test decryption without hash verification"""
        test_key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=test_key)
        
        test_data = {"key": "value"}
        encrypted_payload = service.encrypt(test_data)
        
        # Decrypt without hash
        decrypted_data = service.decrypt(
            encrypted_payload.ciphertext,
            iv=encrypted_payload.iv,
            key_version=encrypted_payload.key_version,
        )
        assert decrypted_data == test_data
    
    def test_integrity_check_failure(self):
        """Test that tampered data fails integrity check"""
        test_key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=test_key)
        
        test_data = {"sensitive": "data"}
        encrypted_payload = service.encrypt(test_data)
        
        # Tamper with encrypted data
        tampered_data = encrypted_payload.ciphertext[:-5] + "XXXXX"
        
        # Should raise ValueError due to hash mismatch
        with pytest.raises(ValueError, match="Data integrity check failed"):
            service.decrypt(
                tampered_data,
                encrypted_payload.data_hash,
                encrypted_payload.iv,
                encrypted_payload.key_version,
                encrypted_payload.algorithm,
            )
    
    def test_wrong_key_decryption_failure(self):
        """Test that wrong key cannot decrypt data"""
        key1 = EncryptionService.generate_key()
        key2 = EncryptionService.generate_key()
        
        service1 = EncryptionService(encryption_key=key1, key_version="v1")
        service2 = EncryptionService(encryption_key=key2, key_version="v2")
        
        test_data = {"secret": "data"}
        encrypted_payload = service1.encrypt(test_data)
        
        # Try to decrypt with wrong key
        with pytest.raises(ValueError, match="Decryption failed"):
            service2.decrypt(
                encrypted_payload.ciphertext,
                encrypted_payload.data_hash,
                encrypted_payload.iv,
                encrypted_payload.key_version,
                encrypted_payload.algorithm,
            )
    
    def test_different_data_different_encryption(self):
        """Test that same data encrypted twice produces different ciphertext"""
        test_key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=test_key)
        
        test_data = {"key": "value"}
        
        encrypted1 = service.encrypt(test_data)
        encrypted2 = service.encrypt(test_data)
        
        # Hashes should be same (same data)
        assert encrypted1.data_hash == encrypted2.data_hash
        
        # Encrypted data should be different (Fernet uses random IV)
        # But both should decrypt to same data
        decrypted1 = service.decrypt(
            encrypted1.ciphertext,
            encrypted1.data_hash,
            encrypted1.iv,
            encrypted1.key_version,
            encrypted1.algorithm,
        )
        decrypted2 = service.decrypt(
            encrypted2.ciphertext,
            encrypted2.data_hash,
            encrypted2.iv,
            encrypted2.key_version,
            encrypted2.algorithm,
        )
        
        assert decrypted1 == decrypted2 == test_data
    
    def test_empty_data(self):
        """Test encryption/decryption of empty dict"""
        test_key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=test_key)
        
        empty_data = {}
        encrypted_payload = service.encrypt(empty_data)
        decrypted_data = service.decrypt(
            encrypted_payload.ciphertext,
            encrypted_payload.data_hash,
            encrypted_payload.iv,
            encrypted_payload.key_version,
            encrypted_payload.algorithm,
        )
        
        assert decrypted_data == empty_data
    
    def test_large_data(self):
        """Test encryption/decryption of large data structure"""
        test_key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=test_key)
        
        large_data = {
            "items": [{"id": i, "data": f"item_{i}" * 100} for i in range(100)],
            "metadata": {"key" * 50: "value" * 50 for _ in range(10)}
        }
        
        encrypted_payload = service.encrypt(large_data)
        decrypted_data = service.decrypt(
            encrypted_payload.ciphertext,
            encrypted_payload.data_hash,
            encrypted_payload.iv,
            encrypted_payload.key_version,
            encrypted_payload.algorithm,
        )
        
        assert decrypted_data == large_data
    
    def test_get_encryption_service_singleton(self):
        """Test that get_encryption_service returns singleton"""
        # Set environment variable for testing
        test_key = EncryptionService.generate_key()
        os.environ['ENCRYPTION_KEY'] = test_key
        
        service1 = get_encryption_service()
        service2 = get_encryption_service()
        
        # Should be same instance
        assert service1 is service2
        
        # Clean up
        del os.environ['ENCRYPTION_KEY']
    
    def test_missing_encryption_key(self):
        """Test that missing encryption key raises error"""
        # Remove key if exists
        old_key = os.environ.pop('ENCRYPTION_KEY', None)
        
        with pytest.raises(ValueError):
            EncryptionService()
        
        # Restore if it existed
        if old_key:
            os.environ['ENCRYPTION_KEY'] = old_key

