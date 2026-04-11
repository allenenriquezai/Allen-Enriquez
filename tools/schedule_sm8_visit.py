"""
schedule_sm8_visit.py — Schedule SM8 site visit with full availability check.

Checks THREE calendars before scheduling:
  1. SM8 EPS Paint — existing scheduled job activities
  2. SM8 EPS Clean — existing scheduled job activities
  3. Google Calendar — time blocks + real meetings

Usage:
    python tools/schedule_sm8_visit.py --job EPSP1938 --date 2026-04-14
    python tools/schedule_sm8_visit.py --job EPSP1938 --date 2026-04-14 --time 11:00
    python tools/schedule_sm8_visit.py --job EPSP1938 --date 2026-04-14 --time 11:00 --duration 60
    python tools/schedule_sm8_visit.py --job EPSP1938 --date 2026-04-14 --check-only

Flags:
    --job         SM8 generated job ID (e.g. EPSP1938)
    --date        Target date (YYYY-MM-DD)
    --time        Requested time (HH:MM, 24h). If omitted, suggests best slots.
    --duration    Duration in minutes (default: 60)
    --staff       Staff name (default: Giovanni)
    --check-only  Show calendar + available slots, don't schedule
    --pipeline    paint or clean (default: paint)
"""

import argparse
import os
import pickle
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
EPS_DIR = ROOT / "projects" / "eps"

from dotenv import load_dotenv
load_dotenv(EPS_DIR / ".env")

# ── config ───────────────────────────────────────────────────────────────────
SM8_BASE_URL = "https://api.servicem8.com/api_1.0"
SM8_KEYS = {
    "paint": os.getenv("SM8_API_KEY_PAINT"),
    "clean": os.getenv("SM8_API_KEY_CLEAN"),
}

AEST = timezone(timedelta(hours=10))  # Brisbane, no DST

# Staff registry — add more as needed
# sm8_uuid can be a string (same across pipelines) or dict keyed by pipeline
STAFF = {
    "giovanni": {
        "sm8_uuid": "0a8efd13-0f36-4956-959a-210ce42c54fb",
        "calendar_id": "giovanni@epsolution.com.au",
        "preferred_start": 11,  # prefers 11AM onwards for site visits
    },
    "vanessa": {
        "sm8_uuid": {
            "paint": "e33f98f0-3f3e-4fe1-b18a-2405b0d9432b",
            "clean": "b534a801-4ebd-4eaf-94cc-1fdba1cda23b",
        },
        "calendar_id": "vanessa@epsolution.com.au",
        "preferred_start": 11,
    },
}

CALENDAR_TOKEN = EPS_DIR / "token_eps.pickle"

# Work hours for slot detection
WORK_START = 7   # 7 AM
WORK_END = 17    # 5 PM


# ── Google Calendar ──────────────────────────────────────────────────────────

def get_calendar_service():
    with open(CALENDAR_TOKEN, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def fetch_events(calendar_id, date):
    """Fetch all events for a given date. Marks recurring events as soft blocks."""
    service = get_calendar_service()
    start = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=AEST)
    end = start + timedelta(days=1)

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=50,
    ).execute()

    events = []
    for e in result.get("items", []):
        s = e["start"].get("dateTime")
        f = e["end"].get("dateTime")
        if not s or not f:
            continue  # skip all-day events
        is_recurring = "recurringEventId" in e
        events.append({
            "summary": e.get("summary", "(no title)"),
            "start": datetime.fromisoformat(s),
            "end": datetime.fromisoformat(f),
            "recurring": is_recurring,
        })
    return events


