"""
Morning Briefing v2 — AI Executive Assistant.

Two-bucket triage: Allen's Plate (only he can do) vs AI Can Handle (EA drafts/actions).
Sends via personal Gmail to keep briefings off the EPS sent folder.

Usage:
    python3 tools/morning_briefing.py                     # generate data files only (no email)
    python3 tools/morning_briefing.py --send               # generate + send email
    python3 tools/morning_briefing.py --dry-run            # preview only, no files written
    python3 tools/morning_briefing.py --to allen@email.com # override recipient (with --send)

Requires:
    projects/eps/.env: PIPEDRIVE_API_KEY, PIPEDRIVE_COMPANY_DOMAIN
    projects/personal/token_personal_ai.pickle: Gmail OAuth token with send scope
"""

import argparse
import base64
import json
import os
import pickle
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'
TMP_DIR = BASE_DIR / '.tmp'
EPS_TOKEN = BASE_DIR / 'projects' / 'eps' / 'token_eps.pickle'
PERSONAL_TOKEN = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'

BRIEFING_FROM_EMAIL = 'allenenriquez@gmail.com'
BRIEFING_FROM_NAME = 'Enriquez OS'
BRIEFING_TO_EMAIL_DEFAULT = 'allenenriquez.ai@gmail.com'

# Import sibling tools
sys.path.insert(0, str(Path(__file__).parent))
from crm_monitor import (run_monitor, load_env, EXEC_ACTIVITY_TYPES,
                         OPERATIONAL_ACTIVITY_TYPES, ACTIVITY_TYPE_NAMES,
                         DISCOVERY_TYPES, CLEAN_FOLLOWUP_TYPES,
                         PAINT_FOLLOWUP_TYPES, VIP_TYPES)


# --- Email filtering ---

PROMO_SENDERS = [
    'noreply@', 'no-reply@', 'newsletter@', 'marketing@', 'promo@',
    'updates@', 'notifications@', 'info@', 'hello@', 'news@',
    'mailchimp.com', 'sendgrid.net', 'hubspot', 'mailgun',
    'constantcontact', 'campaignmonitor', 'sendinblue', 'klaviyo',
    'intercom', 'drip.com', 'convertkit', 'substack',
    'linkedin.com', 'facebookmail', 'accounts.google',
    'notion.so', 'slack.com', 'atlassian', 'trello',
    'canva.com', 'dropbox.com', 'zoom.us',
    'justcall', 'justcall.io',
]

PROMO_SUBJECTS = [
    'unsubscribe', 'weekly digest', 'newsletter', 'new features',
    'product update', 'your weekly', 'your monthly', 'special offer',
    'limited time', 'don\'t miss', 'check out', 'introducing',
    'what\'s new', 'top picks', 'sale ends', 'off your',
]

IMPORTANT_KEYWORDS = [
    'quote', 'quotation', 'estimate', 'proposal', 'tender',
    'accept', 'approved', 'confirmed', 'booking', 'booked',
    'invoice', 'payment', 'deposit', 'paid',
    'urgent', 'asap', 'immediately',
    'site visit', 'inspection', 'measure',
    'complaint', 'issue', 'problem', 'concern',
    'follow up', 'follow-up', 'followup',
    'eps', 'painting', 'cleaning',
]

# Keywords that signal a customer inquiry the AI can draft a response for
INQUIRY_KEYWORDS = [
    'quote', 'estimate', 'pricing', 'price', 'cost',
    'interested', 'enquiry', 'inquiry', 'looking for',
    'need a', 'want a', 'how much', 'available',
]


def is_promotional(email):
    from_addr = email.get('from', '').lower()
    subject = email.get('subject', '').lower()
    snippet = email.get('snippet', '').lower()

    if email.get('important') or email.get('starred'):
        return False

    combined = subject + ' ' + snippet
    for kw in IMPORTANT_KEYWORDS:
        if kw in combined:
            return False

    for promo in PROMO_SENDERS:
        if promo in from_addr:
            return True

    for promo in PROMO_SUBJECTS:
        if promo in subject:
            return True

    label_ids = email.get('label_ids', [])
    if 'CATEGORY_PROMOTIONS' in label_ids or 'CATEGORY_SOCIAL' in label_ids:
        return True

    return False


