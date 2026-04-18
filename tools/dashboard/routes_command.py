"""
Command Center + Claude Chat routes — bolted onto dashboard app.

Usage in app.py:
    from routes_command import command_bp, init_command
    init_command(sheets_service, dashboard_sheet_id)
    app.register_blueprint(command_bp)
"""

import json
import time
from datetime import datetime, timedelta

import anthropic
from flask import Blueprint, jsonify, request

from agent_tools import execute_tool, get_tool_schemas
from config import get_anthropic_key, get_pipedrive_creds, now_ph, today_ph

command_bp = Blueprint('command', __name__)

_sheets_service = None
_dashboard_sheet_id = None
CRM_SHEET_ID = '1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8'


def init_command(sheets_service, dashboard_sheet_id):
    global _sheets_service, _dashboard_sheet_id
    _sheets_service = sheets_service
    _dashboard_sheet_id = dashboard_sheet_id


def _svc():
    global _sheets_service
    if _sheets_service is None:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from personal_crm import get_sheets_service
        _sheets_service = get_sheets_service()
    return _sheets_service


@command_bp.route('/api/command-center')
def command_center():
    """Aggregate status from Dashboard Sheet + CRM Sheet."""
    try:
        service = _svc()
        today = today_ph()
        result = {}

        # --- Checklist completion (from SQLite — same source as Habits tab) ---
        try:
            import db
            config = db.load_config()
            total_items = sum(len(items) for items in config.values())
            completions = db.load_log(today)

            done_count = 0
            for items in config.values():
                for item in items:
                    val = completions.get(item['name'], '')
                    if item['type'] == 'check' and val.upper() in ('TRUE', '1', 'YES'):
                        done_count += 1
                    elif item['type'] == 'count' and val and val != '0':
                        done_count += 1

            pct = round((done_count / total_items * 100)) if total_items else 0
            result['checklist'] = {
                'done': done_count,
                'total': total_items,
                'pct': pct,
            }
        except Exception:
            result['checklist'] = {'done': 0, 'total': 0, 'pct': 0}

        # --- Today's spend ---
        try:
            spend_res = service.spreadsheets().values().get(
                spreadsheetId=_dashboard_sheet_id,
                range="'Spend Log'"
            ).execute()
            spend_rows = spend_res.get('values', [])[1:]
            today_spend = 0
            for row in spend_rows:
                if len(row) >= 3 and row[0] == today:
                    try:
                        today_spend += float(row[2])
                    except (ValueError, IndexError):
                        pass
            result['spend'] = {'today': round(today_spend, 2)}
        except Exception:
            result['spend'] = {'today': 0}

        # Outreach stats moved to /api/outreach/detailed (own cache) — don't re-fetch here
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


_outreach_cache = {'data': None, 'time': 0, 'ttl': 60}


