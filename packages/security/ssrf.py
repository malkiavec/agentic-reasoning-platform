import ipaddress
import socket
from urllib.parse import urlparse

class SSRFViolation(ValueError):
    pass

def _public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )

def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SSRFViolation("unsupported_url")
    if parsed.username or parsed.password:
        raise SSRFViolation("userinfo_not_allowed")
    if parsed.port is not None and parsed.port not in {80, 443}:
        raise SSRFViolation("nonstandard_port_blocked")

    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise SSRFViolation("local_hostname_blocked")

    try:
        if not _public_ip(host):
            raise SSRFViolation("private_address_blocked")
    except ValueError:
        try:
            addresses = {
                result[4][0]
                for result in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
            }
        except socket.gaierror as exc:
            raise SSRFViolation("dns_resolution_failed") from exc
        if not addresses or not all(_public_ip(address) for address in addresses):
            raise SSRFViolation("private_dns_address_blocked")
    return url
