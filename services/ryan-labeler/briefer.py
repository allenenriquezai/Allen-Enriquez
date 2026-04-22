"""Morning brief composer + sender for Ryan.

Fires at 6:30 AM America/Los_Angeles via Cloud Scheduler -> POST /brief.

Sections:
1. Overnight arrivals (Gmail search since yesterday, excluding skip-inbox labels)
2. Bid due dates today (from calendar events tagged "bid")
3. Today's calendar
4. Urgent flags (change-order subjects, priority GC senders, project activation signals)

Sends plain text from allenenriquez.ai@gmail.com to ryan@sc-incorporated.com.
"""
from __future__ import annotations
import base64
import json
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import config
from labeler import get_gmail_service


def _pt_now() -> datetime:
    """California time. PT is UTC-7 (PDT) or -8 (PST); use UTC-7 in April."""
    try:
        import zoneinfo
        return datetime.now(zoneinfo.ZoneInfo("America/Los_Angeles"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-7)))


def fetch_overnight_messages(hours_back: int = 14) -> list[dict]:
    """Messages received in the last N hours, excluding skip-inbox categories."""
    service = get_gmail_service()
    # Gmail query: after:YYYY/MM/DD plus exclusion labels
    since = _pt_now() - timedelta(hours=hours_back)
    # Gmail `after:` is YYYY/MM/DD
    after = since.strftime("%Y/%m/%d")
    # Exclude skip-inbox buckets — load names from routing_rules so renames stay in sync
    rules = config.load_routing_rules()
    skip_labels = [
        cfg["label"]
        for cfg in rules["buckets"].values()
        if cfg.get("skip_inbox") and cfg.get("label")
    ]
    excl = " ".join(f'-label:"{lbl}"' for lbl in skip_labels)
    q = f"after:{after} -category:promotions {excl}"
    resp = service.users().messages().list(userId="me", q=q, maxResults=50).execute()
    ids = [m["id"] for m in resp.get("messages", [])]
    out = []
    for mid in ids:
        m = service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        ts_ms = int(m.get("internalDate", 0))
        # Filter by exact hour cutoff (after: is day-precision only)
        if ts_ms and datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) < since.astimezone(timezone.utc):
            continue
        out.append({
            "id": m["id"],
            "thread_id": m.get("threadId", ""),
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": m.get("snippet", "")[:120],
            "label_ids": m.get("labelIds", []),
        })
    return out


def fetch_calendar_today() -> list[dict]:
    creds = config.ryan_calendar_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    try:
        svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
        pt = _pt_now()
        start = pt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        res = svc.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for e in res.get("items", []):
            events.append({
                "title": e.get("summary", "(no title)"),
                "start": e["start"].get("dateTime", e["start"].get("date", "")),
                "location": e.get("location", ""),
            })
        return events
    except Exception as e:
        # Calendar scope may not yet be granted; degrade gracefully
        return [{"title": f"(calendar unavailable: {e})", "start": "", "location": ""}]


def _get_ryan_label_map() -> dict:
    """Returns {label_id: label_name} for Ryan's Gmail."""
    service = get_gmail_service()
    resp = service.users().labels().list(userId="me").execute()
    return {l["id"]: l["name"] for l in resp["labels"]}


_URGENT_PATTERNS = [
    "change order", "rfi", "punchlist", "walk through", "site visit",
    "purchase order", "awarded", "accepted", "approved", "urgent", "asap",
]


