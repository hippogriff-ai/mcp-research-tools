"""Search tool using local SearXNG instance."""

import httpx

from ..config import ALLOWED_CATEGORIES, SEARXNG_URL
from ..security import sanitize_content


async def searxng_search(
    query: str,
    max_results: int = 10,
    engines: str | None = None,
    categories: str = "general",
) -> dict:
    """Search via local SearXNG JSON API.

    Args:
        query: Search query string.
        max_results: Max results to return (default 10, capped at 50).
        engines: Comma-separated engine names (e.g. "duckduckgo,brave").
        categories: Search category (default "general").

    Returns:
        Dict with query, results list, and count.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    # Cap max_results to prevent abuse
    max_results = min(max(1, max_results), 50)

    # Validate category
    if categories not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Invalid category {categories!r}. "
            f"Allowed: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    # Validate engines — alphanumeric + commas only
    if engines is not None:
        cleaned = engines.strip()
        if not cleaned:
            engines = None
        elif not all(c.isalnum() or c in (",", "_", " ") for c in cleaned):
            raise ValueError(f"Invalid characters in engines parameter: {engines!r}")
        else:
            engines = cleaned

    params: dict = {
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
            "title": sanitize_content(item.get("title", ""), max_length=500),
            "url": item.get("url", ""),
            "snippet": sanitize_content(item.get("content", ""), max_length=2000),
            "engine": item.get("engine", ""),
            "score": item.get("score", 0),
        })

    return {
        "query": query.strip(),
        "results": results,
        "count": len(results),
    }
