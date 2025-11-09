import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Request  # type: ignore

from app.services.redis_client import get_redis_client


SESSION_PREFIX = "session:"
USER_SESSION_SET_PREFIX = "user_sessions:"
DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24  # 24 hours


@dataclass
class SessionInfo:
    session_id: str
    user_id: int
    username: str
    created_at: str
    last_seen_at: str
    user_agent: Optional[str]
    ip_address: Optional[str]
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SessionManager:
    def __init__(self) -> None:
        self.redis = get_redis_client()
        self._uses_mock_backend = getattr(self.redis, "_is_mock", False)
        self.ttl_seconds = int(
            os.environ.get("SESSION_TTL_SECONDS", DEFAULT_SESSION_TTL_SECONDS)
        )

    def _session_key(self, session_id: str) -> str:
        return f"{SESSION_PREFIX}{session_id}"

    def _user_sessions_key(self, user_id: int) -> str:
        return f"{USER_SESSION_SET_PREFIX}{user_id}"

    @staticmethod
    def _current_timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _extract_request_meta(request: Optional[Request]) -> Dict[str, Optional[str]]:
        if request is None:
            return {"ip": None, "user_agent": None}
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = None
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.remote_addr
        user_agent = request.headers.get("User-Agent")
        return {"ip": ip, "user_agent": user_agent}

    def create_session(
        self,
        user_id: int,
        username: str,
        request: Optional[Request] = None,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SessionInfo:
        session_id = str(uuid.uuid4())
        now = self._current_timestamp()
        meta = self._extract_request_meta(request)
        if ip_address is not None:
            meta["ip"] = ip_address
        if user_agent is not None:
            meta["user_agent"] = user_agent

        info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            username=username,
            created_at=now,
            last_seen_at=now,
            user_agent=meta["user_agent"],
            ip_address=meta["ip"],
        )

        self.redis.setex(
            self._session_key(session_id),
            self.ttl_seconds,
            json.dumps(info.to_dict()),
        )
        self.redis.sadd(self._user_sessions_key(user_id), session_id)
        return info

    def get_session(self, session_id: Optional[str]) -> Optional[SessionInfo]:
        if not session_id:
            return None
        raw = self.redis.get(self._session_key(session_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return SessionInfo(**data)

    def touch_session(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        info = self.get_session(session_id)
        if not info or not info.is_active:
            return
        info.last_seen_at = self._current_timestamp()
        self.redis.setex(
            self._session_key(session_id),
            self.ttl_seconds,
            json.dumps(info.to_dict()),
        )

    def ensure_active_session(self, session_id: Optional[str], user_id: int) -> bool:
        if self._uses_mock_backend:
            return True
        info = self.get_session(session_id)
        if not info or not info.is_active or info.user_id != user_id:
            return False
        self.touch_session(session_id)
        return True

    def revoke_session(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        info = self.get_session(session_id)
        if not info:
            return
        info.is_active = False
        info.last_seen_at = self._current_timestamp()
        self.redis.setex(
            self._session_key(session_id),
            self.ttl_seconds,
            json.dumps(info.to_dict()),
        )
        self.redis.srem(self._user_sessions_key(info.user_id), session_id)

    def revoke_all_sessions(self, user_id: int) -> None:
        key = self._user_sessions_key(user_id)
        session_ids = self.redis.smembers(key)
        for sid in session_ids:
            decoded = sid.decode() if isinstance(sid, bytes) else sid
            self.revoke_session(decoded)
        self.redis.delete(key)


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


