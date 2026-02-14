"""Integration test — verifies all tools are registered on the MCP server."""

import asyncio

import pytest

from mcp_research_tools.server import mcp


@pytest.fixture
def tools():
    """Load all registered tools from the MCP server."""
    return asyncio.get_event_loop().run_until_complete(mcp.get_tools())


def test_server_has_all_tools(tools):
    """All 4 MCP tools should be registered."""
    tool_names = set(tools.keys())
    expected = {"searxng_search", "web_fetch", "process_video", "analyze_image"}
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


def test_server_name():
    assert mcp.name == "searxng"


def test_search_tool_has_docstring(tools):
    assert "searxng_search" in tools
    assert "SearXNG" in (tools["searxng_search"].description or "")


def test_process_video_tool_has_docstring(tools):
    assert "process_video" in tools
    assert "YouTube" in (tools["process_video"].description or "")


def test_fetch_tool_has_docstring(tools):
    assert "web_fetch" in tools
    assert "trafilatura" in (tools["web_fetch"].description or "").lower()


def test_analyze_image_tool_has_docstring(tools):
    assert "analyze_image" in tools
    assert "image" in (tools["analyze_image"].description or "").lower()
