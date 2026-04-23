"""
outreach_lifecycle.py — log-sent, follow-up detection, reply drafting
for Allen's PH outreach system.

Called from tools/outreach.py. No __main__ block.
"""

import base64
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import parseaddr
from pathlib import Path

PH_TZ = timezone(timedelta(hours=8))

OPTOUT_KEYWORDS = [
    "stop",
    "unsubscribe",
    "not interested",
    "remove me",
    "dont contact",
    "don't contact",
]

HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_TEMPERATURE = 0.3
HAIKU_MAX_TOKENS = 600

REPLY_SYSTEM_PROMPT = """You are Allen Enriquez replying to prospects who responded to cold outreach.

VOICE:
- 3rd grade reading level
- Under 10 words per sentence
- No jargon, no buzzwords, no filler
- Warm, direct, human
- Sign off as "Allen"

GOAL:
- Move the conversation toward a 10-minute call, OR
- Send one specific resource (a short video, a case study link)

RULES:
- Never make promises about price or timeline without data
- Never invent capabilities Allen hasn't mentioned in the thread
- If they ask a technical question you can't answer, say Allen will follow up personally
- If they already said yes to a call, propose 2 concrete time slots (Manila time)
- Keep replies under 80 words

CLASSIFICATION — pick ONE:
- INTERESTED: they want to talk, ask for call, ask for more info in a positive way
- NOT_INTERESTED: polite pass, "maybe later", "not right now"
- QUESTION: they're asking something specific before deciding
- OPTOUT: stop, unsubscribe, not interested, remove me, don't contact
- OTHER: anything else (auto-reply, out of office, unclear)

Respond in JSON only:
{
  "classification": "INTERESTED" | "NOT_INTERESTED" | "QUESTION" | "OPTOUT" | "OTHER",
  "reply": "the reply message in Allen's voice",
  "reasoning": "one short sentence on why you classified this way"
}
"""


# ============================================================
# Cell helpers (duplicated from outreach.py for self-containment)
# ============================================================

def col_letter(index: int) -> str:
    """0-based column index -> letter (0=A, 25=Z, 26=AA)."""
    result = ''
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result


def write_cell(sheets_svc, spreadsheet_id: str, headers: list,
               row_num: int, field: str, value: str) -> None:
    """Write a single cell. Raises if the header isn't in the sheet."""
    if field not in headers:
        raise ValueError(f"column {field!r} not in sheet")
    letter = col_letter(headers.index(field))
    try:
        sheets_svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"Prospects!{letter}{row_num}",
            valueInputOption='RAW',
            body={'values': [[value]]},
        ).execute()
    except Exception as e:
        raise RuntimeError(f"sheet write failed for {field} row {row_num}: {e}")


def _read_prospects(sheets_svc, spreadsheet_id):
    """Return (headers, rows) where rows are dicts with _row index."""
    try:
        r = sheets_svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="Prospects"
        ).execute()
    except Exception:
        return [], []
    values = r.get('values', [])
    if not values:
        return [], []
    headers = values[0]
    rows = []
    for i, row in enumerate(values[1:], start=2):
        padded = row + [''] * (len(headers) - len(row))
        rows.append({'_row': i, **{h: padded[j] for j, h in enumerate(headers)}})
    return headers, rows


def _today_ph() -> date:
    return datetime.now(PH_TZ).date()


def _parse_date(s: str):
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _safe_write(sheets_svc, spreadsheet_id, headers, row_num, field, value,
                errors=None, overwrite=False, existing=''):
    """Write a cell. Skip if cell has content and overwrite=False. Collect errors."""
    if not overwrite and (existing or '').strip():
        return False
    try:
        write_cell(sheets_svc, spreadsheet_id, headers, row_num, field, value)
        return True
    except Exception as e:
        if errors is not None:
            errors.append(f"row {row_num} {field}: {e}")
        return False


