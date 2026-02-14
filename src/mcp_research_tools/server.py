"""MCP Research Tools server."""

import os

from fastmcp import FastMCP

from .tools.fetch import web_fetch as _web_fetch
from .tools.image import fetch_image
from .tools.media import is_media_url, process_media
from .tools.search import searxng_search as _searxng_search

mcp = FastMCP("searxng")


@mcp.tool()
async def searxng_search(
    query: str,
    max_results: int = 10,
    engines: str | None = None,
    categories: str = "general",
) -> dict:
    """Search the web via local SearXNG (70+ engines). Returns structured JSON results.

    Args:
        query: What to search for.
        max_results: Max number of results (default 10).
        engines: Comma-separated engines e.g. "duckduckgo,brave,google" (default: all).
        categories: Search category: general, images, videos, news (default: general).
    """
    try:
        return await _searxng_search(query, max_results, engines, categories)
    except Exception as e:
        return {"error": str(e), "query": query, "results": [], "count": 0}


@mcp.tool()
async def web_fetch(url: str, extract_text: bool = True) -> dict:
    """Fetch a web page and extract clean text via trafilatura. No DOM bloat.

    Args:
        url: URL to fetch (http/https).
        extract_text: Use trafilatura for clean text extraction (default True).
    """
    try:
        return await _web_fetch(url, extract_text)
    except Exception as e:
        return {"error": str(e), "url": url, "content_text": ""}


@mcp.tool()
async def process_video(url: str) -> dict:
    """Download and process a YouTube/TikTok video into transcript + keyframe images.

    Args:
        url: YouTube or TikTok video URL.
    """
    if not is_media_url(url):
        return {"error": f"Unsupported media URL: {url}. Supports YouTube and TikTok."}
    try:
        return await process_media(url)
    except Exception as e:
        return {"error": str(e), "source_url": url}


@mcp.tool()
async def analyze_image(source: str) -> dict:
    """Fetch an image for vision analysis. Returns a local file path that Claude can read.

    Args:
        source: Image URL (http/https) or local file path.
    """
    try:
        return await fetch_image(source)
    except Exception as e:
        return {"error": str(e), "source": source, "exists": False}


def main():
    """Run the MCP server with transport from env."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "9000"))
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
