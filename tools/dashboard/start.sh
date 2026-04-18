#!/bin/bash
cd "$(dirname "$0")"
# Kill anything on port 5002 before starting
lsof -ti:5002 | xargs kill -9 2>/dev/null || true
sleep 1
exec /Library/Developer/CommandLineTools/usr/bin/python3 -m gunicorn -c gunicorn.conf.py app:app