def is_inquiry(email):
    """Return True if email looks like a customer inquiry the AI can help draft a response for."""
    combined = (email.get('subject', '') + ' ' + email.get('snippet', '')).lower()
    return any(kw in combined for kw in INQUIRY_KEYWORDS)


# --- Gmail & Calendar fetchers ---

def load_token(token_path):
    if not token_path.exists():
        return None
    with open(token_path, 'rb') as f:
        return pickle.load(f)


def fetch_gmail_unread(token_path, label, max_results=30):
    creds = load_token(token_path)
    if not creds:
        print(f"  [{label}] No token — skipping")
        return []

    try:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(
            userId='me', q='is:unread', maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            detail = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = {h['name']: h['value']
                       for h in detail.get('payload', {}).get('headers', [])}
            label_ids = detail.get('labelIds', [])

            emails.append({
                'id': msg['id'],
                'subject': headers.get('Subject', '(no subject)'),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'snippet': detail.get('snippet', ''),
                'important': 'IMPORTANT' in label_ids,
                'starred': 'STARRED' in label_ids,
                'label_ids': label_ids,
            })

        total = len(emails)
        emails = [e for e in emails if not is_promotional(e)]
        filtered = total - len(emails)

        emails.sort(key=lambda e: (not e['important'], not e['starred']))
        print(f"  [{label}] {len(emails)} important emails ({filtered} promotional filtered)")
        return emails

    except Exception as e:
        print(f"  [{label}] Gmail failed: {e}")
        return []


def fetch_calendar_today(token_path, label):
    creds = load_token(token_path)
    if not creds:
        print(f"  [{label}] No token — skipping")
        return []

    try:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('calendar', 'v3', credentials=creds)

        # Today in AEST (UTC+10)
        try:
            import pytz
            aest = pytz.timezone('Australia/Brisbane')
            now_aest = datetime.now(aest)
        except ImportError:
            now_aest = datetime.now(timezone(timedelta(hours=10)))

        start_of_day = now_aest.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            maxResults=20, singleEvents=True, orderBy='startTime'
        ).execute()

        events = []
        for e in events_result.get('items', []):
            start = e['start'].get('dateTime', e['start'].get('date', ''))
            attendees = [a.get('email', '') for a in e.get('attendees', [])]
            events.append({
                'title': e.get('summary', '(no title)'),
                'start': start,
                'location': e.get('location', ''),
                'attendees': attendees[:5],
            })

        print(f"  [{label}] {len(events)} events today")
        return events

    except Exception as e:
        print(f"  [{label}] Calendar failed: {e}")
        return []


# --- Triage classification ---