# ============================================================
# Queue file parser
# ============================================================

_SECTION_RE = re.compile(
    r'^##\s+(?P<id>\d+)\.\s+(?P<channel>EMAIL|FB|IG|DM)\s+T(?P<touch>\d+)\s+.*?Row\s+(?P<row>\d+)',
    re.IGNORECASE,
)


def _parse_queue_file(queue_file: Path) -> dict:
    """
    Parse the daily outreach queue markdown into a dict keyed by queue id.

    Each entry: {id, row_num, channel ('email' | 'fb' | 'ig'), touch, to,
    subject, body, raw}.
    """
    entries = {}
    if not queue_file.exists():
        return entries

    text = queue_file.read_text()
    lines = text.splitlines()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = _SECTION_RE.match(line.strip())
        if not m:
            i += 1
            continue

        qid = int(m.group('id'))
        channel_raw = m.group('channel').upper()
        if channel_raw == 'EMAIL':
            channel = 'email'
        elif channel_raw in ('FB', 'DM'):
            channel = 'fb'
        elif channel_raw == 'IG':
            channel = 'ig'
        else:
            channel = channel_raw.lower()
        touch = int(m.group('touch'))
        row_num = int(m.group('row'))

        # Collect section body until next `## N.` or EOF
        body_lines = []
        j = i + 1
        while j < n and not _SECTION_RE.match(lines[j].strip()):
            body_lines.append(lines[j])
            j += 1

        to = ''
        subject = ''
        msg_lines = []
        k = 0
        # Pull headers at top (To:, Subject:) then the rest is the message.
        while k < len(body_lines):
            raw = body_lines[k]
            stripped = raw.strip()
            low = stripped.lower()
            if low.startswith('to:'):
                to = stripped[3:].strip()
                k += 1
                continue
            if low.startswith('subject:'):
                subject = stripped[8:].strip()
                k += 1
                continue
            if low.startswith('profile:') or low.startswith('url:') or low.startswith('channel:'):
                k += 1
                continue
            break

        # Skip leading blanks before body
        while k < len(body_lines) and not body_lines[k].strip():
            k += 1

        msg_lines = body_lines[k:]
        # Trim trailing blanks
        while msg_lines and not msg_lines[-1].strip():
            msg_lines.pop()
        body = '\n'.join(msg_lines).strip()

        entries[qid] = {
            'id': qid,
            'row_num': row_num,
            'channel': channel,
            'touch': touch,
            'to': to,
            'subject': subject,
            'body': body,
            'raw': '\n'.join(body_lines).strip(),
        }
        i = j

    return entries


# ============================================================
# log_sent
# ============================================================

