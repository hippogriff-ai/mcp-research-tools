"""Tests for SearXNG search tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_research_tools.tools.search import searxng_search


@pytest.mark.asyncio
async def test_search_returns_results():
    mock_response = {
        "results": [
            {"url": "https://example.com", "title": "Example", "content": "A snippet"},
        ],
        "number_of_results": 1,
    }
    with patch("mcp_research_tools.tools.search.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_resp

        result = await searxng_search("test query")

    assert result["query"] == "test query"
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Example"
    assert result["results"][0]["url"] == "https://example.com"
    assert result["results"][0]["snippet"] == "A snippet"
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_search_empty_query_raises():
    with pytest.raises(ValueError, match="empty"):
        await searxng_search("")


@pytest.mark.asyncio
async def test_search_whitespace_query_raises():
    with pytest.raises(ValueError, match="empty"):
        await searxng_search("   ")


@pytest.mark.asyncio
async def test_search_respects_max_results():
    mock_response = {
        "results": [
            {"url": f"https://example.com/{i}", "title": f"Result {i}", "content": f"Snippet {i}"}
            for i in range(20)
        ],
    }
    with patch("mcp_research_tools.tools.search.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_resp

        result = await searxng_search("test", max_results=5)

    assert len(result["results"]) == 5
    assert result["count"] == 5


@pytest.mark.asyncio
async def test_search_passes_engines_param():
    mock_response = {"results": []}
    with patch("mcp_research_tools.tools.search.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_resp

        await searxng_search("test", engines="duckduckgo,brave")

    call_kwargs = mock_instance.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert params["engines"] == "duckduckgo,brave"


@pytest.mark.asyncio
async def test_search_strips_query_whitespace():
    mock_response = {
        "results": [
            {"url": "https://example.com", "title": "Example", "content": "A snippet"},
        ],
    }
    with patch("mcp_research_tools.tools.search.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_resp

        result = await searxng_search("  test query  ")

    assert result["query"] == "test query"


@pytest.mark.asyncio
async def test_search_rejects_invalid_category():
    """Invalid categories should be rejected."""
    with pytest.raises(ValueError, match="Invalid category"):
        await searxng_search("test", categories="evil_category")


@pytest.mark.asyncio
async def test_search_rejects_malicious_engines():
    """Engine params with special characters should be rejected."""
    with pytest.raises(ValueError, match="Invalid characters"):
        await searxng_search("test", engines="duckduckgo;rm -rf /")


@pytest.mark.asyncio
async def test_search_caps_max_results():
    """max_results should be capped at 50."""
    mock_response = {
        "results": [
            {"url": f"https://example.com/{i}", "title": f"R{i}", "content": f"S{i}"}
            for i in range(100)
        ],
    }
    with patch("mcp_research_tools.tools.search.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_resp

        result = await searxng_search("test", max_results=999)

    assert len(result["results"]) <= 50