@command_bp.route('/api/outreach/detailed')
def outreach_detailed():
    """Rich call analytics for the personal brand CRM cold calling dashboard."""
    try:
        # 60s cache — Sheets reads take 5-7s, killing page load
        now_ts = time.time()
        if _outreach_cache['data'] and (now_ts - _outreach_cache['time']) < _outreach_cache['ttl']:
            return jsonify(_outreach_cache['data'])

        import sys
        from pathlib import Path
        from collections import Counter
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from personal_crm import ALL_TABS, HOT_OUTCOMES, parse_row

        service = _svc()
        now = now_ph()
        today_label = f"{now.day} {now.strftime('%B')}"

        # Build date labels for last 14 days
        date_labels = {}
        for d in range(14):
            dt = now - timedelta(days=d)
            label = f"{dt.day} {dt.strftime('%B')}"
            date_labels[label] = dt.strftime('%Y-%m-%d')

        # Week boundaries (Sun–Sat)
        week_start = now - timedelta(days=(now.weekday() + 1) % 7)
        week_labels = set()
        for d in range(7):
            dt = week_start + timedelta(days=d)
            week_labels.add(f"{dt.day} {dt.strftime('%B')}")

        # Outcome categories
        CONVO_OUTCOMES = {
            'Warm Interest', 'Meeting Booked', 'Call Back',
            'Asked For Email', 'Late Follow Up', 'Not Interested - Convo',
        }
        NO_ANSWER = {'No Answer 1', 'No Answer 2', 'No Answer 3', 'No Answer 4', 'No Answer 5'}
        DEAD = {'Invalid Number', 'Hung Up - No Convo', 'Not Interested - Convo'}

        # Collect all lead data
        meta = service.spreadsheets().get(spreadsheetId=CRM_SHEET_ID).execute()
        existing_tabs = {s['properties']['title'] for s in meta['sheets']}

        today_outcomes = []
        week_outcomes = []
        daily_data = {}  # date_str -> list of outcomes
        total_called = 0
        total_uncalled = 0

        # Single batchGet call vs 14 sequential reads — major speedup
        tabs_to_fetch = [t for t in ALL_TABS if t in existing_tabs]
        batch_res = service.spreadsheets().values().batchGet(
            spreadsheetId=CRM_SHEET_ID,
            ranges=[f"'{t}'" for t in tabs_to_fetch],
        ).execute()

        for tab, value_range in zip(tabs_to_fetch, batch_res.get('valueRanges', [])):
            rows = value_range.get('values', [])
            if not rows:
                continue
            headers = rows[0]
            col_map = {h: i for i, h in enumerate(headers)}

            for i, row in enumerate(rows[1:], start=2):
                lead = parse_row(row, col_map, tab, i)
                if not lead:
                    continue
                outcome = lead.get('call_outcome', '') or 'New / No Label'
                dc = (lead.get('date_called', '') or '').strip()

                if not dc or outcome == 'New / No Label':
                    total_uncalled += 1
                    continue

                total_called += 1

                if dc == today_label:
                    today_outcomes.append(outcome)
                if dc in week_labels:
                    week_outcomes.append(outcome)

                if dc in date_labels:
                    date_str = date_labels[dc]
                    daily_data.setdefault(date_str, []).append(outcome)

        # --- Today stats ---
        today_count = Counter(today_outcomes)
        today_total = len(today_outcomes)
        today_convos = sum(1 for o in today_outcomes if o in CONVO_OUTCOMES)
        today_no_answer = sum(1 for o in today_outcomes if o in NO_ANSWER)
        today_hung_up = sum(1 for o in today_outcomes if o == 'Hung Up - No Convo')
        today_not_interested = sum(1 for o in today_outcomes if o == 'Not Interested - Convo')
        today_invalid = sum(1 for o in today_outcomes if o == 'Invalid Number')
        today_warm = sum(1 for o in today_outcomes if o in HOT_OUTCOMES)
        today_callback = sum(1 for o in today_outcomes if o == 'Call Back')
        today_email = sum(1 for o in today_outcomes if o == 'Asked For Email')
        today_meeting = sum(1 for o in today_outcomes if o == 'Meeting Booked')

        DAILY_GOAL = 100

        # --- Week stats ---
        week_count = Counter(week_outcomes)
        week_total = len(week_outcomes)
        week_convos = sum(1 for o in week_outcomes if o in CONVO_OUTCOMES)
        week_no_answer = sum(1 for o in week_outcomes if o in NO_ANSWER)
        week_hung_up = sum(1 for o in week_outcomes if o == 'Hung Up - No Convo')
        week_warm = sum(1 for o in week_outcomes if o in HOT_OUTCOMES)

        # --- Daily trend (last 14 days, sorted) ---
        trend = []
        for d in range(13, -1, -1):
            dt = now - timedelta(days=d)
            date_str = dt.strftime('%Y-%m-%d')
            day_label = dt.strftime('%a')
            day_short = dt.strftime('%d')
            outs = daily_data.get(date_str, [])
            day_total = len(outs)
            day_convos = sum(1 for o in outs if o in CONVO_OUTCOMES)
            trend.append({
                'date': date_str,
                'day': day_label,
                'short': day_short,
                'calls': day_total,
                'convos': day_convos,
                'rate': round(day_convos / day_total * 100) if day_total else 0,
            })

        # --- Streak (consecutive days with calls) ---
        streak = 0
        for d in range(0, 30):
            dt = now - timedelta(days=d)
            label = f"{dt.day} {dt.strftime('%B')}"
            if d == 0:
                # Today doesn't break streak if no calls yet (day not over)
                continue
            if label in date_labels and date_labels[label] in daily_data:
                streak += 1
            else:
                break

        # --- Conversation rate ---
        conv_rate = round(today_convos / today_total * 100) if today_total else 0
        week_conv_rate = round(week_convos / week_total * 100) if week_total else 0

        # --- Historical benchmarks for coaching ---
        past_7 = trend[-8:-1]  # last 7 days excluding today
        past_14 = trend[:-1]   # last 14 excluding today
        past_7_calls = [d['calls'] for d in past_7 if d['calls'] > 0]
        past_14_calls = [d['calls'] for d in past_14 if d['calls'] > 0]
        avg_7 = round(sum(past_7_calls) / len(past_7_calls)) if past_7_calls else 0
        max_7 = max(past_7_calls) if past_7_calls else 0
        avg_14 = round(sum(past_14_calls) / len(past_14_calls)) if past_14_calls else 0

        # Convo rate benchmarks
        past_7_convos = sum(d['convos'] for d in past_7)
        past_7_total = sum(d['calls'] for d in past_7)
        avg_conv_rate_7 = round(past_7_convos / past_7_total * 100) if past_7_total else 0

        # 3-day trend (yesterday, day before, today)
        trend_3 = trend[-3:]
        is_declining_3 = (len(trend_3) == 3
                         and trend_3[0]['calls'] > trend_3[1]['calls'] > trend_3[2]['calls']
                         and trend_3[0]['calls'] > 10)

        # Warm lead velocity — last 3 days vs days 4-10
        warm_last_3 = sum(
            1 for d in trend[-3:] for _ in range(d.get('calls', 0))
            if False  # placeholder, warm not in daily_data per-outcome
        )
        # Count warm from daily_data (we have outcomes there)
        warm_last_3_actual = sum(
            sum(1 for o in daily_data.get(d['date'], []) if o in HOT_OUTCOMES)
            for d in trend[-3:]
        )
        warm_last_10 = sum(
            sum(1 for o in daily_data.get(d['date'], []) if o in HOT_OUTCOMES)
            for d in trend[-11:-3] if d
        )

        # Pace + projection
        hours_elapsed = max((now.hour + now.minute / 60) - 9, 0.1)  # since 9am
        hours_left = max(18 - (now.hour + now.minute / 60), 0)  # until 6pm
        pace_per_hour = round(today_total / hours_elapsed, 1) if today_total > 0 and hours_elapsed > 0.5 else 0
        projected_eod = round(today_total + (pace_per_hour * hours_left)) if pace_per_hour > 0 else today_total

        # --- Next-level coaching nudges (specific, honest, data-driven) ---
        nudges = []

        # ACCOUNTABILITY (hard truths)
        if today_total == 0 and now.hour >= 10:
            if avg_7 > 20:
                nudges.append({'type': 'warning', 'text': f'Zero calls. It\'s {now.hour}:00. Your 7-day avg is {avg_7}. Phone up.'})
            else:
                nudges.append({'type': 'action', 'text': f'No calls yet at {now.hour}:00. First dial breaks inertia. Start now.'})
        elif today_total == 0 and now.hour < 10:
            nudges.append({'type': 'action', 'text': 'Fresh day. First call kicks it off.'})

        if is_declining_3:
            a, b, c = trend_3[0]['calls'], trend_3[1]['calls'], trend_3[2]['calls']
            nudges.append({'type': 'warning', 'text': f'3-day slide: {a} → {b} → {c}. Declining hard. What changed?'})

        # PACE + PROJECTION (forward-looking)
        if today_total > 0 and pace_per_hour > 0 and hours_left > 0.5:
            gap = DAILY_GOAL - today_total
            needed_pace = round(gap / hours_left, 1) if hours_left > 0 else 0
            if projected_eod < DAILY_GOAL * 0.6:
                nudges.append({'type': 'warning', 'text': f'Pace: {pace_per_hour}/hr. EOD projection: {projected_eod}. Need {needed_pace}/hr to hit 100. Big gap.'})
            elif projected_eod < DAILY_GOAL:
                nudges.append({'type': 'push', 'text': f'Pace: {pace_per_hour}/hr → {projected_eod} by EOD. Bump to {needed_pace}/hr for the goal.'})
            else:
                nudges.append({'type': 'win', 'text': f'On pace for {projected_eod} calls. Hold the rhythm.'})

        # COMPARISON (benchmarking)
        if today_total > 5 and avg_7 > 0:
            if today_total < avg_7 * 0.5 and now.hour >= 13:
                nudges.append({'type': 'warning', 'text': f'Today: {today_total}. 7-day avg: {avg_7}. You\'re half your pace. Why?'})
            elif today_total > max_7 and max_7 > 0:
                nudges.append({'type': 'win', 'text': f'New high: {today_total} calls beats your 7-day best ({max_7}). Lock this in.'})

        # LEARNING (pattern detection)
        if today_total >= 10 and avg_conv_rate_7 > 0:
            if conv_rate > avg_conv_rate_7 * 1.3:
                nudges.append({'type': 'win', 'text': f'Conv rate {conv_rate}% vs {avg_conv_rate_7}% avg. Note what you changed today.'})
            elif conv_rate < avg_conv_rate_7 * 0.5 and today_total >= 15:
                nudges.append({'type': 'warning', 'text': f'Conv rate {conv_rate}% vs {avg_conv_rate_7}% avg. Opener is dying. Test a new one on next 10.'})

        if warm_last_3_actual == 0 and warm_last_10 > 3 and today_total > 0:
            nudges.append({'type': 'insight', 'text': f'Zero warm leads in 3 days ({warm_last_10} in days 4-10). Pitch drifted or list went cold.'})

        if today_no_answer > 5 and today_total > 0 and (today_no_answer / today_total) > 0.75:
            pct = round(today_no_answer / today_total * 100)
            nudges.append({'type': 'insight', 'text': f'{pct}% no-answers. Wrong hour or wrong list. Switch to 10-11am or 2-4pm window.'})

        if today_hung_up >= 4 and today_total > 0 and (today_hung_up / today_total) > 0.2:
            nudges.append({'type': 'warning', 'text': f'{today_hung_up} hang-ups. Opener too salesy. Lead with name + reason, not pitch.'})

        if today_invalid > 0 and today_total > 0 and (today_invalid / today_total) > 0.2:
            pct = round(today_invalid / today_total * 100)
            nudges.append({'type': 'insight', 'text': f'{pct}% invalid numbers. Lead source quality dropping. Check where these came from.'})

        # WINS
        if today_warm > 0:
            nudges.append({'type': 'win', 'text': f'{today_warm} warm lead{"s" if today_warm > 1 else ""} today. Follow up inside 24h — goes cold fast.'})

        if today_total >= DAILY_GOAL:
            nudges.append({'type': 'win', 'text': f'Goal hit: {today_total}. Now protect the warm leads. Draft follow-ups.'})

        if streak >= 3:
            nudges.append({'type': 'win', 'text': f'{streak}-day calling streak. Don\'t break it.'})

        # Best day this week
        best_day = max(trend[-7:], key=lambda x: x['calls']) if trend else None

        payload = {
            'ok': True,
            'goal': DAILY_GOAL,
            'today': {
                'total': today_total,
                'no_answer': today_no_answer,
                'hung_up': today_hung_up,
                'not_interested': today_not_interested,
                'invalid': today_invalid,
                'callback': today_callback,
                'email': today_email,
                'warm': today_warm,
                'meeting': today_meeting,
                'convos': today_convos,
                'conv_rate': conv_rate,
            },
            'week': {
                'total': week_total,
                'convos': week_convos,
                'no_answer': week_no_answer,
                'hung_up': week_hung_up,
                'warm': week_warm,
                'conv_rate': week_conv_rate,
            },
            'alltime': {
                'called': total_called,
                'uncalled': total_uncalled,
            },
            'trend': trend,
            'streak': streak,
            'best_day': best_day,
            'nudges': nudges,
            'benchmarks': {
                'avg_7': avg_7,
                'max_7': max_7,
                'avg_conv_rate_7': avg_conv_rate_7,
                'pace_per_hour': pace_per_hour,
                'projected_eod': projected_eod,
            },
        }
        _outreach_cache['data'] = payload
        _outreach_cache['time'] = time.time()
        return jsonify(payload)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# --- Claude Coach's Take (cached 15 min) ---
