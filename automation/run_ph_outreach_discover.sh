#!/bin/bash
# PH Outreach weekly discovery: pull new prospects from all sources.
# Runs Sunday 3am (launchd schedule).

cd "/Users/allenenriquez/Developer/Allen-Enriquez"
export PYTHONPATH="/Users/allenenriquez/Developer/Allen-Enriquez"

PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"
LOG_DIR="/Users/allenenriquez/Developer/Allen-Enriquez/.tmp"
LOG="$LOG_DIR/ph_outreach_discover.log"

echo "[$(date)] === PH Outreach weekly discover ===" >> "$LOG"
$PYTHON tools/personal/outreach.py discover --limit 50 >> "$LOG" 2>&1
echo "[$(date)] === done ===" >> "$LOG"
