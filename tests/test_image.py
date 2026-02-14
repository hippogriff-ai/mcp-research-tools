"""Tests for image analysis tool."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp_research_tools.tools.image import fetch_image, _guess_content_type


@pytest.mark.asyncio
async def test_fetch_image_local_file(tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

    result = await fetch_image(str(img))
    assert result["path"] == str(img)
    assert result["exists"] is True
    assert result["content_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_fetch_image_missing_file():
    result = await fetch_image("/nonexistent/image.jpg")
    assert result["exists"] is False


@pytest.mark.asyncio
async def test_fetch_image_from_url(tmp_path):
    with patch("mcp_research_tools.tools.image.MEDIA_TEMP_DIR", tmp_path):
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


def test_guess_content_type():
    assert _guess_content_type(".jpg") == "image/jpeg"
    assert _guess_content_type(".png") == "image/png"
    assert _guess_content_type(".webp") == "image/webp"
    assert _guess_content_type(".xyz") == "application/octet-stream"