_coach_cache = {'data': None, 'time': 0, 'date': None, 'total': 0}
COACH_SYSTEM_PROMPT = """You are Allen's direct, no-fluff cold calling coach. He's a reformed EPS sales manager building an AI consultancy. He wants honest coaching, not pep talks.

Given today's stats and recent trend, write ONE paragraph (max 3 sentences):
1. What's actually happening right now (use the numbers)
2. What he's doing wrong OR what's working (be specific)
3. ONE specific thing to change in the next hour

Tone: direct, specific, honest. No "great job" unless earned. Use numbers. Never generic.

Examples of good coaching:
- "Pace dropped from 75 Tuesday to 11 today. Not a dip — a collapse. Stop scrolling, pick up the phone for 90 minutes straight."
- "9% conv rate with only 11 dials is too small to panic over. But zero warm leads in 3 days means your opener is dying. Test a new one on the next 10 calls."
- "75 calls is your third-best day this month. But conv rate dropped to 4% — you're dialing for dialing's sake. Slow down by 20%, listen more, pitch less."

Bad coaching (never do):
- "Keep pushing! You've got this!"
- "Every call matters."
- Generic platitudes or motivational speak.

Return only the paragraph. No greeting, no signoff."""


@command_bp.route('/api/coach/daily')
def coach_daily():
    """One-paragraph honest coaching from Claude based on today's outreach data."""
    try:
        import anthropic
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        today_str = today_ph()

        # Fetch current stats (internal call)
        from flask import current_app
        with current_app.test_client() as client:
            # Pass auth header
            token = get_anthropic_key()  # reuse for internal
            auth_token = request.headers.get('X-Token', '')
            resp = client.get('/api/outreach/detailed', headers={'X-Token': auth_token})
            if resp.status_code != 200:
                return jsonify({'ok': False, 'error': 'Stats fetch failed'}), 500
            stats = resp.get_json()

        today = stats.get('today', {})
        bench = stats.get('benchmarks', {})
        trend = stats.get('trend', [])
        today_total = today.get('total', 0)

        # Cache check: same date + total hasn't moved >20 + within 15 min
        now_ts = time.time()
        if (_coach_cache['data']
                and _coach_cache['date'] == today_str
                and abs(_coach_cache['total'] - today_total) < 20
                and (now_ts - _coach_cache['time']) < 900):
            return jsonify({'ok': True, 'text': _coach_cache['data'], 'cached': True})

        # Build compact context for Claude
        last_7 = trend[-8:-1]
        context = f"""Today ({today_str}):
- Calls: {today_total} / goal 100
- Convos: {today.get('convos', 0)} ({today.get('conv_rate', 0)}% rate)
- Breakdown: {today.get('no_answer', 0)} no-answer, {today.get('hung_up', 0)} hung up, {today.get('not_interested', 0)} not interested, {today.get('invalid', 0)} invalid, {today.get('warm', 0)} warm, {today.get('callback', 0)} callback, {today.get('email', 0)} asked for email, {today.get('meeting', 0)} meeting booked
- Pace: {bench.get('pace_per_hour', 0)}/hr, projected EOD: {bench.get('projected_eod', 0)}

Last 7 days:
- Avg: {bench.get('avg_7', 0)} calls/day
- Best: {bench.get('max_7', 0)}
- Avg conv rate: {bench.get('avg_conv_rate_7', 0)}%
- Daily: {', '.join(f"{d['day']}:{d['calls']}" for d in last_7)}

Streak: {stats.get('streak', 0)} days
"""

        client = anthropic.Anthropic(api_key=get_anthropic_key())
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            system=COACH_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': context}],
        )
        coach_text = ''.join(b.text for b in msg.content if b.type == 'text').strip()

        _coach_cache.update({
            'data': coach_text, 'time': now_ts,
            'date': today_str, 'total': today_total,
        })
        return jsonify({'ok': True, 'text': coach_text, 'cached': False})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


