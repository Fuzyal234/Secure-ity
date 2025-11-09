from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.rstrip("Z"))
    except ValueError:
        return None


@dataclass(slots=True)
class ConfigData:
    """
    Supabase configuration payload representation.
    """

    id: Optional[int] = None
    user_id: int = 0
    name: str = ""
    description: Optional[str] = None
    encrypted_data: str = ""
    data_hash: str = ""
    iv: Optional[str] = None
    key_version: Optional[str] = None
    encryption_algorithm: Optional[str] = "AES-256-GCM"
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = ""
    updated_by: str = ""
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "ConfigData":
        return cls(
            id=record.get("id"),
            user_id=record.get("user_id", 0),
            name=record.get("name", ""),
            description=record.get("description"),
            encrypted_data=record.get("encrypted_data", ""),
            data_hash=record.get("data_hash", ""),
            iv=record.get("iv"),
            key_version=record.get("key_version"),
            encryption_algorithm=record.get("encryption_algorithm"),
            version=record.get("version", 1),
            created_at=_parse_timestamp(record.get("created_at")),
            updated_at=_parse_timestamp(record.get("updated_at")),
            created_by=record.get("created_by", ""),
            updated_by=record.get("updated_by", ""),
            is_deleted=record.get("is_deleted", False),
            deleted_at=_parse_timestamp(record.get("deleted_at")),
            metadata=record.get("metadata", {}),
        )

    def to_payload(self, include_encrypted: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "data_hash": self.data_hash,
            "iv": self.iv,
            "key_version": self.key_version,
            "encryption_algorithm": self.encryption_algorithm,
            "version": self.version,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "is_deleted": self.is_deleted,
            "metadata": self.metadata or None,
        }
        if include_encrypted:
            payload["encrypted_data"] = self.encrypted_data
        if self.created_at:
            payload["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            payload["updated_at"] = self.updated_at.isoformat()
        if self.deleted_at:
            payload["deleted_at"] = self.deleted_at.isoformat()
        if self.id is not None:
            payload["id"] = self.id
        return payload

    def __repr__(self) -> str:
        return f"<ConfigData {self.name}>"

