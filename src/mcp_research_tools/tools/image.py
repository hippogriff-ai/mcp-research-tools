"""Image analysis tool: fetch images for Claude vision reasoning."""

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..config import MAX_IMAGE_SIZE_MB, MEDIA_TEMP_DIR
from ..security import safe_get, validate_local_image_path, validate_url


async def fetch_image(source: str) -> dict:
    """Fetch an image from URL or validate a local path.

    For URLs: downloads to temp dir and returns local path.
    For local paths: validates the path is inside MEDIA_TEMP_DIR and has an
    image extension (prevents path-traversal / file-existence probing).

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
    """Check if a local image file exists (restricted to MEDIA_TEMP_DIR)."""
    p = validate_local_image_path(path, allowed_dirs=[MEDIA_TEMP_DIR])
    return {
        "path": str(p),
        "exists": p.exists(),
        "content_type": _guess_content_type(p.suffix),
    }


async def _fetch_remote_image(url: str) -> dict:
    """Download image from URL to temp directory."""
    validate_url(url)

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    parsed = urlparse(url)
    raw_ext = Path(parsed.path).suffix
    ext = raw_ext if raw_ext.lower() in _IMAGE_EXTS else ".jpg"

    images_dir = MEDIA_TEMP_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    local_path = images_dir / f"{url_hash}{ext}"

    if local_path.exists():
        return {
            "path": str(local_path),
            "exists": True,
            "content_type": _guess_content_type(ext),
        }

    max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024

    # follow_redirects=False: safe_get validates each redirect hop
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        resp = await safe_get(client, url)
        resp.raise_for_status()

        if len(resp.content) > max_bytes:
            raise ValueError(f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit")

        local_path.write_bytes(resp.content)
        content_type = resp.headers.get("content-type", _guess_content_type(ext))

    return {"path": str(local_path), "exists": True, "content_type": content_type}


_IMAGE_EXTS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".bmp", ".tiff", ".tif", ".ico", ".heic", ".heif", ".avif",
})


def _guess_content_type(ext: str) -> str:
    """Guess MIME type from file extension."""
    mapping = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".svg": "image/svg+xml",
    }
    return mapping.get(ext.lower(), "application/octet-stream")
