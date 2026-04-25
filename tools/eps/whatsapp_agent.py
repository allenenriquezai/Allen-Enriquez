"""
WhatsApp auto-reply agent — reads inbox, classifies messages, replies or escalates.

Uses Haiku for understanding + Pipedrive API for deal lookups.
EPS-only. No personal data access.

Usage:
    # Process unread messages (dry run — no replies sent)
    python3 tools/whatsapp_agent.py --dry-run

    # Process unread messages (live — sends replies)
    python3 tools/whatsapp_agent.py

    # Process and show detailed reasoning
    python3 tools/whatsapp_agent.py --verbose

    # Stress test with simulated messages
    python3 tools/whatsapp_agent.py --stress-test

Requires in projects/eps/.env:
    WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
    PIPEDRIVE_API_KEY, PIPEDRIVE_COMPANY_DOMAIN

Requires in projects/personal/.env:
    ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
SHARED_ENV = BASE_DIR / "projects" / ".env"
EPS_ENV = BASE_DIR / "projects" / "eps" / ".env"
PERSONAL_ENV = BASE_DIR / "projects" / "personal" / ".env"
INBOX_FILE = BASE_DIR / "projects" / "eps" / ".tmp" / "whatsapp_inbox.json"
ACTIONS_FILE = BASE_DIR / "projects" / "eps" / ".tmp" / "whatsapp_pending_actions.json"
LOG_FILE = BASE_DIR / "projects" / "eps" / ".tmp" / "whatsapp_agent.log"


def load_env(path):
    env = {}
    if not path.exists():
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# Load credentials
SHARED = load_env(SHARED_ENV)
EPS = load_env(EPS_ENV)
PERSONAL = load_env(PERSONAL_ENV)

ANTHROPIC_API_KEY = PERSONAL.get("ANTHROPIC_API_KEY") or SHARED.get("ANTHROPIC_API_KEY", "")
PIPEDRIVE_API_KEY = EPS.get("PIPEDRIVE_API_KEY", "")
PIPEDRIVE_DOMAIN = EPS.get("PIPEDRIVE_COMPANY_DOMAIN", "api.pipedrive.com")
WHATSAPP_TOKEN = EPS.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_ID = EPS.get("WHATSAPP_PHONE_NUMBER_ID", "")


# ── Pipedrive helpers ──

def pipedrive_search(query: str, item_type: str = "deal") -> list:
    """Search Pipedrive for deals, persons, or organizations."""
    params = urllib.parse.urlencode({
        "term": query,
        "item_types": item_type,
        "limit": 5,
        "api_token": PIPEDRIVE_API_KEY,
    })
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1/itemSearch?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("data", {}).get("items", [])
    except Exception as e:
        return [{"error": str(e)}]


def pipedrive_get_deal(deal_id: int) -> dict:
    """Get deal details by ID."""
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1/deals/{deal_id}?api_token={PIPEDRIVE_API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("data", {})
    except Exception as e:
        return {"error": str(e)}


def pipedrive_get_deal_activities(deal_id: int) -> list:
    """Get activities for a deal."""
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1/deals/{deal_id}/activities?api_token={PIPEDRIVE_API_KEY}&limit=5"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("data", []) or []
    except Exception as e:
        return [{"error": str(e)}]


# ── WhatsApp helpers ──

def send_whatsapp(to: str, message: str) -> dict:
    """Send a WhatsApp text message."""
    url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_ID}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


# ── Haiku classifier ──

SYSTEM_PROMPT = """You are Allen's executive assistant at EPS (Essential Property Solutions), a painting & cleaning company in Brisbane, Australia.

You reply to team members on WhatsApp. You are direct, concise, and friendly.

RULES:
- Reply in the same language the message was sent in (English, Tagalog, or Spanish)
- Keep replies short — 1-3 sentences max
- You have access to Pipedrive deal data. Use it to answer questions about deals.
- NEVER share personal information about Allen outside of EPS work
- NEVER make up deal information. Only use data provided to you.

CLASSIFICATION — classify each message as one of:
- AUTO_REPLY: You can answer this directly (deal status, schedule info, basic questions)
- DRAFT_ACTION: Team wants something done (reschedule, update, follow up) — draft the action for Allen's approval
- ESCALATE: New inquiry, new client, money decisions, anything you're unsure about — flag for Allen

For AUTO_REPLY: provide the reply text.
For DRAFT_ACTION: describe the action needed and draft a short reply telling the team member you'll get back to them.
For ESCALATE: draft a short reply saying Allen will review this, and note why it's escalated.

