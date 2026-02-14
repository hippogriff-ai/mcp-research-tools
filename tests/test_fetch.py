"""Tests for web fetch tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_research_tools.tools.fetch import web_fetch


def _make_mock_client(html_bytes, status_code, url, content_type):
    """Helper to build the nested async mock for httpx streaming."""
    mock_client = MagicMock()

    mock_stream = MagicMock()
    mock_stream.status_code = status_code
    mock_stream.url = url
    mock_stream.headers = {"content-type": content_type}
    mock_stream.raise_for_status = MagicMock()

    async def fake_aiter():
        yield html_bytes

    mock_stream.aiter_bytes = fake_aiter

    # client.stream("GET", url) must return an async context manager
    stream_cm = MagicMock()
    stream_cm.__aenter__ = AsyncMock(return_value=mock_stream)
    stream_cm.__aexit__ = AsyncMock(return_value=False)

    mock_instance = MagicMock()
    mock_instance.stream.return_value = stream_cm

    # AsyncClient() must return an async context manager
    mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_client


@pytest.mark.asyncio
async def test_fetch_html_extracts_text():
    html = b"<html><head><title>Test Page</title></head><body><p>Hello world content</p></body></html>"
    mock_client = _make_mock_client(html, 200, "https://example.com", "text/html")

    with patch("mcp_research_tools.tools.fetch.httpx.AsyncClient", mock_client):
        result = await web_fetch("https://example.com")

    assert result["status_code"] == 200
    assert "content_text" in result
    assert result["content_type"] == "text/html"


@pytest.mark.asyncio
async def test_fetch_invalid_url_raises():
    with pytest.raises(ValueError, match="Invalid URL"):
        await web_fetch("not-a-url")


@pytest.mark.asyncio
async def test_fetch_ftp_url_raises():
    with pytest.raises(ValueError, match="Invalid URL"):
        await web_fetch("ftp://files.example.com/data")


@pytest.mark.asyncio
async def test_fetch_html_extracts_title():
    html = b"<html><head><title>My Title</title></head><body><p>Content here</p></body></html>"
    mock_client = _make_mock_client(html, 200, "https://example.com", "text/html; charset=utf-8")

    with patch("mcp_research_tools.tools.fetch.httpx.AsyncClient", mock_client):
        result = await web_fetch("https://example.com")

    assert result["title"] == "My Title"
    assert result["content_type"] == "text/html"


@pytest.mark.asyncio
async def test_fetch_json_content():
    json_bytes = b'{"key": "value"}'
    mock_client = _make_mock_client(json_bytes, 200, "https://api.example.com/data", "application/json")

    with patch("mcp_research_tools.tools.fetch.httpx.AsyncClient", mock_client):
        result = await web_fetch("https://api.example.com/data")

    assert result["content_text"] == '{"key": "value"}'
    assert result["content_type"] == "application/json"


@pytest.mark.asyncio
async def test_fetch_respects_size_limit():
    """Test that exceeding MAX_FETCH_SIZE_MB raises ValueError."""
    mock_client = _make_mock_client(
        b"some content that exceeds 0 MB", 200, "https://example.com/huge", "text/html"
    )

    with patch("mcp_research_tools.tools.fetch.MAX_FETCH_SIZE_MB", 0):
        with patch("mcp_research_tools.tools.fetch.httpx.AsyncClient", mock_client):
            with pytest.raises(ValueError, match="exceeds"):
                await web_fetch("https://example.com/huge")


@pytest.mark.asyncio
async def test_fetch_follows_redirects():
    """Test that the final URL is captured after redirects."""
    html = b"<html><body><p>Redirected content</p></body></html>"
    mock_client = _make_mock_client(html, 200, "https://example.com/final", "text/html")

    with patch("mcp_research_tools.tools.fetch.httpx.AsyncClient", mock_client):
        result = await web_fetch("https://example.com/redirect")

    assert result["url"] == "https://example.com/final"