def classify_for_triage(crm_data, gmail_eps):
    """Split all data into two buckets: Allen's Plate vs AI Can Handle."""
    action_items = crm_data.get('action_items', [])

    # Sort action items: URGENT > HIGH > MEDIUM > LOW
    priority_order = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    action_items.sort(key=lambda x: priority_order.get(x['priority'], 4))

    # AI-handleable: follow-ups in QUOTE SENT / LATE FOLLOW UP where action is email-based
    ai_chase_stages = {'QUOTE SENT', 'LATE FOLLOW UP', 'NEGOTIATION / FOLLOW UP'}
    ai_chase_actions = {'email', 'call_then_email'}

    ai_chase = []
    allen_crm = []
    for item in action_items:
        if (item['type'] == 'follow_up'
                and item.get('stage') in ai_chase_stages
                and item.get('recommended_action') in ai_chase_actions):
            ai_chase.append(item)
        else:
            allen_crm.append(item)

    # Inquiry emails from EPS inbox
    ai_inquiry_emails = [e for e in gmail_eps if is_inquiry(e)]
    other_eps_emails = [e for e in gmail_eps if not is_inquiry(e)]

    # Number all AI-actionable items for the action loop
    action_number = 0
    action_manifest = []

    for email in ai_inquiry_emails:
        action_number += 1
        email['_action_number'] = action_number
        action_manifest.append({
            'number': action_number,
            'type': 'inquiry',
            'gmail_message_id': email['id'],
            'from': email['from'],
            'subject': email['subject'],
            'snippet': email['snippet'],
        })

    for item in ai_chase:
        action_number += 1
        item['_action_number'] = action_number
        action_manifest.append({
            'number': action_number,
            'type': 'chase',
            'deal_id': item.get('deal_id'),
            'deal_title': item.get('deal_title'),
            'person_name': item.get('person_name'),
            'stage': item.get('stage'),
            'pipeline': item.get('pipeline'),
            'days_since_activity': item.get('days_since_activity'),
        })

    # Stale deals — AI suggests next action
    stale_deals = [i for i in allen_crm if i['type'] == 'stale_deal']
    non_stale_crm = [i for i in allen_crm if i['type'] != 'stale_deal']

    for item in stale_deals:
        action_number += 1
        item['_action_number'] = action_number
        action_manifest.append({
            'number': action_number,
            'type': 'stale',
            'deal_id': item.get('deal_id'),
            'deal_title': item.get('deal_title'),
            'pipeline': item.get('pipeline'),
            'days_since_activity': item.get('days_since_activity'),
            'suggested_action': 'send_checkin',
        })

    # Group today's activities + overdue by tier
    todays = crm_data.get('todays_activities', [])
    overdue_allen = crm_data.get('overdue_activities_allen', [])
    all_due = todays + overdue_allen
    # Priority order: Discoveries > Clean Follow-Ups > Paint Follow-Ups > VIP
    _tier1_order = {t: 0 for t in DISCOVERY_TYPES}
    _tier1_order.update({t: 1 for t in CLEAN_FOLLOWUP_TYPES})
    _tier1_order.update({t: 2 for t in PAINT_FOLLOWUP_TYPES})
    _tier1_order.update({t: 3 for t in VIP_TYPES})
    tier1 = sorted([a for a in all_due if a.get('type') in EXEC_ACTIVITY_TYPES],
                   key=lambda a: (_tier1_order.get(a.get('type', ''), 9), a.get('due_time') or 'zz'))
    tier2 = [a for a in all_due if a.get('type') in OPERATIONAL_ACTIVITY_TYPES]
    tier_other = [a for a in all_due
                  if a.get('type') not in EXEC_ACTIVITY_TYPES
                  and a.get('type') not in OPERATIONAL_ACTIVITY_TYPES]

    return {
        'eps': {
            'allens_plate': {
                'crm_items': non_stale_crm,
            },
            'ai_can_handle': {
                'inquiry_emails': ai_inquiry_emails,
                'chase_followups': ai_chase,
                'stale_deals': stale_deals,
            },
            'other_emails': other_eps_emails,
        },
        'todays_activities': {'tier1': tier1, 'tier2': tier2, 'other': tier_other},
        'quick_stats': {
            'pipeline_deals': crm_data.get('kpis', {}).get('pipeline_deals', 0),
            'pipeline_value': crm_data.get('kpis', {}).get('pipeline_value', 0),
            'won_week': crm_data.get('kpis', {}).get('deals_won_week', 0),
            'won_value_week': crm_data.get('kpis', {}).get('won_value_week', 0),
            'lost_week': crm_data.get('kpis', {}).get('deals_lost_month', 0),
            'lost_value_week': crm_data.get('kpis', {}).get('lost_value_month', 0),
            'yesterday_cold_calls': crm_data.get('yesterday_cold_calls', 0),
            'yesterday_total_calls': crm_data.get('yesterday_total_calls', 0),
        },
        'action_manifest': action_manifest,
    }


