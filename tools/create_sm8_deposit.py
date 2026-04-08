"""
create_sm8_deposit.py — Calculate deposit amount for a job.

Usage:
    python tools/create_sm8_deposit.py --deal-id 1076
    python tools/create_sm8_deposit.py --deal-id 1076 --pct 30
    python tools/create_sm8_deposit.py --deal-id 1076 --amount 50

What it does:
    1. Reads sm8_data.json (+ quote_data.json if using --pct) from projects/eps/.tmp/
    2. Calculates deposit amount
    3. Prints the SM8 job details and deposit amount to use in the SM8 UI

NOTE: SM8's REST API does not support creating invoices or partial invoices.
The partial invoice must be created in the SM8 UI:
    Billing → Send Quote → Partial Invoice → set amount → Send
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
EPS_DIR = ROOT / "projects" / "eps"
TMP_DIR = EPS_DIR / ".tmp"

load_dotenv(EPS_DIR / ".env")

DEFAULT_DEPOSIT_PCT = 50


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deal-id", required=True, help="Pipedrive deal ID")
    parser.add_argument(
        "--pct",
        type=float,
        help=f"Deposit as percentage of quote total (default: {DEFAULT_DEPOSIT_PCT})",
    )
    parser.add_argument(
        "--amount",
        type=float,
        help="Deposit as a fixed dollar amount (inc GST)",
    )
    args = parser.parse_args()

    if args.amount and args.pct:
        print("ERROR: Use --amount or --pct, not both.")
        sys.exit(1)

    # ── load sm8 data ──────────────────────────────────────────────────────────
    sm8_path = TMP_DIR / "sm8_data.json"
    if not sm8_path.exists():
        print(f"ERROR: {sm8_path} not found. Run push_sm8_job.py first.")
        sys.exit(1)

    with open(sm8_path) as f:
        sm8_data = json.load(f)

    if sm8_data["deal_id"] != args.deal_id:
        print(
            f"WARNING: sm8_data.json is for deal #{sm8_data['deal_id']}, "
            f"but you passed --deal-id {args.deal_id}."
        )
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != "y":
            sys.exit(0)

    # ── calculate deposit ──────────────────────────────────────────────────────
    if args.amount:
        deposit_amount = round(args.amount, 2)
        pct_label = "fixed"
    else:
        quote_path = TMP_DIR / "quote_data.json"
        if not quote_path.exists():
            print(f"ERROR: {quote_path} not found. Use --amount for a fixed dollar deposit.")
            sys.exit(1)
        with open(quote_path) as f:
            quote = json.load(f)
        pct = args.pct if args.pct else DEFAULT_DEPOSIT_PCT
        total_inc_gst = quote["total"]
        deposit_amount = round(total_inc_gst * pct / 100, 2)
        pct_label = f"{pct}%"
        print(f"  Quote total (inc GST): ${total_inc_gst:,.2f}")

    # ── print instructions ─────────────────────────────────────────────────────
    print(f"""
─────────────────────────────────────────
Deposit Invoice — Manual Step Required
─────────────────────────────────────────
Deal:          #{args.deal_id}
SM8 Job:       {sm8_data['sm8_job_number']}
Pipeline:      {sm8_data['pipeline']}
Deposit:       {pct_label} = ${deposit_amount:,.2f}
─────────────────────────────────────────
In SM8:
  1. Open job {sm8_data['sm8_job_number']}
  2. Billing → Send Quote → Partial Invoice
  3. Set amount to ${deposit_amount:,.2f}
  4. Send to client
─────────────────────────────────────────
""")


if __name__ == "__main__":
    main()
