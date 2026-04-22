"""
Agent tool registry — wraps existing tools/*.py for Claude API tool use.

Each tool has: name, description, input_schema, fn.
The fn receives parsed arguments and returns a JSON-serializable dict.
"""

import json
import sys
import traceback
import urllib.parse
import urllib.request
from pathlib import Path

# Add tools/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_pipedrive_creds, get_base_dir

WORK_DIR = get_base_dir()


# ============================================================
# Tool implementations
# ============================================================

def _crm_pipeline_status(**kwargs):
    """Get full Pipedrive CRM pipeline status."""
    from crm_monitor import run_monitor, load_env
    env = load_env()
    result = run_monitor(
        api_key=env.get('PIPEDRIVE_API_KEY', ''),
        domain=env.get('PIPEDRIVE_COMPANY_DOMAIN', ''),
        dry_run=True,
    )
    # Trim to essential fields
    return {
        'kpis': result.get('kpis', {}),
        'action_items': result.get('action_items', [])[:20],
        'todays_activities': result.get('todays_activities', [])[:15],
        'overdue': result.get('overdue_activities_allen', [])[:10],
        'yesterday_cold_calls': result.get('yesterday_cold_calls', 0),
        'yesterday_total_calls': result.get('yesterday_total_calls', 0),
    }


def _search_deals(query='', **kwargs):
    """Search Pipedrive deals by name."""
    creds = get_pipedrive_creds()
    params = urllib.parse.urlencode({
        'term': query,
        'item_types': 'deal',
        'api_token': creds['api_key'],
    })
    url = f"https://{creds['domain']}/v1/deals/search?{params}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        items = data.get('data', {}).get('items', [])
        return {
            'count': len(items),
            'deals': [
                {
                    'id': d['item']['id'],
                    'title': d['item']['title'],
                    'value': d['item'].get('value', 0),
                    'currency': d['item'].get('currency', 'AUD'),
                    'status': d['item'].get('status', ''),
                    'stage': d['item'].get('stage', {}).get('name', ''),
                    'person': d['item'].get('person', {}).get('name', ''),
                    'org': d['item'].get('organization', {}).get('name', ''),
                }
                for d in items[:15]
            ],
        }
    except Exception as e:
        return {'error': str(e)}


def _get_deal_details(deal_id=None, **kwargs):
    """Get full deal details from Pipedrive."""
    if not deal_id:
        return {'error': 'deal_id is required'}
    creds = get_pipedrive_creds()
    url = f"https://{creds['domain']}/v1/deals/{deal_id}?api_token={creds['api_key']}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        deal = data.get('data', {})
        return {
            'id': deal.get('id'),
            'title': deal.get('title'),
            'value': deal.get('value'),
            'currency': deal.get('currency'),
            'status': deal.get('status'),
            'stage_id': deal.get('stage_id'),
            'pipeline_id': deal.get('pipeline_id'),
            'person_name': deal.get('person_id', {}).get('name', '') if isinstance(deal.get('person_id'), dict) else '',
            'person_email': deal.get('person_id', {}).get('email', [{}])[0].get('value', '') if isinstance(deal.get('person_id'), dict) else '',
            'person_phone': deal.get('person_id', {}).get('phone', [{}])[0].get('value', '') if isinstance(deal.get('person_id'), dict) else '',
            'org_name': deal.get('org_id', {}).get('name', '') if isinstance(deal.get('org_id'), dict) else '',
            'owner': deal.get('owner_name', ''),
            'add_time': deal.get('add_time'),
            'update_time': deal.get('update_time'),
            'last_activity_date': deal.get('last_activity_date'),
            'next_activity_date': deal.get('next_activity_date'),
            'notes_count': deal.get('notes_count', 0),
        }
    except Exception as e:
        return {'error': str(e)}


def _post_note(deal_id=None, content='', **kwargs):
    """Post a note to a Pipedrive deal."""
    if not deal_id or not content:
        return {'error': 'deal_id and content are required'}
    creds = get_pipedrive_creds()
    url = f"https://{creds['domain']}/v1/notes?api_token={creds['api_key']}"
    body = json.dumps({'deal_id': int(deal_id), 'content': content}).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        return {'ok': True, 'note_id': data.get('data', {}).get('id')}
    except Exception as e:
        return {'error': str(e)}


