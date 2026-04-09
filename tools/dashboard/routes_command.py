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

        # --- Checklist completion ---
        try:
            config_res = service.spreadsheets().values().get(
                spreadsheetId=_dashboard_sheet_id,
                range="'Checklist Config'"
            ).execute()
            config_all = config_res.get('values', [])
            if config_all:
                headers = config_all[0]
                col = {h: i for i, h in enumerate(headers)}
                active_idx = col.get('Active', 99)
                active_items = [
                    r for r in config_all[1:]
                    if (r[active_idx] if active_idx < len(r) else 'TRUE').upper() == 'TRUE'
                ]
            else:
                active_items = []
            total_items = len(active_items)

            log_res = service.spreadsheets().values().get(
                spreadsheetId=_dashboard_sheet_id,
                range="'Checklist Log'"
            ).execute()
            log_rows = log_res.get('values', [])[1:]
            today_done = set()
            for row in log_rows:
                if len(row) >= 3 and row[0] == today:
                    val = row[2] if len(row) > 2 else ''
                    if val and val != '0' and val.upper() != 'FALSE':
                        today_done.add(row[1])

            done_count = len(today_done)
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

        # --- Personal CRM outreach (Google Sheets) ---
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from personal_crm import (
                ALL_TABS, HOT_OUTCOMES, parse_row,
            )

            CONNECTED_OUTCOMES = {
                'Warm Interest', 'Meeting Booked', 'Call Back',
                'Asked For Email', 'Late Follow Up', 'Not Interested - Convo',
            }

            now = now_ph()
            today_label = f"{now.day} {now.strftime('%B')}"
            # Build set of date labels for this week (Mon–Sun)
            week_start = now - timedelta(days=now.weekday())
            week_labels = set()
            for d in range(7):
                dt = week_start + timedelta(days=d)
                week_labels.add(f"{dt.day} {dt.strftime('%B')}")

            meta = service.spreadsheets().get(spreadsheetId=CRM_SHEET_ID).execute()
            existing_tabs = {s['properties']['title'] for s in meta['sheets']}

            p_today = {'calls': 0, 'connected': 0, 'warm': 0}
            p_week = {'calls': 0, 'connected': 0, 'warm': 0}

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

                for i, row in enumerate(rows[1:], start=2):
                    lead = parse_row(row, col_map, tab, i)
                    if not lead:
                        continue
                    outcome = lead.get('call_outcome', '') or ''
                    dc = (lead.get('date_called', '') or '').strip()
                    if not dc:
                        continue

                    is_today = (dc == today_label)
                    is_week = (dc in week_labels)

                    if is_today:
                        p_today['calls'] += 1
                        if outcome in CONNECTED_OUTCOMES:
                            p_today['connected'] += 1
                        if outcome in HOT_OUTCOMES:
                            p_today['warm'] += 1
                    if is_week:
                        p_week['calls'] += 1
                        if outcome in CONNECTED_OUTCOMES:
                            p_week['connected'] += 1
                        if outcome in HOT_OUTCOMES:
                            p_week['warm'] += 1

            result['personal_outreach'] = {'today': p_today, 'week': p_week}
        except Exception:
            result['personal_outreach'] = {
                'today': {'calls': 0, 'connected': 0, 'warm': 0},
                'week': {'calls': 0, 'connected': 0, 'warm': 0},
            }

        # --- EPS outreach (Pipedrive activities) ---
        try:
            from crm_monitor import fetch_activities, COLD_ACTIVITY_PREFIX

            creds = get_pipedrive_creds()
            now = now_ph()
            today_str = now.strftime('%Y-%m-%d')
            week_start_str = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')

            activities = fetch_activities(
                api_key=creds['api_key'], domain=creds['domain'],
                start_date=week_start_str, done=True,
            )

            # "Connected" for EPS = activity marked done + type contains 'call' + has a deal
            # "Warm" = deal moved to warm stages (approximate: activity note contains interest signals)
            # Simpler: count call activities done today vs this week
            e_today = {'calls': 0, 'connected': 0, 'warm': 0}
            e_week = {'calls': 0, 'connected': 0, 'warm': 0}

            CALL_TYPES = {'call', 'cold__call', 'cold__paint_call', 'cold__clean_call'}

            for act in activities:
                act_type = (act.get('type') or '').lower()
                due_date = act.get('due_date', '')
                is_call = ('call' in act_type or act_type.startswith('cold__'))

                if not is_call:
                    continue

                # This week (all fetched activities are this week)
                e_week['calls'] += 1

                # Today
                if due_date == today_str:
                    e_today['calls'] += 1

            result['eps_outreach'] = {'today': e_today, 'week': e_week}
        except Exception:
            result['eps_outreach'] = {
                'today': {'calls': 0, 'connected': 0, 'warm': 0},
                'week': {'calls': 0, 'connected': 0, 'warm': 0},
            }

        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