# --- HTML formatting v2 ---

STYLE_CARD = 'background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px;'
STYLE_AMBER_CARD = STYLE_CARD + ' border-left: 4px solid #f59e0b;'
STYLE_BLUE_CARD = STYLE_CARD + ' border-left: 4px solid #3b82f6;'
STYLE_SECTION_HEADER = 'background: #1e293b; color: white; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-size: 16px; font-weight: 600;'


def format_time(time_str):
    if 'T' in time_str:
        try:
            return datetime.fromisoformat(time_str).strftime('%I:%M %p')
        except ValueError:
            pass
    return time_str


def _context_badge_html(item):
    """Return (badge_html, detail_html) for person-level context, or empty strings."""
    tag = item.get('context_tag')
    if not tag:
        return '', ''
    colors = {
        'ACTIVE_ELSEWHERE': ('#e0f2fe', '#0369a1'),
        'HAS_NEXT_STEP': ('#dcfce7', '#15803d'),
        'WAITING_ON_CLIENT': ('#fef9c3', '#a16207'),
        'NEEDS_ATTENTION': ('#fef2f2', '#dc2626'),
    }
    bg, fg = colors.get(tag, ('#f3f4f6', '#374151'))
    label = tag.replace('_', ' ')
    badge = f'<span style="background: {bg}; color: {fg}; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{label}</span>'
    detail = f'<div style="font-size: 12px; color: #6b7280; margin-top: 2px; font-style: italic;">{item.get("context_detail", "")}</div>' if item.get('context_detail') else ''
    return badge, detail


def format_action_item_html(item, bg_color):
    icons = {'URGENT': '&#128308;', 'HIGH': '&#128992;', 'MEDIUM': '&#128993;', 'LOW': '&#9898;'}
    icon = icons.get(item['priority'], '&#9898;')

    if item['type'] == 'follow_up':
        action_map = {
            'call_then_email': 'Call first. If no answer, send email.',
            'email': 'Send email nudge.',
            'urgent': 'Follow up IMMEDIATELY.',
        }
        action_text = action_map.get(item['recommended_action'], item['recommended_action'])
        value_str = f" &middot; ${item['value']:,.0f}" if item.get('value') else ''
        person = item.get('person_name') or item.get('org_name') or ''
        person_str = f" ({person})" if person else ''
        ctx_badge, ctx_detail = _context_badge_html(item)

        return f"""
  <div style="background: {bg_color}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
    <div style="font-size: 14px; font-weight: 600;">{icon} {item['deal_title']}{person_str}{ctx_badge}</div>
    <div style="font-size: 13px; color: #666; margin-top: 4px;">
      {item['pipeline']} &middot; {item['stage']}{value_str}<br>
      Owner: {item.get('owner_name', 'Unknown')} &middot; Last activity: {item['last_activity_date']} ({item['days_since_activity']}d ago)
    </div>{ctx_detail}
    <div style="font-size: 13px; color: #1d4ed8; margin-top: 6px; font-weight: 500;">&rarr; {action_text}</div>
  </div>"""

    elif item['type'] == 'overdue_activity':
        return f"""
  <div style="background: {bg_color}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
    <div style="font-size: 14px; font-weight: 600;">{icon} OVERDUE: {item['subject']}</div>
    <div style="font-size: 13px; color: #666; margin-top: 4px;">
      {item['activity_type']} &middot; Due: {item['due_date']} ({item['days_overdue']}d overdue)<br>
      Deal: {item.get('deal_title', 'N/A')} &middot; Owner: {item.get('owner_name', 'Unknown')}
    </div>
  </div>"""

    elif item['type'] == 'stale_deal':
        num = item.get('_action_number', '')
        action_badge = f'<span style="background: #3b82f6; color: white; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">#{num} AI: send check-in</span>' if num else ''
        ctx_badge, ctx_detail = _context_badge_html(item)
        return f"""
  <div style="background: {bg_color}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
    <div style="font-size: 13px;">{icon} {item['deal_title']} &mdash; {item['pipeline']} / {item['stage']} &middot; {item['days_since_activity']}d stale{ctx_badge}{action_badge}</div>{ctx_detail}
  </div>"""

    return ''


