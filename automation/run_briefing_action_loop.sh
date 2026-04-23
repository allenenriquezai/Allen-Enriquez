#!/bin/bash
cd "/Users/allenenriquez/Developer/Allen-Enriquez"
export PYTHONPATH="/Users/allenenriquez/Developer/Allen-Enriquez"

PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"
MAX_RETRIES=3
RETRY_DELAY=30

for attempt in $(seq 1 $MAX_RETRIES); do
    $PYTHON tools/personal/briefing_action_loop.py && exit 0
    echo "[$(date)] Attempt $attempt failed (exit $?). Retrying in ${RETRY_DELAY}s..." >&2
    sleep $RETRY_DELAY
done

echo "[$(date)] Briefing action loop failed after $MAX_RETRIES attempts" >&2
exit 1
