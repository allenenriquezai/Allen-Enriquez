"""
Brief routes — live briefing data for EPS, Personal CRM, and AI Learning.

Optimizations:
- Stale-while-revalidate: always returns cached data instantly, refreshes in background
- Learn: persisted to disk, manual advance only (no auto-cycle)
- Pre-warm cache on init
"""

import json
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import now_ph, today_ph

brief_bp = Blueprint('brief', __name__)

# Add tools/ to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

_sheets_service = None
CRM_SHEET_ID = '1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8'
TMP_DIR = Path(__file__).parent.parent.parent / '.tmp'
LEARN_STATE_FILE = TMP_DIR / 'learning_state.json'

# --- Response cache (stale-while-revalidate + disk persistence) ---
_brief_cache: dict[str, dict] = {}
BRIEF_CACHE_TTL = 300  # 5 min — return fresh within this window
_refreshing: set[str] = set()  # sections currently being refreshed
DISK_CACHE_DIR = TMP_DIR / 'brief_cache'


def _disk_cache_path(section: str) -> Path:
    return DISK_CACHE_DIR / f'{section}.json'


def _load_disk_cache(section: str):
    """Load cached data from disk. Returns dict or None."""
    path = _disk_cache_path(section)
    if path.exists():
        try:
            entry = json.loads(path.read_text())
            return entry
        except (json.JSONDecodeError, IOError):
            pass
    return None


def _save_disk_cache(section: str, data: dict, ts: float):
    """Persist cache entry to disk for cold-start recovery."""
    DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _disk_cache_path(section).write_text(
            json.dumps({'data': data, 'ts': ts}, default=str)
        )
    except IOError:
        pass


def _cached(section: str):
    """Return cached response if it exists (fresh or stale). None only if never fetched."""
    entry = _brief_cache.get(section)
    if entry:
        return entry['data']
    # Cold start: try disk
    disk = _load_disk_cache(section)
    if disk:
        _brief_cache[section] = disk
        return disk['data']
    return None


def _is_stale(section: str) -> bool:
    """Check if cache entry is stale (older than TTL)."""
    entry = _brief_cache.get(section)
    if not entry:
        return True
    return (time.time() - entry['ts']) >= BRIEF_CACHE_TTL


def _set_cache(section: str, data: dict):
    ts = time.time()
    _brief_cache[section] = {'data': data, 'ts': ts}
    _save_disk_cache(section, data, ts)


def _refresh_in_background(section: str, fetch_fn):
    """Kick off a background thread to refresh a section if not already refreshing."""
    if section in _refreshing:
        return
    _refreshing.add(section)

    def _do_refresh():
        try:
            data = fetch_fn()
            if data:
                _set_cache(section, data)
        except Exception:
            traceback.print_exc()
        finally:
            _refreshing.discard(section)

    t = threading.Thread(target=_do_refresh, daemon=True)
    t.start()


def init_brief(sheets_service):
    global _sheets_service
    _sheets_service = sheets_service


def warm_cache():
    """Pre-warm all brief caches on startup. Call from app.py after init."""
    def _warm():
        try:
            data = _fetch_eps()
            if data:
                _set_cache('eps', data)
            print("  [warm] EPS brief cached")
        except Exception:
            print("  [warm] EPS brief failed")

        try:
            data = _fetch_personal()
            if data:
                _set_cache('personal', data)
            print("  [warm] Personal brief cached")
        except Exception:
            print("  [warm] Personal brief failed")

        try:
            data = _fetch_learning()
            if data:
                _set_cache('learning', data)
            print("  [warm] Learning cached")
        except Exception:
            print("  [warm] Learning failed")

    t = threading.Thread(target=_warm, daemon=True)
    t.start()


def _svc():
    global _sheets_service
    if _sheets_service is None:
        from personal_crm import get_sheets_service
        _sheets_service = get_sheets_service()
    return _sheets_service


# ============================================================
# EPS Brief — Pipedrive pipeline + activities + emails
# ============================================================