def format_activity_html(activity, today_str=None):
    """Format a single Pipedrive activity as HTML."""
    atype = activity.get('type', '')
    label = ACTIVITY_TYPE_NAMES.get(atype, atype)
    subject = activity.get('subject', '')
    deal_title = activity.get('deal_title', '')
    due_date = activity.get('due_date', '')
    due_time = activity.get('due_time', '')
    time_str = due_time[:5] if due_time else ''

    is_overdue = today_str and due_date and due_date < today_str
    overdue_badge = f'<span style="background: #fef2f2; color: #dc2626; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">OVERDUE ({due_date})</span>' if is_overdue else ''

    deal_html = f' &middot; {deal_title}' if deal_title else ''

    return f"""  <div style="padding: 8px 10px; border-bottom: 1px solid #f0f0f0; font-size: 13px;">
    <span style="font-weight: 600;">{label}</span>{deal_html}{overdue_badge}
    {f'<div style="font-size: 12px; color: #666; margin-top: 2px;">{subject}</div>' if subject else ''}
  </div>"""


def format_html_v2(triage_data):
    """Build the simplified daily action plan briefing HTML."""
    eps = triage_data['eps']
    stats = triage_data['quick_stats']
    activities = triage_data['todays_activities']
    manifest = triage_data['action_manifest']
    date_str = datetime.now().strftime('%A, %d %B %Y')
    today_str = datetime.now().strftime('%Y-%m-%d')

    allen_count = len(eps['allens_plate']['crm_items'])
    ai_count = (len(eps['ai_can_handle']['inquiry_emails'])
                + len(eps['ai_can_handle']['chase_followups'])
                + len(eps['ai_can_handle']['stale_deals']))
    total_activities = len(activities['tier1']) + len(activities['tier2']) + len(activities['other'])

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 0 auto; padding: 16px; color: #1a1a1a; background: #f5f5f5;">

<div style="{STYLE_CARD}">
  <h1 style="margin: 0 0 4px 0; font-size: 22px;">Morning Briefing</h1>
  <p style="margin: 0; color: #666; font-size: 14px;">{date_str}</p>
</div>
"""

    # ===================== QUICK STATS =====================
    html += f"""<div style="{STYLE_CARD} padding: 14px 20px;">
  <div style="font-size: 13px; color: #555; line-height: 1.8;">
    <strong>Yesterday:</strong> {stats['yesterday_total_calls']} calls ({stats['yesterday_cold_calls']} cold) &nbsp;&middot;&nbsp;
    <strong>Pipeline:</strong> {stats['pipeline_deals']} deals (${stats['pipeline_value']:,.0f}) &nbsp;&middot;&nbsp;
    <strong>Won this week:</strong> {stats['won_week']} (${stats['won_value_week']:,.0f})
  </div>