def find_open_slots(events, date, duration_min, preferred_start=11):
    """Find open slots during work hours.

    Recurring events (time blocks) are treated as SOFT — site visits can override them.
    One-off events (real meetings) are HARD blocks.
    Returns slots sorted: preferred_start+ first, then by fewest soft conflicts.
    """
    duration = timedelta(minutes=duration_min)

    hard_busy = [(e["start"], e["end"]) for e in events if not e.get("recurring")]
    soft_busy = [(e["start"], e["end"], e["summary"]) for e in events if e.get("recurring")]

    current = datetime(date.year, date.month, date.day, WORK_START, 0, 0, tzinfo=AEST)
    work_end = datetime(date.year, date.month, date.day, WORK_END, 0, 0, tzinfo=AEST)

    slots = []
    while current + duration <= work_end:
        slot_end = current + duration

        # Hard conflict = skip entirely
        hard_conflict = any(
            not (slot_end <= b_start or current >= b_end)
            for b_start, b_end in hard_busy
        )
        if not hard_conflict:
            # Count soft conflicts (recurring blocks overridden)
            soft_hits = [
                name for b_start, b_end, name in soft_busy
                if not (slot_end <= b_start or current >= b_end)
            ]
            slots.append((current, slot_end, soft_hits))

        current += timedelta(minutes=30)

    # Sort: preferred hours first, then fewer soft conflicts, then earlier
    def sort_key(slot):
        hour = slot[0].hour
        preferred = 0 if hour >= preferred_start else 1
        return (preferred, len(slot[2]), hour)

    slots.sort(key=sort_key)
    return slots


def check_conflict(events, start_dt, end_dt):
    """Check if a specific time conflicts with any calendar event."""
    conflicts = []
    for e in events:
        if not (end_dt <= e["start"] or start_dt >= e["end"]):
            conflicts.append(e)
    return conflicts


# ── ServiceM8 ────────────────────────────────────────────────────────────────

def sm8_get(path, api_key, params=None):
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    r = requests.get(f"{SM8_BASE_URL}{path}", headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def sm8_post(path, api_key, payload):
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.post(f"{SM8_BASE_URL}{path}", headers=headers, json=payload)
    r.raise_for_status()
    location = r.headers.get("Location", "")
    uuid = location.split("/")[-1].replace(".json", "") if location else None
    return r.json(), uuid


def find_sm8_job(job_number, api_key):
    jobs = sm8_get(
        "/job.json", api_key,
        params={"$filter": f"generated_job_id eq '{job_number}'"},
    )
    if not jobs:
        raise RuntimeError(f"No SM8 job found: {job_number}")
    return jobs[0]


def find_sm8_job_by_deal(deal_id):
    """Search both SM8 pipelines for a job linked to a Pipedrive deal.

    Looks for purchase_order_number eq 'PipeDrive-{deal_id}'.
    Returns (job_dict, pipeline_key) or (None, None).
    """
    po_number = f"PipeDrive-{deal_id}"
    for pipeline, api_key in SM8_KEYS.items():
        if not api_key:
            continue
        try:
            jobs = sm8_get(
                "/job.json", api_key,
                params={"$filter": f"purchase_order_number eq '{po_number}'"},
            )
            if jobs:
                return jobs[0], pipeline
        except Exception as e:
            print(f"  WARNING: SM8 {pipeline} search failed: {e}")
            continue
    return None, None


def find_sm8_staff(name, api_key):
    """Look up SM8 staff UUID by name (case-insensitive partial match)."""
    staff_list = sm8_get("/staff.json", api_key)
    name_lower = name.lower()
    for s in staff_list:
        full = f"{s.get('first', '')} {s.get('last', '')}".strip().lower()
        if name_lower in full:
            return s["uuid"]
    return None


def _resolve_sm8_uuid(sm8_uuid_config, pipeline):
    """Resolve SM8 UUID — handles both single string and per-pipeline dict."""
    if isinstance(sm8_uuid_config, dict):
        return sm8_uuid_config.get(pipeline)
    return sm8_uuid_config


def fetch_sm8_activities(sm8_uuid_config, date):
    """Fetch scheduled activities for a staff member across BOTH SM8 pipelines."""
    target = date.strftime("%Y-%m-%d")
    activities = []

    for pipeline, api_key in SM8_KEYS.items():
        if not api_key:
            continue
        staff_uuid = _resolve_sm8_uuid(sm8_uuid_config, pipeline)
        if not staff_uuid:
            continue
        try:
            all_acts = sm8_get(
                "/jobactivity.json", api_key,
                params={"$filter": f"staff_uuid eq '{staff_uuid}'"},
            )
        except Exception as e:
            print(f"  WARNING: Could not fetch SM8 {pipeline} activities: {e}")
            continue

        for a in all_acts:
            start_str = a.get("start_date", "")
            if not start_str.startswith(target):
                continue
            if not a.get("activity_was_scheduled"):
                continue

            # Look up job number for display
            job_uuid = a.get("job_uuid", "")
            job_label = job_uuid[:8]
            try:
                job = sm8_get(f"/job/{job_uuid}.json", api_key)
                job_label = job.get("generated_job_id", job_uuid[:8])
            except Exception:
                pass

            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=AEST)
            end_str = a.get("end_date", "")
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=AEST) if end_str else start_dt + timedelta(hours=1)

            activities.append({
                "summary": f"Site Visit — {job_label}",
                "start": start_dt,
                "end": end_dt,
                "recurring": False,  # SM8 activities are always hard blocks
                "source": f"SM8 {pipeline.title()}",
            })

    return activities


