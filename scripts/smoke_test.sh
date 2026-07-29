#!/usr/bin/env bash
# Docker Compose smoke test — validates the full stack comes up healthy.
# Usage: bash scripts/smoke_test.sh

set -euo pipefail

COMPOSE_CMD="docker compose"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:8080}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "=== Recipelity Smoke Test ==="
echo "Frontend : $FRONTEND_URL"
echo "Backend  : $BACKEND_URL"

# ── 1. Backend health ───────────────────────────────────────────────────
echo ""
echo "[1/5] Backend liveness..."
for i in $(seq 1 10); do
  if curl -sf "$BACKEND_URL/health/live" > /dev/null 2>&1; then
    echo "  PASS: /health/live"
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "  FAIL: /health/live not reachable after 10 attempts"
    exit 1
  fi
  sleep 2
done

echo "[2/5] Backend readiness..."
for i in $(seq 1 10); do
  STATUS=$(curl -sf "$BACKEND_URL/health/ready" 2>&1 || true)
  if echo "$STATUS" | grep -q '"database":"connected"'; then
    echo "  PASS: /health/ready — $STATUS"
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "  FAIL: /health/ready not healthy after 10 attempts"
    exit 1
  fi
  sleep 2
done

# ── 2. Frontend homepage ────────────────────────────────────────────────
echo ""
echo "[3/5] Frontend homepage..."
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$FRONTEND_URL/" 2>&1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "  PASS: Frontend homepage returns 200"
else
  echo "  FAIL: Frontend returned HTTP $HTTP_CODE"
  exit 1
fi

# ── 3. SPA deep link ────────────────────────────────────────────────────
echo ""
echo "[4/5] SPA deep link (/recipes/1)..."
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$FRONTEND_URL/recipes/1" 2>&1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "  PASS: Deep link /recipes/1 returns 200 (SPA fallback works)"
else
  echo "  FAIL: Deep link returned HTTP $HTTP_CODE"
  exit 1
fi

# ── 4. API recipes list ─────────────────────────────────────────────────
echo ""
echo "[5/5] API reachable via frontend proxy..."
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$FRONTEND_URL/api/v1/recipes?page=1&page_size=1" 2>&1 || echo "fail")
if [ "$HTTP_CODE" = "200" ]; then
  echo "  PASS: /api/v1/recipes returns 200 via frontend proxy"
else
  echo "  FAIL: API via frontend proxy returned: $HTTP_CODE"
  exit 1
fi

echo ""
echo "=== All smoke tests PASSED ==="
