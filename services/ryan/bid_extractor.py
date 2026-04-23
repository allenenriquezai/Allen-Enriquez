"""Extract bid due dates from email metadata and create Google Calendar events."""
from __future__ import annotations
import json
import logging
from datetime import datetime

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import config

log = logging.getLogger(__name__)


def extract_bid_due(
    msg_id: str,
    from_addr: str,
    subject: str,
    snippet: str,
) -> dict | None:
    """Parse bid due date via Claude, create Calendar event if found.

    Returns {created, event_id, due_date, assignee} or None.
    """
    # Parse due date with Claude Haiku (fast + cheap)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.anthropic_api_key())
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            messages=[{
                "role": "user",
                "content": (
                    "Extract the bid due date from this email. "
                    "Return JSON only, nothing else.\n"
                    f"From: {from_addr}\n"
                    f"Subject: {subject}\n"
                    f"Snippet: {snippet}\n\n"
                    'Return: {"due_date": "YYYY-MM-DD or null", "project_hint": "name or null"}'
                ),
            }],
        )
        data = json.loads(resp.content[0].text.strip())
        due_date = data.get("due_date")
        project_hint = data.get("project_hint")
    except Exception as e:
        log.warning("bid_extractor: Claude parse failed: %s", e)
        return None

    if not due_date or due_date == "null":
        return None

    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        log.warning("bid_extractor: invalid date format: %s", due_date)
        return None

    # Round-robin assignee: Kharene (even) / Kim (odd)
    try:
        state = config.load_state()
        counter = state.get("bid_assignee_counter", 0)
        assignee = "Kharene" if counter % 2 == 0 else "Kim"
        state["bid_assignee_counter"] = counter + 1
        config.save_state(state)
    except Exception:
        assignee = "Kharene"

    title = f"BID DUE: {(project_hint or subject)[:60]}"
    description = f"From: {from_addr}\nSubject: {subject}\nAssignee: {assignee}"

    try:
        creds = config.ryan_calendar_creds()
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = svc.events().insert(
            calendarId="primary",
            body={
                "summary": title,
                "description": description,
                "start": {"date": due_date},
                "end": {"date": due_date},
                "colorId": "11",  # Tomato red
            },
        ).execute()
        event_id = event.get("id", "")
        log.info("bid_extractor: created event %s on %s — %s", event_id, due_date, assignee)
        return {"created": True, "event_id": event_id, "due_date": due_date, "assignee": assignee}
    except Exception as e:
        log.warning("bid_extractor: Calendar insert failed: %s", e)
        return None
