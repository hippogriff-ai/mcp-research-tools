"""Tests for media processing tool."""

import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path

from mcp_research_tools.tools.media import is_media_url, process_media, _find_video_file, _list_frames


def test_is_media_url_youtube():
    assert is_media_url("https://www.youtube.com/watch?v=abc123")
    assert is_media_url("https://youtu.be/abc123")
    assert is_media_url("https://m.youtube.com/watch?v=abc123")


def test_is_media_url_tiktok():
    assert is_media_url("https://www.tiktok.com/@user/video/123")
    assert is_media_url("https://vm.tiktok.com/abc123")


def test_is_media_url_regular_site():
    assert not is_media_url("https://example.com")
    assert not is_media_url("https://google.com")


def test_is_media_url_rejects_spoofed_hostname():
    """Attacker embedding youtube.com in path should NOT match."""
    assert not is_media_url("https://evil.com/youtube.com/watch?v=abc")
    assert not is_media_url("https://evil.com?redirect=youtube.com")


def test_find_video_file(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"fake")
    assert _find_video_file(tmp_path) == tmp_path / "video.mp4"


def test_find_video_file_missing(tmp_path):
    assert _find_video_file(tmp_path) is None


def test_list_frames(tmp_path):
    (tmp_path / "out_0001.jpg").write_bytes(b"f1")
    (tmp_path / "out_0002.jpg").write_bytes(b"f2")
    (tmp_path / "other.txt").write_bytes(b"x")
    frames = _list_frames(tmp_path)
    assert len(frames) == 2
    assert all("out_" in f for f in frames)


def test_list_frames_empty_dir(tmp_path):
    assert _list_frames(tmp_path) == []


def test_list_frames_nonexistent():
    assert _list_frames(Path("/nonexistent")) == []


@pytest.mark.asyncio
async def test_process_media_download_failure(tmp_path):
    with patch("mcp_research_tools.tools.media.MEDIA_TEMP_DIR", tmp_path):
        with patch("mcp_research_tools.tools.media.validate_url", return_value="https://youtu.be/test123"):
            with patch("mcp_research_tools.tools.media._run_cmd", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = (1, "", "download error")
                result = await process_media("https://youtu.be/test123")

    assert "error" in result
    assert "Download failed" in result["error"]
    assert result["source_url"] == "https://youtu.be/test123"


@pytest.mark.asyncio
async def test_process_media_rejects_unsupported_url():
    """Non-media URLs should be rejected."""
    with pytest.raises(ValueError, match="Unsupported"):
        await process_media("https://example.com/video.mp4")
