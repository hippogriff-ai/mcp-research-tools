"""Configuration for mcp-research-tools."""

import os
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# SearXNG
# ---------------------------------------------------------------------------
_raw_searxng = os.getenv("SEARXNG_URL", "http://localhost:8080")
_parsed_searxng = urlparse(_raw_searxng)
if _parsed_searxng.scheme not in ("http", "https") or not _parsed_searxng.netloc:
    raise RuntimeError(
        f"SEARXNG_URL must be a valid http(s) URL, got: {_raw_searxng!r}"
    )
SEARXNG_URL: str = _raw_searxng

# Allowed SearXNG search categories
ALLOWED_CATEGORIES = frozenset({
    "general", "images", "videos", "news", "music",
    "it", "science", "files", "social media",
})

# ---------------------------------------------------------------------------
# Media processing
# ---------------------------------------------------------------------------
MEDIA_TEMP_DIR = Path(os.getenv("MEDIA_TEMP_DIR", "/tmp/mcp-media"))
if MEDIA_TEMP_DIR == Path("/"):
    raise RuntimeError("MEDIA_TEMP_DIR must not be the filesystem root")
_created = not MEDIA_TEMP_DIR.exists()
MEDIA_TEMP_DIR.mkdir(parents=True, exist_ok=True)
if _created:
    # Restrict permissions to owner only for directories we create
    MEDIA_TEMP_DIR.chmod(0o700)

MAX_VIDEO_SECONDS = int(os.getenv("MAX_VIDEO_SECONDS", "120"))
FRAME_EVERY_SECONDS = int(os.getenv("FRAME_EVERY_SECONDS", "3"))

# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_CPP_BIN = os.getenv("WHISPER_CPP_BIN", "whisper-cli")
WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    str(Path.home() / ".cache" / "whisper-cpp" / f"ggml-{WHISPER_MODEL}.bin"),
)

# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "9000"))

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------
MAX_FETCH_SIZE_MB = int(os.getenv("MAX_FETCH_SIZE_MB", "10"))
FETCH_TIMEOUT_SECONDS = int(os.getenv("FETCH_TIMEOUT_SECONDS", "30"))
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "25"))
# Max characters returned in content_text (prevents bloating LLM context)
MAX_CONTENT_CHARS = int(os.getenv("MAX_CONTENT_CHARS", "50000"))
