from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from backend.config import SESSION_SECRET_PATH, ensure_directories
from backend.database import get_setting, set_setting

ADMIN_PASSWORD_KEY = "admin_password_hash"
PBKDF2_ITERS = 120_000


def load_or_create_session_secret() -> str:
    ensure_directories()
    if SESSION_SECRET_PATH.exists():
        return SESSION_SECRET_PATH.read_text(encoding="utf-8").strip()
    secret = secrets.token_hex(32)
    SESSION_SECRET_PATH.write_text(secret, encoding="utf-8")
    return secret


def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERS
    )
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
    except ValueError:
        return False
    candidate = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, stored)


def admin_password_configured() -> bool:
    value = get_setting(ADMIN_PASSWORD_KEY)
    return bool(value)


def set_admin_password(password: str) -> None:
    set_setting(ADMIN_PASSWORD_KEY, hash_password(password))


def check_admin_password(password: str) -> bool:
    stored = get_setting(ADMIN_PASSWORD_KEY)
    if not stored:
        return False
    return verify_password(password, stored)


def is_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def require_admin_redirect(request: Request) -> Optional[RedirectResponse]:
    if not admin_password_configured():
        return RedirectResponse("/admin/setup", status_code=302)
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    return None
