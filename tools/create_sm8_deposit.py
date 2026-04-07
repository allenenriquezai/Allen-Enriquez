"""
create_sm8_deposit.py — Create a deposit (partial invoice) in SM8.

Usage:
    python tools/create_sm8_deposit.py --deal-id 1076
    python tools/create_sm8_deposit.py --deal-id 1076 --pct 30

What it does:
    1. Reads sm8_data.json + quote_data.json from projects/eps/.tmp/
    2. Calculates deposit amount (default 50% of quote total, ex-GST)
    3. Records a deposit payment against the SM8 job (default 50% of total inc-GST)
    4. Prints the deposit amount for confirmation

NOTE: SM8's API records payments received (JobPayment endpoint).
If you need SM8 to generate and send an invoice PDF to the client,
that currently requires: SM8 UI → Job → Invoice → Partial Invoice.
This script handles the backend record. Invoice sending = manual step for now.
"""

import argparse
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
EPS_DIR = ROOT / "projects" / "eps"
TMP_DIR = EPS_DIR / ".tmp"

load_dotenv(EPS_DIR / ".env")

# ── config ────────────────────────────────────────────────────────────────────
SM8_API_KEY_CLEAN = os.getenv("SM8_API_KEY_CLEAN")
SM8_API_KEY_PAINT = os.getenv("SM8_API_KEY_PAINT")
SM8_BASE_URL = "https://api.servicem8.com/api_1.0"

PIPELINE_API_KEYS = {
    "EPS Clean": SM8_API_KEY_CLEAN,
    "EPS Paint": SM8_API_KEY_PAINT,
}

DEFAULT_DEPOSIT_PCT = 50


def sm8_post(path, api_key, payload):
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{SM8_BASE_URL}{path}"
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deal-id", required=True, help="Pipedrive deal ID")
    parser.add_argument(
        "--pct",
        type=float,
        default=DEFAULT_DEPOSIT_PCT,
        help=f"Deposit percentage (default: {DEFAULT_DEPOSIT_PCT})",
    )
    args = parser.parse_args()

    # ── load tmp data ──────────────────────────────────────────────────────────
    sm8_path = TMP_DIR / "sm8_data.json"
    quote_path = TMP_DIR / "quote_data.json"

    for path in [sm8_path, quote_path]:
        if not path.exists():
            print(f"ERROR: {path} not found.")
            print("Run push_sm8_job.py first.")
            sys.exit(1)

    with open(sm8_path) as f:
        sm8_data = json.load(f)

    with open(quote_path) as f:
        quote = json.load(f)

    # ── validate deal match ────────────────────────────────────────────────────
    if sm8_data["deal_id"] != args.deal_id:
        print(
            f"WARNING: sm8_data.json is for deal #{sm8_data['deal_id']}, "
            f"but you passed --deal-id {args.deal_id}."
        )
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != "y":
            sys.exit(0)

    sm8_uuid = sm8_data["sm8_job_uuid"]
    pipeline = sm8_data["pipeline"]
    api_key = PIPELINE_API_KEYS.get(pipeline)

    if not api_key:
        env_var = "SM8_API_KEY_CLEAN" if pipeline == "EPS Clean" else "SM8_API_KEY_PAINT"
        print(f"ERROR: {env_var} is not set in .env")
        sys.exit(1)

    # ── calculate deposit ──────────────────────────────────────────────────────
    total_inc_gst = quote["total"]
    deposit_amount = round(total_inc_gst * args.pct / 100, 2)

    print(f"\nDeposit calculation:")
    print(f"  Quote total (inc GST): ${total_inc_gst:,.2f}")
    print(f"  Deposit:               {args.pct}% = ${deposit_amount:,.2f}")
    print(f"  SM8 Job:               {sm8_data['sm8_job_number']}")
    print(f"  Pipeline:              {pipeline}")

    confirm = input("\nCreate deposit payment record in SM8? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        sys.exit(0)

    # ── create payment record in SM8 ───────────────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "job_uuid": sm8_uuid,
        "amount": str(deposit_amount),
        "timestamp": now,
        "note": f"{int(args.pct)}% deposit — {quote['quote_title']}",
    }

    print("\nCreating deposit payment in SM8...")
    sm8_post("/jobpayment.json", api_key, payload)
    print("Payment record created.")

    # ── summary ────────────────────────────────────────────────────────────────
    print(f"""
─────────────────────────────────────────
Deposit Recorded
─────────────────────────────────────────
Deal:          #{args.deal_id}
SM8 Job:       {sm8_data['sm8_job_number']}
Deposit:       {args.pct}% = ${deposit_amount:,.2f}
─────────────────────────────────────────
NEXT STEP (manual):
Open SM8 → find job {sm8_data['sm8_job_number']} →
Invoices → New Partial Invoice → set amount to ${deposit_amount:,.2f}
Send invoice to client from SM8.
─────────────────────────────────────────
""")


if __name__ == "__main__":
    main()