SYSTEM_PROMPT = """You are Allen's executive assistant — Enriquez OS.
Two domains: EPS (painting & cleaning company, Brisbane AU) and Personal (AI consultancy).

Project root: /Users/allenenriquez/Desktop/Allen Enriquez/

## Rules
- **Bias to action.** Do the thing first, report after. Don't ask clarifying questions unless truly ambiguous.
- Be concise — mobile chat. Short answers. 1-2 sentences max when reporting results.
- If Allen says "send an email to X saying Y" — draft it, show it in 2 lines, and ask "Send?" That's it. Don't ask for subject line, formatting preferences, or tone. Pick sensible defaults.
- If Allen gives you enough info to act, ACT. Fill in reasonable defaults for anything missing (subject lines, greetings, sign-offs).
- Show email drafts before sending, but keep the preview SHORT — just the key content, not a full formatted display.
- Simple English. 3rd-5th grade reading level for client copy.
- EPS email: sales@epsolution.com.au. Personal: allenenriquez006@gmail.com.
- Never fabricate data — always fetch from tools.
- For shell tools, working dir is project root. Key scripts in tools/*.py.
- When using tools, chain them without stopping to narrate each step. Get the data, do the thing, report the result.
"""

# Conversation memory per session (resets on server restart)
_conversations: dict[str, list] = {}