Respond in JSON format:
{
    "classification": "AUTO_REPLY" | "DRAFT_ACTION" | "ESCALATE",
    "reply": "the message to send back to the team member",
    "action": "description of action needed (for DRAFT_ACTION only, null otherwise)",
    "reason": "brief internal note on why this was classified this way"
}"""


def classify_message(sender_name: str, message: str, deal_context: str = "") -> dict:
    """Use Haiku to classify and respond to a message."""
    user_content = f"From: {sender_name}\nMessage: {message}"
    if deal_context:
        user_content += f"\n\nRelevant deal data from Pipedrive:\n{deal_context}"

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        text = data.get("content", [{}])[0].get("text", "")
        # Extract JSON from response
        if "{" in text:
            json_str = text[text.index("{"):text.rindex("}") + 1]
            return json.loads(json_str)
        return {"classification": "ESCALATE", "reply": "Allen will review this.", "reason": "Failed to parse response"}
    except Exception as e:
        return {"classification": "ESCALATE", "reply": "Allen will review this shortly.", "reason": f"Error: {e}"}


def get_deal_context(message: str) -> str:
    """Search Pipedrive for deals mentioned in the message."""
    # Try to find deal references in the message
    results = pipedrive_search(message, "deal")
    if not results or (results and "error" in results[0]):
        return ""

    context_parts = []
    for item in results[:3]:
        r = item.get("item", {})
        deal_id = r.get("id")
        if deal_id:
            deal = pipedrive_get_deal(deal_id)
            if deal and "error" not in deal:
                stage = deal.get("stage_id", "")
                status = deal.get("status", "")
                org = deal.get("org_name", "")
                person = deal.get("person_name", "")
                title = deal.get("title", "")
                value = deal.get("value", 0)
                currency = deal.get("currency", "AUD")
                next_activity = deal.get("next_activity_date", "none")
                context_parts.append(
                    f"Deal #{deal_id}: {title}\n"
                    f"  Client: {person} ({org})\n"
                    f"  Status: {status} | Value: {currency} {value}\n"
                    f"  Next activity: {next_activity}"
                )
    return "\n".join(context_parts)


# ── Inbox processing ──

def load_inbox() -> list:
    if INBOX_FILE.exists():
        with open(INBOX_FILE) as f:
            return json.load(f)
    return []


def save_inbox(messages: list):
    with open(INBOX_FILE, "w") as f:
        json.dump(messages, f, indent=2)


def load_actions() -> list:
    if ACTIONS_FILE.exists():
        with open(ACTIONS_FILE) as f:
            return json.load(f)
    return []


def save_actions(actions: list):
    ACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIONS_FILE, "w") as f:
        json.dump(actions, f, indent=2)


def log(msg: str):
    ts = datetime.now().isoformat()[:19]
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(line.strip())


def process_inbox(dry_run=False, verbose=False):
    """Process all unread messages in the inbox."""
    messages = load_inbox()
    unread = [m for m in messages if not m.get("read")]

    if not unread:
        log("No unread messages.")
        return

    log(f"Processing {len(unread)} unread messages...")
    actions = load_actions()
    stats = {"auto_reply": 0, "draft_action": 0, "escalate": 0, "errors": 0}

    for msg in unread:
        sender = msg.get("name", "Unknown")
        content = msg.get("content", "")
        from_num = msg.get("from", "")

        # Skip non-text messages for now
        if msg.get("type") != "text":
            msg["read"] = True
            log(f"  Skipped non-text from {sender}: {content}")
            continue

        log(f"  Processing: {sender} — \"{content}\"")

        # Look up deal context if message seems deal-related
        deal_context = ""
        deal_keywords = ["deal", "job", "client", "quote", "reschedule", "status", "update",
                         "inspection", "paint", "clean", "tender", "schedule"]
        if any(kw in content.lower() for kw in deal_keywords):
            deal_context = get_deal_context(content)
            if verbose and deal_context:
                log(f"    Deal context found: {deal_context[:100]}...")

        # Classify with Haiku
        result = classify_message(sender, content, deal_context)
        classification = result.get("classification", "ESCALATE")
        reply = result.get("reply", "Allen will review this shortly.")
        reason = result.get("reason", "")

        if verbose:
            log(f"    Classification: {classification}")
            log(f"    Reply: {reply}")
            log(f"    Reason: {reason}")

        # Handle based on classification
        if classification == "AUTO_REPLY":
            stats["auto_reply"] += 1
            if not dry_run:
                send_whatsapp(from_num, reply)
                log(f"    → Sent auto-reply to {sender}")
            else:
                log(f"    → [DRY RUN] Would reply: {reply}")

        elif classification == "DRAFT_ACTION":
            stats["draft_action"] += 1
            action = {
                "from": sender,
                "from_number": from_num,
                "message": content,
                "action": result.get("action", ""),
                "drafted_reply": reply,
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
            }
            actions.append(action)
            if not dry_run:
                send_whatsapp(from_num, reply)
                log(f"    → Sent holding reply + queued action for Allen")
            else:
                log(f"    → [DRY RUN] Would reply: {reply} | Action: {result.get('action', '')}")

        elif classification == "ESCALATE":
            stats["escalate"] += 1
            action = {
                "from": sender,
                "from_number": from_num,
                "message": content,
                "action": f"ESCALATED: {reason}",
                "drafted_reply": "",
                "timestamp": datetime.now().isoformat(),
                "status": "escalated",
            }
            actions.append(action)
            if not dry_run:
                send_whatsapp(from_num, reply)
                log(f"    → Escalated to Allen")
            else:
                log(f"    → [DRY RUN] Would escalate: {reason}")

        msg["read"] = True
        msg["classification"] = classification
        msg["reply_sent"] = reply if not dry_run else None

    save_inbox(messages)
    save_actions(actions)

    log(f"\nDone. Auto-replied: {stats['auto_reply']} | Actions queued: {stats['draft_action']} | Escalated: {stats['escalate']}")


# ── Stress test ──

STRESS_MESSAGES = [
    # English — deal status
    {"name": "James", "from": "61400000001", "content": "Hey, how's the Smith Construction deal going?", "type": "text"},
    {"name": "Maria", "from": "61400000002", "content": "What's the status on deal 1263?", "type": "text"},
    # English — reschedule
    {"name": "James", "from": "61400000001", "content": "Can we reschedule the inspection for 123 George St to next week?", "type": "text"},
    # English — new inquiry
    {"name": "Carlos", "from": "61400000003", "content": "Hey Allen, got a new client wanting a full repaint for a 4-bedroom house in Paddington. What should I quote?", "type": "text"},
    # English — basic question
    {"name": "Maria", "from": "61400000002", "content": "What's our rate for exterior painting per sqm?", "type": "text"},
    # Tagalog — deal status
    {"name": "James", "from": "61400000001", "content": "Boss, kamusta na yung deal sa Rycon? May update ba?", "type": "text"},
    # Tagalog — basic question
    {"name": "Carlos", "from": "61400000003", "content": "Pare, anong schedule natin bukas?", "type": "text"},
    # Spanish — reschedule
    {"name": "Maria", "from": "61400000002", "content": "Oye, podemos mover la visita del miércoles al viernes?", "type": "text"},
    # Money / pricing decision
    {"name": "James", "from": "61400000001", "content": "Client is asking for 15% discount on the cleaning job. Can we do that?", "type": "text"},
    # Ambiguous / personal
    {"name": "Carlos", "from": "61400000003", "content": "Hey Allen, what are you up to this weekend?", "type": "text"},
    # Image (non-text)
    {"name": "Maria", "from": "61400000002", "content": "[Image] site photo", "type": "image"},
    # Urgent
    {"name": "James", "from": "61400000001", "content": "URGENT: client just called, water damage at the job site, what do we do?", "type": "text"},
]


def run_stress_test():
    """Run stress test with simulated messages."""
    log("=" * 60)
    log("STRESS TEST — 12 simulated messages")
    log("=" * 60)

    # Save simulated messages to inbox
    test_messages = []
    for i, m in enumerate(STRESS_MESSAGES):
        test_messages.append({
            "id": f"stress_test_{i}",
            "from": m["from"],
            "name": m["name"],
            "type": m["type"],
            "content": m["content"],
            "timestamp": str(int(time.time())),
            "received_at": datetime.now().isoformat(),
            "read": False,
        })

    # Backup existing inbox
    existing = load_inbox()
    save_inbox(test_messages)

    # Process in dry-run mode
    process_inbox(dry_run=True, verbose=True)

    # Restore original inbox
    save_inbox(existing)
    log("\nStress test complete. Original inbox restored.")


def main():
    parser = argparse.ArgumentParser(description="WhatsApp auto-reply agent")
    parser.add_argument("--dry-run", action="store_true", help="Don't send replies, just show what would happen")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed reasoning")
    parser.add_argument("--stress-test", action="store_true", help="Run stress test with simulated messages")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not found in projects/personal/.env", file=sys.stderr)
        sys.exit(1)

    if args.stress_test:
        run_stress_test()
    else:
        process_inbox(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
