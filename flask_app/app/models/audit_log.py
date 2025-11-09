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
class AuditLog:
    """
    Lightweight representation of Supabase audit log records.
    """

    id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    event_type: str = ""
    event_description: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    status: str = "success"
    severity: str = "info"
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "AuditLog":
        """
        Create an AuditLog from a Supabase row (dict).
        """
        return cls(
            id=record.get("id"),
            user_id=record.get("user_id"),
            username=record.get("username"),
            event_type=record.get("event_type", ""),
            event_description=record.get("event_description", ""),
            ip_address=record.get("ip_address"),
            user_agent=record.get("user_agent"),
            resource_type=record.get("resource_type"),
            resource_id=record.get("resource_id"),
            status=record.get("status", "success"),
            severity=record.get("severity", "info"),
            timestamp=_parse_timestamp(record.get("timestamp")),
            metadata=record.get("metadata")
            or record.get("event_metadata")
            or {},
        )

    def to_payload(self) -> Dict[str, Any]:
        """
        Serialise the model for Supabase insert/update operations.
        """
        payload = {
            "user_id": self.user_id,
            "username": self.username,
            "event_type": self.event_type,
            "event_description": self.event_description,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "status": self.status,
            "severity": self.severity,
            "metadata": self.metadata or None,
        }
        if self.timestamp:
            payload["timestamp"] = self.timestamp.isoformat()
        if self.id is not None:
            payload["id"] = self.id
        return payload

    def __repr__(self) -> str:
        return f"<AuditLog {self.event_type} by {self.username}>"
