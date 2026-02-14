"""Web fetch tool with clean text extraction via trafilatura."""

from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from ..config import FETCH_TIMEOUT_SECONDS, MAX_FETCH_SIZE_MB


async def web_fetch(url: str, extract_text: bool = True) -> dict:
    """Fetch URL and extract clean text content.

    Args:
        url: URL to fetch (must be http/https).
        extract_text: Use trafilatura for clean text extraction (default True).

    Returns:
        Dict with content_text, title, status_code, url.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    max_bytes = MAX_FETCH_SIZE_MB * 1024 * 1024

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()

            content = b""
            async for chunk in resp.aiter_bytes():
                content += chunk
                if len(content) > max_bytes:
                    raise ValueError(f"Content exceeds {MAX_FETCH_SIZE_MB}MB limit")

            status_code = resp.status_code
            final_url = str(resp.url)
            content_type = resp.headers.get("content-type", "").split(";")[0].strip()

    result = {"status_code": status_code, "url": final_url, "content_type": content_type}

    if "text/html" in content_type and extract_text:
        extracted = trafilatura.extract(content, include_tables=True, no_fallback=False)
        result["content_text"] = extracted or ""
        soup = BeautifulSoup(content, "lxml")
        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else ""
    elif "application/json" in content_type:
        result["content_text"] = content.decode("utf-8", errors="ignore")
    else:
        result["content_text"] = content.decode("utf-8", errors="ignore")

    return result
