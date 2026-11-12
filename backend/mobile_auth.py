from __future__ import annotations

import hashlib
import ipaddress
import math
import os
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request

from backend import database as db
from backend.auth import hash_password, verify_password

ACCESS_TOKEN_LIFETIME = timedelta(hours=8)
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_FAILURE_LIMIT = 8
_login_failures: dict[str, deque[float]] = {}
_login_failures_lock = threading.Lock()
_dummy_password_hash = hash_password(secrets.token_urlsafe(32))


def utc_timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_secure_mobile_transport(request: Request) -> None:
    if request.url.scheme.lower() == "https":
        return
    if os.environ.get("MOBILE_API_ALLOW_HTTP") == "1":
        return
    host = request.url.hostname or ""
    client_host = request.client.host if request.client else ""
    try:
        local_host = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local_host = host.lower() == "localhost" or host.lower().endswith(".localhost")
    try:
        local_client = ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        local_client = False
    if local_host and local_client:
        return
    raise HTTPException(
        status_code=426,
        detail=(
            "The mobile API requires HTTPS. Configure a trusted HTTPS proxy, "
            "or explicitly allow HTTP only behind an encrypted managed VPN."
        ),
    )


def check_login_rate_limit(client_host: str) -> None:
    now = time.monotonic()
    with _login_failures_lock:
        for key, failures in list(_login_failures.items()):
            while failures and now - failures[0] >= _LOGIN_WINDOW_SECONDS:
                failures.popleft()
            if not failures:
                del _login_failures[key]
        if len(_login_failures) > 4096:
            for key in list(_login_failures)[:1024]:
                del _login_failures[key]
        failures = _login_failures.get(client_host, deque())
        if len(failures) >= _LOGIN_FAILURE_LIMIT:
            retry_after = math.ceil(_LOGIN_WINDOW_SECONDS - (now - failures[0]))
            raise HTTPException(
                status_code=429,
                detail="Too many sign-in attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def record_login_failure(client_host: str) -> None:
    now = time.monotonic()
    with _login_failures_lock:
        failures = _login_failures.setdefault(client_host, deque())
        while failures and now - failures[0] >= _LOGIN_WINDOW_SECONDS:
            failures.popleft()
        failures.append(now)


def clear_login_failures(client_host: str) -> None:
    with _login_failures_lock:
        _login_failures.pop(client_host, None)


def authenticate_mobile_user(username: str, password: str) -> dict[str, Any] | None:
    user = db.get_mobile_user_by_username(username)
    password_hash = user["password_hash"] if user else _dummy_password_hash
    password_valid = verify_password(password, password_hash)
    if not user or not user["is_active"] or not password_valid:
        return None
    return user


def issue_access_token(user_id: int) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + ACCESS_TOKEN_LIFETIME
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.create_mobile_access_token(
        token_hash,
        user_id,
        utc_timestamp(now),
        utc_timestamp(expires_at),
    )
    return token, utc_timestamp(expires_at)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate_bearer_token(request: Request) -> tuple[dict[str, Any], str]:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not token
        or len(token) > 256
    ):
        raise HTTPException(
            status_code=401,
            detail="Mobile authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    hashed_token = token_hash(token)
    user = db.get_mobile_user_for_token(hashed_token, utc_timestamp())
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Mobile session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user, hashed_token


def mobile_user_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
    }
