from __future__ import annotations

import pytest

from backend.mobile_discovery import discovery_hostname, discovery_port
from backend.serve import server_options


def test_discovery_hostname_is_normalized_and_uses_local_domain(monkeypatch):
    monkeypatch.setenv("MOBILE_DISCOVERY_HOSTNAME", "Attendance-Host")

    assert discovery_hostname() == "attendance-host.local."


def test_discovery_hostname_rejects_invalid_dns_names(monkeypatch):
    monkeypatch.setenv("MOBILE_DISCOVERY_HOSTNAME", "attendance host")

    with pytest.raises(ValueError, match="MOBILE_DISCOVERY_HOSTNAME"):
        discovery_hostname()


def test_discovery_port_validates_range(monkeypatch):
    monkeypatch.setenv("MOBILE_HTTPS_PORT", "70000")

    with pytest.raises(ValueError, match="between 1 and 65535"):
        discovery_port()


def test_server_uses_http_defaults_without_tls():
    assert server_options({}) == {"host": "0.0.0.0", "port": 8000}


def test_server_requires_both_tls_files():
    with pytest.raises(ValueError, match="Set both"):
        server_options({"MOBILE_TLS_CERT_FILE": "certificate.pem"})


def test_server_enables_tls_with_existing_certificate_files(tmp_path):
    certificate = tmp_path / "host.crt"
    private_key = tmp_path / "host.key"
    certificate.write_text("certificate", encoding="ascii")
    private_key.write_text("private key", encoding="ascii")

    options = server_options(
        {
            "MOBILE_TLS_CERT_FILE": str(certificate),
            "MOBILE_TLS_KEY_FILE": str(private_key),
            "MOBILE_HTTPS_PORT": "9443",
        }
    )

    assert options == {
        "host": "0.0.0.0",
        "port": 9443,
        "ssl_certfile": str(certificate),
        "ssl_keyfile": str(private_key),
    }