</div>
"""

    # ===================== TODAY'S ACTIVITIES =====================
    html += f'<div style="{STYLE_SECTION_HEADER}">Today\'s Activities ({total_activities})</div>\n'

    if total_activities == 0:
        html += f'<div style="{STYLE_CARD}"><p style="color: #888; font-size: 13px; margin: 0;">No activities scheduled for today.</p></div>\n'
    else:
        # Tier 1 — EXEC
        if activities['tier1']:
            html += f'<div style="{STYLE_AMBER_CARD}">\n'
            html += '  <div style="font-size: 13px; font-weight: 600; color: #92400e; margin-bottom: 8px;">PRIORITY &mdash; Discoveries & Follow-Ups</div>\n'
            for act in activities['tier1']:
                html += format_activity_html(act, today_str)
            html += '</div>\n'

        # Tier 2 — Operational
        if activities['tier2']:
            html += f'<div style="{STYLE_CARD}">\n'
            html += '  <div style="font-size: 13px; font-weight: 600; color: #555; margin-bottom: 8px;">OPERATIONAL &mdash; Tasks, Site Visits, Quotes</div>\n'
            for act in activities['tier2']:
                html += format_activity_html(act, today_str)
            html += '</div>\n'

        # Other
        if activities['other']:
            html += f'<div style="{STYLE_CARD}">\n'
            html += '  <div style="font-size: 13px; font-weight: 600; color: #888; margin-bottom: 8px;">OTHER</div>\n'
            for act in activities['other']:
                html += format_activity_html(act, today_str)
            html += '</div>\n'

    # ===================== ALLEN'S PLATE =====================
    eps_plate = eps['allens_plate']
    if eps_plate['crm_items']:
        html += f'<div style="{STYLE_SECTION_HEADER}">Allen\'s Plate ({len(eps_plate["crm_items"])})</div>\n'
        html += f'<div style="{STYLE_AMBER_CARD}">\n'

        urgent_items = [i for i in eps_plate['crm_items'] if i['priority'] == 'URGENT']
        high_items = [i for i in eps_plate['crm_items'] if i['priority'] == 'HIGH']
        medium_items = [i for i in eps_plate['crm_items'] if i['priority'] == 'MEDIUM']
        low_items = [i for i in eps_plate['crm_items'] if i['priority'] == 'LOW']

        for items, bg in [(urgent_items, '#fef2f2'), (high_items, '#fff7ed'),
                          (medium_items, '#fefce8'), (low_items, '#f9fafb')]:
            for item in items:
                html += format_action_item_html(item, bg)
        html += '</div>\n'

    # ===================== AI CAN HANDLE =====================
    ai = eps['ai_can_handle']
    ai_total = len(ai['inquiry_emails']) + len(ai['chase_followups']) + len(ai['stale_deals'])

    if ai_total > 0:
        html += f'<div style="{STYLE_SECTION_HEADER}">AI Can Handle ({ai_total})</div>\n'
        html += f'<div style="{STYLE_BLUE_CARD}">\n'

        if ai['inquiry_emails']:
            html += '  <div style="font-size: 13px; font-weight: 600; color: #666; margin-bottom: 6px;">CUSTOMER INQUIRIES</div>\n'
            for email in ai['inquiry_emails']:
                num = email.get('_action_number', '')
                from_short = email['from'].split('<')[0].strip().strip('"')
                html += f"""  <div style="background: #eff6ff; border-radius: 8px; padding: 10px; margin-bottom: 6px;">
    <div style="font-size: 13px;">
      <span style="background: #3b82f6; color: white; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">#{num}</span>
      <span style="font-weight: 600; margin-left: 4px;">{from_short}</span>
      <span style="background: #dbeafe; color: #1e40af; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">AI will draft response</span>
    </div>
    <div style="font-size: 13px; margin-top: 4px; font-weight: 500;">{email['subject']}</div>
    <div style="font-size: 12px; color: #666; margin-top: 2px;">{email['snippet'][:120]}</div>
  </div>\n"""

        if ai['chase_followups']:
            html += '  <div style="font-size: 13px; font-weight: 600; color: #666; margin: 8px 0 6px 0;">FOLLOW-UP EMAILS</div>\n'
            for item in ai['chase_followups']:
                num = item.get('_action_number', '')
                person = item.get('person_name') or item.get('org_name') or ''
                person_str = f" ({person})" if person else ''
                value_str = f" &middot; ${item['value']:,.0f}" if item.get('value') else ''
                ctx_badge, ctx_detail = _context_badge_html(item)
                html += f"""  <div style="background: #eff6ff; border-radius: 8px; padding: 10px; margin-bottom: 6px;">
    <div style="font-size: 13px;">
      <span style="background: #3b82f6; color: white; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">#{num}</span>
      <span style="font-weight: 600; margin-left: 4px;">{item['deal_title']}{person_str}</span>
      <span style="background: #dbeafe; color: #1e40af; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">AI will draft chase</span>{ctx_badge}
    </div>
    <div style="font-size: 12px; color: #666; margin-top: 4px;">{item['pipeline']} &middot; {item['stage']}{value_str} &middot; {item['days_since_activity']}d since last activity</div>{ctx_detail}
  </div>\n"""

        if ai['stale_deals']:
            html += '  <div style="font-size: 13px; font-weight: 600; color: #666; margin: 8px 0 6px 0;">STALE DEALS</div>\n'
            for item in ai['stale_deals']:
                num = item.get('_action_number', '')
                ctx_badge, ctx_detail = _context_badge_html(item)
                html += f"""  <div style="background: #f0f9ff; border-radius: 8px; padding: 10px; margin-bottom: 6px;">
    <div style="font-size: 13px;">
      <span style="background: #3b82f6; color: white; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">#{num}</span>
      <span style="margin-left: 4px;">{item['deal_title']} &mdash; {item['pipeline']} / {item['stage']} &middot; {item['days_since_activity']}d stale</span>
      <span style="background: #dbeafe; color: #1e40af; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">AI: send check-in</span>{ctx_badge}
    </div>{ctx_detail}
  </div>\n"""

        html += '</div>\n'

    # ===================== EPS INBOX =====================
    if eps.get('other_emails'):
        html += f'<div style="{STYLE_SECTION_HEADER}">EPS Inbox ({len(eps["other_emails"])})</div>\n'
        html += f'<div style="{STYLE_CARD}">\n'
        for email in eps['other_emails']:
            badges = ''
            if email.get('important'):
                badges += '<span style="background: #fef2f2; color: #dc2626; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">IMPORTANT</span>'
            if email.get('starred'):
                badges += '<span style="background: #fefce8; color: #ca8a04; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">STARRED</span>'
            from_short = email['from'].split('<')[0].strip().strip('"')
            html += f"""  <div style="padding: 8px 0; border-bottom: 1px solid #eee;">
    <div style="font-size: 13px; color: #666;">{from_short}{badges}</div>
    <div style="font-size: 14px; font-weight: 600; margin: 2px 0;">{email['subject']}</div>
    <div style="font-size: 12px; color: #888;">{email['snippet'][:120]}</div>
  </div>\n"""
        html += '</div>\n'

    # ===================== ACTION FOOTER =====================
    if manifest:
        numbers = ', '.join(str(m['number']) for m in manifest)
        html += f"""