def fetch_inbox_grouped(hours_back: int = 48) -> dict:
    """Fetch recent inbox messages grouped into {urgent, projects, bids, team, other}."""
    service = get_gmail_service()
    label_map = _get_ryan_label_map()

    since = _pt_now() - timedelta(hours=hours_back)
    after = since.strftime("%Y/%m/%d")

    resp = service.users().messages().list(
        userId="me",
        q=f"after:{after} (label:inbox OR label:important) -category:promotions",
        maxResults=100,
    ).execute()

    urgent, bids, team, other = [], [], [], []
    projects: dict[str, list] = {}

    for mid in [m["id"] for m in resp.get("messages", [])]:
        m = service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        ts_ms = int(m.get("internalDate", 0))
        if ts_ms and datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) < since.astimezone(timezone.utc):
            continue

        subj_lower = (headers.get("subject") or "").lower()
        msg_labels = [label_map.get(lid, "") for lid in m.get("labelIds", [])]
        msg = {
            "id": m["id"],
            "thread_id": m.get("threadId", ""),
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": m.get("snippet", "")[:120],
            "label_ids": m.get("labelIds", []),
        }

        is_urgent = any(p in subj_lower for p in _URGENT_PATTERNS)
        project_label = next(
            (l for l in msg_labels if "/B. Ongoing/" in l or "/C. Completed/" in l), None
        )
        is_bid = any("Bids" in l or "Invites" in l for l in msg_labels)
        is_team = any("Daily Accomplishments" in l or "2. Team" in l for l in msg_labels)

        if is_urgent:
            msg["reasons"] = [p for p in _URGENT_PATTERNS if p in subj_lower][:2]
            urgent.append(msg)
        elif project_label:
            projects.setdefault(project_label.split("/")[-1], []).append(msg)
        elif is_bid:
            bids.append(msg)
        elif is_team:
            team.append(msg)
        else:
            other.append(msg)

    return {"urgent": urgent, "projects": projects, "bids": bids, "team": team, "other": other}


def fetch_upcoming_calendar(days_ahead: int = 7) -> list[dict]:
    """Fetch events for today + next N days, with bid-due and assignee detection."""
    creds = config.ryan_calendar_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    try:
        svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
        pt = _pt_now()
        start = pt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=days_ahead)
        res = svc.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            maxResults=60,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for e in res.get("items", []):
            title = e.get("summary", "(no title)")
            start_val = e["start"].get("dateTime", e["start"].get("date", ""))
            desc = (e.get("description") or "").lower()
            assignee = "Kharene" if "kharene" in desc else ("Kim" if "kim" in desc else None)
            is_bid_due = any(kw in title.lower() for kw in ["bid", "due", "deadline", "proposal"])
            event_date = start_val[:10] if start_val else ""
            # Compute end_date
            if e["end"].get("date"):
                # All-day: end date is exclusive — subtract 1 day
                end_d = datetime.strptime(e["end"]["date"], "%Y-%m-%d").date() - timedelta(days=1)
                end_date = end_d.strftime("%Y-%m-%d")
            else:
                end_val = e["end"].get("dateTime", "")
                end_date = end_val[:10] if end_val else event_date
            color_id = e.get("colorId", "")
            events.append({
                "title": title,
                "start": start_val,
                "date": event_date,
                "end_date": end_date,
                "location": e.get("location", ""),
                "assignee": assignee,
                "is_bid_due": is_bid_due,
                "color": color_id,
            })
        return events
    except Exception as ex:
        return [{"title": f"(calendar unavailable: {ex})", "start": "", "date": "", "end_date": "", "location": "", "assignee": None, "is_bid_due": False, "color": ""}]


def find_urgent(messages: list[dict]) -> list[dict]:
    """Flag anything smelling like a change order, priority GC, or new project activation."""
    rules = config.load_routing_rules()
    gc_senders = [g.lower() for g in rules.get("gc_priority_senders", {}).get("senders", [])]
    urgent_patterns = [
        "change order", "rfi", "punchlist", "walk through", "site visit",
        "po ", "purchase order", "awarded", "accepted", "approved",
        "urgent", "asap", "today", "this morning",
    ]
    flagged = []
    for m in messages:
        subject_lower = m["subject"].lower()
        from_lower = m["from"].lower()
        reasons = []
        for p in urgent_patterns:
            if p in subject_lower:
                reasons.append(f"subject contains '{p}'")
                break
        for gc in gc_senders:
            if gc.lower() in from_lower:
                reasons.append(f"from priority GC: {gc}")
                break
        if reasons:
            flagged.append({**m, "reasons": reasons})
    return flagged


