"""
Daily automation status report — sends a WhatsApp summary of all launchd jobs.

Checks launchctl for enriquezOS jobs, reads log tails for errors,
pulls CRM sync metrics, and sends a formatted WhatsApp message.

Usage:
    python3 tools/shared/automation_status.py              # Send report to WhatsApp
    python3 tools/shared/automation_status.py --dry-run    # Print message only, don't send

Scheduled daily at 17:30 PH time via launchd.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- Setup ----------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / ".tmp"

from tools.eps import whatsapp

# Allen's WhatsApp number — UPDATE THIS with actual number
ALLEN_PHONE = "639454203195"

# Map of launchd labels to friendly names and their log files
JOBS = {
    "com.enriquezOS.eps-dashboard": {
        "name": "EPS Dashboard",
        "logs": ["eps-dashboard.log"],
        "error_logs": ["eps-dashboard-error.log"],
    },
    "com.enriquezOS.eod-ops": {
        "name": "EOD Ops + CRM Sync",
        "logs": ["eod-ops.log"],
        "error_logs": ["eod-ops-error.log"],
    },
    "com.enriquezOS.crm-sync": {
        "name": "CRM Sync (10min)",
        "logs": ["crm-sync.log"],
        "error_logs": ["crm-sync-error.log"],
    },
    "com.enriquezOS.morning-briefing": {
        "name": "Morning Briefing",
        "logs": ["briefing-cron.log"],
        "error_logs": ["briefing-cron-error.log"],
    },
    "com.enriquezOS.jibble-clockin": {
        "name": "Jibble Clock-In",
        "logs": ["jibble-clockin.log"],
        "error_logs": ["jibble-clockin-error.log"],
    },
    "com.enriquezOS.ai-learning-brief": {
        "name": "AI Learning Brief",
        "logs": ["ai-learning-brief-cron.log"],
        "error_logs": ["ai-learning-brief-cron-error.log"],
    },
    "com.enriquezOS.briefing-action-loop": {
        "name": "Briefing Action Loop",
        "logs": ["action-loop-cron.log"],
        "error_logs": ["action-loop-cron-error.log"],
    },
    "com.enriquezOS.dashboard": {
        "name": "Personal Dashboard",
        "logs": ["dashboard.log"],
        "error_logs": ["dashboard-error.log"],
    },
    "com.enriquezOS.personal-crm-cleanup": {
        "name": "Personal CRM Cleanup",
        "logs": ["personal-crm-cleanup.log"],
        "error_logs": [],
    },
    "com.enriquezOS.tender-batch": {
        "name": "Tender Batch",
        "logs": ["tender-batch.log"],
        "error_logs": ["tender-batch-error.log"],
    },
    "com.enriquezOS.reengage-campaign": {
        "name": "Re-engage Campaign",
        "logs": [],
        "error_logs": [],
    },
}

# Exit codes that mean "not a real error"
# 78 = launchd couldn't find plist / config issue (common for disabled jobs)
KNOWN_CODES = {
    0: "OK",
    1: "Error",
    78: "No manifest",
}


# --- Helpers --------------------------------------------------------------


def get_launchctl_jobs() -> dict:
    """Run launchctl list, return {label: (pid, exit_code)} for enriquezOS jobs."""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, timeout=10,
        )
        jobs = {}
        for line in result.stdout.strip().split("\n"):
            if "enriquezOS" not in line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            pid_str, exit_str, label = parts[0], parts[1], parts[2]
            pid = int(pid_str) if pid_str != "-" else None
            exit_code = int(exit_str) if exit_str.strip() else 0
            jobs[label.strip()] = (pid, exit_code)
        return jobs
    except Exception as e:
        print(f"ERROR reading launchctl: {e}", file=sys.stderr)
        return {}


def tail_file(filepath: Path, lines: int = 5) -> str:
    """Read last N lines of a file. Returns empty string if file missing."""
    if not filepath.exists():
        return ""
    try:
        text = filepath.read_text(errors="replace")
        return "\n".join(text.strip().split("\n")[-lines:])
    except Exception:
        return ""


def check_log_errors(job_config: dict):
    """Check error logs for recent issues. Returns error snippet or None."""
    for log_name in job_config.get("error_logs", []):
        log_path = TMP_DIR / log_name
        tail = tail_file(log_path, lines=5)
        if tail.strip():
            # Check for actual errors (not just empty or info lines)
            lower = tail.lower()
            for keyword in ["error", "traceback", "exception", "failed", "refused", "conflict", "denied"]:
                if keyword in lower:
                    # Return first meaningful error line
                    for line in tail.split("\n"):
                        if keyword in line.lower():
                            return line.strip()[:80]
                    return tail.split("\n")[-1].strip()[:80]
    return None


def get_crm_metrics():
    """Read CRM sync metrics from .tmp/crm_sync.json."""
    sync_file = TMP_DIR / "crm_sync.json"
    if not sync_file.exists():
        return None
    try:
        data = json.loads(sync_file.read_text())
        return data
    except Exception:
        return None


def format_job_status(label, config, pid, exit_code):
    """Format a single job's status line."""
    name = config["name"]

    # Check if running (has PID)
    if pid is not None:
        return f"  *Running (PID {pid})*"

    # Check error logs for details
    log_error = check_log_errors(config)

    if exit_code == 0:
        return f"  OK"
    elif exit_code == 78:
        return f"  No manifest"
    elif log_error:
        return f"  Exit {exit_code} — {log_error}"
    else:
        code_desc = KNOWN_CODES.get(exit_code, f"Exit {exit_code}")
        return f"  {code_desc}"