<div style="{STYLE_CARD} background: #f0f9ff; border: 1px solid #bfdbfe;">
  <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #1e40af;">AI Actions Ready ({len(manifest)})</h3>
  <div style="font-size: 13px; color: #333; line-height: 1.6;">"""
        for m in manifest:
            label = {'inquiry': 'Draft response', 'chase': 'Draft chase email', 'stale': 'Send check-in'}.get(m['type'], m['type'])
            title = m.get('subject') or m.get('deal_title') or ''
            html += f'    <strong>#{m["number"]}</strong> {label}: {title}<br>\n'
        html += f"""  </div>
  <div style="margin-top: 12px; padding: 10px; background: #dbeafe; border-radius: 6px; font-size: 13px; font-weight: 500; color: #1e3a5f;">
    Reply: <strong>GO {numbers}</strong> to approve &nbsp;|&nbsp; <strong>SKIP #</strong> to dismiss &nbsp;|&nbsp; <strong>GO ALL</strong>
  </div>
</div>
"""

    # Footer
    html += f"""
<div style="text-align: center; padding: 16px; color: #999; font-size: 12px;">
  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; Enriquez OS Executive Assistant
</div>

</body></html>"""

    return html


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description='Morning Briefing v2')
    parser.add_argument('--send', action='store_true', help='Send email (default: generate data files only)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no files written')
    parser.add_argument('--to', help='Override recipient email (requires --send)')
    args = parser.parse_args()

    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY', '')
    domain = env.get('PIPEDRIVE_COMPANY_DOMAIN', '')
    to_email = args.to or BRIEFING_TO_EMAIL_DEFAULT

    if not api_key or not domain:
        print("ERROR: Missing Pipedrive credentials in .env", file=sys.stderr)
        sys.exit(1)

    # 1. CRM Monitor
    print("=== CRM Monitor ===")
    crm_data = run_monitor(api_key=api_key, domain=domain, dry_run=True)

    # 2. Gmail (EPS only — personal moved to evening briefing)
    print("\n=== Gmail ===")
    gmail_eps = fetch_gmail_unread(EPS_TOKEN, 'EPS')

    # 3. Classify into triage buckets
    print("\n=== Triage ===")
    triage = classify_for_triage(crm_data, gmail_eps)

    activities = triage['todays_activities']
    total_activities = len(activities['tier1']) + len(activities['tier2']) + len(activities['other'])
    allen_count = len(triage['eps']['allens_plate']['crm_items'])
    ai_count = len(triage['action_manifest'])
    print(f"  Today's activities: {total_activities} ({len(activities['tier1'])} exec, {len(activities['tier2'])} operational)")
    print(f"  Allen's Plate: {allen_count} items")
    print(f"  AI Can Handle: {ai_count} items")

    # 5. Format HTML
    print("\n=== Formatting ===")
    html = format_html_v2(triage)

    if args.dry_run:
        print(f"\n=== DRY RUN — preview only, no files written ===")
        stats = triage['quick_stats']
        print(f"\n  Pipeline: {stats['pipeline_deals']} deals (${stats['pipeline_value']:,.0f})")
        print(f"  Yesterday: {stats['yesterday_total_calls']} calls ({stats['yesterday_cold_calls']} cold)")
        print(f"  Today's activities: {total_activities}")
        print(f"  Allen's Plate: {allen_count} items")
        print(f"  AI Can Handle: {ai_count} items")
        print(f"  Unread emails: {len(gmail_eps)} EPS")
        return

    # Save data files (default behavior + --send)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    html_file = TMP_DIR / 'morning_briefing.html'
    html_file.write_text(html)
    print(f"  HTML saved to: {html_file}")

    # Save action manifest for the action loop
    manifest_file = TMP_DIR / 'briefing_actions.json'
    manifest_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'actions': triage['action_manifest'],
    }
    manifest_file.write_text(json.dumps(manifest_data, indent=2))
    print(f"  Action manifest saved to: {manifest_file}")

    if not args.send:
        print(f"\n=== Data files generated (no email sent) ===")
        print(f"  Use --send to also send the briefing email")
        return

    # 6. Send via personal Gmail (only with --send)
    print(f"\n=== Sending to {to_email} (via personal Gmail) ===")
    date_str = crm_data['date']
    subject = f"Morning Briefing {date_str} — {total_activities} activities, {allen_count} action items"

    if not PERSONAL_TOKEN.exists():
        print("ERROR: Personal token not found. Run: python3 tools/auth_personal.py",
              file=sys.stderr)
        sys.exit(1)
    with open(PERSONAL_TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    msg = MIMEMultipart('alternative')
    msg['to'] = to_email
    msg['from'] = f"{BRIEFING_FROM_NAME} <{BRIEFING_FROM_EMAIL}>"
    msg['subject'] = subject
    msg.attach(MIMEText(html, 'html'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().send(
        userId='me', body={'raw': raw}
    ).execute()

    # Save message ID for action loop
    manifest_data['briefing_message_id'] = result.get('id')
    manifest_file.write_text(json.dumps(manifest_data, indent=2))

    print(f"  Sent! Message ID: {result.get('id')}")


if __name__ == '__main__':
    main()
