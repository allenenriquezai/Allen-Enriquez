#!/bin/bash
cd "/Users/allenenriquez/Developer/Allen-Enriquez"
export PYTHONPATH="/Users/allenenriquez/Developer/Allen-Enriquez"

PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"

$PYTHON tools/shared/ryan_self_improve.py >> .tmp/ryan-self-improve.log 2>&1