def compose_brief(overnight: list[dict], events: list[dict], urgent: list[dict]) -> tuple[str, str]:
    """Returns (subject, body_text)."""
    pt = _pt_now()
    date_str = pt.strftime("%A %b %d")
    subject = f"Morning brief — {date_str}"

    lines = [
        f"Good morning Ryan,",
        "",
        f"Quick rundown for {date_str}:",
        "",
    ]

    # Urgent first
    if urgent:
        lines.append(f"🔔 Needs you first ({len(urgent)})")
        for u in urgent[:8]:
            reasons = "; ".join(u["reasons"])
            lines.append(f"  • {u['subject'][:90]}")
            lines.append(f"    from {u['from'][:60]} — {reasons}")
        lines.append("")
    else:
        lines.append("🔔 Nothing urgent overnight.")
        lines.append("")

    # Today's calendar
    lines.append(f"📅 Today ({len(events)} event{'s' if len(events) != 1 else ''})")
    if not events:
        lines.append("  (nothing on calendar)")
    else:
        for e in events[:10]:
            start = e["start"]
            # Extract time if datetime form
            time_part = ""
            if "T" in start:
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    time_part = dt.strftime("%-I:%M %p")
                except Exception:
                    pass
            loc = f" @ {e['location']}" if e["location"] else ""
            lines.append(f"  • {time_part or 'all day'} — {e['title']}{loc}")
    lines.append("")

    # Overnight summary
    non_urgent = [m for m in overnight if m not in urgent]
    lines.append(f"📬 Overnight ({len(overnight)} total, {len(non_urgent)} routine)")
    for m in non_urgent[:6]:
        lines.append(f"  • {m['subject'][:80]} — {m['from'][:50]}")
    if len(non_urgent) > 6:
        lines.append(f"  ...and {len(non_urgent) - 6} more (sorted into labels)")
    lines.append("")

    lines.append("Bids, Lowes promos, and PH vendor pricing requests are off this list — they're")
    lines.append("filed in their own labels, quiet.")
    lines.append("")
    lines.append("- Allen")
    lines.append("")
    lines.append("--")
    lines.append("Reply `fix <label>` if anything's in the wrong bucket. I'll tune the rule.")

    return subject, "\n".join(lines)


def send_brief(subject: str, body: str) -> dict:
    """Send via Allen's .ai Gmail to Ryan."""
    creds = config.allen_ai_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
    msg = MIMEText(body, "plain")
    msg["to"] = config.RYAN_EMAIL
    msg["from"] = f"Allen Enriquez <{config.ALLEN_AI_EMAIL}>"
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"sent": True, "message_id": result.get("id")}


def run_brief(dry_run: bool = False) -> dict:
    """End-to-end: fetch data, compose, send (or preview)."""
    overnight = fetch_overnight_messages(hours_back=14)
    events = fetch_calendar_today()
    urgent = find_urgent(overnight)
    subject, body = compose_brief(overnight, events, urgent)

    if dry_run:
        return {"dry_run": True, "subject": subject, "body": body,
                "counts": {"overnight": len(overnight), "events": len(events), "urgent": len(urgent)}}

    send_result = send_brief(subject, body)
    # Update state
    state = config.load_state()
    state["last_brief_sent_at"] = _pt_now().isoformat()
    config.save_state(state)
    return {
        "dry_run": False,
        "subject": subject,
        "counts": {"overnight": len(overnight), "events": len(events), "urgent": len(urgent)},
        **send_result,
    }


# ── Evening brief ──────────────────────────────────────────────────────────────

def fetch_team_daily_today(hours_back: int = 12) -> list[dict]:
    """Fetch today's team daily report emails from the team_daily label."""
    service = get_gmail_service()
    since = _pt_now() - timedelta(hours=hours_back)
    after = since.strftime("%Y/%m/%d")
    q = f'after:{after} label:"2. Team/Daily Accomplishments PH"'
    resp = service.users().messages().list(userId="me", q=q, maxResults=20).execute()
    ids = [m["id"] for m in resp.get("messages", [])]
    out = []
    for mid in ids:
        m = service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        ts_ms = int(m.get("internalDate", 0))
        if ts_ms and datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) < since.astimezone(timezone.utc):
            continue
        out.append({
            "id": m["id"],
            "thread_id": m.get("threadId", ""),
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": m.get("snippet", "")[:120],
        })
    return out