def log_sent(ids: list, sheets_svc, spreadsheet_id: str, headers: list,
             queue_file: Path) -> dict:
    """
    Mark each id from today's queue as sent. For each:
      - Touch N Date = today (PH)
      - Touch N Channel = channel
      - Touch N Msg    = body
      - Status         = 'sent_t{touch}'
    Never overwrites non-empty Touch N cells (except Status always updates).
    """
    result = {'marked': 0, 'errors': []}
    if not queue_file.exists():
        result['errors'].append(f"queue file missing: {queue_file}")
        return result

    entries = _parse_queue_file(queue_file)
    if not entries:
        result['errors'].append(f"no entries parsed from {queue_file}")
        return result

    # Read current sheet so we know what's already populated
    sheet_headers, rows = _read_prospects(sheets_svc, spreadsheet_id)
    if not sheet_headers:
        result['errors'].append("could not read Prospects tab")
        return result
    # Prefer the sheet's real headers over the caller's if mismatched
    headers = sheet_headers
    rows_by_num = {r['_row']: r for r in rows}

    today_str = _today_ph().strftime('%Y-%m-%d')

    for qid in ids:
        entry = entries.get(qid)
        if not entry:
            result['errors'].append(f"id {qid} not found in queue file")
            continue

        row_num = entry['row_num']
        touch = entry['touch']
        channel = entry['channel']
        body = entry['body']

        if touch not in (1, 2, 3):
            result['errors'].append(f"id {qid}: unsupported touch {touch}")
            continue

        date_col = f'Touch {touch} Date'
        chan_col = f'Touch {touch} Channel'
        msg_col = f'Touch {touch} Msg'

        missing = [c for c in (date_col, chan_col, msg_col, 'Status') if c not in headers]
        if missing:
            result['errors'].append(f"id {qid}: sheet missing columns {missing}")
            continue

        existing = rows_by_num.get(row_num, {})

        _safe_write(sheets_svc, spreadsheet_id, headers, row_num, date_col,
                    today_str, result['errors'], overwrite=False,
                    existing=existing.get(date_col, ''))
        _safe_write(sheets_svc, spreadsheet_id, headers, row_num, chan_col,
                    channel, result['errors'], overwrite=False,
                    existing=existing.get(chan_col, ''))
        _safe_write(sheets_svc, spreadsheet_id, headers, row_num, msg_col,
                    body, result['errors'], overwrite=False,
                    existing=existing.get(msg_col, ''))
        # Status always updates
        try:
            write_cell(sheets_svc, spreadsheet_id, headers, row_num, 'Status',
                       f'sent_t{touch}')
            result['marked'] += 1
        except Exception as e:
            result['errors'].append(f"id {qid}: status write failed: {e}")

    return result


# ============================================================
# detect_followups
# ============================================================

def detect_followups(sheets_svc, spreadsheet_id: str, wait_rules: dict,
                     today: date) -> list:
    """
    Scan Prospects, return the list of rows due for Touch 2 or Touch 3.
    Also writes Status = 'cold' for rows where Touch 3 has aged out.
    """
    headers, rows = _read_prospects(sheets_svc, spreadsheet_id)
    if not headers:
        return []

    wait_t1_t2 = int(wait_rules.get('touch_1_to_2', 3))
    wait_t2_t3 = int(wait_rules.get('touch_2_to_3', 5))
    wait_t3_cold = int(wait_rules.get('touch_3_to_cold', 7))

    due = []

    for r in rows:
        status = (r.get('Status') or '').strip().lower()
        if status in ('do_not_contact', 'converted', 'cold'):
            continue
        if status.startswith('replied_'):
            continue

        last_reply = (r.get('Last Reply Date') or '').strip()
        if last_reply:
            # If they already replied, do not auto-followup
            continue

        t1_date = _parse_date(r.get('Touch 1 Date', ''))
        t2_date = _parse_date(r.get('Touch 2 Date', ''))
        t3_date = _parse_date(r.get('Touch 3 Date', ''))

        current_touch = 0
        next_touch = None
        anchor_date = None

        if status.startswith('sent_t3') or t3_date:
            current_touch = 3
            anchor_date = t3_date
            # Check cold-drop
            if anchor_date and (today - anchor_date).days >= wait_t3_cold:
                try:
                    write_cell(sheets_svc, spreadsheet_id, headers, r['_row'],
                               'Status', 'cold')
                except Exception:
                    pass
            continue  # No Touch 4; T3 is terminal outreach step
        elif status.startswith('sent_t2') or t2_date:
            current_touch = 2
            next_touch = 3
            anchor_date = t2_date
            wait_days = wait_t2_t3
        elif status.startswith('sent_t1') or t1_date:
            current_touch = 1
            next_touch = 2
            anchor_date = t1_date
            wait_days = wait_t1_t2
        else:
            continue

        if not anchor_date:
            continue
        if (today - anchor_date).days < wait_days:
            continue

        # Pick channel for the follow-up: default to whatever channel was used
        # in the most recent prior touch, fall back to email if no data.
        prior_channel = ''
        for t in (current_touch, 1):
            chan = (r.get(f'Touch {t} Channel') or '').strip().lower()
            if chan:
                prior_channel = chan
                break
        channel = prior_channel or ('email' if (r.get('Email') or '').strip() else 'fb')

        due.append({
            '_row': r['_row'],
            'name': r.get('Name', '') or '',
            'company': r.get('Company', '') or '',
            'current_touch': current_touch,
            'next_touch': next_touch,
            'channel': channel,
            'profile_url': r.get('Profile URL', '') or '',
            'email': r.get('Email', '') or '',
            'fb_url': r.get('FB URL', '') or '',
            'personal_hook': r.get('Personal Hook', '') or '',
            'segment': r.get('Segment', '') or '',
        })

    return due