MAX_TOOL_ROUNDS = 10
MAX_HISTORY_MESSAGES = 20  # Keep last N messages to avoid token bloat
MAX_TOOL_RESULT_CHARS = 3000  # Truncate individual tool results
RETRY_ATTEMPTS = 2
RETRY_DELAY = 3  # seconds


def _sanitize_history(messages):
    """Remove orphaned tool_use blocks from conversation history.

    The Anthropic API requires every assistant tool_use block to be followed
    by a user message containing the matching tool_result. If a conversation
    ended with unresolved tool_use (e.g. stop_reason was end_turn but content
    had tool_use blocks), the next user message would break the chain.
    Strip tool_use blocks from the last assistant message if they have no
    corresponding tool_results.
    """
    if len(messages) < 2:
        return

    # Check if the second-to-last message is assistant with tool_use
    # and the last message is a plain user message (not tool_results)
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get('role') != 'assistant':
            continue
        content = msg.get('content', [])
        if not isinstance(content, list):
            break

        has_tool_use = any(
            (getattr(b, 'type', None) == 'tool_use' if hasattr(b, 'type') else
             isinstance(b, dict) and b.get('type') == 'tool_use')
            for b in content
        )
        if not has_tool_use:
            break

        # Check if next message has matching tool_results
        if i + 1 < len(messages):
            next_msg = messages[i + 1]
            next_content = next_msg.get('content', [])
            has_results = (
                isinstance(next_content, list)
                and any(
                    (isinstance(b, dict) and b.get('type') == 'tool_result')
                    for b in next_content
                )
            )
            if has_results:
                break  # properly paired, no fix needed

        # Strip tool_use blocks, keep only text
        cleaned = [
            b for b in content
            if (getattr(b, 'type', None) == 'text' if hasattr(b, 'type') else
                isinstance(b, dict) and b.get('type') == 'text')
        ]
        if cleaned:
            msg['content'] = cleaned
        else:
            # No text blocks at all — remove the message
            messages.pop(i)
        break