def _send_email(to='', subject='', body='', deal_id=None, **kwargs):
    """Send an email via EPS Gmail."""
    if not to or not subject or not body:
        return {'error': 'to, subject, and body are required'}
    from send_email_gmail import send_email
    try:
        result = send_email(to, subject, body, deal_id=deal_id)
        return {'ok': True, 'result': str(result)}
    except Exception as e:
        return {'error': str(e)}


def _draft_follow_up(deal_id=None, template_key='follow_up_quote', **kwargs):
    """Draft a follow-up email for a Pipedrive deal (does NOT send)."""
    if not deal_id:
        return {'error': 'deal_id is required'}
    from draft_follow_up_email import load_template, fill_template, get_deal_from_pipedrive
    from crm_monitor import load_env

    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY', '')
    domain = env.get('PIPEDRIVE_COMPANY_DOMAIN', '')

    deal = get_deal_from_pipedrive(str(deal_id), api_key, domain)
    if not deal:
        return {'error': f'Deal {deal_id} not found'}

    template = load_template(template_key)
    if not template:
        return {'error': f'Template {template_key} not found'}

    person = deal.get('person_id', {}) or {}
    first_name = (person.get('name') or '').split()[0] if person.get('name') else 'there'
    email = ''
    if isinstance(person.get('email'), list) and person['email']:
        email = person['email'][0].get('value', '')

    fields = {
        'first_name': first_name,
        'deal_title': deal.get('title', ''),
        'company': (deal.get('org_id', {}) or {}).get('name', ''),
    }
    filled = fill_template(template, fields)

    return {
        'draft': filled,
        'to': email,
        'deal_title': deal.get('title', ''),
        'person_name': person.get('name', ''),
        'template_used': template_key,
    }


def _personal_crm_status(**kwargs):
    """Get personal brand CRM summary."""
    from personal_crm import scan_crm, classify_lead, HOT_OUTCOMES
    leads = scan_crm()

    callbacks_due = 0
    warm = 0
    need_email = 0
    by_tab = {}

    for lead in leads:
        tab = lead.get('tab', 'Unknown')
        by_tab[tab] = by_tab.get(tab, 0) + 1
        lead_type, priority = classify_lead(lead)
        if lead.get('call_outcome') in HOT_OUTCOMES:
            warm += 1
        if lead_type == 'callback' and priority in ('HIGH', 'URGENT'):
            callbacks_due += 1
        if lead_type == 'email_needed':
            need_email += 1

    return {
        'total_leads': len(leads),
        'callbacks_due': callbacks_due,
        'warm': warm,
        'need_email': need_email,
        'by_tab': by_tab,
    }


def _run_shell_command(command='', timeout=30, **kwargs):
    """Run a shell command and return output."""
    if not command:
        return {'error': 'command is required'}
    import subprocess
    timeout = min(int(timeout), 60)
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True,
            timeout=timeout, cwd=WORK_DIR,
        )
        return {
            'stdout': result.stdout[:5000],
            'stderr': result.stderr[:2000],
            'returncode': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {'error': f'Command timed out after {timeout}s'}
    except Exception as e:
        return {'error': str(e)}


def _read_file(path='', **kwargs):
    """Read a file from the project directory."""
    if not path:
        return {'error': 'path is required'}
    import os
    full_path = os.path.join(WORK_DIR, path) if not os.path.isabs(path) else path
    try:
        with open(full_path, 'r') as f:
            content = f.read(10000)
        return {'path': full_path, 'content': content}
    except Exception as e:
        return {'error': str(e)}


def _send_personal_email(to='', subject='', body='', **kwargs):
    """Send an email via personal Gmail (allenenriquez.ai@gmail.com)."""
    if not to or not subject or not body:
        return {'error': 'to, subject, and body are required'}
    from send_personal_email import send_email
    try:
        result = send_email(to, subject, body)
        return {'ok': True, 'result': result}
    except Exception as e:
        return {'error': str(e)}


def _read_personal_gmail(max_results=10, query='is:unread', **kwargs):
    """Read emails from personal Gmail (allenenriquez.ai@gmail.com)."""
    import pickle
    from pathlib import Path
    from google.auth.transport.requests import Request as GRequest
    from googleapiclient.discovery import build

    token_path = Path(WORK_DIR) / 'projects' / 'personal' / 'token_personal_ai.pickle'
    if not token_path.exists():
        return {'error': 'Personal Gmail token not found'}

    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(GRequest())

    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(
        userId='me', q=query, maxResults=min(int(max_results), 20)
    ).execute()
    messages = result.get('messages', [])

    emails = []
    for msg in messages:
        detail = service.users().messages().get(
            userId='me', id=msg['id'], format='metadata',
            metadataHeaders=['From', 'Subject', 'Date'],
        ).execute()
        headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
        emails.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'snippet': detail.get('snippet', ''),
        })
    return {'count': len(emails), 'emails': emails}


