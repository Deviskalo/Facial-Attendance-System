from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from backend.config import HOST, PORT, print_access_urls
from backend.mobile_discovery import DEFAULT_HTTPS_PORT


def server_options(environ: dict[str, str] | None = None) -> dict[str, object]:
    environment = environ if environ is not None else os.environ
    certificate = environment.get("MOBILE_TLS_CERT_FILE", "").strip()
    private_key = environment.get("MOBILE_TLS_KEY_FILE", "").strip()
    if bool(certificate) != bool(private_key):
        raise ValueError(
            "Set both MOBILE_TLS_CERT_FILE and MOBILE_TLS_KEY_FILE to enable HTTPS."
        )
    if not certificate:
        return {"host": HOST, "port": PORT}

    for label, file_path in (("certificate", certificate), ("private key", private_key)):
        if not Path(file_path).is_file():
            raise FileNotFoundError(f"The configured TLS {label} does not exist: {file_path}")

    try:
        port = int(environment.get("MOBILE_HTTPS_PORT", str(DEFAULT_HTTPS_PORT)))
    except ValueError as exc:
        raise ValueError("MOBILE_HTTPS_PORT must be a valid TCP port.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("MOBILE_HTTPS_PORT must be between 1 and 65535.")

    return {
        "host": HOST,
        "port": port,
        "ssl_certfile": certificate,
        "ssl_keyfile": private_key,
    }


def main() -> None:
    options = server_options()
    secure = "ssl_certfile" in options
    os.environ["MOBILE_TLS_ENABLED"] = "1" if secure else "0"
    if secure:
        os.environ["SESSION_COOKIE_SECURE"] = "1"
    print_access_urls()
    uvicorn.run("backend.main:app", **options)


if __name__ == "__main__":
    main()