# ============================================================
# Gmail + Haiku reply drafting
# ============================================================

def _gmail_list_inbound(gmail_svc, query: str = 'in:inbox is:unread newer_than:14d') -> list:
    try:
        resp = gmail_svc.users().messages().list(
            userId='me', q=query, maxResults=100,
        ).execute()
        return resp.get('messages', []) or []
    except Exception:
        return []


def _gmail_get_message(gmail_svc, msg_id: str) -> dict:
    try:
        return gmail_svc.users().messages().get(
            userId='me', id=msg_id, format='full',
        ).execute()
    except Exception:
        return {}


def _gmail_get_thread(gmail_svc, thread_id: str) -> dict:
    try:
        return gmail_svc.users().threads().get(
            userId='me', id=thread_id, format='full',
        ).execute()
    except Exception:
        return {}


def _header(message: dict, name: str) -> str:
    headers = (message.get('payload') or {}).get('headers') or []
    for h in headers:
        if h.get('name', '').lower() == name.lower():
            return h.get('value', '') or ''
    return ''


def _decode_body(payload: dict) -> str:
    if not payload:
        return ''
    mime = payload.get('mimeType', '')
    body = payload.get('body') or {}
    data = body.get('data')
    if data and mime.startswith('text/'):
        try:
            raw = base64.urlsafe_b64decode(data + '==')
            return raw.decode('utf-8', errors='replace')
        except Exception:
            return ''
    parts = payload.get('parts') or []
    # Prefer text/plain, then text/html
    for p in parts:
        if p.get('mimeType') == 'text/plain':
            text = _decode_body(p)
            if text:
                return text
    for p in parts:
        if p.get('mimeType') == 'text/html':
            html = _decode_body(p)
            if html:
                return re.sub(r'<[^>]+>', ' ', html)
    for p in parts:
        text = _decode_body(p)
        if text:
            return text
    return ''


def _extract_plaintext(message: dict) -> str:
    text = _decode_body(message.get('payload') or {})
    if not text:
        return ''
    # Strip quoted reply sections crudely
    lines = []
    for line in text.splitlines():
        if line.strip().startswith('>'):
            continue
        if re.match(r'^On .* wrote:$', line.strip()):
            break
        lines.append(line)
    return '\n'.join(lines).strip()


def _normalise_email(addr: str) -> str:
    _, e = parseaddr(addr or '')
    return (e or '').strip().lower()


def _thread_recent_messages(gmail_svc, thread_id: str, max_msgs: int = 5) -> list:
    thread = _gmail_get_thread(gmail_svc, thread_id)
    messages = thread.get('messages') or []
    picked = messages[-max_msgs:] if messages else []
    out = []
    for m in picked:
        frm = _header(m, 'From')
        date_hdr = _header(m, 'Date')
        text = _extract_plaintext(m)
        out.append({
            'from': frm,
            'date': date_hdr,
            'text': text[:2000],
        })
    return out


def _detect_optout(text: str) -> bool:
    lower = (text or '').lower()
    for kw in OPTOUT_KEYWORDS:
        if kw in lower:
            return True
    return False


