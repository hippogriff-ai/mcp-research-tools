# MCP Research Tools

MCP server providing web search (SearXNG), page fetch (trafilatura), video/audio processing (yt-dlp + ffmpeg + whisper), and image analysis — all running locally on macOS Apple Silicon.

## Architecture

```
Docker                              Native (Mac mini)
┌──────────────┐                    ┌─────────────────────────┐
│  SearXNG     │◄── JSON API ──────│  MCP Server (FastMCP)   │
│  :8080       │                    │  ├─ searxng_search      │
│  Redis       │                    │  ├─ web_fetch           │
└──────────────┘                    │  ├─ process_video       │
                                    │  └─ analyze_image       │
                                    └────────┬────────────────┘
                                       stdio │ streamable-http
                                    Claude Code / Agent Harness
```

SearXNG + Redis run in Docker. The MCP server and media tools (ffmpeg, yt-dlp, whisper-cli) run natively so whisper gets Apple Silicon Metal acceleration.

## Quick Start

```bash
git clone git@github.com:hippogriff-ai/mcp-research-tools.git
cd mcp-research-tools
chmod +x install.sh
./install.sh
```

The install script:
1. Installs `ffmpeg`, `yt-dlp`, `whisper-cpp` via Homebrew
2. Downloads the Whisper `small` model (~465MB)
3. Starts SearXNG + Redis via Docker Compose
4. Creates a Python venv and installs the project

## Tools

### `searxng_search` — Web Search

Queries local SearXNG instance (70+ search engines aggregated, zero API cost).

```
searxng - searxng_search(query="your search", max_results=10, engines="duckduckgo,brave")
```

Returns: `{ query, results: [{ title, url, snippet, engine, score }], count }`

### `web_fetch` — Page Fetch

Downloads a web page and extracts clean readable text via trafilatura. No DOM bloat.

```
searxng - web_fetch(url="https://example.com", extract_text=true)
```

Returns: `{ status_code, url, content_type, content_text, title }`

### `process_video` — Video Processing

Downloads YouTube/TikTok videos, trims to 120s, extracts audio + keyframes every 3s, transcribes audio via whisper-cli.

```
searxng - process_video(url="https://youtube.com/watch?v=...")
```

Returns: `{ transcript, frames: ["/tmp/.../frame_0001.jpg", ...], audio_path, duration_seconds }`

### `analyze_image` — Image Analysis

Fetches images from URLs (cached locally) or validates local paths for Claude vision reasoning.

```
searxng - analyze_image(source="https://example.com/photo.jpg")
```

Returns: `{ path, exists, content_type }`

## Usage

### Claude Code (stdio)

Add to your project `.mcp.json`:

```json
{
  "mcpServers": {
    "searxng": {
      "command": "/path/to/mcp-research-tools/venv/bin/python",
      "args": ["-m", "mcp_research_tools.server"]
    }
  }
}
```

Or add globally in `~/.claude.json` under the `mcpServers` key for every session.

### Remote Agent Harness (streamable-http)

```bash
source venv/bin/activate
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=9000 \
  python -m mcp_research_tools.server
```

Connect from client at `http://<mac-mini-ip>:9000/mcp`.

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | `http://localhost:8080` | SearXNG instance URL |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | Bind host for HTTP transport |
| `MCP_PORT` | `9000` | Port for HTTP transport |
| `MAX_VIDEO_SECONDS` | `120` | Max video duration to process |
| `FRAME_EVERY_SECONDS` | `3` | Keyframe extraction interval |
| `WHISPER_MODEL` | `small` | Whisper model (tiny/base/small/medium/large) |
| `WHISPER_CPP_BIN` | `whisper-cli` | Whisper binary name |
| `WHISPER_MODEL_PATH` | `~/.cache/whisper-cpp/ggml-small.bin` | Path to whisper model |
| `MAX_FETCH_SIZE_MB` | `10` | Max page download size |
| `FETCH_TIMEOUT_SECONDS` | `30` | Page fetch timeout |

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Docker Desktop
- Homebrew
- Python 3.13+

## Development

```bash
source venv/bin/activate

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Managing SearXNG

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f searxng

# Test JSON API
curl 'http://localhost:8080/search?q=test&format=json' | python3 -m json.tool
```
