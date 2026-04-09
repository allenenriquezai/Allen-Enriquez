"""
Post-call processor: fetches JustCall transcript for a Pipedrive deal and
writes the raw transcript + metadata to .tmp/ for the CRM-notes agent to format.

Modes:
  --call-id   Direct JustCall call ID (skips phone lookup)
  --deal-id   Pipedrive deal ID → looks up contact phone → finds most recent call

Usage:
    python3 tools/process_call.py --deal-id 123
    python3 tools/process_call.py --deal-id 123 --call-id 456
    python3 tools/process_call.py --deal-id 123 --call-type discovery

Output (JSON to stdout):
    { deal, contact, call_id, duration, direction, transcript_file }

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY, PIPEDRIVE_COMPANY_DOMAIN
    JUSTCALL_API_KEY, JUSTCALL_API_SECRET
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"
TMP_DIR = BASE_DIR / "projects" / "eps" / ".tmp"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def api_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def pipedrive_get(path, env):
    domain = env["PIPEDRIVE_COMPANY_DOMAIN"]
    key = env["PIPEDRIVE_API_KEY"]
    url = f"https://{domain}/api/v1/{path}"
    sep = "&" if "?" in path else "?"
    url += f"{sep}api_token={key}"
    return api_get(url)


def justcall_headers(env):
    token = base64.b64encode(
        f"{env['JUSTCALL_API_KEY']}:{env['JUSTCALL_API_SECRET']}".encode()
    ).decode()
    return {"Accept": "application/json", "Authorization": f"Basic {token}"}


# ── Pipedrive helpers ──────────────────────────────────────────────


def get_deal(deal_id, env):
    data = pipedrive_get(f"deals/{deal_id}", env)
    deal = data.get("data")
    if not deal:
        print(f"ERROR: Deal {deal_id} not found in Pipedrive", file=sys.stderr)
        sys.exit(1)
    return deal


def get_person_phone(person_id, env):
    data = pipedrive_get(f"persons/{person_id}", env)
    person = data.get("data", {})
    phones = person.get("phone", [])
    for p in phones:
        val = p.get("value", "").strip()
        if val:
            return val, person.get("name", "")
    return None, person.get("name", "")


def get_call_id_from_notes(deal_id, env):
    """Fallback: scan recent Pipedrive notes for a JustCall Call ID."""
    data = pipedrive_get(
        f"deals/{deal_id}/notes?limit=20&sort=add_time%20DESC", env
    )
    for note in data.get("data") or []:
        content = note.get("content", "")
        match = re.search(r"Call ID[:\s]+(\d+)", content)
        if match:
            return match.group(1)
    return None


def get_iq_transcript_url_from_activities(deal_id, env):
    """Scan Pipedrive activities for a JustCall AI transcript URL."""
    data = pipedrive_get(
        f"deals/{deal_id}/activities?limit=30", env
    )
    # Sort by ID descending to check most recent first
    activities = sorted(data.get("data") or [], key=lambda a: a.get("id", 0), reverse=True)
    for activity in activities:
        note = activity.get("note", "") or ""
        match = re.search(r'(https://iq-app\.justcall\.io/app/(?:voicetranscript|meetingtranscript)[^\s"<>]+)', note)
        if match:
            return match.group(1)
    return None


# ── JustCall helpers ───────────────────────────────────────────────


def find_calls_by_phone(phone, env):
    """Search JustCall for calls matching a phone number."""
    headers = justcall_headers(env)
    # Normalise: keep only digits and leading +
    clean = re.sub(r"[^\d+]", "", phone)
    url = f"https://api.justcall.io/v2/calls?contact_number={clean}&per_page=5&sort=desc"
    try:
        data = api_get(url, headers)
        return data.get("data", [])
    except Exception:
        return []


def get_call(call_id, env):
    headers = justcall_headers(env)
    url = f"https://api.justcall.io/v2/calls/{call_id}"
    data = api_get(url, headers)
    return data.get("data", {})


def extract_transcript(call_data):
    """Try multiple fields where JustCall stores transcripts."""
    for key in ("transcript", "ai_transcript", "call_transcript"):
        val = call_data.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return None


# ── Main ───────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Fetch JustCall transcript for a Pipedrive deal")
    parser.add_argument("--deal-id", required=True, help="Pipedrive deal ID")
    parser.add_argument("--call-id", help="JustCall call ID (skip phone lookup)")
    parser.add_argument(
        "--call-type",
        default="general",
        help="Call type label: discovery, follow-up, site-visit, cold-call, general",
    )
    args = parser.parse_args()

    env = load_env()
    for key in ("PIPEDRIVE_API_KEY", "PIPEDRIVE_COMPANY_DOMAIN", "JUSTCALL_API_KEY", "JUSTCALL_API_SECRET"):
        if not env.get(key):
            print(f"ERROR: {key} not set in projects/eps/.env", file=sys.stderr)
            sys.exit(1)

    # 1. Get deal info
    deal = get_deal(args.deal_id, env)
    deal_title = deal.get("title", "")
    person_id = None
    if deal.get("person_id"):
        person_id = deal["person_id"].get("value") if isinstance(deal["person_id"], dict) else deal["person_id"]
    org_id = None
    if deal.get("org_id"):
        org_id = deal["org_id"].get("value") if isinstance(deal["org_id"], dict) else deal["org_id"]

    # 2. Resolve call ID
    call_id = args.call_id
    contact_name = ""
    contact_phone = ""

    if not call_id and person_id:
        contact_phone, contact_name = get_person_phone(person_id, env)
        if contact_phone:
            calls = find_calls_by_phone(contact_phone, env)
            if calls:
                call_id = str(calls[0].get("id", ""))

    if not call_id:
        # Fallback: scan Pipedrive notes for Call ID
        call_id = get_call_id_from_notes(args.deal_id, env)

    if not call_id:
        print("ERROR: Could not find a JustCall call for this deal. "
              "Provide --call-id directly or ensure a call exists.", file=sys.stderr)
        sys.exit(1)

    # 3. Fetch the call + transcript
    call_data = get_call(call_id, env)
    transcript = extract_transcript(call_data)

    if not transcript:
        # Fallback: look for JustCall AI transcript URL in Pipedrive activities
        iq_url = get_iq_transcript_url_from_activities(args.deal_id, env)
        if iq_url:
            print(json.dumps({
                "status": "transcript_url",
                "call_id": call_id,
                "iq_transcript_url": iq_url,
                "message": "Transcript available via JustCall AI link — fetch via browser."
            }))
            sys.exit(0)
        print(json.dumps({
            "status": "transcript_not_ready",
            "call_id": call_id,
            "message": "Transcript isn't ready yet — try again in a few minutes."
        }))
        sys.exit(0)

    # 4. Write transcript to .tmp
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    transcript_file = TMP_DIR / f"transcript_{args.deal_id}.txt"
    transcript_file.write_text(transcript)

    # 5. Build metadata
    result = {
        "status": "ok",
        "deal_id": int(args.deal_id),
        "deal_title": deal_title,
        "person_id": person_id,
        "org_id": org_id,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "call_id": call_id,
        "call_type": args.call_type,
        "duration": call_data.get("duration") or call_data.get("call_duration"),
        "direction": call_data.get("direction") or call_data.get("type"),
        "datetime": call_data.get("datetime") or call_data.get("call_date"),
        "transcript_file": str(transcript_file),
        "transcript_length": len(transcript),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
