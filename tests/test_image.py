"""Tests for image analysis tool."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp_research_tools.tools.image import fetch_image, _guess_content_type


@pytest.mark.asyncio
async def test_fetch_image_local_file(tmp_path):
    """Local images inside MEDIA_TEMP_DIR should work."""
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

    with patch("mcp_research_tools.tools.image.MEDIA_TEMP_DIR", tmp_path):
        result = await fetch_image(str(img))

    assert result["path"] == str(img)
    assert result["exists"] is True
    assert result["content_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_fetch_image_rejects_path_outside_allowed(tmp_path):
    """Path traversal: paths outside MEDIA_TEMP_DIR should be blocked."""
    with patch("mcp_research_tools.tools.image.MEDIA_TEMP_DIR", tmp_path):
        with pytest.raises(ValueError, match="outside"):
            await fetch_image("/etc/secret.jpg")


@pytest.mark.asyncio
async def test_fetch_image_rejects_non_image(tmp_path):
    """Non-image extensions should be blocked for local paths."""
    txt = tmp_path / "secret.txt"
    txt.touch()
    with patch("mcp_research_tools.tools.image.MEDIA_TEMP_DIR", tmp_path):
        with pytest.raises(ValueError, match="extension"):
            await fetch_image(str(txt))


@pytest.mark.asyncio
async def test_fetch_image_from_url(tmp_path):
    with patch("mcp_research_tools.tools.image.MEDIA_TEMP_DIR", tmp_path):
        with patch("mcp_research_tools.tools.image.validate_url", return_value="https://example.com/photo.jpg"):
            with patch("mcp_research_tools.tools.image.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_resp = MagicMock()
                mock_resp.content = b"\xff\xd8\xff\xe0fake-jpeg"
                mock_resp.raise_for_status = MagicMock()
                mock_resp.headers = {"content-type": "image/jpeg"}
                mock_instance.get = AsyncMock(return_value=mock_resp)

                result = await fetch_image("https://example.com/photo.jpg")

    assert result["exists"] is True
    assert result["path"].endswith(".jpg")
    assert result["content_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_fetch_image_blocks_private_ip():
    """SSRF: image fetch from private IP should be blocked."""
    with pytest.raises(ValueError, match="[Bb]locked"):
        await fetch_image("http://192.168.1.1/image.jpg")


def test_guess_content_type():
    assert _guess_content_type(".jpg") == "image/jpeg"
    assert _guess_content_type(".png") == "image/png"
    assert _guess_content_type(".webp") == "image/webp"
    assert _guess_content_type(".xyz") == "application/octet-stream"
