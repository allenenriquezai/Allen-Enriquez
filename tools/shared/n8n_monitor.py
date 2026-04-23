"""
n8n Workflow Error Monitor — Self-Healing Edition

Every 10 min (via launchd):
  1. Railway health check — if down, auto-redeploy + backfill missed emails
  2. n8n execution check — auto-retry failures, Claude diagnosis on repeat fails
  3. Audit sync — pull /audit/export from Railway, persist locally for self-improve

Usage:
    python3 tools/shared/n8n_monitor.py              # normal run
    python3 tools/shared/n8n_monitor.py --dry-run    # print only, no changes
    python3 tools/shared/n8n_monitor.py --reset      # clear seen state

Requires in projects/.env:
    N8N_API_KEY=...
    N8N_BASE_URL=https://your-instance.app.n8n.cloud
    ANTHROPIC_API_KEY=...
"""

import argparse
import base64
import json
import os
import pickle
import subprocess
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
LOCAL_AUDIT_FILE = BASE_DIR / '.tmp' / 'ryan_audit_local.jsonl'
SERVICE_CODE_DIR = BASE_DIR / 'services' / 'ryan'

RAILWAY_URL = 'https://ryan-labeler-production.up.railway.app'
RAILWAY_PROJECT = 'enriquez-os'
RAILWAY_SERVICE = 'ryan-labeler'
RAILWAY_ENV = 'production'
RAILWAY_CLI = '/opt/homebrew/bin/railway'
DASHBOARD_TOKEN = 'ryan-sc'

ALERT_TO = 'allenenriquez.ai@gmail.com'
FROM_EMAIL = 'allenenriquez.ai@gmail.com'
FROM_NAME = 'Enriquez OS'

# Error fingerprint → known fix (skips slow Claude call)
KNOWN_ISSUES = {
    'Application not found': (
        'Railway service deleted or not deployed',
        'Triggered auto-redeploy — Railway service is back up',
    ),
    'fetch_message failed': (
        'Gmail message deleted or moved before processing',
        'Message no longer accessible — skip, nothing to fix',
    ),
    'resource you are requesting could not be found': (
        'Railway returned 404 — Gmail message deleted or moved before processing',
        'Message no longer accessible — skip, nothing to fix',
    ),
    'Token has been expired': (
        'Gmail OAuth token expired',
        'Re-authenticate Ryan Gmail account manually',
    ),
    'ECONNREFUSED': (
        'Railway container not accepting connections',
        'Service is starting up or crashed — will retry',
    ),
}


# ---------------------------------------------------------------------------
# Env
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# n8n API
# ---------------------------------------------------------------------------

def _n8n_headers():
    key = os.environ.get('N8N_API_KEY', '')
    if not key:
        raise ValueError('N8N_API_KEY not set')
    return {'X-N8N-API-KEY': key, 'Accept': 'application/json'}


def _n8n_base():
    base = os.environ.get('N8N_BASE_URL', '').rstrip('/')
    if not base:
        raise ValueError('N8N_BASE_URL not set')
    return base


