import base64
import binascii
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import requests


class KeyManagementError(RuntimeError):
    """Raised when the key management service cannot return a usable key."""


@dataclass(frozen=True)
class ManagedKey:
    """Container for key material fetched from the KMS/Vault backend."""

    key: bytes
    version: str


class _BaseKeyProvider:
    """Interface for concrete key providers."""

    def get_active_key(self) -> ManagedKey:
        raise NotImplementedError

    def get_key(self, version: Optional[str] = None) -> ManagedKey:
        raise NotImplementedError


class _EnvKeyProvider(_BaseKeyProvider):
    """
    Simple provider that sources key material from environment variables.
    Acts as a fallback when a dedicated KMS/Vault is not configured.
    """

    def __init__(self) -> None:
        key_b64 = (
            os.environ.get("KMS_DATA_KEY")
            or os.environ.get("ENCRYPTION_KEY")
            or ""
        ).strip()
        if not key_b64:
            raise KeyManagementError(
                "No key material found. Set KMS_DATA_KEY or ENCRYPTION_KEY."
            )

        try:
            key = base64.urlsafe_b64decode(key_b64)
        except (ValueError, binascii.Error) as exc:  # type: ignore[name-defined]
            raise KeyManagementError("Key material must be base64-encoded") from exc

        if len(key) != 32:
            raise KeyManagementError(
                "Key material must decode to 32 bytes for AES-256-GCM"
            )

        version = os.environ.get("KMS_KEY_VERSION", "env-default")
        object.__setattr__(self, "_managed_key", ManagedKey(key=key, version=version))

    def get_active_key(self) -> ManagedKey:
        return self._managed_key

    def get_key(self, version: Optional[str] = None) -> ManagedKey:
        key = self._managed_key
        if version and version != key.version:
            raise KeyManagementError(
                f"Requested key version '{version}' not available in environment"
            )
        return key


class _VaultKeyProvider(_BaseKeyProvider):
    """
    HashiCorp Vault KV (v2) provider.
    Expects the secret data to contain `key` (base64) and optional `version`.
    """

    def __init__(self) -> None:
        addr = os.environ.get("VAULT_ADDR")
        token = os.environ.get("VAULT_TOKEN")
        secret_path = os.environ.get("VAULT_SECRET_PATH")
        if not addr or not token or not secret_path:
            raise KeyManagementError(
                "Vault provider requires VAULT_ADDR, VAULT_TOKEN, and VAULT_SECRET_PATH"
            )

        self._addr = addr.rstrip("/")
        self._token = token
        self._secret_path = secret_path.lstrip("/")
        self._field_name = os.environ.get("VAULT_KEY_FIELD", "key")
        self._version_field = os.environ.get("VAULT_KEY_VERSION_FIELD", "version")

    def _fetch_secret(self, params: Optional[dict] = None) -> ManagedKey:
        url = f"{self._addr}/v1/{self._secret_path}"
        response = requests.get(
            url,
            headers={"X-Vault-Token": self._token},
            params=params,
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()

        data = payload.get("data") or {}
        metadata = {}
        # Handle KV v2 layout
        if "data" in data and isinstance(data["data"], dict):
            metadata = data.get("metadata") or {}
            data = data["data"]

        key_b64 = data.get(self._field_name)
        if not key_b64:
            raise KeyManagementError(
                f"Vault secret missing '{self._field_name}' field"
            )

        try:
            key = base64.urlsafe_b64decode(key_b64)
        except (ValueError, binascii.Error) as exc:  # type: ignore[name-defined]
            raise KeyManagementError("Vault key must be base64 encoded") from exc

        if len(key) != 32:
            raise KeyManagementError(
                "Vault key must decode to 32 bytes for AES-256-GCM"
            )

        version = (
            str(data.get(self._version_field))
            if data.get(self._version_field) is not None
            else str(metadata.get("version", "vault"))
        )

        return ManagedKey(key=key, version=version)

    def get_active_key(self) -> ManagedKey:
        return self._fetch_secret()

    def get_key(self, version: Optional[str] = None) -> ManagedKey:
        params = {"version": version} if version else None
        return self._fetch_secret(params=params)


class KeyManagementService:
    """
    Facade to source AES keys from a configured backend (Vault or env fallback).
    Includes simple in-process caching to avoid repeated network calls.
    """

    def __init__(self) -> None:
        provider_name = os.environ.get("KMS_PROVIDER", "env").strip().lower()
        if provider_name == "vault":
            provider: _BaseKeyProvider = _VaultKeyProvider()
        else:
            provider = _EnvKeyProvider()

        self._provider = provider
        self._cache_ttl = int(os.environ.get("KMS_CACHE_SECONDS", "60"))
        self._cached_key: Optional[ManagedKey] = None
        self._cache_expires_at: float = 0.0
        self._lock = threading.Lock()

    def _get_cached(self, loader: Callable[[], ManagedKey], force: bool = False) -> ManagedKey:
        with self._lock:
            now = time.time()
            if (
                not force
                and self._cached_key is not None
                and now < self._cache_expires_at
            ):
                return self._cached_key

            key = loader()
            self._cached_key = key
            self._cache_expires_at = now + max(self._cache_ttl, 1)
            return key

    def get_active_key(self) -> ManagedKey:
        return self._get_cached(self._provider.get_active_key)

    def get_key(self, version: Optional[str] = None) -> ManagedKey:
        if version is None:
            return self.get_active_key()
        # Bypass cache when requesting a specific version to avoid stale results.
        if self._cached_key and self._cached_key.version == version:
            return self._cached_key
        return self._provider.get_key(version)


