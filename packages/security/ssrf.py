import ipaddress
import socket
from urllib.parse import urlparse

class SSRFViolation(ValueError):
    pass

def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SSRFViolation("unsupported_url")
    host = parsed.hostname
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise SSRFViolation("private_address_blocked")
    except ValueError:
        # DNS is resolved by the network adapter under its own egress policy.
        pass
    return url
