"""Shared host validation primitives for connector-style network targets."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = frozenset({"localhost"})

BLOCKED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("0.0.0.0/32"),
    ipaddress.ip_network("::1/128"),
)

ODBC_HOST_KEYS = frozenset({"server", "host", "data source"})

BLOCK_REASON = (
    "host is in a blocked range (loopback / RFC1918 / link-local / localhost). "
    "Add it to the connector host allowlist if this is an intentional on-prem or "
    "air-gapped target."
)


def normalize_allowlist(allowlist: Iterable[str]) -> set[str]:
    """Normalize an allowlist into case-insensitive exact host matches."""

    return {host.strip().lower() for host in allowlist if host and host.strip()}


def normalize_trusted_proxy_cidrs(
    trusted_proxy_cidrs: Iterable[str],
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """Parse configured trusted-proxy CIDRs into normalized network objects."""

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw_value in trusted_proxy_cidrs:
        if not raw_value:
            continue
        for candidate in raw_value.split(","):
            token = candidate.strip()
            if not token:
                continue
            try:
                networks.append(ipaddress.ip_network(token, strict=False))
            except ValueError as exc:
                raise ValueError(
                    f"Trusted proxy CIDR {token!r} is invalid. Use CIDR values like "
                    "'10.0.0.0/24' or single-host ranges like '10.0.0.8/32'."
                ) from exc
    return tuple(networks)


def is_trusted_proxy_ip(client_host: str | None, trusted_proxy_cidrs: Iterable[str]) -> bool:
    """Return True when the caller IP falls within a configured trusted-proxy CIDR."""

    if client_host is None or not client_host.strip():
        return False
    try:
        client_ip = ipaddress.ip_address(client_host.strip())
    except ValueError:
        return False

    for network in normalize_trusted_proxy_cidrs(trusted_proxy_cidrs):
        if client_ip.version == network.version and client_ip in network:
            return True
    return False


def is_blocked_host(host: str, allowlist: Iterable[str] = ()) -> bool:
    """Return True when a host is blocked and not explicitly allowlisted."""

    if not host or not host.strip():
        return True
    normalized = host.strip().lower()
    allow = normalize_allowlist(allowlist)
    if normalized in allow:
        return False
    if normalized in BLOCKED_HOSTNAMES:
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    for network in BLOCKED_NETWORKS:
        if ip.version == network.version and ip in network:
            return True
    return False


def validate_url_host(url: str, allowlist: Iterable[str] = ()) -> None:
    """Raise ValueError if a URL resolves to a blocked host value."""

    parsed = urlparse(url)
    host = (parsed.hostname or "").strip()
    if is_blocked_host(host, allowlist):
        raise ValueError(f"Connector URL {url!r}: {BLOCK_REASON}")


def extract_odbc_host(connection_string: str) -> str | None:
    """Extract the ODBC host-ish field from a connection string."""

    if not connection_string:
        return None
    for part in connection_string.split(";"):
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        if key.strip().lower() not in ODBC_HOST_KEYS:
            continue
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
            value = value[1:-1]
        for separator in (",", ":"):
            if separator in value:
                value = value.split(separator, 1)[0]
        value = value.strip()
        return value or None
    return None


def validate_odbc_connection_string(connection_string: str, allowlist: Iterable[str] = ()) -> None:
    """Raise ValueError if an ODBC connection string host is blocked or missing."""

    host = extract_odbc_host(connection_string)
    if host is None:
        raise ValueError(
            "ODBC connection string does not contain a parseable Server/Host/Data Source "
            "field. Fail-closed: add an explicit Server=... entry before saving."
        )
    if is_blocked_host(host, allowlist):
        raise ValueError(f"ODBC connector host {host!r}: {BLOCK_REASON}")


__all__ = [
    "BLOCK_REASON",
    "BLOCKED_HOSTNAMES",
    "BLOCKED_NETWORKS",
    "ODBC_HOST_KEYS",
    "extract_odbc_host",
    "is_blocked_host",
    "is_trusted_proxy_ip",
    "normalize_allowlist",
    "normalize_trusted_proxy_cidrs",
    "validate_odbc_connection_string",
    "validate_url_host",
]