def fetch_inbox_sections(hours_back: int = 168) -> dict:
    """Fetch messages by Gmail label for the Inbox tab.

    Queries directly by label (not inbox status) so archived emails show up.
    Returns {bids, ongoing: {project_name: [msgs]}, team, vendors}.
    """
    service = get_gmail_service()
    since = _pt_now() - timedelta(hours=hours_back)
    after = since.strftime("%Y/%m/%d")

    def _fetch_label(label_q: str, max_results: int = 20) -> list[dict]:
        resp = service.users().messages().list(
            userId="me",
            q=f'after:{after} label:"{label_q}"',
            maxResults=max_results,
        ).execute()
        out = []
        for mid in [m["id"] for m in resp.get("messages", [])]:
            m = service.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
            ts_ms = int(m.get("internalDate", 0))
            if ts_ms and datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) < since.astimezone(timezone.utc):
                continue
            out.append({
                "id": m["id"],
                "thread_id": m.get("threadId", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "snippet": m.get("snippet", "")[:120],
                "label_ids": m.get("labelIds", []),
                "ts_ms": ts_ms,
            })
        return out

    bids = _fetch_label("3. Bids/Invites", 25)
    team = _fetch_label("2. Team", 20)
    vendors = _fetch_label("4. Vendors/Pricing", 20)

    label_map = _get_ryan_label_map()
    ongoing_raw = _fetch_label("1. Projects/B. Ongoing", 40)
    ongoing: dict[str, list] = {}
    for msg in ongoing_raw:
        proj_label = next(
            (label_map.get(lid, "") for lid in msg["label_ids"]
             if "B. Ongoing/" in label_map.get(lid, "")),
            None,
        )
        name = proj_label.split("/")[-1] if proj_label else "Other"
        ongoing.setdefault(name, []).append(msg)

    return {"bids": bids, "ongoing": ongoing, "team": team, "vendors": vendors}


def fetch_calendar_tomorrow() -> list[dict]:
    creds = config.ryan_calendar_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    try:
        svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
        pt = _pt_now()
        start = (pt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        res = svc.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for e in res.get("items", []):
            events.append({
                "title": e.get("summary", "(no title)"),
                "start": e["start"].get("dateTime", e["start"].get("date", "")),
                "location": e.get("location", ""),
            })
        return events
    except Exception as e:
        return [{"title": f"(calendar unavailable: {e})", "start": "", "location": ""}]


def compose_evening_brief(
    today_msgs: list[dict],
    team_daily: list[dict],
    events_tomorrow: list[dict],
    urgent: list[dict],
) -> tuple[str, str]:
    """Returns (subject, body_text) for evening brief."""
    pt = _pt_now()
    date_str = pt.strftime("%A %b %d")
    tomorrow_str = (pt + timedelta(days=1)).strftime("%A %b %d")
    subject = f"Evening brief — {date_str}"

    lines = [
        "Good evening Ryan,",
        "",
        f"End of day wrap for {date_str}:",
        "",
    ]

    # Team daily reports
    lines.append(f"📋 Team reports today ({len(team_daily)})")
    if not team_daily:
        lines.append("  (none received — check in with Kim/Kharene)")
    else:
        for t in team_daily:
            sender = t["from"].split("<")[0].strip() or t["from"][:40]
            lines.append(f"  ✅ {sender[:30]} — {t['subject'][:70]}")
    lines.append("")

    # Urgent items that still need response
    if urgent:
        lines.append(f"🔔 Still needs attention ({len(urgent)})")
        for u in urgent[:6]:
            lines.append(f"  • {u['subject'][:90]}")
            lines.append(f"    from {u['from'][:60]}")
        lines.append("")

    # Tomorrow's calendar
    lines.append(f"📅 Tomorrow — {tomorrow_str} ({len(events_tomorrow)} event{'s' if len(events_tomorrow) != 1 else ''})")
    if not events_tomorrow:
        lines.append("  (nothing on calendar)")
    else:
        for e in events_tomorrow[:10]:
            start = e["start"]
            time_part = ""
            if "T" in start:
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    time_part = dt.strftime("%-I:%M %p")
                except Exception:
                    pass
            loc = f" @ {e['location']}" if e["location"] else ""
            lines.append(f"  • {time_part or 'all day'} — {e['title']}{loc}")
    lines.append("")

    lines.append(f"📬 Total today: {len(today_msgs)} emails processed")
    lines.append("")
    lines.append("- Allen")

    return subject, "\n".join(lines)


_EMOJI_HDRS = {"🔔", "📬", "📅", "📋", "📊", "🌙", "☀️", "👥"}


def _brief_nav_html(active: str, token: str) -> str:
    def _tab(label: str, href: str, key: str) -> str:
        cls = "tab active" if active == key else "tab"
        return f'<a class="{cls}" href="{href}?token={token}">{label}</a>'
    return (
        '<nav class="topnav">'
        '<div class="nav-left">'
        '<div class="nav-mark">SC</div>'
        '<span class="nav-brand">SC-INCORPORATED</span>'
        '</div>'
        '<div class="nav-tabs">'
        + _tab("Dashboard", "/dashboard", "dashboard")
        + _tab("Inbox", "/inbox", "inbox")
        + _tab("Calendar", "/calendar", "calendar")
        + _tab("Morning Brief", "/brief-preview", "morning")
        + _tab("Evening Brief", "/evening-brief-preview", "evening")
        + '</div></nav>'
    )


def _brief_as_html(subject: str, body: str, token: str = "ryan-sc") -> str:
    """Wrap a plain-text brief body in a branded HTML page for browser preview."""
    esc = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines_html = "".join(
        f'<div class="line hdr">{l}</div>' if any(x in l for x in _EMOJI_HDRS)
        else f'<div class="line">{l}</div>'
        for l in esc.splitlines()
    )
    active = "evening" if "Evening" in subject else "morning"
    nav = _brief_nav_html(active, token)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Roboto+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --blue: #02B3E9; --blue-glow: rgba(2,179,233,0.45);
  --blue-soft: rgba(2,179,233,0.12); --blue-border: rgba(2,179,233,0.25);
  --navy: #0a1220; --white: #ffffff; --grey: #c6d1e3; --grey-dim: #8592ab;
  --mono: 'Roboto Mono',monospace; --sans: 'Montserrat',sans-serif;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:var(--navy);color:var(--white);font-family:var(--sans);font-weight:300;
  line-height:1.6;-webkit-font-smoothing:antialiased;min-height:100vh;overflow-x:hidden;}}
