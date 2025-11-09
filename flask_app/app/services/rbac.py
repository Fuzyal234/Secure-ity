from functools import wraps
from typing import Callable, Iterable, Set

from flask import jsonify  # type: ignore
from flask_jwt_extended import get_jwt, jwt_required  # type: ignore

from app.utils.logger import log_security_event

ROLE_PERMISSIONS = {
    "admin": {
        "config:read",
        "config:write",
        "config:delete",
        "config:audit",
        "user:read",
        "user:manage",
    },
    "user": {
        "config:read:own",
        "config:write:own",
        "config:delete:own",
        "user:read:self",
    },
}


def _get_permissions(role: str) -> Set[str]:
    return ROLE_PERMISSIONS.get(role, set())


def requires_permissions(*permissions: str, refresh: bool = False) -> Callable:
    """
    Ensure the caller has all listed permissions.
    """

    def decorator(fn: Callable) -> Callable:
        @jwt_required(refresh=refresh)
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            role = claims.get("role")
            allowed = _get_permissions(role)
            missing = [perm for perm in permissions if perm not in allowed]
            if missing:
                log_security_event(
                    "rbac_denied",
                    f"Access denied. Missing permissions: {missing}",
                    "warning",
                    "failure",
                    {"role": role, "required": permissions},
                    claims.get("sub"),
                    claims.get("username"),
                )
                return (
                    jsonify(
                        {
                            "error": "Access denied",
                            "missing_permissions": missing,
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def requires_any_permission(*permissions: str) -> Callable:
    """
    Ensure the caller has at least one permission from the list.
    """

    def decorator(fn: Callable) -> Callable:
        @jwt_required()
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            role = claims.get("role")
            allowed = _get_permissions(role)
            if not any(perm in allowed for perm in permissions):
                log_security_event(
                    "rbac_denied",
                    "Access denied. Missing required permission.",
                    "warning",
                    "failure",
                    {"role": role, "required_any": permissions},
                    claims.get("sub"),
                    claims.get("username"),
                )
                return (
                    jsonify({"error": "Access denied"}),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def has_permission(role: str, permission: str) -> bool:
    return permission in _get_permissions(role)


def has_any_permission(role: str, permissions: Iterable[str]) -> bool:
    allowed = _get_permissions(role)
    return any(perm in allowed for perm in permissions)