def _read_email_body(message_id='', **kwargs):
    """Read the full body of a personal Gmail email by message ID."""
    if not message_id:
        return {'error': 'message_id is required'}
    import base64
    import pickle
    from pathlib import Path
    from google.auth.transport.requests import Request as GRequest
    from googleapiclient.discovery import build

    token_path = Path(WORK_DIR) / 'projects' / 'personal' / 'token_personal_ai.pickle'
    if not token_path.exists():
        return {'error': 'Personal Gmail token not found'}

    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(GRequest())

    service = build('gmail', 'v1', credentials=creds)
    detail = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}

    # Extract body text
    body = ''
    payload = detail.get('payload', {})
    if payload.get('body', {}).get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    elif payload.get('parts'):
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                break

    return {
        'from': headers.get('From', ''),
        'to': headers.get('To', ''),
        'subject': headers.get('Subject', ''),
        'date': headers.get('Date', ''),
        'body': body[:5000],
    }


def _checklist_status(date=None, **kwargs):
    """Get today's habit checklist completion."""
    from datetime import datetime
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    from app import get_sheet_id, _svc, _load_config

    config = _load_config()
    total = sum(len(items) for items in config.values())

    sheet_id = get_sheet_id()
    result = _svc().spreadsheets().values().get(
        spreadsheetId=sheet_id, range="'Checklist Log'"
    ).execute()
    rows = result.get('values', [])

    completions = {}
    for row in rows[1:]:
        if len(row) >= 3 and row[0] == date:
            completions[row[1]] = row[2]

    done = 0
    items_status = []
    for cat, items in config.items():
        for item in items:
            val = completions.get(item['name'], '')
            is_done = False
            if item['type'] == 'check':
                is_done = val.upper() in ('TRUE', '1', 'YES') if val else False
            elif item['type'] == 'count':
                is_done = bool(val and val != '0')
            if is_done:
                done += 1
            items_status.append({
                'name': item['name'],
                'category': cat,
                'type': item['type'],
                'done': is_done,
                'value': val,
            })

    return {
        'date': date,
        'done': done,
        'total': total,
        'pct': round(done / total * 100) if total else 0,
        'items': items_status,
    }


# ============================================================
# Tool registry
# ============================================================

