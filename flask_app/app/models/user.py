from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.rstrip("Z"))
    except ValueError:
        return None


@dataclass(slots=True)
class User:
    """
    Supabase-backed user model helper.
    """

    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: str = "user"
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "User":
        return cls(
            id=record.get("id"),
            username=record.get("username", ""),
            email=record.get("email", ""),
            password_hash=record.get("password_hash", ""),
            role=record.get("role", "user"),
            is_active=record.get("is_active", True),
            failed_login_attempts=record.get("failed_login_attempts", 0),
            locked_until=_parse_timestamp(record.get("locked_until")),
            last_login=_parse_timestamp(record.get("last_login")),
            created_at=_parse_timestamp(record.get("created_at")),
            updated_at=_parse_timestamp(record.get("updated_at")),
        )

    def to_payload(self) -> Dict[str, Any]:
        payload = {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "is_active": self.is_active,
            "failed_login_attempts": self.failed_login_attempts,
        }
        if self.locked_until:
            payload["locked_until"] = self.locked_until.isoformat()
        if self.last_login:
            payload["last_login"] = self.last_login.isoformat()
        if self.created_at:
            payload["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            payload["updated_at"] = self.updated_at.isoformat()
        if self.id is not None:
            payload["id"] = self.id
        return payload

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except ValueError:
            return False

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_locked(self) -> bool:
        return bool(self.locked_until and datetime.utcnow() < self.locked_until)

    def increment_failed_login(self) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    def reset_failed_login(self) -> None:
        self.failed_login_attempts = 0
        self.locked_until = None

    def __repr__(self) -> str:
        return f"<User {self.username}>"

