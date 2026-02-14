"""Image analysis tool: fetch images for Claude vision reasoning."""

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..config import MEDIA_TEMP_DIR


async def fetch_image(source: str) -> dict:
    """Fetch an image from URL or validate a local path.

    For URLs: downloads to temp dir and returns local path.
    For local paths: validates existence and returns path.

    Args:
        source: URL (http/https) or local file path.

    Returns:
        Dict with path, exists, content_type.
    """
    if source.startswith(("http://", "https://")):
        return await _fetch_remote_image(source)
    else:
        return _check_local_image(source)


def _check_local_image(path: str) -> dict:
    """Check if a local image file exists."""
    p = Path(path)
    return {
        "path": str(p),
        "exists": p.exists(),
        "content_type": _guess_content_type(p.suffix),
    }


async def _fetch_remote_image(url: str) -> dict:
    """Download image from URL to temp directory."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix or ".jpg"

    images_dir = MEDIA_TEMP_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    local_path = images_dir / f"{url_hash}{ext}"

    if local_path.exists():
        return {"path": str(local_path), "exists": True, "content_type": _guess_content_type(ext)}

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)

        content_type = resp.headers.get("content-type", _guess_content_type(ext))

    return {"path": str(local_path), "exists": True, "content_type": content_type}


def _guess_content_type(ext: str) -> str:
    """Guess MIME type from file extension."""
    mapping = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".svg": "image/svg+xml",
    }
    return mapping.get(ext.lower(), "application/octet-stream")