TOOLS = [
    {
        'name': 'crm_pipeline_status',
        'description': 'Get the current Pipedrive CRM pipeline status including KPIs (pipeline value, deals won, calls), today\'s activities, overdue items, and action items needing follow-up. Use this to answer questions about the sales pipeline, deals, or daily workload.',
        'input_schema': {
            'type': 'object',
            'properties': {},
            'required': [],
        },
        'fn': _crm_pipeline_status,
    },
    {
        'name': 'search_deals',
        'description': 'Search for Pipedrive deals by name, person, or organization. Returns matching deals with their status, stage, value, and contact info.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'Search term (deal name, person name, or org name)'},
            },
            'required': ['query'],
        },
        'fn': _search_deals,
    },
    {
        'name': 'get_deal_details',
        'description': 'Get full details for a specific Pipedrive deal by ID, including contact info, dates, stage, and value.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'deal_id': {'type': 'integer', 'description': 'Pipedrive deal ID'},
            },
            'required': ['deal_id'],
        },
        'fn': _get_deal_details,
    },
    {
        'name': 'post_note',
        'description': 'Post a note to a Pipedrive deal. Use this to record information, call summaries, or action items on a deal.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'deal_id': {'type': 'integer', 'description': 'Pipedrive deal ID'},
                'content': {'type': 'string', 'description': 'Note content (supports HTML)'},
            },
            'required': ['deal_id', 'content'],
        },
        'fn': _post_note,
    },
    {
        'name': 'send_email',
        'description': 'Send an email via the EPS Gmail account (sales@epsolution.com.au). IMPORTANT: Always show the draft to the user and get explicit confirmation before sending.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'to': {'type': 'string', 'description': 'Recipient email address'},
                'subject': {'type': 'string', 'description': 'Email subject line'},
                'body': {'type': 'string', 'description': 'Email body text'},
                'deal_id': {'type': 'integer', 'description': 'Optional Pipedrive deal ID to link the email to'},
            },
            'required': ['to', 'subject', 'body'],
        },
        'fn': _send_email,
    },
    {
        'name': 'draft_follow_up',
        'description': 'Draft a follow-up email for a Pipedrive deal using templates. Returns the draft text — does NOT send. Available template keys: follow_up_quote, follow_up_general, follow_up_check_in.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'deal_id': {'type': 'integer', 'description': 'Pipedrive deal ID'},
                'template_key': {
                    'type': 'string',
                    'description': 'Email template to use',
                    'default': 'follow_up_quote',
                },
            },
            'required': ['deal_id'],
        },
        'fn': _draft_follow_up,
    },
    {
        'name': 'personal_crm_status',
        'description': 'Get the personal brand CRM summary — total leads, callbacks due, warm leads, leads needing emails, broken down by status tab.',
        'input_schema': {
            'type': 'object',
            'properties': {},
            'required': [],
        },
        'fn': _personal_crm_status,
    },
    {
        'name': 'checklist_status',
        'description': 'Get today\'s habit checklist completion status — which items are done, progress percentage.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'date': {'type': 'string', 'description': 'Date in YYYY-MM-DD format. Defaults to today.'},
            },
            'required': [],
        },
        'fn': _checklist_status,
    },
    {
        'name': 'send_personal_email',
        'description': 'Send an email from Allen\'s personal Gmail (allenenriquez.ai@gmail.com). For personal brand outreach, follow-ups, networking. IMPORTANT: Show the draft to the user and get confirmation before sending.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'to': {'type': 'string', 'description': 'Recipient email address'},
                'subject': {'type': 'string', 'description': 'Email subject line'},
                'body': {'type': 'string', 'description': 'Email body (plain text)'},
            },
            'required': ['to', 'subject', 'body'],
        },
        'fn': _send_personal_email,
    },
    {
        'name': 'read_personal_gmail',
        'description': 'Read emails from Allen\'s personal Gmail (allenenriquez.ai@gmail.com). Default: unread emails. Use the query parameter for custom Gmail search (e.g. "from:someone@email.com", "subject:invoice", "is:starred", "newer_than:2d").',
        'input_schema': {
            'type': 'object',
            'properties': {
                'max_results': {'type': 'integer', 'description': 'Max emails to return (1-20)', 'default': 10},
                'query': {'type': 'string', 'description': 'Gmail search query', 'default': 'is:unread'},
            },
            'required': [],
        },
        'fn': _read_personal_gmail,
    },
    {
        'name': 'read_email_body',
        'description': 'Read the full body/content of a specific personal Gmail email by its message ID (from read_personal_gmail results).',
        'input_schema': {
            'type': 'object',
            'properties': {
                'message_id': {'type': 'string', 'description': 'Gmail message ID'},
            },
            'required': ['message_id'],
        },
        'fn': _read_email_body,
    },
    {
        'name': 'run_shell_command',
        'description': 'Run a shell command on Allen\'s machine. Use this for anything not covered by other tools — reading emails, checking calendar, running Python scripts from tools/, listing files, git status, etc. Working directory is the project root. Useful examples: "python3 tools/morning_briefing.py --dry-run", "cat projects/personal/.tmp/pending_inquiries.json", "ls tools/". Max 60s timeout.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'command': {'type': 'string', 'description': 'Shell command to execute'},
                'timeout': {'type': 'integer', 'description': 'Timeout in seconds (max 60)', 'default': 30},
            },
            'required': ['command'],
        },
        'fn': _run_shell_command,
    },
    {
        'name': 'read_file',
        'description': 'Read a file from the project. Paths are relative to the project root (Allen Enriquez/). Use for reading configs, notes, workflows, CLAUDE.md files, or any project file.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string', 'description': 'File path (relative to project root or absolute)'},
            },
            'required': ['path'],
        },
        'fn': _read_file,
    },
]

TOOL_MAP = {t['name']: t for t in TOOLS}


def get_tool_schemas():
    """Return tool definitions for the Anthropic API (without fn key)."""
    return [
        {
            'name': t['name'],
            'description': t['description'],
            'input_schema': t['input_schema'],
        }
        for t in TOOLS
    ]


def execute_tool(name, arguments):
    """Execute a tool by name, return result dict."""
    tool = TOOL_MAP.get(name)
    if not tool:
        return {'error': f'Unknown tool: {name}'}
    try:
        return tool['fn'](**arguments)
    except Exception as e:
        traceback.print_exc()
        return {'error': str(e)}