def _trim_history(messages):
    """Keep only the last MAX_HISTORY_MESSAGES messages to control token usage.

    Preserves tool_use/tool_result pairing — never splits a pair.
    """
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return

    # Find a safe cut point — don't split tool_use/tool_result pairs
    cut = len(messages) - MAX_HISTORY_MESSAGES
    # Walk forward from the cut point to avoid orphaning tool results
    while cut < len(messages):
        msg = messages[cut]
        content = msg.get('content', [])
        # If this is a tool_result message, we need the assistant message before it
        if (isinstance(content, list)
                and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content)):
            cut -= 1  # include the preceding assistant tool_use message
            break
        # If this is an assistant message with tool_use, include the next tool_result too
        if msg.get('role') == 'assistant' and isinstance(content, list):
            has_tool = any(
                (getattr(b, 'type', None) == 'tool_use' if hasattr(b, 'type') else
                 isinstance(b, dict) and b.get('type') == 'tool_use')
                for b in content
            )
            if has_tool:
                cut -= 1  # back up so the pair stays together
                break
        break

    if cut > 0:
        del messages[:cut]


def _truncate_result(result_str):
    """Truncate tool result strings to MAX_TOOL_RESULT_CHARS."""
    if len(result_str) <= MAX_TOOL_RESULT_CHARS:
        return result_str
    return result_str[:MAX_TOOL_RESULT_CHARS] + '...(truncated)'


