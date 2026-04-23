"""One-shot backfill: apply Gmail labels to Ryan's last-60-days inbox.

Reuses the already-classified messages at
    projects/personal/clients/ryan/classifications.json
(1,695 messages classified via Haiku during the audit run). NO new Haiku calls
are made here -- we just push labels to Gmail based on what's on disk.

Routing + label logic is delegated to the Cloud Run service code under
    services/ryan-labeler/{labeler,registry,config}.py
We sys.path-hack that directory and set CONFIG_DIR to the live Ryan client
folder so auto-created projects persist back to the real registry.

Usage
-----
    # Dry run (recommended first): prints what WOULD happen, no Gmail writes.
    python tools/ryan_backfill.py --dry-run

    # Smoke test on 20 messages.
    python tools/ryan_backfill.py --limit 20

    # Full run (resumable if interrupted -- state file tracks progress).
    python tools/ryan_backfill.py

    # Resume after a crash.
    python tools/ryan_backfill.py --resume

Prereq
------
Token at projects/personal/clients/ryan/token_ryan.pickle MUST have been
re-authed via tools/ryan_reauth.py to include gmail.modify + gmail.labels.
This script fails fast if those scopes aren't present.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = REPO_ROOT / "projects/personal/clients/ryan"
SERVICE_DIR = REPO_ROOT / "services/ryan-labeler"
CLASSIFICATIONS_FILE = CLIENT_DIR / "classifications.json"
STATE_FILE = CLIENT_DIR / "backfill_state.json"
TOKEN_FILE = CLIENT_DIR / "token_ryan.pickle"

REQUIRED_SCOPES = {
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
}


def check_scopes() -> None:
    """Fail fast if token lacks gmail.modify + gmail.labels."""
    if not TOKEN_FILE.exists():
        sys.exit(f"FATAL: token not found at {TOKEN_FILE}. Run tools/ryan_reauth.py first.")
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    granted = set(creds.scopes or [])
    missing = REQUIRED_SCOPES - granted
    if missing:
        sys.exit(
            "FATAL: Ryan token is missing required scopes:\n  "
            + "\n  ".join(sorted(missing))
            + "\n\nRun tools/ryan_reauth.py to upgrade the token."
        )


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "processed_ids": [],
        "counts": {},
        "errors": [],
        "started_at": None,
        "last_id": None,
    }


def save_state_atomic(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def build_classification(raw: dict) -> dict:
    """Turn the lean {category, project_hint} entry into the full classifier shape."""
    return {
        "category": raw.get("category") or "other",
        "project_hint": raw.get("project_hint"),
        "confidence": 0.85,  # already Haiku-classified during audit
        "reason": "backfill-from-audit",
        "took_ms": 0,
    }


def label_with_retry(labeler, message_id: str, classification: dict, dry_run: bool,
                     verbose: bool) -> dict:
    """Call route_and_label with exponential backoff on 429 / transient HttpError."""
    from googleapiclient.errors import HttpError
    for attempt in range(4):
        try:
            return labeler.route_and_label(message_id, classification, dry_run=dry_run)
        except HttpError as e:
            msg = str(e)
            transient = (
                "429" in msg or "rateLimit" in msg.lower()
                or "concurrent" in msg.lower() or "500" in msg or "503" in msg
            )
            if transient and attempt < 3:
                wait = 2 ** attempt + 0.5
                if verbose:
                    print(f"  rate/transient (attempt {attempt+1}) waiting {wait:.1f}s: {msg[:120]}",
                          file=sys.stderr)
                time.sleep(wait)
                continue
            return {
                "dry_run": dry_run,
                "message_id": message_id,
                "bucket": classification["category"],
                "applied": False,
                "error": msg,
            }
    return {
        "dry_run": dry_run,
        "message_id": message_id,
        "bucket": classification["category"],
        "applied": False,
        "error": "exhausted retries",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill Ryan's inbox with Gmail labels.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Only process the first N messages (for testing).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what WOULD happen; no Gmail calls.")
    ap.add_argument("--resume", action="store_true",
                    help="Skip message IDs already recorded in the state file.")
    ap.add_argument("--verbose", action="store_true",
                    help="Log every message outcome, not just every 50th.")
    args = ap.parse_args()

    check_scopes()

    if not CLASSIFICATIONS_FILE.exists():
        sys.exit(f"FATAL: classifications not found at {CLASSIFICATIONS_FILE}")

    # Point the service code at the real Ryan config BEFORE importing it.
    os.environ["CONFIG_DIR"] = str(CLIENT_DIR)
    sys.path.insert(0, str(SERVICE_DIR))
    import labeler  # noqa: E402
    import registry  # noqa: E402  (imported to force load; used indirectly)
    import config as svc_config  # noqa: E402

    _ = registry  # keep import alive for side effects / linting

    # Sanity-check the config loader is reading from the right place.
    if svc_config.CONFIG_DIR != Path(str(CLIENT_DIR)):
        sys.exit(f"FATAL: service config.CONFIG_DIR={svc_config.CONFIG_DIR} != {CLIENT_DIR}")

    classifications: dict[str, dict] = json.loads(CLASSIFICATIONS_FILE.read_text())
    all_ids = list(classifications.keys())
    total = len(all_ids)
    print(f"Loaded {total} classifications from {CLASSIFICATIONS_FILE.name}")

    state = load_state() if args.resume else {
        "processed_ids": [], "counts": {}, "errors": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_id": None,
    }
    if args.resume:
        print(f"Resuming: {len(state['processed_ids'])} already processed.")
    if not state.get("started_at"):
        state["started_at"] = datetime.now(timezone.utc).isoformat()

    done_set = set(state["processed_ids"])
    counts: Counter = Counter(state.get("counts", {}))
    errors: list = list(state.get("errors", []))

    work_ids = [mid for mid in all_ids if mid not in done_set]
    if args.limit is not None:
        work_ids = work_ids[: args.limit]
    print(f"Processing {len(work_ids)} messages "
          f"(dry_run={args.dry_run}, limit={args.limit}, resume={args.resume})")

    start_wall = time.time()
    processed_this_run = 0
    for i, mid in enumerate(work_ids, 1):
        classification = build_classification(classifications[mid])
        result = label_with_retry(labeler, mid, classification,
                                  dry_run=args.dry_run, verbose=args.verbose)

        bucket = result.get("bucket", "unknown")
        counts[bucket] += 1
        if result.get("error"):
            errors.append({"id": mid, "bucket": bucket, "error": result["error"]})
            if args.verbose:
                print(f"  ERR {mid}: {result['error'][:200]}", file=sys.stderr)
        elif args.verbose:
            added = result.get("labels_added") or result.get("would_add") or []
            print(f"  OK  {mid} -> {bucket} :: {added}")

        state["processed_ids"].append(mid)
        state["last_id"] = mid
        processed_this_run += 1

        # Simple throttle (Gmail modify quota = 250 units/user/sec; modify = 5 units).
        if not args.dry_run:
            time.sleep(0.1)

        if i % 50 == 0:
            elapsed = time.time() - start_wall
            rate = processed_this_run / elapsed if elapsed else 0
            top = ", ".join(f"{b}:{c}" for b, c in counts.most_common(6))
            print(f"  {i}/{len(work_ids)} labeled ({rate:.1f} msg/s) -- {top}")
            state["counts"] = dict(counts)
            state["errors"] = errors
            save_state_atomic(state)

    # Final state flush.
    state["counts"] = dict(counts)
    state["errors"] = errors
    save_state_atomic(state)

    elapsed = time.time() - start_wall
    print("\n=== Backfill summary ===")
    print(f"Processed this run : {processed_this_run}")
    print(f"Total recorded     : {len(state['processed_ids'])} / {total}")
    print(f"Elapsed            : {elapsed:.1f}s "
          f"({processed_this_run / elapsed:.1f} msg/s)" if elapsed else "")
    print("Per-bucket counts  :")
    for bucket, n in counts.most_common():
        print(f"  {bucket:<15} {n}")
    if errors:
        print(f"\nErrors: {len(errors)} (first 10)")
        for e in errors[:10]:
            print(f"  {e['id']} [{e['bucket']}]: {e['error'][:160]}")
    else:
        print("\nNo errors.")
    print(f"\nState file: {STATE_FILE}")
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
