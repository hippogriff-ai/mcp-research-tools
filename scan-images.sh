#!/usr/bin/env bash
# Scan SearXNG Docker images for vulnerabilities, pull updates, and restart.
# Designed to run weekly via cron on macOS.
set -euo pipefail

# Ensure cron can find binaries (Homebrew + Docker Desktop)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y-%m-%d_%H%M)
LOG_FILE="$LOG_DIR/scan-$TIMESTAMP.log"
IMAGES=("searxng/searxng:latest" "valkey/valkey:8-alpine")

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== SearXNG Image Scan Started ==="

# ── 1. Pull latest images ──────────────────────────────
for img in "${IMAGES[@]}"; do
    log "Pulling $img..."
    if docker pull "$img" >> "$LOG_FILE" 2>&1; then
        log "  ✓ Pulled $img"
    else
        log "  ✗ Failed to pull $img"
    fi
done

# ── 2. Scan each image with Trivy (JSON for accurate counts) ──
FOUND_ISSUES=0
for img in "${IMAGES[@]}"; do
    log "Scanning $img..."

    # JSON output for accurate vulnerability counts
    JSON_OUTPUT=$(trivy image --severity HIGH,CRITICAL --format json --scanners vuln "$img" 2>/dev/null) || true
    HIGH_COUNT=$(echo "$JSON_OUTPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
count = sum(1 for r in data.get('Results', []) for v in r.get('Vulnerabilities', []) if v.get('Severity') == 'HIGH')
print(count)
" 2>/dev/null || echo 0)
    CRIT_COUNT=$(echo "$JSON_OUTPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
count = sum(1 for r in data.get('Results', []) for v in r.get('Vulnerabilities', []) if v.get('Severity') == 'CRITICAL')
print(count)
" 2>/dev/null || echo 0)

    # Table output for human-readable log
    trivy image --severity HIGH,CRITICAL --format table --scanners vuln "$img" >> "$LOG_FILE" 2>&1 || true

    if [ "$CRIT_COUNT" -gt 0 ]; then
        log "  ⚠ $img: $CRIT_COUNT CRITICAL, $HIGH_COUNT HIGH vulnerabilities"
        FOUND_ISSUES=1
    elif [ "$HIGH_COUNT" -gt 0 ]; then
        log "  △ $img: $HIGH_COUNT HIGH vulnerabilities (no critical)"
    else
        log "  ✓ $img: No HIGH/CRITICAL vulnerabilities"
    fi
done

# ── 3. Restart containers if images were updated ───────
CURRENT_SEARXNG=$(docker inspect searxng --format '{{.Image}}' 2>/dev/null || echo "none")
LATEST_SEARXNG=$(docker image inspect searxng/searxng:latest --format '{{.Id}}' 2>/dev/null || echo "unknown")

if [ "$CURRENT_SEARXNG" != "$LATEST_SEARXNG" ]; then
    log "Image updated — restarting containers..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d >> "$LOG_FILE" 2>&1
    log "  ✓ Containers restarted with latest images"
else
    log "Images unchanged — no restart needed"
fi

# ── 4. Prune old logs (keep last 30) ──────────────────
ls -t "$LOG_DIR"/scan-*.log 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null || true

log "=== Scan Complete ==="

# Exit non-zero if critical vulnerabilities found (useful for alerting)
if [ "$FOUND_ISSUES" -eq 1 ]; then
    log "Action needed: CRITICAL vulnerabilities detected"
    exit 1
fi
exit 0
