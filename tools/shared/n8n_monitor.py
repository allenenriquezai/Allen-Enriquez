"""
n8n Workflow Error Monitor + Auto-Fix

Polls n8n API for failed executions, sends email alerts, retries automatically,
and uses Claude to diagnose persistent failures.

Usage:
    python3 tools/n8n_monitor.py              # check for new errors
    python3 tools/n8n_monitor.py --dry-run    # print what would happen, no send/retry
    python3 tools/n8n_monitor.py --reset      # clear seen state (re-alert all current errors)

Requires in projects/.env:
    N8N_API_KEY=...
    N8N_BASE_URL=https://your-instance.app.n8n.cloud

Requires in projects/personal/.env:
    ANTHROPIC_API_KEY=...

Requires:
    projects/personal/token_personal_ai.pickle
"""

import argparse
import base64
import json
import os
import pickle
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent.parent
SHARED_ENV = BASE_DIR / 'projects' / '.env'
PERSONAL_ENV = BASE_DIR / 'projects' / 'personal' / '.env'
PERSONAL_TOKEN = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
STATE_FILE = BASE_DIR / '.tmp' / 'n8n_monitor_state.json'
SERVICE_CODE_DIR = BASE_DIR / 'services' / 'ryan-labeler'

ALERT_TO = 'allenenriquez.ai@gmail.com'
FROM_EMAIL = 'allenenriquez.ai@gmail.com'
FROM_NAME = 'Enriquez OS'


def load_env():
    for env_file in [SHARED_ENV, PERSONAL_ENV]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()


# --- n8n API ---

def _n8n_headers():
    key = os.environ.get('N8N_API_KEY', '')
    if not key:
        raise ValueError("N8N_API_KEY not set in projects/.env")
    return {'X-N8N-API-KEY': key, 'Accept': 'application/json'}


def _n8n_base():
    base = os.environ.get('N8N_BASE_URL', '').rstrip('/')
    if not base:
        raise ValueError("N8N_BASE_URL not set in projects/.env — add your n8n instance URL")
    return base


def n8n_get(path):
    url = f"{_n8n_base()}/api/v1{path}"
    req = urllib.request.Request(url, headers=_n8n_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def n8n_post(path, data=None):
    body = json.dumps(data or {}).encode()
    headers = {**_n8n_headers(), 'Content-Type': 'application/json'}
    req = urllib.request.Request(
        f"{_n8n_base()}/api/v1{path}",
        data=body,
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'http_error': e.code, 'reason': e.reason}


def fetch_failed_executions():
    data = n8n_get('/executions?status=error&limit=50&includeData=false')
    return data.get('data', [])


def fetch_execution_detail(exec_id):
    return n8n_get(f'/executions/{exec_id}?includeData=true')


def retry_execution(exec_id):
    return n8n_post(f'/executions/{exec_id}/retry')


def build_workflow_name_map():
    try:
        data = n8n_get('/workflows?limit=250')
        return {w['id']: w['name'] for w in data.get('data', [])}
    except Exception:
        return {}


# --- State ---

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'seen_ids': []}


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --- Gmail ---