SYSTEM_PROMPT = """You are Allen's executive assistant and orchestrator — the Enriquez OS.
You manage Allen's day-to-day across two domains: EPS (day job — painting & cleaning company, Brisbane AU) and Personal (AI automation consultancy, personal life).

PROJECT ROOT: /Users/allenenriquez/Desktop/Allen Enriquez/

## Your Tools (Direct)
- Pipedrive CRM: search deals, get details, post notes, send EPS emails (sales@epsolution.com.au)
- Personal Gmail: read/send from allenenriquez006@gmail.com
- Personal CRM: Google Sheets with leads, callbacks, follow-ups
- Habit checklist: read today's completion status
- Shell commands: run any tool, script, or command on Allen's machine
- File reader: read any project file

## Tools You Can Run via Shell (tools/*.py)
- morning_briefing.py — daily briefing (pipeline + emails + action items)
- ai_learning_brief.py — AI curriculum + article digest
- calculate_quote.py — pricing engine for EPS quotes
- qa_quote.py — QA checker for quotes
- fetch_call_transcript.py — get JustCall transcript for a deal
- process_cold_calls.py — batch format/post cold lead notes
- draft_follow_up_email.py — template-based follow-up drafts
- personal_crm.py — full CRM operations (report, draft, cleanup)
- research_prospect.py — research a prospect before a call
- generate_content.py — content engine for personal brand
- send_personal_email.py — CLI for personal Gmail
- send_email_gmail.py — CLI for EPS Gmail
- crm_monitor.py — Pipedrive pipeline monitor
- deal_context.py — pull full deal context from Pipedrive
- create_sm8_deposit.py / push_sm8_job.py — ServiceM8 operations

## Workflows (SOPs in projects/*/workflows/)
- EPS: create-quote.md, calculate-line-items.md, measure-floor-plan.md
- Personal: crm-daily-review.md, content-calendar.md, follow-up-sequence.md

## Agents (specialists in .claude/agents/)
EPS: eps-quote-agent, eps-email-agent, eps-crm-agent, eps-qa-agent, eps-call-notes, eps-cold-calls
Personal: personal-content-agent, personal-followup-agent, personal-research-agent

## Rules
- Be concise — this is a mobile chat interface. Short answers.
- When sending ANY email, show the draft and ask for confirmation first.
- Simple English. 3rd-5th grade reading level for client-facing content.
- For EPS client work, use sales@epsolution.com.au. For personal brand, use allenenriquez006@gmail.com.
- If a task is complex, break it into steps and tell Allen the plan before executing.
- Never fabricate data — always fetch from tools.
"""

# Conversation memory per session (resets on server restart)
_conversations: dict[str, list] = {}

MAX_TOOL_ROUNDS = 10


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

        messages.append({'role': 'user', 'content': message})

        # Agentic loop — call Claude, execute tools, repeat
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            # Check if response contains tool_use blocks (don't rely solely on stop_reason)
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
                        'content': json.dumps(result),
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
