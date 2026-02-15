"""Security utilities: SSRF protection, content sanitization, path validation."""

import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------

# Additional explicit blocks beyond ipaddress.is_global (belt + suspenders)
_EXTRA_BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.169.254/32"),  # Cloud metadata (AWS/GCP/Azure)
    ipaddress.ip_network("100.100.100.200/32"),  # Alibaba Cloud metadata
    ipaddress.ip_network("fd00:ec2::254/128"),   # AWS IPv6 metadata
]


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if the IP is private, reserved, or otherwise non-global."""
    if not ip.is_global:
        return True
    return any(ip in net for net in _EXTRA_BLOCKED_NETWORKS)


def validate_url(url: str) -> str:
    """Validate a URL for safe outbound fetching.

    Checks:
      - Scheme must be http or https.
      - Hostname must be present.
      - If hostname is a raw IP, it must be globally routable.
      - If hostname is a name, all DNS-resolved IPs must be globally routable.

    Returns the original URL on success; raises ``ValueError`` on failure.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"URL scheme must be http or https, got: {parsed.scheme!r}"
        )
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"URL must include a hostname: {url}")

    # Raw IP literal?
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_blocked_ip(ip):
            raise ValueError(f"Blocked: private/reserved IP {ip}")
        return url
    except ValueError as exc:
        if "Blocked" in str(exc):
            raise
        # Not an IP → fall through to DNS resolution

    # Hostname – resolve and check every returned address
    try:
        results = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname {hostname!r}: {exc}")

    if not results:
        raise ValueError(f"No DNS results for hostname {hostname!r}")

    for _family, _type, _proto, _canon, sockaddr in results:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if _is_blocked_ip(ip):
            raise ValueError(
                f"Blocked: {hostname!r} resolves to private/reserved IP {ip}"
            )

    return url


def validate_redirect_url(final_url: str) -> str:
    """Validate the final URL after redirect chain.

    Same rules as ``validate_url`` but with a friendlier error message.
    """
    try:
        return validate_url(final_url)
    except ValueError:
        raise ValueError(
            f"Redirect target blocked (private/reserved IP): {final_url}"
        )


# ---------------------------------------------------------------------------
# Content sanitization (anti-prompt-injection)
# ---------------------------------------------------------------------------

# Invisible / zero-width Unicode characters used to hide text
_INVISIBLE_RE = re.compile(
    "["
    "\u00ad"       # Soft hyphen
    "\u034f"       # Combining grapheme joiner
    "\u061c"       # Arabic letter mark
    "\u115f"       # Hangul choseong filler
    "\u1160"       # Hangul jungseong filler
    "\u17b4"       # Khmer vowel inherent aq
    "\u17b5"       # Khmer vowel inherent aa
    "\u180e"       # Mongolian vowel separator
    "\u200b"       # Zero-width space
    "\u200c"       # Zero-width non-joiner
    "\u200d"       # Zero-width joiner
    "\u200e"       # Left-to-right mark
    "\u200f"       # Right-to-left mark
    "\u202a-\u202e"  # Bidi embedding/override
    "\u2060"       # Word joiner
    "\u2061"       # Function application
    "\u2062"       # Invisible times
    "\u2063"       # Invisible separator
    "\u2064"       # Invisible plus
    "\u2066-\u2069"  # Bidi isolate
    "\u206a-\u206f"  # Deprecated formatting
    "\u3164"       # Hangul filler
    "\ufeff"       # BOM / zero-width no-break space
    "\uffa0"       # Halfwidth hangul filler
    "\U000e0001"   # Language tag
    "\U000e0020-\U000e007f"  # Tag characters
    "]+"
)

# Patterns that suggest prompt-injection attempts
_INJECTION_PATTERNS = [
    re.compile(
        r"(?i)\b(?:ignore|disregard|forget)\b.{0,40}"
        r"\b(?:previous|above|prior|all|earlier)\b.{0,40}"
        r"\b(?:instructions?|prompts?|rules?|context)\b"
    ),
    re.compile(r"(?i)\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\b"),
    re.compile(r"(?i)\b(?:system\s*prompt|system\s*message|hidden\s*instruction)\b"),
    re.compile(r"(?i)\bnew\s+(?:instructions?|rules?|prompt)\s*:"),
    re.compile(r"(?i)\b(?:do\s+not|don'?t)\s+(?:follow|obey|listen\s+to)\b"),
    re.compile(r"(?i)<\s*(?:system|instruction|prompt|command)\s*>"),
    re.compile(r"(?i)\[/?INST\]|\[SYSTEM\]"),
    re.compile(r"(?i)<<\s*SYS\s*>>"),
    re.compile(r"(?i)\bBEGIN\s+(?:HIDDEN|SECRET|OVERRIDE)\b"),
]

def sanitize_content(text: str, *, max_length: int = 50_000) -> str:
    """Clean fetched content to reduce prompt-injection surface.

    - Strips invisible Unicode characters.
    - Removes HTML comments.
    - Truncates to *max_length*.
    """
    if not text:
        return ""

    text = _INVISIBLE_RE.sub("", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    if len(text) > max_length:
        text = text[:max_length] + "\n\n[Content truncated]"

    return text


def detect_injection_patterns(text: str) -> list[str]:
    """Scan text for common prompt-injection patterns.

    Returns a list of short descriptions for each detected pattern.
    An empty list means nothing suspicious was found.
    Only scans the first 20 KB for performance.
    """
    sample = text[:20_000]
    hits: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(sample):
            hits.append(pattern.pattern[:80])
    return hits


# ---------------------------------------------------------------------------
# Path-traversal protection
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".bmp", ".tiff", ".tif", ".ico", ".heic", ".heif", ".avif",
})


def validate_local_image_path(path: str, allowed_dirs: list[Path]) -> Path:
    """Validate that *path* is inside one of *allowed_dirs* and has an image extension.

    Returns the resolved ``Path`` on success; raises ``ValueError`` otherwise.
    """
    p = Path(path).resolve()

    if p.suffix.lower() not in _IMAGE_EXTENSIONS:
        raise ValueError(f"Not a recognised image extension: {p.suffix!r}")

    for allowed in allowed_dirs:
        try:
            p.relative_to(allowed.resolve())
            return p
        except ValueError:
            continue

    raise ValueError(f"Path is outside allowed directories: {path!r}")
