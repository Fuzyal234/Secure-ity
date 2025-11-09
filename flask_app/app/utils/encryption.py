import base64
import binascii
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.services.key_management import (
    KeyManagementError,
    KeyManagementService,
    ManagedKey,
)


@dataclass(frozen=True)
class EncryptedPayload:
    ciphertext: str
    data_hash: str
    iv: str
    key_version: str
    algorithm: str = "AES-256-GCM"

    def __iter__(self):
        """
        Provide backward compatibility with earlier tuple returns:
        `ciphertext, data_hash = encrypt(...)`.
        """
        yield self.ciphertext
        yield self.data_hash

    def to_dict(self) -> Dict[str, str]:
        return {
            "ciphertext": self.ciphertext,
            "data_hash": self.data_hash,
            "iv": self.iv,
            "key_version": self.key_version,
            "algorithm": self.algorithm,
        }


class EncryptionService:
    """Encryption service backed by AES-256-GCM with legacy Fernet support."""

    def __init__(
        self,
        kms_service: Optional[KeyManagementService] = None,
        *,
        encryption_key: Optional[Union[str, bytes]] = None,
        key_version: str = "direct",
    ) -> None:
        if encryption_key is not None:
            self._managed_key = ManagedKey(
                key=self._normalize_direct_key(encryption_key),
                version=key_version,
            )
            self._kms_service = None
        else:
            self._managed_key = None
            try:
                self._kms_service = kms_service or KeyManagementService()
            except KeyManagementError as exc:
                raise ValueError(str(exc)) from exc
        self._legacy_cipher: Optional[Fernet] = None

    def _load_legacy_cipher(self) -> Fernet:
        if self._legacy_cipher is not None:
            return self._legacy_cipher

        key_source = os.environ.get("ENCRYPTION_KEY")
        if not key_source:
            raise ValueError(
                "Legacy decryption requested but ENCRYPTION_KEY is not configured"
            )
        key_bytes = key_source.encode() if isinstance(key_source, str) else key_source
        fernet_key = self._derive_fernet_key(key_bytes)
        self._legacy_cipher = Fernet(fernet_key)
        return self._legacy_cipher

    @staticmethod
    def _derive_fernet_key(key: bytes) -> bytes:
        if len(key) == 44:
            try:
                base64.urlsafe_b64decode(key)
                return key
            except (ValueError, binascii.Error):
                pass

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"secure_ity_salt",
            iterations=100_000,
            backend=default_backend(),
        )
        derived_key = kdf.derive(key)
        return base64.urlsafe_b64encode(derived_key)

    @staticmethod
    def _hash_payload(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _normalize_direct_key(key: Union[str, bytes]) -> bytes:
        if isinstance(key, str):
            key_bytes = key.encode("utf-8")
        else:
            key_bytes = key

        # Allow direct 32-byte key material or base64 encoded key.
        if len(key_bytes) == 32:
            return key_bytes
        try:
            decoded = base64.urlsafe_b64decode(key_bytes)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Direct encryption_key must be raw 32 bytes or base64 encoded") from exc
        if len(decoded) != 32:
            raise ValueError("Direct encryption_key must decode to 32 bytes for AES-256-GCM")
        return decoded

    def encrypt(self, data: Dict[str, Any]) -> EncryptedPayload:
        """
        Encrypt a dictionary using AES-256-GCM and return ciphertext + metadata.
        """
        json_data = json.dumps(data, sort_keys=True).encode("utf-8")
        try:
            managed_key = (
                self._managed_key
                if self._managed_key is not None
                else self._kms_service.get_active_key()  # type: ignore[union-attr]
            )
        except KeyManagementError as exc:
            raise ValueError(f"Unable to load encryption key: {exc}") from exc

        aesgcm = AESGCM(managed_key.key)
        iv_bytes = os.urandom(12)
        ciphertext = aesgcm.encrypt(iv_bytes, json_data, None)

        encrypted_data = base64.urlsafe_b64encode(ciphertext).decode("utf-8")
        iv = base64.urlsafe_b64encode(iv_bytes).decode("utf-8")
        data_hash = self._hash_payload(json_data)

        return EncryptedPayload(
            ciphertext=encrypted_data,
            data_hash=data_hash,
            iv=iv,
            key_version=managed_key.version,
            algorithm="AES-256-GCM",
        )

    def decrypt(
        self,
        encrypted_data: str,
        expected_hash: Optional[str] = None,
        iv: Optional[str] = None,
        key_version: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decrypt payloads encrypted via AES-256-GCM or legacy Fernet.
        """
        chosen_algorithm = (algorithm or "AES-256-GCM").upper()

        if iv and chosen_algorithm == "AES-256-GCM":
            try:
                managed_key = (
                    self._managed_key
                    if self._managed_key is not None
                    else self._kms_service.get_key(key_version)  # type: ignore[union-attr]
                )
            except KeyManagementError as exc:
                raise ValueError(f"Unable to load encryption key: {exc}") from exc

            if (
                self._managed_key is not None
                and key_version is not None
                and key_version != self._managed_key.version
            ):
                raise ValueError("Requested key version does not match provided direct key")

            aesgcm = AESGCM(managed_key.key)
            try:
                iv_bytes = base64.urlsafe_b64decode(iv.encode("utf-8"))
                ciphertext = base64.urlsafe_b64decode(encrypted_data.encode("utf-8"))
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Encrypted payload is not valid base64") from exc

            try:
                plaintext = aesgcm.decrypt(iv_bytes, ciphertext, None)
            except InvalidTag as exc:
                raise ValueError("Decryption failed: authentication error") from exc

            if expected_hash and self._hash_payload(plaintext) != expected_hash:
                raise ValueError("Data integrity check failed: hash mismatch")

            return json.loads(plaintext.decode("utf-8"))

        # Legacy fallback (Fernet)
        cipher = self._load_legacy_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode("utf-8"))
        try:
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
        except Exception as exc:
            raise ValueError("Decryption failed: legacy cipher error") from exc
        if expected_hash and self._hash_payload(decrypted_bytes) != expected_hash:
            raise ValueError("Data integrity check failed: hash mismatch")
        return json.loads(decrypted_bytes.decode("utf-8"))

    @staticmethod
    def generate_key() -> str:
        """Generate a Fernet-compatible key (legacy helper)."""
        key = Fernet.generate_key()
        return key.decode("utf-8")


_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Singleton accessor for the encryption service."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service