def _fetch_eps():
    """Fetch EPS brief data from Pipedrive. Returns dict or None."""
    from crm_monitor import run_monitor, load_env
    from crm_monitor import (EXEC_ACTIVITY_TYPES, OPERATIONAL_ACTIVITY_TYPES,
                             ACTIVITY_TYPE_NAMES, DISCOVERY_TYPES,
                             CLEAN_FOLLOWUP_TYPES, PAINT_FOLLOWUP_TYPES,
                             VIP_TYPES)

    import os as _os
    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY') or _os.environ.get('PIPEDRIVE_API_KEY', '')
    domain = env.get('PIPEDRIVE_COMPANY_DOMAIN') or _os.environ.get('PIPEDRIVE_COMPANY_DOMAIN', '')

    if not api_key or not domain:
        return None

    crm_data = run_monitor(api_key=api_key, domain=domain, dry_run=True)

    kpis = crm_data.get('kpis', {})
    stats = {
        'pipeline_deals': kpis.get('pipeline_deals', 0),
        'pipeline_value': kpis.get('pipeline_value', 0),
        'won_week': kpis.get('deals_won_week', 0),
        'won_value_week': kpis.get('won_value_week', 0),
        'yesterday_cold_calls': crm_data.get('yesterday_cold_calls', 0),
        'yesterday_total_calls': crm_data.get('yesterday_total_calls', 0),
        'calls_this_week': kpis.get('calls_this_week', 0),
    }

    todays = crm_data.get('todays_activities', [])
    overdue = crm_data.get('overdue_activities_allen', [])
    all_due = todays + overdue
    today_str = today_ph()

    _tier_order = {t: 0 for t in DISCOVERY_TYPES}
    _tier_order.update({t: 1 for t in CLEAN_FOLLOWUP_TYPES})
    _tier_order.update({t: 2 for t in PAINT_FOLLOWUP_TYPES})
    _tier_order.update({t: 3 for t in VIP_TYPES})

    tier1 = sorted(
        [a for a in all_due if a.get('type') in EXEC_ACTIVITY_TYPES],
        key=lambda a: (_tier_order.get(a.get('type', ''), 9), a.get('due_time') or 'zz')
    )
    tier2 = [a for a in all_due if a.get('type') in OPERATIONAL_ACTIVITY_TYPES]
    tier_other = [a for a in all_due
                  if a.get('type') not in EXEC_ACTIVITY_TYPES
                  and a.get('type') not in OPERATIONAL_ACTIVITY_TYPES]

    def format_activity(act):
        label = ACTIVITY_TYPE_NAMES.get(act.get('type', ''), act.get('type', ''))
        due_date = act.get('due_date', '')
        is_overdue = due_date and due_date < today_str
        return {
            'id': act.get('id', ''),
            'label': label,
            'subject': act.get('subject', ''),
            'deal_title': act.get('deal_title', ''),
            'deal_id': act.get('deal_id', ''),
            'due_date': due_date,
            'due_time': (act.get('due_time') or '')[:5],
            'done': act.get('done', False),
            'overdue': is_overdue,
        }

    activities = {
        'tier1': [format_activity(a) for a in tier1],
        'tier2': [format_activity(a) for a in tier2],
        'other': [format_activity(a) for a in tier_other],
    }

    action_items = crm_data.get('action_items', [])
    priority_order = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    action_items.sort(key=lambda x: priority_order.get(x['priority'], 4))

    ai_chase_stages = {'QUOTE SENT', 'LATE FOLLOW UP', 'NEGOTIATION / FOLLOW UP'}
    ai_chase_actions = {'email', 'call_then_email'}

    allens_plate = []
    ai_can_handle = []
    for item in action_items:
        entry = {
            'deal_id': item.get('deal_id', ''),
            'deal_title': item.get('deal_title', ''),
            'person_name': item.get('person_name', ''),
            'pipeline': item.get('pipeline', ''),
            'stage': item.get('stage', ''),
            'priority': item.get('priority', 'LOW'),
            'type': item.get('type', ''),
            'value': item.get('value', 0),
            'days_since_activity': item.get('days_since_activity', 0),
            'recommended_action': item.get('recommended_action', ''),
        }
        if (item['type'] == 'follow_up'
                and item.get('stage') in ai_chase_stages
                and item.get('recommended_action') in ai_chase_actions):
            ai_can_handle.append(entry)
        elif item['type'] != 'stale_deal':
            allens_plate.append(entry)

    stale = [
        {
            'deal_id': i.get('deal_id', ''),
            'deal_title': i.get('deal_title', ''),
            'pipeline': i.get('pipeline', ''),
            'stage': i.get('stage', ''),
            'days_since_activity': i.get('days_since_activity', 0),
        }
        for i in action_items if i['type'] == 'stale_deal'
    ]

    return {
        'ok': True,
        'stats': stats,
        'activities': activities,
        'allens_plate': allens_plate,
        'ai_can_handle': ai_can_handle,
        'stale_deals': stale,
        'updated': now_ph().strftime('%H:%M'),
    }


