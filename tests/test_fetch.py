"""Tests for web fetch tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_research_tools.tools.fetch import web_fetch


def _make_safe_stream_cm(html_bytes, status_code, url, content_type):
    """Build an async context manager mimicking safe_stream() return."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.url = url
    mock_resp.headers = {"content-type": content_type}
    mock_resp.raise_for_status = MagicMock()
    mock_resp.is_redirect = False

    async def fake_aiter():
        yield html_bytes

    mock_resp.aiter_bytes = fake_aiter

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_fetch_html_extracts_text():
    html = b"<html><head><title>Test Page</title></head><body><p>Hello world content</p></body></html>"
    cm = _make_safe_stream_cm(html, 200, "https://example.com", "text/html")

    with (
        patch("mcp_research_tools.tools.fetch.validate_url"),
        patch("mcp_research_tools.tools.fetch.safe_stream", return_value=cm),
    ):
        result = await web_fetch("https://example.com")

    assert result["status_code"] == 200
    assert "content_text" in result
    assert result["content_type"] == "text/html"


@pytest.mark.asyncio
async def test_fetch_invalid_url_raises():
    with pytest.raises(ValueError, match="scheme"):
        await web_fetch("not-a-url")


@pytest.mark.asyncio
async def test_fetch_ftp_url_raises():
    with pytest.raises(ValueError, match="scheme"):
        await web_fetch("ftp://files.example.com/data")


@pytest.mark.asyncio
async def test_fetch_html_extracts_title():
    html = b"<html><head><title>My Title</title></head><body><p>Content here</p></body></html>"
    cm = _make_safe_stream_cm(html, 200, "https://example.com", "text/html; charset=utf-8")

    with (
        patch("mcp_research_tools.tools.fetch.validate_url"),
        patch("mcp_research_tools.tools.fetch.safe_stream", return_value=cm),
    ):
        result = await web_fetch("https://example.com")

    assert result["title"] == "My Title"
    assert result["content_type"] == "text/html"


@pytest.mark.asyncio
async def test_fetch_json_content():
    json_bytes = b'{"key": "value"}'
    cm = _make_safe_stream_cm(json_bytes, 200, "https://api.example.com/data", "application/json")

    with (
        patch("mcp_research_tools.tools.fetch.validate_url"),
        patch("mcp_research_tools.tools.fetch.safe_stream", return_value=cm),
    ):
        result = await web_fetch("https://api.example.com/data")

    assert result["content_text"] == '{"key": "value"}'
    assert result["content_type"] == "application/json"


@pytest.mark.asyncio
async def test_fetch_respects_size_limit():
    """Test that exceeding MAX_FETCH_SIZE_MB raises ValueError."""
    cm = _make_safe_stream_cm(
        b"some content that exceeds 0 MB", 200, "https://example.com/huge", "text/html"
    )

    with (
        patch("mcp_research_tools.tools.fetch.validate_url"),
        patch("mcp_research_tools.tools.fetch.safe_stream", return_value=cm),
        patch("mcp_research_tools.tools.fetch.MAX_FETCH_SIZE_MB", 0),
    ):
        with pytest.raises(ValueError, match="exceeds"):
            await web_fetch("https://example.com/huge")


@pytest.mark.asyncio
async def test_fetch_follows_redirects():
    """Test that the final URL is captured (safe_stream handles redirects internally)."""
    html = b"<html><body><p>Redirected content</p></body></html>"
    cm = _make_safe_stream_cm(html, 200, "https://example.com/final", "text/html")

    with (
        patch("mcp_research_tools.tools.fetch.validate_url"),
        patch("mcp_research_tools.tools.fetch.safe_stream", return_value=cm),
    ):
        result = await web_fetch("https://example.com/redirect")

    assert result["url"] == "https://example.com/final"


@pytest.mark.asyncio
async def test_fetch_blocks_private_ip():
    """SSRF: fetching a private IP should be rejected."""
    with pytest.raises(ValueError, match="[Bb]locked"):
        await web_fetch("http://127.0.0.1/admin")


@pytest.mark.asyncio
async def test_fetch_blocks_metadata_endpoint():
    """SSRF: cloud metadata endpoint should be rejected."""
    with pytest.raises(ValueError, match="[Bb]locked"):
        await web_fetch("http://169.254.169.254/latest/meta-data/")