def n8n_get(path):
    req = urllib.request.Request(f'{_n8n_base()}/api/v1{path}', headers=_n8n_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def n8n_post(path, data=None):
    body = json.dumps(data or {}).encode()
    headers = {**_n8n_headers(), 'Content-Type': 'application/json'}
    req = urllib.request.Request(
        f'{_n8n_base()}/api/v1{path}', data=body, headers=headers, method='POST',
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


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        'seen_ids': [],
        'railway_fail_count': 0,
        'railway_last_fail_at': None,
        'railway_last_redeploy_at': None,
        'audit_last_sync_at': None,
        'run_count': 0,
    }


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------

def send_email(subject, body):
    if not PERSONAL_TOKEN.exists():
        print(f'ERROR: Gmail token missing at {PERSONAL_TOKEN}', file=sys.stderr)
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
    msg['from'] = f'{FROM_NAME} <{FROM_EMAIL}>'
    msg['subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return True


# ---------------------------------------------------------------------------
# Railway — health + auto-redeploy
# ---------------------------------------------------------------------------

def check_railway_health():
    try:
        req = urllib.request.Request(
            f'{RAILWAY_URL}/health', headers={'User-Agent': 'n8n-monitor/2.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return data.get('ok') is True
    except Exception:
        return False


def wait_for_railway_up(max_wait=120):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if check_railway_health():
            return True
        time.sleep(10)
    return False


def redeploy_railway():
    """Re-link + set env vars + deploy. Returns (success, log_str)."""
    steps = []

    def run(cmd, **kw):
        r = subprocess.run(
            cmd, cwd=str(SERVICE_CODE_DIR), capture_output=True, text=True,
            timeout=kw.pop('timeout', 60), **kw
        )
        return r.returncode == 0, r.stdout.strip() or r.stderr.strip()

    # Link
    ok, out = run([RAILWAY_CLI, 'link', '-p', RAILWAY_PROJECT, '-s', RAILWAY_SERVICE, '-e', RAILWAY_ENV])
    steps.append(f'link: {"ok" if ok else out}')
    if not ok:
        return False, '\n'.join(steps)

    # Env vars
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if api_key:
        run([RAILWAY_CLI, 'variable', 'set', f'ANTHROPIC_API_KEY={api_key}'], timeout=20)
        steps.append('anthropic key: set')

    for var, path in [
        ('RYAN_GMAIL_TOKEN', BASE_DIR / 'projects/personal/clients/ryan/token_ryan.pickle'),
        ('ALLEN_AI_GMAIL_TOKEN', BASE_DIR / 'projects/personal/token_personal_ai.pickle'),
    ]:
        if Path(path).exists():
            b64 = base64.b64encode(Path(path).read_bytes()).decode()
            run([RAILWAY_CLI, 'variable', 'set', f'{var}={b64}'], timeout=20)
            steps.append(f'{var}: set')

    # Deploy
    ok, out = run([RAILWAY_CLI, 'up', '--detach'], timeout=120)
    steps.append(f'deploy: {"triggered" if ok else out}')

    return ok, '\n'.join(steps)


def backfill_missed_emails():
    """Re-POST all unprocessed message_ids from failed n8n executions."""
    executions = fetch_failed_executions()
    seen_ids = set()
    messages = []
    for ex in executions:
        try:
            detail = fetch_execution_detail(str(ex['id']))
            trigger_runs = detail['data']['resultData']['runData']['Gmail Trigger']
            for item in trigger_runs[0]['data']['main'][0]:
                mid = item['json'].get('id')
                tid = item['json'].get('threadId')
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    messages.append({'message_id': mid, 'thread_id': tid})
        except (KeyError, IndexError, TypeError):
            pass

    ok_count = fail_count = 0
    for m in messages:
        try:
            body = json.dumps(m).encode()
            req = urllib.request.Request(
                f'{RAILWAY_URL}/label', data=body,
                headers={'Content-Type': 'application/json'}, method='POST',
            )
            with urllib.request.urlopen(req, timeout=30):
                ok_count += 1
        except Exception:
            fail_count += 1
        time.sleep(0.3)

    return ok_count, fail_count, len(messages)


def handle_railway_down(state, dry_run=False):
    """Orchestrate: redeploy → wait → backfill → alert."""
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # Avoid redeploy loops — wait at least 15 min between attempts
    last = state.get('railway_last_redeploy_at')
    if last:
        mins_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() / 60
        if mins_since < 15:
            print(f'  Railway down but last redeploy was {mins_since:.0f} min ago — waiting')
            return

    print('  Railway down — starting auto-redeploy...')
    if dry_run:
        print('  DRY RUN — would redeploy Railway and backfill emails')
        return

    deploy_ok, deploy_log = redeploy_railway()
    state['railway_last_redeploy_at'] = datetime.now(timezone.utc).isoformat()

    if not deploy_ok:
        send_email(
            '[ryan-labeler] Railway down — auto-redeploy FAILED',
            f'Railway health check failed and auto-redeploy did not complete.\n\nDetected: {ts}\n\nDeploy log:\n{deploy_log}\n\nManual fix: cd services/ryan && railway link && railway up',
        )
        return

    print('  Deploy triggered — waiting for service to come up...')
    up = wait_for_railway_up(max_wait=150)

    if not up:
        send_email(
            '[ryan-labeler] Railway redeployed but not responding',
            f'Auto-redeploy triggered but /health still failing after 150s.\n\nDetected: {ts}\n\nDeploy log:\n{deploy_log}\n\nCheck Railway dashboard.',
        )
        return

    print('  Service up — backfilling missed emails...')
    ok_count, fail_count, total = backfill_missed_emails()
    state['railway_fail_count'] = 0

    send_email(
        '[ryan-labeler] Auto-fixed: Railway redeployed',
        (
            f'Railway was down. Auto-redeploy succeeded.\n\n'
            f'Detected: {ts}\n\n'
            f'Backfill: {ok_count}/{total} emails labeled ({fail_count} already deleted)\n\n'
            f'Deploy log:\n{deploy_log}\n\n'
            f'No action needed.'
        ),
    )
    print(f'  Recovered. Backfill: {ok_count}/{total} labeled.')


# ---------------------------------------------------------------------------
# Audit sync (local persistence for self-improve)
# ---------------------------------------------------------------------------

def sync_audit_from_railway():
    """Pull /audit/export from Railway, append new entries to local JSONL."""
    try:
        req = urllib.request.Request(
            f'{RAILWAY_URL}/audit/export?token={DASHBOARD_TOKEN}',
            headers={'User-Agent': 'n8n-monitor/2.0'},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            entries = json.loads(r.read())
    except Exception as e:
        print(f'  Audit sync skipped: {e}')
        return 0

    existing_ids = set()
    if LOCAL_AUDIT_FILE.exists():
        for line in LOCAL_AUDIT_FILE.read_text().splitlines():
            try:
                existing_ids.add(json.loads(line).get('message_id'))
            except Exception:
                pass

    LOCAL_AUDIT_FILE.parent.mkdir(exist_ok=True)
    new_count = 0
    with open(LOCAL_AUDIT_FILE, 'a') as f:
        for entry in entries:
            if entry.get('message_id') not in existing_ids:
                f.write(json.dumps(entry) + '\n')
                new_count += 1

    return new_count


# ---------------------------------------------------------------------------
# Claude diagnosis
# ---------------------------------------------------------------------------

def known_issue_fix(error_msg):
    for fingerprint, (cause, fix) in KNOWN_ISSUES.items():
        if fingerprint.lower() in error_msg.lower():
            return cause, fix
    return None, None


def diagnose_with_claude(workflow_name, error_msg, node_name, exec_id):
    cause, fix = known_issue_fix(error_msg)
    if cause:
        return f'ROOT CAUSE: {cause}\nFIX: {fix}\nSEVERITY: medium'

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return '(Claude diagnosis unavailable — ANTHROPIC_API_KEY not set)'

    code_context = ''
    if any(kw in workflow_name.lower() for kw in ('ryan', 'label', 'brief', 'inbox')):
        for fname in ['main.py', 'classifier.py', 'labeler.py', 'config.py']:
            fpath = SERVICE_CODE_DIR / fname
            if fpath.exists():
                code_context += f'\n--- {fname} ---\n{fpath.read_text()[:2500]}\n'

    prompt = (
        f'An n8n workflow failed. Diagnose the root cause and provide a specific fix.\n\n'
        f'Workflow: {workflow_name}\nFailed node: {node_name}\nError: {error_msg}\nExec ID: {exec_id}\n'
        f'{chr(10) + "Relevant service code:" + code_context if code_context else ""}\n\n'
        f'Respond in this exact format:\n'
        f'ROOT CAUSE: <one sentence>\nFIX: <specific steps or code change>\nSEVERITY: low/medium/high'
    )

    payload = json.dumps({
        'model': 'claude-sonnet-4-6',
        'max_tokens': 500,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=payload,
        headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())['content'][0]['text']
    except Exception as e:
        return f'(Claude diagnosis failed: {e})'


# ---------------------------------------------------------------------------
# Error extraction
# ---------------------------------------------------------------------------

def extract_error_info(detail):
    error_msg = 'unknown error'
    node_name = 'unknown node'
    try:
        result_data = detail.get('data', {}).get('resultData', {})
        last_node = result_data.get('lastNodeExecuted', '')
        if last_node:
            node_name = last_node
        top_error = result_data.get('error', {})
        if top_error:
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


# ---------------------------------------------------------------------------
# Per-execution handler
# ---------------------------------------------------------------------------

def process_execution(exec_info, name_map=None, dry_run=False):
    exec_id = str(exec_info.get('id', ''))
    workflow_id = exec_info.get('workflowId', '')
    workflow_name = (name_map or {}).get(workflow_id) or workflow_id or 'unknown workflow'
    started_at = exec_info.get('startedAt', '')

    print(f'  [{exec_id}] {workflow_name} — {started_at}')

    detail = fetch_execution_detail(exec_id)
    error_msg, node_name = extract_error_info(detail)
    print(f'    Error: {error_msg[:120]}')

    retry_status = 'skipped (dry-run)'
    retry_outcome = None

    if not dry_run:
        retry_result = retry_execution(exec_id)
        if retry_result.get('http_error'):
            retry_status = f'FAILED (HTTP {retry_result["http_error"]} {retry_result.get("reason", "")})'
        else:
            new_exec_id = str(retry_result.get('id', ''))
            retry_status = 'TRIGGERED'
            if new_exec_id:
                time.sleep(20)
                try:
                    new_detail = fetch_execution_detail(new_exec_id)
                    retry_outcome = new_detail.get('status', 'unknown')
                    retry_status = f'TRIGGERED → {retry_outcome.upper()}'
                except Exception:
                    retry_status = 'TRIGGERED (outcome unknown)'

    diagnosis = ''
    retry_failed = retry_outcome in ('error', 'crashed') or 'FAILED' in retry_status
    if not dry_run and retry_failed:
        print('    Retry failed — diagnosing...')
        diagnosis = diagnose_with_claude(workflow_name, error_msg, node_name, exec_id)

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        f'Workflow:    {workflow_name}',
        f'Exec ID:     {exec_id}',
        f'Failed node: {node_name}',
        f'Error:       {error_msg}',
        f'Started:     {started_at}',
        f'Detected:    {ts}',
        f'Auto-retry:  {retry_status}',
    ]
    if diagnosis:
        lines += ['', '─' * 40, 'Diagnosis:', diagnosis]

    body = '\n'.join(lines)
    subject = f'[n8n ERROR] {workflow_name}'

    if dry_run:
        print(f'    DRY RUN — would send: {subject}')
        print(f'    ---\n{body}\n    ---')
    else:
        sent = send_email(subject, body)
        print(f'    Email: {"sent ✓" if sent else "FAILED"}')

    return exec_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--reset', action='store_true', help='Clear seen state')
    args = parser.parse_args()

    state = load_state()
    first_run = not STATE_FILE.exists() or not state.get('seen_ids')

    if args.reset:
        state = {**load_state(), 'seen_ids': [], 'railway_fail_count': 0}
        first_run = True
        print('State reset.')

    seen = set(state.get('seen_ids', []))
    state['run_count'] = state.get('run_count', 0) + 1

    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'[{ts}] n8n monitor (run #{state["run_count"]})')

    # ------------------------------------------------------------------
    # 1. Railway health check
    # ------------------------------------------------------------------
    print('Checking Railway health...')
    rail_healthy = check_railway_health()

    if not rail_healthy:
        state['railway_fail_count'] = state.get('railway_fail_count', 0) + 1
        state['railway_last_fail_at'] = datetime.now(timezone.utc).isoformat()
        print(f'  Railway DOWN (consecutive failures: {state["railway_fail_count"]})')

        if state['railway_fail_count'] >= 2:
            handle_railway_down(state, dry_run=args.dry_run)
        else:
            print('  Waiting for next run to confirm before redeploying.')
    else:
        if state.get('railway_fail_count', 0) > 0:
            print(f'  Railway recovered after {state["railway_fail_count"]} failures.')
        state['railway_fail_count'] = 0
        print('  Railway OK')

    # ------------------------------------------------------------------
    # 2. n8n execution check
    # ------------------------------------------------------------------
    print('Checking n8n failed executions...')
    try:
        executions = fetch_failed_executions()
        name_map = build_workflow_name_map()
    except Exception as e:
        print(f'ERROR: Cannot reach n8n API — {e}', file=sys.stderr)
        save_state({**state, 'seen_ids': list(seen)})
        sys.exit(1)

    new_failures = [e for e in executions if str(e.get('id', '')) not in seen]
    print(f'  Total errors: {len(executions)} | New: {len(new_failures)}')

    if first_run and new_failures and not args.dry_run:
        run_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        lines = [
            f'n8n monitor started. {len(new_failures)} existing failure(s) — marking as seen.',
            f'Detected: {run_ts}', '',
        ]
        for e in new_failures:
            wname = name_map.get(e.get('workflowId', ''), e.get('workflowId', ''))
            lines.append(f'  [{e.get("id")}] {wname} — {e.get("startedAt", "")}')
        lines += ['', 'New failures from this point trigger individual alerts + auto-retry.']
        send_email('[n8n] Monitor active — existing errors catalogued', '\n'.join(lines))
        for e in new_failures:
            seen.add(str(e.get('id', '')))
        print(f'  First-run digest sent. {len(new_failures)} errors marked seen.')
    elif first_run and new_failures and args.dry_run:
        print(f'  DRY RUN first-run: would send digest of {len(new_failures)} errors.')
    else:
        for exec_info in new_failures:
            exec_id = process_execution(exec_info, name_map=name_map, dry_run=args.dry_run)
            if not args.dry_run:
                seen.add(exec_id)

    # ------------------------------------------------------------------
    # 3. Audit sync (every 6 runs ≈ 1 hour)
    # ------------------------------------------------------------------
    if rail_healthy and state['run_count'] % 6 == 0:
        print('Syncing audit from Railway...')
        new_entries = sync_audit_from_railway()
        print(f'  Audit sync: +{new_entries} entries')
        state['audit_last_sync_at'] = datetime.now(timezone.utc).isoformat()

    if not args.dry_run:
        state['seen_ids'] = list(seen)
        state['last_run'] = datetime.now(timezone.utc).isoformat()
        save_state(state)

    print('Done.')


if __name__ == '__main__':
    main()
