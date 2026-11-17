from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import socket
from dataclasses import dataclass

from backend.config import local_ip

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_faceattendance._tcp.local."
SERVICE_NAME = "Face Attendance"
DEFAULT_HTTPS_PORT = 8443


def discovery_hostname() -> str:
    hostname = os.environ.get("MOBILE_DISCOVERY_HOSTNAME") or socket.gethostname()
    hostname = hostname.strip().lower().rstrip(".")
    if hostname.endswith(".local"):
        hostname = hostname[:-6]
    labels = hostname.split(".")
    if not labels or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ):
        raise ValueError(
            "MOBILE_DISCOVERY_HOSTNAME must be a DNS hostname without the .local suffix."
        )
    return f"{hostname}.local."


def discovery_port() -> int:
    try:
        port = int(os.environ.get("MOBILE_HTTPS_PORT", str(DEFAULT_HTTPS_PORT)))
    except ValueError as exc:
        raise ValueError("MOBILE_HTTPS_PORT must be a valid TCP port.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("MOBILE_HTTPS_PORT must be between 1 and 65535.")
    return port


@dataclass
class LocalMobileDiscovery:
    zeroconf: object
    service_info: object

    async def close(self) -> None:
        await self.zeroconf.async_unregister_service(self.service_info)
        await self.zeroconf.async_close()


async def start_local_mobile_discovery() -> LocalMobileDiscovery:
    from zeroconf import IPVersion, ServiceInfo
    from zeroconf.asyncio import AsyncZeroconf

    ip_address = ipaddress.IPv4Address(local_ip())
    if ip_address.is_loopback or ip_address.is_unspecified:
        raise OSError("No reachable IPv4 network interface is available for discovery.")

    hostname = discovery_hostname()
    service_name = f"{SERVICE_NAME} ({hostname[:-7]})"
    info = ServiceInfo(
        SERVICE_TYPE,
        f"{service_name}.{SERVICE_TYPE}",
        addresses=[ip_address.packed],
        port=discovery_port(),
        properties={
            b"api": b"1",
            b"scheme": b"https",
            b"hostname": hostname[:-1].encode("ascii"),
        },
        server=hostname,
    )
    zeroconf = AsyncZeroconf(ip_version=IPVersion.V4Only)
    try:
        await zeroconf.async_register_service(info, allow_name_change=True)
    except Exception:
        await zeroconf.async_close()
        raise

    logger.info(
        "Advertising mobile HTTPS service at https://%s:%s",
        hostname[:-1],
        info.port,
    )
    return LocalMobileDiscovery(zeroconf, info)


async def close_local_mobile_discovery(
    discovery: LocalMobileDiscovery | None,
) -> None:
    if discovery is not None:
        await discovery.close()
