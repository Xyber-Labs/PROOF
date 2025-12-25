"""Validation utilities."""

import re
from urllib.parse import urlparse


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format."""
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(uuid_pattern.match(uuid_str))


def validate_https_url(url_str: str) -> bool:
    """Validate HTTPS URL (allows HTTP for localhost and docker service names in development)."""
    try:
        parsed = urlparse(url_str)
        # Allow HTTP for localhost/127.0.0.1 and docker service names for local development
        if parsed.scheme == "http":
            # Allow HTTP for localhost, docker service names (no dots), or .local domains
            hostname = parsed.hostname or ""
            if (
                hostname in ("localhost", "127.0.0.1", "0.0.0.0")
                or ("." not in hostname and hostname)
                or hostname.endswith(".local")
            ):
                return bool(parsed.netloc)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False
