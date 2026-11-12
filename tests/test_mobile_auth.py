from __future__ import annotations

import secrets

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend import database as db
from backend.auth import hash_password
from backend.mobile_auth import (
    authenticate_bearer_token,
    authenticate_mobile_user,
    check_login_rate_limit,
    issue_access_token,
    record_login_failure,
    require_secure_mobile_transport,
    token_hash,
    utc_timestamp,
)


def _request(
    *,
    scheme: str = "https",
    host: str = "attendance.example",
    client_host: str = "192.0.2.10",
    authorization: str = "",
) -> Request:
    headers = [(b"host", host.encode("ascii"))]
    if authorization:
        headers.append((b"authorization", authorization.encode("ascii")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": scheme,
        "path": "/api/v1/mobile/me",
        "raw_path": b"/api/v1/mobile/me",
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 12345),
        "server": (host, 443 if scheme == "https" else 80),
    }
    return Request(scope)


def test_mobile_user_authentication_is_case_insensitive(test_db):
    user = db.create_mobile_user(
        "operator.one",
        "Operator One",
        hash_password("correct horse battery staple"),
        "operator",
    )

    authenticated = authenticate_mobile_user(
        "OPERATOR.ONE", "correct horse battery staple"
    )
    assert authenticated is not None
    assert authenticated["id"] == user["id"]
    assert authenticate_mobile_user("operator.one", "wrong password") is None


def test_access_token_is_hashed_revocable_and_expires(test_db):
    user = db.create_mobile_user(
        "reviewer",
        "Attendance Reviewer",
        hash_password("reviewer secure password"),
        "reviewer",
    )
    token, expires_at = issue_access_token(user["id"])
    hashed = token_hash(token)

    stored = test_db.execute(
        "SELECT token_hash, expires_at FROM mobile_access_tokens WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    assert stored["token_hash"] == hashed
    assert stored["token_hash"] != token
    assert stored["expires_at"] == expires_at

    request = _request(authorization=f"Bearer {token}")
    authorized_user, authorized_hash = authenticate_bearer_token(request)
    assert authorized_user["username"] == "reviewer"
    assert authorized_hash == hashed

    db.revoke_mobile_access_token(hashed, utc_timestamp())
    with pytest.raises(HTTPException) as error:
        authenticate_bearer_token(request)
    assert error.value.status_code == 401


def test_inactive_mobile_user_cannot_use_existing_token(test_db):
    user = db.create_mobile_user(
        "inactive",
        "Inactive Account",
        hash_password("inactive account password"),
        "operator",
    )
    token, _ = issue_access_token(user["id"])
    db.update_mobile_user(user["id"], is_active=0)

    with pytest.raises(HTTPException) as error:
        authenticate_bearer_token(_request(authorization=f"Bearer {token}"))
    assert error.value.status_code == 401


def test_mobile_auth_requires_secure_transport(monkeypatch):
    monkeypatch.delenv("MOBILE_API_ALLOW_HTTP", raising=False)
    require_secure_mobile_transport(_request())
    require_secure_mobile_transport(
        _request(scheme="http", host="localhost", client_host="127.0.0.1")
    )
    with pytest.raises(HTTPException) as error:
        require_secure_mobile_transport(_request(scheme="http"))
    assert error.value.status_code == 426


def test_mobile_login_rate_limit_is_per_client(test_db):
    client = f"test-{secrets.token_hex(8)}"
    for _ in range(8):
        check_login_rate_limit(client)
        record_login_failure(client)

    with pytest.raises(HTTPException) as error:
        check_login_rate_limit(client)
    assert error.value.status_code == 429

    check_login_rate_limit(client + "-other")
