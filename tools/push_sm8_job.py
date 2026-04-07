"""
push_sm8_job.py — Migrate quote data into an existing SM8 job card.

Usage:
    python tools/push_sm8_job.py --deal-id 1076

What it does:
    1. Loads quote_data.json from projects/eps/.tmp/
    2. Fetches the Pipedrive deal to get pipeline + SM8 job #
    3. Looks up the SM8 job by generated_job_id
    4. Pushes job description to the SM8 job
    5. Creates line items (JobMaterials) in SM8
    6. Moves the Pipedrive deal to DEPOSIT PROCESS stage
    7. Saves SM8 job UUID to .tmp/sm8_data.json
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
EPS_DIR = ROOT / "projects" / "eps"
TMP_DIR = EPS_DIR / ".tmp"

load_dotenv(EPS_DIR / ".env")

# ── config ────────────────────────────────────────────────────────────────────
PIPEDRIVE_API_KEY = os.getenv("PIPEDRIVE_API_KEY")
PIPEDRIVE_DOMAIN = os.getenv("PIPEDRIVE_COMPANY_DOMAIN")
SM8_API_KEY_CLEAN = os.getenv("SM8_API_KEY_CLEAN")
SM8_API_KEY_PAINT = os.getenv("SM8_API_KEY_PAINT")

SM8_JOB_FIELD_KEY = "052a8b8271d035ca4780f8ae06cd7b5370df544c"
SM8_BASE_URL = "https://api.servicem8.com/api_1.0"

PIPELINE_CONFIG = {
    1: {"name": "EPS Clean", "api_key_var": SM8_API_KEY_CLEAN, "deposit_stage": 47},
    2: {"name": "EPS Paint", "api_key_var": SM8_API_KEY_PAINT, "deposit_stage": 48},
}


def pipedrive_get(path, params=None):
    params = params or {}
    params["api_token"] = PIPEDRIVE_API_KEY
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1{path}"
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"Pipedrive error: {data}")
    return data["data"]


def pipedrive_put(path, payload):
    params = {"api_token": PIPEDRIVE_API_KEY}
    url = f"https://{PIPEDRIVE_DOMAIN}/api/v1{path}"
    r = requests.put(url, params=params, json=payload)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"Pipedrive update error: {data}")
    return data["data"]


def sm8_get(path, api_key, params=None):
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    url = f"{SM8_BASE_URL}{path}"
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


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


def find_sm8_job(job_number, api_key):
    """Look up SM8 job by generated_job_id (e.g. 'EPS-6383')."""
    jobs = sm8_get(
        "/job.json",
        api_key,
        params={"$filter": f"generated_job_id eq '{job_number}'"},
    )
    if not jobs:
        raise RuntimeError(f"No SM8 job found with generated_job_id = '{job_number}'")
    return jobs[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deal-id", required=True, help="Pipedrive deal ID")
    args = parser.parse_args()
    deal_id = args.deal_id

    # ── load quote data ────────────────────────────────────────────────────────
    quote_path = TMP_DIR / "quote_data.json"
    if not quote_path.exists():
        print(f"ERROR: {quote_path} not found. Run the quote pipeline first.")
        sys.exit(1)

    with open(quote_path) as f:
        quote = json.load(f)

    print(f"Quote loaded: {quote['quote_title']} | Total: ${quote['total']:,.2f}")

    # ── fetch Pipedrive deal ───────────────────────────────────────────────────
    print(f"\nFetching deal #{deal_id} from Pipedrive...")
    deal = pipedrive_get(f"/deals/{deal_id}")
    pipeline_id = deal["pipeline_id"]

    if pipeline_id not in PIPELINE_CONFIG:
        print(f"ERROR: Pipeline {pipeline_id} is not EPS Clean or EPS Paint. Aborting.")
        sys.exit(1)

    config = PIPELINE_CONFIG[pipeline_id]
    api_key = config["api_key_var"]
    deposit_stage = config["deposit_stage"]

    if not api_key:
        env_var = "SM8_API_KEY_CLEAN" if pipeline_id == 1 else "SM8_API_KEY_PAINT"
        print(f"ERROR: {env_var} is not set in .env")
        sys.exit(1)

    sm8_job_raw = deal.get(SM8_JOB_FIELD_KEY)
    if not sm8_job_raw:
        print("ERROR: 'Sm8 Job #' field is empty on this deal. Has the automation run?")
        sys.exit(1)

    # strip leading # → "EPS-6383"
    sm8_job_number = sm8_job_raw.lstrip("#")
    print(f"Pipeline: {config['name']} | SM8 Job: {sm8_job_raw}")

    # ── find SM8 job ───────────────────────────────────────────────────────────
    print(f"\nLooking up SM8 job {sm8_job_number}...")
    sm8_job = find_sm8_job(sm8_job_number, api_key)
    sm8_uuid = sm8_job["uuid"]
    print(f"Found: UUID = {sm8_uuid}")

    # ── push job description ───────────────────────────────────────────────────
    job_description = "\n\n".join(quote["job_description"])
    print("\nPushing job description to SM8...")
    sm8_post(f"/job/{sm8_uuid}.json", api_key, {"job_description": job_description})
    print("Job description updated.")

    # ── create line items ──────────────────────────────────────────────────────
    line_items = quote["line_items"]
    print(f"\nCreating {len(line_items)} line items in SM8...")

    for i, item in enumerate(line_items, 1):
        payload = {
            "job_uuid": sm8_uuid,
            "name": item["description"],
            "quantity": str(item["quantity"]),
            "price": str(item["rate"]),
        }
        sm8_post("/jobmaterial.json", api_key, payload)
        print(f"  [{i}/{len(line_items)}] {item['description']} — {item['quantity']} {item['unit']} @ ${item['rate']}")

    print("Line items created.")

    # ── move deal to DEPOSIT PROCESS ───────────────────────────────────────────
    print(f"\nMoving deal to DEPOSIT PROCESS (stage {deposit_stage})...")
    pipedrive_put(f"/deals/{deal_id}", {"stage_id": deposit_stage})
    print("Deal moved.")

    # ── save sm8 data ──────────────────────────────────────────────────────────
    sm8_data = {
        "deal_id": deal_id,
        "sm8_job_uuid": sm8_uuid,
        "sm8_job_number": sm8_job_number,
        "pipeline": config["name"],
    }
    sm8_path = TMP_DIR / "sm8_data.json"
    with open(sm8_path, "w") as f:
        json.dump(sm8_data, f, indent=2)

    # ── summary ────────────────────────────────────────────────────────────────
    print(f"""
─────────────────────────────────────────
SM8 Job Populated
─────────────────────────────────────────
Deal:         #{deal_id}
SM8 Job:      {sm8_job_raw}
Pipeline:     {config['name']}
Description:  pushed
Line items:   {len(line_items)} created
Pipedrive:    moved to DEPOSIT PROCESS
─────────────────────────────────────────
Next: python tools/create_sm8_deposit.py --deal-id {deal_id}
""")


if __name__ == "__main__":
    main()