def schedule_activity(job_uuid, staff_uuid, start_dt, end_dt, api_key):
    """Create a scheduled job activity on SM8."""
    payload = {
        "job_uuid": job_uuid,
        "staff_uuid": staff_uuid,
        "start_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "activity_was_scheduled": 1,
    }
    _, uuid = sm8_post("/jobactivity.json", api_key, payload)
    return uuid


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Schedule SM8 site visit with calendar check")
    job_group = parser.add_mutually_exclusive_group(required=True)
    job_group.add_argument("--job", help="SM8 job ID (e.g. EPSP1938)")
    job_group.add_argument("--deal-id", help="Pipedrive deal ID — auto-resolves SM8 job via PO link")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--time", help="Preferred time HH:MM (24h). Omit to see suggestions.")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes (default: 60)")
    parser.add_argument("--staff", default="giovanni", help="Staff name (default: giovanni)")
    parser.add_argument("--check-only", action="store_true", help="Show calendar only, don't schedule")
    parser.add_argument("--pipeline", default="paint", choices=["paint", "clean"])
    args = parser.parse_args()

    # ── Resolve SM8 job from deal ID if provided ─────────────────────────────
    if args.deal_id:
        print(f"Searching SM8 for job linked to Pipedrive deal {args.deal_id}...")
        job_data, resolved_pipeline = find_sm8_job_by_deal(args.deal_id)
        if not job_data:
            print(f"NOT_FOUND: No SM8 job linked to deal {args.deal_id}")
            sys.exit(1)
        args.job = job_data["generated_job_id"]
        args.pipeline = resolved_pipeline
        print(f"Found: {args.job} on SM8 {resolved_pipeline.title()} (PO: {job_data.get('purchase_order_number')})")

    api_key = SM8_KEYS[args.pipeline]
    if not api_key:
        print(f"ERROR: SM8 API key not set for {args.pipeline}")
        sys.exit(1)

    date = datetime.strptime(args.date, "%Y-%m-%d").date()
    staff_key = args.staff.lower()
    staff_info = STAFF.get(staff_key)

    # Resolve staff details
    if staff_info:
        sm8_uuid_config = staff_info["sm8_uuid"]
        staff_uuid = _resolve_sm8_uuid(sm8_uuid_config, args.pipeline)
        if not staff_uuid:
            print(f"ERROR: {args.staff.title()} has no SM8 UUID for {args.pipeline} pipeline")
            sys.exit(1)
        calendar_id = staff_info["calendar_id"]
        preferred_start = staff_info["preferred_start"]
    else:
        print(f"Staff '{args.staff}' not in registry. Looking up SM8...")
        staff_uuid = find_sm8_staff(args.staff, api_key)
        if not staff_uuid:
            print(f"ERROR: Staff '{args.staff}' not found in SM8")
            sys.exit(1)
        sm8_uuid_config = staff_uuid
        calendar_id = None
        preferred_start = 11
        print(f"Found SM8 UUID: {staff_uuid}")
        print("WARNING: No calendar ID for this staff — skipping calendar check")

    # ── Fetch all three calendars ────────────────────────────────────────────
    all_events = []

    # 1. SM8 Paint + Clean — existing site visits (HARD blocks)
    print(f"\n--- SM8 Scheduled Activities — {date} ---")
    sm8_acts = fetch_sm8_activities(sm8_uuid_config, date)
    if sm8_acts:
        for e in sm8_acts:
            s = e["start"].strftime("%H:%M")
            f = e["end"].strftime("%H:%M")
            print(f"  {s}–{f}  {e['summary']}  [{e['source']}]")
        all_events.extend(sm8_acts)
    else:
        print("  No existing site visits")

    # 2. Google Calendar — time blocks + meetings
    if calendar_id:
        print(f"\n--- Google Calendar — {date} ---")
        gcal_events = fetch_events(calendar_id, date)
        if gcal_events:
            for e in gcal_events:
                s = e["start"].strftime("%H:%M")
                f = e["end"].strftime("%H:%M")
                tag = " [recurring]" if e.get("recurring") else " [MEETING]"
                print(f"  {s}–{f}  {e['summary']}{tag}")
            all_events.extend(gcal_events)
        else:
            print("  No events — day is clear")

    # ── Find slots (using merged events) ──────────────────────────────────────
    slots = find_open_slots(all_events, date, args.duration, preferred_start)
    print(f"\n--- Available {args.duration}-min slots (preferred {preferred_start}:00+) ---")
    print("  Recurring time blocks are soft — site visits can override them.")
    if not slots:
        print("  No open slots (hard conflicts block entire day)!")
        if args.check_only:
            return
        print("  Override with --time to force a booking")
    else:
        for i, (s, e, soft_hits) in enumerate(slots[:8]):
            marker = " <-- BEST" if i == 0 else ""
            override = f"  (overrides: {', '.join(soft_hits)})" if soft_hits else ""
            print(f"  {s.strftime('%H:%M')}–{e.strftime('%H:%M')}{marker}{override}")

    if args.check_only:
        return

    # ── Determine booking time ────────────────────────────────────────────────
    if args.time:
        h, m = map(int, args.time.split(":"))
        start_dt = datetime(date.year, date.month, date.day, h, m, 0, tzinfo=AEST)
    elif slots:
        start_dt = slots[0][0]
        print(f"\nNo --time specified. Using best slot: {start_dt.strftime('%H:%M')}")
    else:
        print("\nERROR: No time specified and no open slots. Use --time to force.")
        sys.exit(1)

    end_dt = start_dt + timedelta(minutes=args.duration)

    # ── Check conflicts (hard only — recurring are expected) ──────────────────
    hard_conflicts = [e for e in all_events if not e.get("recurring")]
    real_conflicts = check_conflict(hard_conflicts, start_dt, end_dt)
    if real_conflicts:
        print(f"\nWARNING: Hard conflict at {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}:")
        for c in real_conflicts:
            print(f"  {c['start'].strftime('%H:%M')}–{c['end'].strftime('%H:%M')}  {c['summary']}")
        print("This is a real meeting, not a time block. Proceeding — but flag this.")

    # ── Find SM8 job ──────────────────────────────────────────────────────────
    print(f"\nLooking up SM8 job {args.job}...")
    job = find_sm8_job(args.job, api_key)
    job_uuid = job["uuid"]
    print(f"Found: {job.get('generated_job_id')} — {job.get('job_address', 'no address')}")

    # ── Schedule ──────────────────────────────────────────────────────────────
    print(f"\nScheduling site visit: {start_dt.strftime('%Y-%m-%d %H:%M')}–{end_dt.strftime('%H:%M')}...")
    activity_uuid = schedule_activity(job_uuid, staff_uuid, start_dt, end_dt, api_key)

    print(f"""
─────────────────────────────────────────
Site Visit Scheduled
─────────────────────────────────────────
Job:      {args.job}
Staff:    {args.staff.title()}
Date:     {date}
Time:     {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}
Duration: {args.duration} min
Activity: {activity_uuid}
─────────────────────────────────────────
""")


if __name__ == "__main__":
    main()