@brief_bp.route('/api/brief/eps')
def brief_eps():
    """EPS briefing — returns cached data instantly, refreshes in background if stale."""
    cached = _cached('eps')
    if _is_stale('eps'):
        _refresh_in_background('eps', _fetch_eps)
    if cached:
        return jsonify(cached)
    # First load ever — must wait
    try:
        data = _fetch_eps()
        if data:
            _set_cache('eps', data)
            return jsonify(data)
        return jsonify({'ok': False, 'error': 'Failed to fetch EPS data'}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# Personal Brief — CRM leads status
# ============================================================

def _fetch_personal():
    """Fetch personal CRM brief data from Google Sheets. Returns dict or None."""
    from personal_crm import (
        ALL_TABS, HOT_OUTCOMES, ACTION_OUTCOMES, CALLBACK_OUTCOMES,
        classify_lead, get_cell, parse_row,
    )

    service = _svc()
    meta = service.spreadsheets().get(spreadsheetId=CRM_SHEET_ID).execute()
    existing_tabs = {s['properties']['title'] for s in meta['sheets']}
    today = today_ph()

    total_leads = 0
    by_status = {}
    hot_leads = []
    callbacks_due = []
    emails_to_draft = []
    follow_ups = []
    no_answers = []

    for tab in ALL_TABS:
        if tab not in existing_tabs:
            continue
        tab_res = service.spreadsheets().values().get(
            spreadsheetId=CRM_SHEET_ID, range=f"'{tab}'"
        ).execute()
        rows = tab_res.get('values', [])
        if not rows:
            continue
        headers = rows[0]
        col_map = {h: i for i, h in enumerate(headers)}
        tab_count = 0

        for i, row in enumerate(rows[1:], start=2):
            lead = parse_row(row, col_map, tab, i)
            if not lead:
                continue
            total_leads += 1
            tab_count += 1
            lead_type, priority = classify_lead(lead)

            entry = {
                'business_name': lead['business_name'],
                'decision_maker': lead.get('decision_maker', ''),
                'call_outcome': lead['call_outcome'],
                'follow_up_date': lead.get('follow_up_date', ''),
                'date_called': lead.get('date_called', ''),
                'notes': lead.get('notes_truncated', ''),
                'tab': tab.split(' | ')[-1] if ' | ' in tab else tab,
                'group': tab.split(' | ')[0] if ' | ' in tab else '',
                'priority': priority,
                'email': lead.get('email', ''),
                'phone': lead.get('phone', ''),
            }

            if lead_type == 'hot_lead':
                entry['overdue'] = bool(
                    lead.get('follow_up_date') and lead['follow_up_date'] <= today
                )
                hot_leads.append(entry)
            elif lead_type == 'email_needed':
                emails_to_draft.append(entry)
            elif lead_type == 'callback':
                is_due = lead.get('follow_up_date') and lead['follow_up_date'] <= today
                entry['overdue'] = bool(is_due)
                if is_due:
                    callbacks_due.append(entry)
                else:
                    follow_ups.append(entry)
            elif lead_type == 'follow_up':
                follow_ups.append(entry)
            elif lead_type == 'no_answer' and lead['call_outcome'] in (
                'No Answer 1', 'No Answer 2',
            ):
                no_answers.append(entry)

        by_status[tab] = tab_count

    prio = {'URGENT': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    hot_leads.sort(key=lambda x: prio.get(x['priority'], 4))
    callbacks_due.sort(key=lambda x: x.get('follow_up_date') or 'zz')
    emails_to_draft.sort(key=lambda x: x.get('date_called') or 'zz')

    return {
        'ok': True,
        'stats': {
            'total_leads': total_leads,
            'hot': len(hot_leads),
            'callbacks_due': len(callbacks_due),
            'emails_to_draft': len(emails_to_draft),
            'follow_ups': len(follow_ups),
        },
        'hot_leads': hot_leads[:10],
        'callbacks_due': callbacks_due[:10],
        'emails_to_draft': emails_to_draft[:10],
        'follow_ups': follow_ups[:10],
        'no_answers': no_answers[:10],
        'by_status': by_status,
        'updated': now_ph().strftime('%H:%M'),
    }


@brief_bp.route('/api/brief/personal')
def brief_personal():
    """Personal CRM — returns cached data instantly, refreshes in background if stale."""
    cached = _cached('personal')
    if _is_stale('personal'):
        _refresh_in_background('personal', _fetch_personal)
    if cached:
        return jsonify(cached)
    # First load ever
    try:
        data = _fetch_personal()
        if data:
            _set_cache('personal', data)
            return jsonify(data)
        return jsonify({'ok': False, 'error': 'Failed to fetch personal data'}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# AI Learning — persisted to disk, manual advance only
# ============================================================

def _load_learn_state():
    """Load learning state from disk. Returns dict or None."""
    if LEARN_STATE_FILE.exists():
        try:
            return json.loads(LEARN_STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return None


def _save_learn_state(state):
    """Save learning state to disk."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    LEARN_STATE_FILE.write_text(json.dumps(state, indent=2))


def _generate_lesson(lesson_index):
    """Generate lesson content for a given index. Returns full state dict."""
    from ai_learning_brief import (
        CURRICULUM, EXPERTS,
        search_articles, fetch_page_text, call_claude,
    )

    total_lessons = sum(len(w['lessons']) for w in CURRICULUM)
    idx = lesson_index % total_lessons

    count = 0
    lesson_data = None
    for week in CURRICULUM:
        for i, lesson in enumerate(week['lessons']):
            if count == idx:
                lesson_data = {
                    'title': lesson['title'],
                    'week': week['week'],
                    'theme': week['theme'],
                    'day_in_week': i + 1,
                    'week_label': f"Week {week['week']}: {week['theme']} — Day {i + 1}/7",
                    'progress': f"Lesson {lesson_index + 1} of {total_lessons}",
                    'query': lesson['query'],
                }
                break
            count += 1
        if lesson_data:
            break

    if not lesson_data:
        lesson_data = {'title': 'Rest Day', 'week_label': '', 'progress': ''}

    # Fetch articles
    articles = []
    if lesson_data.get('query'):
        articles = search_articles(lesson_data['query'], max_results=5)

    article_list = [
        {'title': a['title'], 'snippet': a['snippet'], 'url': a['url']}
        for a in articles
    ]

    # Pre-generate summaries for all articles
    summaries = {}
    for a in article_list:
        try:
            page_text = fetch_page_text(a['url'], max_chars=3000)
            if page_text:
                prompt = (
                    f'Summarize this article about "{a["title"]}" for someone with zero tech background.\n'
                    f'Write like you are explaining to a 10 year old. Use the simplest words possible.\n'
                    f'No jargon. No big words. If you must use a technical term, explain it in the same sentence.\n\n'
                    f'Return EXACTLY this format:\n\n'
                    f'BULLETS:\n- [3-4 key takeaway bullet points]\n\n'
                    f'ACTION:\n- [1-2 things the reader can try today]\n\n'
                    f'Keep each bullet under 20 words. Be specific, not vague.\n\n'
                    f'ARTICLE TEXT:\n{page_text}'
                )
                summary = call_claude(prompt, max_tokens=400)
                if summary:
                    summaries[a['url']] = summary
        except Exception:
            pass

    lesson_data['articles'] = article_list

    # Expert digest
    expert_digest = []
    for expert in EXPERTS:
        expert_articles = search_articles(expert['query'], max_results=2)
        expert_digest.append({
            'name': expert['name'],
            'articles': [
                {'title': a['title'], 'snippet': a['snippet'], 'url': a['url']}
                for a in expert_articles
            ],
        })

    state = {
        'lesson_index': lesson_index,
        'generated_at': now_ph().isoformat(),
        'lesson': lesson_data,
        'experts': expert_digest,
        'summaries': summaries,
    }
    _save_learn_state(state)
    return state


def _fetch_learning():
    """Load learning data — from disk if available, else generate fresh."""
    state = _load_learn_state()
    if state and state.get('lesson'):
        return {
            'ok': True,
            'lesson': state['lesson'],
            'experts': state.get('experts', []),
            'summaries': state.get('summaries', {}),
            'updated': state.get('generated_at', '')[:16].replace('T', ' '),
        }
    # First time — generate lesson 0
    state = _generate_lesson(0)
    return {
        'ok': True,
        'lesson': state['lesson'],
        'experts': state.get('experts', []),
        'summaries': state.get('summaries', {}),
        'updated': state.get('generated_at', '')[:16].replace('T', ' '),
    }


@brief_bp.route('/api/brief/learning')
def brief_learning():
    """Today's AI learning lesson — served from disk, instant load."""
    cached = _cached('learning')
    if cached:
        return jsonify(cached)
    try:
        data = _fetch_learning()
        if data:
            _set_cache('learning', data)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@brief_bp.route('/api/learn/next', methods=['POST'])
def learn_next():
    """Advance to the next lesson. Generates content in background, returns immediately."""
    state = _load_learn_state()
    current_index = state['lesson_index'] if state else -1
    next_index = current_index + 1

    # Clear cache so next load picks up new data
    _brief_cache.pop('learning', None)

    def _gen():
        try:
            new_state = _generate_lesson(next_index)
            result = {
                'ok': True,
                'lesson': new_state['lesson'],
                'experts': new_state.get('experts', []),
                'summaries': new_state.get('summaries', {}),
                'updated': new_state.get('generated_at', '')[:16].replace('T', ' '),
            }
            _set_cache('learning', result)
            print(f"  [learn] Generated lesson {next_index}")
        except Exception:
            traceback.print_exc()

    t = threading.Thread(target=_gen, daemon=True)
    t.start()

    return jsonify({'ok': True, 'generating': True, 'lesson_index': next_index})


# ============================================================
# Learn — per-article Claude summarization (pre-cached)
# ============================================================

@brief_bp.route('/api/learn/summarize', methods=['POST'])
def learn_summarize():
    """Return pre-cached summary from learn state, or generate on demand."""
    data = request.json or {}
    url = data.get('url', '')

    if not url:
        return jsonify({'ok': False, 'error': 'Missing url'}), 400

    # Check disk state for pre-cached summary
    state = _load_learn_state()
    if state and state.get('summaries', {}).get(url):
        return jsonify({'ok': True, 'summary': state['summaries'][url], 'url': url})

    # Check memory cache
    cache_key = f"learn_summary:{url}"
    cached = _cached(cache_key)
    if cached:
        return jsonify(cached)

    # Fallback: generate on demand
    try:
        from ai_learning_brief import fetch_page_text, call_claude

        title = data.get('title', '')
        page_text = fetch_page_text(url, max_chars=3000)
        if not page_text:
            return jsonify({'ok': True, 'summary': None, 'reason': 'Could not fetch page'})

        prompt = (
            f'Summarize this article about "{title}" for someone with zero tech background.\n'
            f'Write like you are explaining to a 10 year old. Use the simplest words possible.\n'
            f'No jargon. No big words. If you must use a technical term, explain it in the same sentence.\n\n'
            f'Return EXACTLY this format:\n\n'
            f'BULLETS:\n- [3-4 key takeaway bullet points]\n\n'
            f'ACTION:\n- [1-2 things the reader can try today]\n\n'
            f'Keep each bullet under 20 words. Be specific, not vague.\n\n'
            f'ARTICLE TEXT:\n{page_text}'
        )

        result_text = call_claude(prompt, max_tokens=400)
        if not result_text:
            return jsonify({'ok': True, 'summary': None, 'reason': 'Claude unavailable'})

        result = {'ok': True, 'summary': result_text, 'url': url}
        _set_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500
