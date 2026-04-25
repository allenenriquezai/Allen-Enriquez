#!/bin/bash
# Weekly Instagram (FB Graph) long-lived token refresh.
# Hits the deployed Railway endpoint so the refresh runs against the
# production DB row (Railway sqlite volume), not the local dev DB.

set -u
LOG_DIR="/Users/allenenriquez/Developer/Allen-Enriquez/.tmp"
mkdir -p "$LOG_DIR"

URL="https://content-hub-production-b28e.up.railway.app/api/instagram/refresh-token"
STATUS_URL="https://content-hub-production-b28e.up.railway.app/api/instagram/token-status"

TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TS] POST $URL"

HTTP_CODE=$(curl -sS -o /tmp/ig_refresh_resp.json -w "%{http_code}" \
    -X POST "$URL" \
    -H "Content-Type: application/json" \
    --max-time 30)

BODY=$(cat /tmp/ig_refresh_resp.json 2>/dev/null || echo "")
echo "[$TS] HTTP $HTTP_CODE :: $BODY"

if [ "$HTTP_CODE" != "200" ]; then
    echo "[$TS] IG token refresh FAILED" >&2
    # Best-effort status check for context
    curl -sS --max-time 10 "$STATUS_URL" >&2 || true
    exit 1
fi

# Optional follow-up status log
curl -sS --max-time 10 "$STATUS_URL" || true
echo ""
exit 0
