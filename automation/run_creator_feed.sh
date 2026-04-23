#!/bin/bash
cd "/Users/allenenriquez/Developer/Allen-Enriquez"
export PYTHONPATH="/Users/allenenriquez/Developer/Allen-Enriquez"
export PATH="/opt/homebrew/bin:$PATH"

PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"
MAX_RETRIES=2
RETRY_DELAY=60

for attempt in $(seq 1 $MAX_RETRIES); do
    $PYTHON tools/creator_feed.py && exit 0
    echo "[$(date)] Attempt $attempt failed (exit $?). Retrying in ${RETRY_DELAY}s..." >&2
    sleep $RETRY_DELAY
done

echo "[$(date)] Creator feed failed after $MAX_RETRIES attempts" >&2
exit 1