.bg-glow{{position:fixed;top:-30vh;left:50%;transform:translateX(-50%);width:120vw;height:100vh;
  background:radial-gradient(ellipse at center,var(--blue-soft) 0%,transparent 60%);
  pointer-events:none;z-index:0;}}
.topnav{{background:rgba(10,18,32,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-bottom:1px solid var(--blue-border);padding:0 32px;
  display:flex;align-items:stretch;position:sticky;top:0;z-index:10;}}
.nav-left{{display:flex;align-items:center;gap:12px;padding:14px 24px 14px 0;
  border-right:1px solid rgba(255,255,255,0.06);margin-right:8px;flex-shrink:0;}}
.nav-mark{{width:36px;height:36px;background:var(--blue-soft);border:1px solid var(--blue-border);
  border-radius:9px;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-weight:700;font-size:13px;color:var(--blue);
  box-shadow:0 0 16px var(--blue-glow);flex-shrink:0;}}
.nav-brand{{font-family:var(--mono);font-weight:700;font-size:13px;letter-spacing:0.1em;
  color:var(--white);text-shadow:0 0 16px var(--blue-glow);}}
.nav-tabs{{display:flex;align-items:stretch;}}
.tab{{display:flex;align-items:center;padding:0 20px;font-family:var(--mono);font-size:11px;
  font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--grey-dim);
  text-decoration:none;border-bottom:2px solid transparent;transition:color .15s,border-color .15s;white-space:nowrap;}}
.tab:hover{{color:var(--blue);}}
.tab.active{{color:var(--blue);border-bottom-color:var(--blue);}}
.brief-wrap{{max-width:700px;margin:0 auto;padding:48px 32px;position:relative;z-index:1;}}
.preview-tag{{display:inline-block;background:var(--blue-soft);border:1px solid var(--blue-border);
  border-radius:6px;padding:4px 12px;font-family:var(--mono);font-size:11px;font-weight:700;
  color:var(--blue);margin-bottom:20px;letter-spacing:0.08em;}}
.brief-title{{font-family:var(--mono);font-weight:700;font-size:22px;color:var(--blue);
  letter-spacing:0.04em;margin-bottom:32px;padding-bottom:20px;
  border-bottom:1px solid var(--blue-border);
  text-shadow:0 0 24px var(--blue-glow);line-height:1.3;}}
.line{{font-size:16px;font-weight:300;line-height:1.9;white-space:pre-wrap;
  min-height:1.9em;color:var(--grey);}}
.line.hdr{{font-family:var(--mono);font-size:15px;font-weight:700;color:var(--white);
  margin-top:32px;margin-bottom:6px;min-height:auto;}}
