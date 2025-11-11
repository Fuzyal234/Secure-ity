import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

# Access request context safely to enrich audit logs when available.
try:
    from flask import has_request_context, request  # type: ignore
except Exception:  # pragma: no cover - flask not available in some contexts
    has_request_context = lambda: False  # type: ignore
    request = None  # type: ignore

try:
    from app.db.supabase_client import get_supabase_client
except Exception:
    get_supabase_client = None  # type: ignore

__all__ = ["setup_logging", "log_security_event"]

_TRUTHY = {"1", "true", "t", "yes", "on"}
LOG_SUCCESS_EVENTS = (
    os.environ.get("LOG_SUCCESS_EVENTS", "false").strip().lower() in _TRUTHY
)


def mask_sensitive_data(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Mask common sensitive fields in a shallow dict."""
    if not isinstance(data, dict):
        return data

    sensitive_keys = {
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "auth",
        "apikey",
        "api_key",
        "bearer",
    }
    masked: Dict[str, Any] = {}
    for key, value in data.items():
        if any(sk in key.lower() for sk in sensitive_keys):
            masked[key] = "***MASKED***"
        else:
            masked[key] = value
    return masked


def setup_logging(app=None) -> None:
    """Configure structured JSON logging."""
    level_name = (os.environ.get("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.handlers:
        return

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    noisy_loggers = ["httpx", "supabase", "asyncio", "urllib3"]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)


def _extract_client_info() -> Dict[str, Optional[str]]:
    """
    Derive client networking details from the current request, if any.
    Honors common proxy headers set by nginx / load balancers.
    """
    if not has_request_context() or request is None:
        return {"ip_address": None, "user_agent": None}

    # Prefer X-Forwarded-For (left-most original client IP), then X-Real-IP, then remote_addr
    xff = request.headers.get("X-Forwarded-For", "") or ""
    ip_from_xff = xff.split(",")[0].strip() if xff else None
    ip_real = request.headers.get("X-Real-IP")
    ip_addr = ip_from_xff or ip_real or getattr(request, "remote_addr", None)

    ua = request.headers.get("User-Agent")
    return {"ip_address": ip_addr, "user_agent": ua}


def _infer_resource_fields(
    event_type: str,
    masked_meta: Dict[str, Any],
    user_id: Optional[int],
) -> Dict[str, Optional[Any]]:
    """
    Provide best-effort defaults for resource classification so existing callers
    do not need to be changed. Prefer explicit IDs from metadata.
    """
    resource_type: Optional[str] = None
    resource_id: Optional[Any] = None

    # Config operations commonly include config_id in metadata
    if "config_id" in masked_meta:
        resource_type = "config"
        resource_id = masked_meta.get("config_id")
    elif event_type.startswith("config_"):
        resource_type = "config"
        resource_id = masked_meta.get("id") or masked_meta.get("config")  # fallback keys
    elif event_type in {"login", "logout", "register"}:
        resource_type = "user"
        resource_id = user_id

    return {"resource_type": resource_type, "resource_id": resource_id}


def log_security_event(
    event_type: str,
    message: str,
    severity: str,
    status: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
) -> None:
    """
    Emit a structured log entry and persist to Supabase audit_logs.
    Failure to persist should never disrupt request handling.
    """
    masked_meta = mask_sensitive_data(metadata or {})

    logger = logging.getLogger("app.security")
    severity_normalized = (severity or "info").lower()
    status_normalized = (status or "success").lower()

    client_info = _extract_client_info()
    log_payload = {
        "event_type": event_type,
        "message": message,
        "event_description": message,
        "severity": severity_normalized,
        "status": status_normalized,
        "user_id": user_id,
        "username": username,
        "metadata": masked_meta,
        "ip_address": client_info.get("ip_address"),
        "user_agent": client_info.get("user_agent"),
    }

    log_method = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(severity_normalized, logger.info)

    if severity_normalized == "info" and status_normalized == "success":
        if LOG_SUCCESS_EVENTS:
            log_method(json.dumps(log_payload))
    else:
        log_method(json.dumps(log_payload))

    if get_supabase_client is None:
        return

    try:
        client = get_supabase_client()
        resource_fields = _infer_resource_fields(event_type, masked_meta, user_id)
        client_info = _extract_client_info()
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
            "event_description": message,
            "severity": severity,
            "status": status,
            "user_id": user_id,
            "username": username,
            "metadata": masked_meta,
            "event_metadata": masked_meta,
            "ip_address": client_info.get("ip_address"),
            "user_agent": client_info.get("user_agent"),
            "resource_type": resource_fields.get("resource_type"),
            "resource_id": resource_fields.get("resource_id"),
        }
        client.table("audit_logs").insert(payload).execute()
    except Exception:
        logging.getLogger("app.security").warning(
            "Failed to persist audit log to Supabase", exc_info=True
        )
