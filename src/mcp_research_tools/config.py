"""Configuration for mcp-research-tools."""

import os
from pathlib import Path

# SearXNG
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080")

# Media processing
MEDIA_TEMP_DIR = Path(os.getenv("MEDIA_TEMP_DIR", "/tmp/mcp-media"))
MAX_VIDEO_SECONDS = int(os.getenv("MAX_VIDEO_SECONDS", "120"))
FRAME_EVERY_SECONDS = int(os.getenv("FRAME_EVERY_SECONDS", "3"))

# Whisper
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_CPP_BIN = os.getenv("WHISPER_CPP_BIN", "whisper-cli")
WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    str(Path.home() / ".cache" / "whisper-cpp" / f"ggml-{WHISPER_MODEL}.bin"),
)

# Transport
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "9000"))

# Fetch
MAX_FETCH_SIZE_MB = int(os.getenv("MAX_FETCH_SIZE_MB", "10"))
FETCH_TIMEOUT_SECONDS = int(os.getenv("FETCH_TIMEOUT_SECONDS", "30"))