@media(max-width:600px){{
  .nav-brand{{display:none;}}
  .topnav{{padding:0 16px;}}
  .tab{{padding:0 12px;font-size:10px;}}
  .brief-wrap{{padding:32px 20px;}}
  .brief-title{{font-size:18px;}}
  .line{{font-size:15px;}}
}}
</style>
</head>
<body>
<div class="bg-glow"></div>
{nav}
<div class="brief-wrap">
  <div class="preview-tag">PREVIEW — not sent yet</div>
  <div class="brief-title">{subject}</div>
  <div class="brief-body">{lines_html}</div>
</div>
</body>
</html>"""


def run_brief_preview(token: str = "ryan-sc") -> str:
    result = run_brief(dry_run=True)
    return _brief_as_html(result["subject"], result["body"], token=token)


def run_evening_brief_preview(token: str = "ryan-sc") -> str:
    result = run_evening_brief(dry_run=True)
    return _brief_as_html(result["subject"], result["body"], token=token)


def run_evening_brief(dry_run: bool = False) -> dict:
    """End-to-end: fetch data, compose, send (or preview)."""
    today_msgs = fetch_overnight_messages(hours_back=12)
    team_daily = fetch_team_daily_today(hours_back=12)
    events_tomorrow = fetch_calendar_tomorrow()
    urgent = find_urgent(today_msgs)
    subject, body = compose_evening_brief(today_msgs, team_daily, events_tomorrow, urgent)

    if dry_run:
        return {
            "dry_run": True, "subject": subject, "body": body,
            "counts": {
                "today": len(today_msgs), "team_daily": len(team_daily),
                "events_tomorrow": len(events_tomorrow), "urgent": len(urgent),
            },
        }

    send_result = send_brief(subject, body)
    state = config.load_state()
    state["last_evening_brief_sent_at"] = _pt_now().isoformat()
    config.save_state(state)
    return {
        "dry_run": False,
        "subject": subject,
        "counts": {
            "today": len(today_msgs), "team_daily": len(team_daily),
            "events_tomorrow": len(events_tomorrow), "urgent": len(urgent),
        },
        **send_result,
    }


# ── Tasks ─────────────────────────────────────────────────────────────────────

def _tasks_path():
    import config
    return config.CONFIG_DIR / "tasks.json"


def fetch_tasks() -> list[dict]:
    """Load tasks from disk. Returns list of {id, text, done, created_at}."""
    p = _tasks_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def add_task(text: str) -> dict:
    """Add a new task. Returns the new task dict."""
    import uuid
    tasks = fetch_tasks()
    task = {
        "id": str(uuid.uuid4())[:8],
        "text": text.strip()[:200],
        "done": False,
        "created_at": _pt_now().isoformat(),
    }
    tasks.append(task)
    _tasks_path().write_text(json.dumps(tasks, indent=2))
    return task


def toggle_task(task_id: str) -> bool:
    """Toggle done status of a task. Returns new done value."""
    tasks = fetch_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t["done"]
            _tasks_path().write_text(json.dumps(tasks, indent=2))
            return t["done"]
    return False


def delete_task(task_id: str) -> None:
    """Delete a task by id."""
    tasks = fetch_tasks()
    tasks = [t for t in tasks if t["id"] != task_id]
    _tasks_path().write_text(json.dumps(tasks, indent=2))


def fetch_thread(thread_id: str) -> list[dict]:
    """Fetch all messages in a Gmail thread. Returns list of message dicts."""
    import base64
    creds = config.ryan_gmail_creds()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    thread = service.users().threads().get(
        userId="me", id=thread_id, format="full"
    ).execute()

    msgs = []
    for m in thread.get("messages", []):
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        ts_ms = int(m.get("internalDate", 0))

        # Extract text/plain body (walk MIME tree)
        def _extract_plain(part):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            for p in part.get("parts", []):
                result = _extract_plain(p)
                if result:
                    return result
            return ""

        body = _extract_plain(m.get("payload", {}))

        msgs.append({
            "message_id": m["id"],
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", "(no subject)"),
            "date_str": headers.get("date", ""),
            "ts_ms": ts_ms,
            "body": body[:8000],  # cap at 8KB
            "label_ids": m.get("labelIds", []),
        })
    return msgs