def send_email(subject, body):
    if not PERSONAL_TOKEN.exists():
        print(f"ERROR: Gmail token missing at {PERSONAL_TOKEN}", file=sys.stderr)
        return False
    with open(PERSONAL_TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(PERSONAL_TOKEN, 'wb') as f:
            pickle.dump(creds, f)
    service = build('gmail', 'v1', credentials=creds)
    msg = MIMEText(body, 'plain')
    msg['to'] = ALERT_TO
    msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg['subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return True


# --- Claude Diagnosis ---

def diagnose_with_claude(workflow_name, error_msg, node_name, exec_id):
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return "(Claude diagnosis unavailable — ANTHROPIC_API_KEY not set)"

    code_context = ""
    if any(kw in workflow_name.lower() for kw in ('ryan', 'label', 'brief', 'inbox')):
        for fname in ['main.py', 'classifier.py', 'labeler.py', 'config.py']:
            fpath = SERVICE_CODE_DIR / fname
            if fpath.exists():
                code_context += f"\n--- {fname} ---\n{fpath.read_text()[:2500]}\n"

    prompt = (
        f"An n8n workflow failed. Diagnose the root cause and provide a specific fix.\n\n"
        f"Workflow: {workflow_name}\n"
        f"Failed node: {node_name}\n"
        f"Error: {error_msg}\n"
        f"Execution ID: {exec_id}\n"
        f"{chr(10) + 'Relevant service code:' + code_context if code_context else ''}\n\n"
        f"Respond in this exact format:\n"
        f"ROOT CAUSE: <one sentence>\n"
        f"FIX: <specific steps or code change>\n"
        f"SEVERITY: low/medium/high"
    )

    payload = json.dumps({
        'model': 'claude-sonnet-4-6',
        'max_tokens': 500,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            return resp['content'][0]['text']
    except Exception as e:
        return f"(Claude diagnosis failed: {e})"


# --- Error extraction ---

def extract_error_info(detail):
    error_msg = "unknown error"
    node_name = "unknown node"
    try:
        result_data = detail.get('data', {}).get('resultData', {})
        last_node = result_data.get('lastNodeExecuted', '')
        if last_node:
            node_name = last_node
        top_error = result_data.get('error', {})
        if top_error:
            # n8n cloud uses 'description' for body (may be HTML), 'message' as fallback
            raw = top_error.get('message') or top_error.get('description') or str(top_error)
            if raw.lstrip().startswith('<'):
                raw = raw.split('\n')[0][:120] + ' [HTML — likely 404/5xx from downstream service]'
            error_msg = raw
        else:
            for node, runs in result_data.get('runData', {}).items():
                for run in (runs or []):
                    err = run.get('error', {})
                    if err:
                        raw = err.get('message') or err.get('description') or str(err)
                        error_msg = raw
                        node_name = node
                        break
    except Exception:
        pass
    return error_msg, node_name


# --- Per-execution handler ---

def process_execution(exec_info, name_map=None, dry_run=False):
    exec_id = str(exec_info.get('id', ''))
    workflow_id = exec_info.get('workflowId', '')
    workflow_name = (name_map or {}).get(workflow_id) or workflow_id or 'unknown workflow'
    started_at = exec_info.get('startedAt', '')

    print(f"  [{exec_id}] {workflow_name} — {started_at}")

    detail = fetch_execution_detail(exec_id)
    error_msg, node_name = extract_error_info(detail)
    print(f"    Error: {error_msg[:120]}")

    retry_status = "skipped (dry-run)"
    retry_outcome = None

    if not dry_run:
        retry_result = retry_execution(exec_id)
        if retry_result.get('http_error'):
            retry_status = f"FAILED (HTTP {retry_result['http_error']} {retry_result.get('reason', '')})"
        else:
            new_exec_id = str(retry_result.get('id', ''))
            retry_status = "TRIGGERED"
            if new_exec_id:
                time.sleep(20)
                try:
                    new_detail = fetch_execution_detail(new_exec_id)
                    retry_outcome = new_detail.get('status', 'unknown')
                    retry_status = f"TRIGGERED → {retry_outcome.upper()}"
                except Exception:
                    retry_status = "TRIGGERED (outcome unknown)"

    diagnosis = ""
    retry_failed = retry_outcome in ('error', 'crashed') or (
        'FAILED' in retry_status and 'http_error' not in retry_status
    )
    if not dry_run and retry_failed:
        print(f"    Retry failed — calling Claude for diagnosis...")
        diagnosis = diagnose_with_claude(workflow_name, error_msg, node_name, exec_id)

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        f"Workflow:    {workflow_name}",
        f"Exec ID:     {exec_id}",
        f"Failed node: {node_name}",
        f"Error:       {error_msg}",
        f"Started:     {started_at}",
        f"Detected:    {ts}",
        f"Auto-retry:  {retry_status}",
    ]
    if diagnosis:
        lines += ["", "─" * 40, "Claude Diagnosis:", diagnosis]

    body = "\n".join(lines)
    subject = f"[n8n ERROR] {workflow_name}"

    if dry_run:
        print(f"    DRY RUN — would send email: {subject}")
        print(f"    ---\n{body}\n    ---")
    else:
        sent = send_email(subject, body)
        print(f"    Email: {'sent ✓' if sent else 'FAILED'}")

    return exec_id


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Monitor n8n for workflow errors")
    parser.add_argument('--dry-run', action='store_true', help='Print actions, no email/retry')
    parser.add_argument('--reset', action='store_true', help='Clear seen state to re-alert all current errors')
    args = parser.parse_args()

    state = load_state()
    first_run = not STATE_FILE.exists() or not state.get('seen_ids')

    if args.reset:
        state = {'seen_ids': []}
        first_run = True
        print("State reset — will re-alert all current failures.")

    seen = set(state.get('seen_ids', []))

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Checking n8n for failed executions...")
    try:
        executions = fetch_failed_executions()
        name_map = build_workflow_name_map()
    except Exception as e:
        print(f"ERROR: Could not reach n8n API — {e}", file=sys.stderr)
        sys.exit(1)

    new_failures = [e for e in executions if str(e.get('id', '')) not in seen]
    print(f"  Total errors on record: {len(executions)} | New since last run: {len(new_failures)}")

    # First run: send one digest instead of N individual emails, then mark all seen
    if first_run and new_failures and not args.dry_run:
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        lines = [f"n8n monitor started. {len(new_failures)} existing failure(s) found — marking as seen.", f"Detected: {ts}", ""]
        for e in new_failures:
            wid = e.get('workflowId', '')
            wname = name_map.get(wid, wid)
            lines.append(f"  [{e.get('id')}] {wname} — {e.get('startedAt', '')}")
        lines += ["", "New failures from this point will trigger individual alerts + auto-retry."]
        send_email("[n8n] Monitor active — existing errors catalogued", "\n".join(lines))
        for e in new_failures:
            seen.add(str(e.get('id', '')))
        print(f"  First run digest sent. {len(new_failures)} errors marked as seen.")
    elif first_run and new_failures and args.dry_run:
        print(f"  DRY RUN first-run: would send digest of {len(new_failures)} existing errors.")
    else:
        for exec_info in new_failures:
            exec_id = process_execution(exec_info, name_map=name_map, dry_run=args.dry_run)
            if not args.dry_run:
                seen.add(exec_id)

    if not args.dry_run:
        state['seen_ids'] = list(seen)
        state['last_run'] = datetime.now(timezone.utc).isoformat()
        save_state(state)

    print("Done.")


if __name__ == '__main__':
    main()
