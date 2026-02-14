#!/bin/bash
set -euo pipefail

echo "=== MCP Research Tools — Install ==="

# 1. Brew dependencies
echo "Installing brew dependencies..."
brew install ffmpeg yt-dlp whisper-cpp

# 2. Whisper model
WHISPER_MODEL="${WHISPER_MODEL:-small}"
MODEL_DIR="$HOME/.cache/whisper-cpp"
MODEL_FILE="$MODEL_DIR/ggml-${WHISPER_MODEL}.bin"

if [ ! -f "$MODEL_FILE" ]; then
    echo "Downloading whisper $WHISPER_MODEL model..."
    mkdir -p "$MODEL_DIR"
    # Try brew download script first, fall back to HuggingFace direct download
    WHISPER_PREFIX="$(brew --prefix whisper-cpp)"
    if [ -f "$WHISPER_PREFIX/models/download-ggml-model.sh" ]; then
        bash "$WHISPER_PREFIX/models/download-ggml-model.sh" "$WHISPER_MODEL"
        # Move model to our cache dir if downloaded elsewhere
        if [ -f "$WHISPER_PREFIX/models/ggml-${WHISPER_MODEL}.bin" ]; then
            cp "$WHISPER_PREFIX/models/ggml-${WHISPER_MODEL}.bin" "$MODEL_FILE"
        fi
    else
        echo "Brew download script not found, downloading from HuggingFace..."
        curl -L --progress-bar \
            -o "$MODEL_FILE" \
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-${WHISPER_MODEL}.bin"
    fi
else
    echo "Whisper model already downloaded: $MODEL_FILE"
fi

# 3. SearXNG Docker
echo "Starting SearXNG + Redis..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Generate secret key if placeholder exists
if grep -q "REPLACE_ME" "$SCRIPT_DIR/searxng/settings.yml" 2>/dev/null; then
    SECRET=$(openssl rand -hex 32)
    sed -i '' "s/REPLACE_ME/$SECRET/" "$SCRIPT_DIR/searxng/settings.yml"
    echo "Generated SearXNG secret key"
fi

cd "$SCRIPT_DIR"
docker compose up -d

# 4. Python venv
echo "Setting up Python environment..."
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
fi
source "$SCRIPT_DIR/venv/bin/activate"
pip install -e ".[dev]"

# 5. Verify
echo ""
echo "=== Verification ==="
echo "ffmpeg:      $(which ffmpeg)"
echo "yt-dlp:      $(which yt-dlp)"
echo "whisper-cli: $(which whisper-cli)"
echo "whisper model: $MODEL_FILE"
echo ""
echo "Test SearXNG:"
echo "  curl 'http://localhost:8080/search?q=test&format=json' | python3 -m json.tool"
echo ""
echo "Run MCP server (stdio):"
echo "  source venv/bin/activate && python -m mcp_research_tools.server"
echo ""
echo "Run MCP server (HTTP):"
echo "  MCP_TRANSPORT=streamable-http MCP_PORT=9000 python -m mcp_research_tools.server"
echo ""
echo "=== Done ==="
