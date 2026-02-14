"""Search tool using local SearXNG instance."""

import httpx

from ..config import SEARXNG_URL


async def searxng_search(
    query: str,
    max_results: int = 10,
    engines: str | None = None,
    categories: str = "general",
) -> dict:
    """Search via local SearXNG JSON API.

    Args:
        query: Search query string.
        max_results: Max results to return (default 10).
        engines: Comma-separated engine names (e.g. "duckduckgo,brave").
        categories: Search category (default "general").

    Returns:
        Dict with query, results list, and count.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    params = {
        "q": query.strip(),
        "format": "json",
        "categories": categories,
    }
    if engines:
        params["engines"] = engines

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{SEARXNG_URL}/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "engine": item.get("engine", ""),
            "score": item.get("score", 0),
        })

    return {
        "query": query.strip(),
        "results": results,
        "count": len(results),
    }
