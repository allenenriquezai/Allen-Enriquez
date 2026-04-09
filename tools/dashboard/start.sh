#!/bin/bash
cd "$(dirname "$0")"
exec /Library/Developer/CommandLineTools/usr/bin/python3 -m gunicorn -c gunicorn.conf.py app:app