def _call_claude(client, tools, messages):
    """Call Claude API with retry on 429 rate limit errors."""
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            return client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
        except anthropic.RateLimitError:
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


@command_bp.route('/api/claude/message', methods=['POST'])
def claude_message():
    """Send a message to Claude, with agentic tool-use loop."""
    data = request.json
    message = data.get('message', '').strip()
    conv_id = data.get('conversation_id', 'default')

    if not message:
        return jsonify({'ok': False, 'error': 'Empty message'}), 400

    try:
        client = anthropic.Anthropic(api_key=get_anthropic_key())
        tools = get_tool_schemas()

        # Build or continue conversation
        messages = _conversations.setdefault(conv_id, [])

        # Fix any orphaned tool_use blocks before adding new user message
        _sanitize_history(messages)

        # Trim old messages to stay under token limits
        _trim_history(messages)

        messages.append({'role': 'user', 'content': message})

        # Agentic loop — call Claude, execute tools, repeat
        for _ in range(MAX_TOOL_ROUNDS):
            response = _call_claude(client, tools, messages)

            # Check if response contains tool_use blocks
            tool_use_blocks = [b for b in response.content if b.type == 'tool_use']

            if tool_use_blocks:
                # Execute each tool call
                messages.append({'role': 'assistant', 'content': response.content})
                tool_results = []
                for block in tool_use_blocks:
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        'type': 'tool_result',
                        'tool_use_id': block.id,
                        'content': _truncate_result(json.dumps(result)),
                    })
                messages.append({'role': 'user', 'content': tool_results})
            else:
                # No tool use — extract text and return
                text = ''.join(
                    block.text for block in response.content
                    if block.type == 'text'
                )
                messages.append({'role': 'assistant', 'content': response.content})
                return jsonify({'ok': True, 'response': text or 'Done.'})

        # Hit max rounds — return whatever text we have
        return jsonify({'ok': True, 'response': 'Reached maximum tool rounds. Please try a simpler request.'})

    except anthropic.RateLimitError:
        return jsonify({'ok': False, 'error': 'Rate limited — too many requests. Try again in a minute.'}), 429
    except anthropic.APIError as e:
        return jsonify({'ok': False, 'error': f'Claude API error: {e.message}'}), 502
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@command_bp.route('/api/claude/clear', methods=['POST'])
def claude_clear():
    """Clear conversation history."""
    conv_id = request.json.get('conversation_id', 'default') if request.json else 'default'
    _conversations.pop(conv_id, None)
    return jsonify({'ok': True})