def _call_haiku_for_reply(anthropic_api_key: str, context_block: str) -> dict:
    if not anthropic_api_key:
        return {
            'classification': 'OTHER',
            'reply': '',
            'reasoning': 'ANTHROPIC_API_KEY missing',
        }
    payload = json.dumps({
        'model': HAIKU_MODEL,
        'max_tokens': HAIKU_MAX_TOKENS,
        'temperature': HAIKU_TEMPERATURE,
        'system': REPLY_SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': context_block}],
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'x-api-key': anthropic_api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'classification': 'OTHER', 'reply': '',
                'reasoning': f'Haiku HTTP {e.code}'}
    except Exception as e:
        return {'classification': 'OTHER', 'reply': '',
                'reasoning': f'Haiku error: {e}'}

    text = ''
    for block in data.get('content') or []:
        if block.get('type') == 'text':
            text += block.get('text', '')

    # Extract JSON from response
    if '{' not in text or '}' not in text:
        return {'classification': 'OTHER', 'reply': '',
                'reasoning': 'Haiku returned no JSON'}
    try:
        json_str = text[text.index('{'):text.rindex('}') + 1]
        parsed = json.loads(json_str)
    except Exception as e:
        return {'classification': 'OTHER', 'reply': '',
                'reasoning': f'JSON parse error: {e}'}

    parsed.setdefault('classification', 'OTHER')
    parsed.setdefault('reply', '')
    parsed.setdefault('reasoning', '')
    return parsed


_STATUS_BY_CLASSIFICATION = {
    'INTERESTED': 'replied_warm',
    'NOT_INTERESTED': 'replied_not_interested',
    'QUESTION': 'replied_question',
    'OTHER': 'replied_other',
}


def poll_replies_and_draft(gmail_svc, sheets_svc, spreadsheet_id: str,
                           headers: list, anthropic_api_key: str,
                           drafts_file: Path) -> dict:
    """
    Poll Gmail INBOX for replies from prospects we've emailed. For each match:
      - Detect opt-out -> Status = do_not_contact, no draft
      - Otherwise Haiku classifies + drafts
      - Update Last Reply Date / Last Reply / Status in Sheet
      - Append draft section to drafts_file (markdown)
    """
    result = {'inbound': 0, 'drafts_written': 0, 'optouts': 0}

    sheet_headers, rows = _read_prospects(sheets_svc, spreadsheet_id)
    if not sheet_headers:
        return result
    headers = sheet_headers

    # Build email -> row data map (only prospects we've actually emailed).
    prospects_by_email = {}
    for r in rows:
        email = _normalise_email(r.get('Email', ''))
        if not email:
            continue
        status = (r.get('Status') or '').strip().lower()
        if not status.startswith('sent_'):
            continue
        has_touch = any((r.get(f'Touch {t} Date') or '').strip() for t in (1, 2, 3))
        if not has_touch:
            continue
        prospects_by_email[email] = r

    if not prospects_by_email:
        return result

    msg_refs = _gmail_list_inbound(gmail_svc)
    if not msg_refs:
        return result

    today_str = _today_ph().strftime('%Y-%m-%d')
    draft_sections = []
    processed_rows = set()

    for ref in msg_refs:
        msg = _gmail_get_message(gmail_svc, ref.get('id', ''))
        if not msg:
            continue

        sender_email = _normalise_email(_header(msg, 'From'))
        if not sender_email or sender_email not in prospects_by_email:
            continue

        prospect = prospects_by_email[sender_email]
        row_num = prospect['_row']

        # Avoid double-handling if multiple messages arrive for one prospect
        # in this run — act on the most recent one only.
        if row_num in processed_rows:
            continue
        processed_rows.add(row_num)

        result['inbound'] += 1

        reply_text = _extract_plaintext(msg)
        snippet = (reply_text or msg.get('snippet') or '').strip()
        snippet_short = snippet[:200]

        # Write Last Reply Date + Last Reply up-front (don't overwrite existing).
        if 'Last Reply Date' in headers:
            _safe_write(sheets_svc, spreadsheet_id, headers, row_num,
                        'Last Reply Date', today_str, None, overwrite=False,
                        existing=prospect.get('Last Reply Date', ''))
        if 'Last Reply' in headers:
            _safe_write(sheets_svc, spreadsheet_id, headers, row_num,
                        'Last Reply', snippet_short, None, overwrite=False,
                        existing=prospect.get('Last Reply', ''))

        # Opt-out short-circuit (keyword match OR Haiku-confirmed OPTOUT).
        if _detect_optout(reply_text):
            try:
                write_cell(sheets_svc, spreadsheet_id, headers, row_num,
                           'Status', 'do_not_contact')
            except Exception:
                pass
            result['optouts'] += 1
            continue

        # Build Haiku context.
        thread_id = msg.get('threadId')
        recent = _thread_recent_messages(gmail_svc, thread_id, max_msgs=5) if thread_id else []
        thread_block = '\n\n'.join(
            f"[{m.get('date', '?')} | {m.get('from', '?')}]\n{m.get('text', '')}"
            for m in recent
        ) or reply_text

        offer_line = 'Allen helps PH businesses automate sales + ops with AI. Goal: 10-min discovery call or share a short resource.'

        context_block = (
            f"Prospect: {prospect.get('Name', '')} ({prospect.get('Company', '')})\n"
            f"Segment: {prospect.get('Segment', '')}\n"
            f"Allen's offer: {offer_line}\n\n"
            f"Recent thread (most recent last):\n{thread_block}\n\n"
            f"Draft Allen's reply to the MOST RECENT inbound message."
        )

        haiku = _call_haiku_for_reply(anthropic_api_key, context_block)
        classification = (haiku.get('classification') or 'OTHER').upper()
        draft_reply = (haiku.get('reply') or '').strip()
        reasoning = haiku.get('reasoning', '')

        if classification == 'OPTOUT':
            try:
                write_cell(sheets_svc, spreadsheet_id, headers, row_num,
                           'Status', 'do_not_contact')
            except Exception:
                pass
            result['optouts'] += 1
            continue

        status_val = _STATUS_BY_CLASSIFICATION.get(classification, 'replied_other')
        try:
            write_cell(sheets_svc, spreadsheet_id, headers, row_num,
                       'Status', status_val)
        except Exception:
            pass

        if not draft_reply:
            # Still record inbound, but no draft to write.
            continue

        subject = _header(msg, 'Subject') or 'quick reply'
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        reply_file = f".tmp/reply_{row_num}.txt"
        send_cmd = (
            f"python3 tools/send_personal_email.py "
            f"--to {sender_email} "
            f"--subject '{subject}' "
            f"--body-file {reply_file}"
        )

        section = []
        section.append(
            f"## Reply to {prospect.get('Name', '(unknown)')} "
            f"({prospect.get('Company', '')}) — Row {row_num}"
        )
        their_preview = reply_text.strip().replace('\n', ' ')[:400] or '(empty body)'
        section.append(f"Their message: \"{their_preview}\"")
        section.append(f"Classification: {classification}")
        if reasoning:
            section.append(f"Reasoning: {reasoning}")
        section.append("---")
        section.append("Suggested reply:\n")
        section.append(draft_reply)
        section.append("")
        section.append("Send command:")
        section.append(f"`{send_cmd}`")
        section.append("---\n")
        draft_sections.append('\n'.join(section))
        result['drafts_written'] += 1

    if draft_sections:
        try:
            drafts_file.parent.mkdir(parents=True, exist_ok=True)
            header_block = (
                f"# PH Outreach Reply Drafts — "
                f"{datetime.now(PH_TZ).strftime('%Y-%m-%d %H:%M PH')}\n\n"
            )
            drafts_file.write_text(header_block + '\n'.join(draft_sections))
        except Exception:
            pass

    return result