def pick_emoji(pid, exit_code):
    """Pick status emoji."""
    if pid is not None:
        return "\u2705"  # running
    if exit_code == 0:
        return "\u2705"  # OK
    if exit_code == 78:
        return "\u274c"  # no manifest
    return "\u26a0\ufe0f"  # warning/error


def build_message() -> str:
    """Build the full status report message."""
    now = datetime.now()
    date_str = now.strftime("%-d %b %Y, %-I:%M %p")

    launchctl_jobs = get_launchctl_jobs()
    crm = get_crm_metrics()

    lines = [
        "\U0001f4ca *Enriquez OS \u2014 Daily Report*",
        f"{date_str}",
        "",
    ]

    # Job statuses
    for label, config in JOBS.items():
        name = config["name"]
        if label in launchctl_jobs:
            pid, exit_code = launchctl_jobs[label]
            emoji = pick_emoji(pid, exit_code)
            status = format_job_status(label, config, pid, exit_code)
            # Add CRM sync metric inline
            if label == "com.enriquezOS.crm-sync" and crm and exit_code == 0 and pid is None:
                activities = crm.get("activities_posted", 0)
                notes = crm.get("notes_synced", 0)
                status = f"  OK ({activities} activities, {notes} notes)"
            lines.append(f"{emoji} *{name}* \u2014{status}")
        else:
            lines.append(f"\u2753 *{name}* \u2014 Not registered")

    # Any jobs in launchctl not in our map
    for label in launchctl_jobs:
        if label not in JOBS and "enriquezOS" in label:
            pid, exit_code = launchctl_jobs[label]
            emoji = pick_emoji(pid, exit_code)
            short_name = label.replace("com.enriquezOS.", "")
            lines.append(f"{emoji} *{short_name}* \u2014 (unlisted)")

    # CRM metrics footer
    if crm:
        lines.append("")
        deals = crm.get("deals_checked", 0)
        sm8 = crm.get("deals_with_sm8", 0)
        notes = crm.get("notes_synced", 0)
        activities = crm.get("activities_posted", 0)
        lines.append(f"Pipeline: {deals} deals synced")
        lines.append(f"SM8: {sm8} deals | {notes} notes | {activities} activities")

    return "\n".join(lines)


# --- Main -----------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Send daily automation status via WhatsApp")
    parser.add_argument("--dry-run", action="store_true", help="Print message without sending")
    parser.add_argument("--to", default=ALLEN_PHONE, help="Override recipient phone number")
    args = parser.parse_args()

    message = build_message()

    if args.dry_run:
        print(message)
        print("\n--- DRY RUN: Message not sent ---")
        return

    if "XXXXXXXXXX" in args.to:
        print("ERROR: Allen's phone number not configured.", file=sys.stderr)
        print("Update ALLEN_PHONE in tools/automation_status.py or pass --to", file=sys.stderr)
        print("\nMessage that would be sent:")
        print(message)
        sys.exit(1)

    try:
        result = whatsapp.send_message(args.to, message)
        msg_id = result.get("messages", [{}])[0].get("id", "unknown")
        print(f"Sent. Message ID: {msg_id}")
    except Exception as e:
        print(f"ERROR sending WhatsApp: {e}", file=sys.stderr)
        print("\nMessage content:")
        print(message)
        sys.exit(1)


if __name__ == "__main__":
    main()
