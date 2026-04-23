#!/bin/bash
# PH Outreach daily pipeline: enrich -> queue -> followups -> replies.
# Sends WhatsApp notification when queue is ready.
# Runs 6am PH (launchd schedule).

cd "/Users/allenenriquez/Developer/Allen-Enriquez"
export PYTHONPATH="/Users/allenenriquez/Developer/Allen-Enriquez"

PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"
LOG_DIR="/Users/allenenriquez/Developer/Allen-Enriquez/.tmp"
LOG="$LOG_DIR/ph_outreach_daily.log"
DATE=$(date +%Y-%m-%d)

echo "[$(date)] === PH Outreach daily run ===" >> "$LOG"

$PYTHON tools/outreach.py enrich --limit 20 >> "$LOG" 2>&1
$PYTHON tools/outreach.py followups >> "$LOG" 2>&1
$PYTHON tools/outreach.py queue >> "$LOG" 2>&1
$PYTHON tools/outreach.py replies >> "$LOG" 2>&1

QUEUE_FILE="projects/personal/.tmp/outreach_queue_${DATE}.md"
if [ -f "$QUEUE_FILE" ]; then
    COUNT=$(grep -c "^## [0-9]" "$QUEUE_FILE" 2>/dev/null || echo 0)
    MSG="PH outreach ready: $COUNT messages for $DATE. Open $QUEUE_FILE, send, then run: python3 tools/outreach.py log-sent --ids 1,2,3..."
    $PYTHON tools/whatsapp.py --body "$MSG" >> "$LOG" 2>&1 || echo "[$(date)] whatsapp notify failed" >> "$LOG"
fi

echo "[$(date)] === done ===" >> "$LOG"
