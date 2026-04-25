#!/bin/bash
# Inbox auto-sync — pings each platform's inbox endpoint on Railway prod
# every 15 min so comments + DMs arrive without manual button clicks.

set -u
LOG_DIR="/Users/allenenriquez/Developer/Allen-Enriquez/.tmp"
mkdir -p "$LOG_DIR"

BASE="https://content-hub-production-b28e.up.railway.app"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

ENDPOINTS=(
  "/api/facebook/comments"
  "/api/facebook/conversations"
  "/api/instagram/comments"
  "/api/instagram/conversations"
  "/api/youtube/comments"
)

OVERALL=0
for path in "${ENDPOINTS[@]}"; do
  URL="${BASE}${path}"
  HTTP_CODE=$(curl -sS -o /tmp/inbox_sync_resp.json -w "%{http_code}" \
      "$URL" --max-time 60)
  BODY=$(cat /tmp/inbox_sync_resp.json 2>/dev/null | head -c 500 || echo "")
  echo "[$TS] $path → $HTTP_CODE :: $BODY"
  if [ "$HTTP_CODE" != "200" ]; then
    OVERALL=1
  fi
done

exit "$OVERALL"
