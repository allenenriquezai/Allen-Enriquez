#!/bin/bash
cd "/Users/allenenriquez/Developer/Allen-Enriquez"
export PYTHONPATH="/Users/allenenriquez/Developer/Allen-Enriquez"
export PATH="/opt/homebrew/bin:$PATH"

PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"

$PYTHON tools/daily_token_audit.py
