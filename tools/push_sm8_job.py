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
import uuid
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
SM8_CATALOG_PATH = EPS_DIR / "config" / "sm8_catalog.json"
CATALOG_CODE_FIELD = "item_number"   # SM8 field for item code/SKU — update if needed

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
    # Extract UUID from Location header (e.g. /api_1.0/jobmaterial/{uuid}.json)
    location = r.headers.get("Location", "")
    uuid = location.split("/")[-1].replace(".json", "") if location else None
    return r.json(), uuid


def sm8_put(path, api_key, payload):
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{SM8_BASE_URL}{path}"
    r = requests.put(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


def sm8_delete(path, api_key):
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    url = f"{SM8_BASE_URL}{path}"
    r = requests.delete(url, headers=headers)
    r.raise_for_status()


def delete_existing_line_items(sm8_uuid, api_key):
    """Deactivate all active JobMaterials for this job so re-runs are clean."""
    items = sm8_get(
        "/jobmaterial.json",
        api_key,
        params={"$filter": f"job_uuid eq '{sm8_uuid}' and active eq 1"},
    )
    if not items:
        return 0
    for item in items:
        sm8_put(f"/jobmaterial/{item['uuid']}.json", api_key, {"active": 0})
    return len(items)


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


def load_catalog(pipeline_name):
    """Build {item_code: material_uuid} lookup from saved SM8 catalog. Returns {} if no catalog file."""
    if not SM8_CATALOG_PATH.exists():
        return {}
    with open(SM8_CATALOG_PATH) as f:
        catalog = json.load(f)
    items = catalog.get(pipeline_name, [])
    return {
        item.get(CATALOG_CODE_FIELD, "").strip(): item["uuid"]
        for item in items
        if item.get(CATALOG_CODE_FIELD, "").strip() and item.get("uuid")
    }


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
    sm8_put(f"/job/{sm8_uuid}.json", api_key, {"job_description": job_description})
    print("Job description updated.")

    # ── load SM8 catalog for this pipeline ────────────────────────────────────
    catalog_lookup = load_catalog(config["name"])
    if not catalog_lookup:
        print("ERROR: SM8 catalog not found. Run fetch_sm8_catalog.py first.")
        sys.exit(1)
    print(f"Catalog loaded: {len(catalog_lookup)} items for {config['name']}")

    # ── delete existing line items (clean re-runs) ─────────────────────────────
    deleted = delete_existing_line_items(sm8_uuid, api_key)
    if deleted:
        print(f"Deleted {deleted} existing line item(s).")

    # ── create line items ──────────────────────────────────────────────────────
    line_items = quote["line_items"]
    print(f"\nCreating {len(line_items)} line items in SM8...")

    # Build material_uuid → rate lookup for price-setting step
    mat_rate_lookup = {}

    for i, item in enumerate(line_items, 1):
        item_code = item.get("code", "")
        material_uuid = catalog_lookup.get(item_code)
        if not material_uuid:
            print(f"  ERROR: No catalog match for code '{item_code}' — cannot push without material_uuid")
            sys.exit(1)

        sm8_post("/jobmaterial.json", api_key, {
            "job_uuid": sm8_uuid,
            "material_uuid": material_uuid,
            "name": item["description"],
            "quantity": str(item["quantity"]),
            "active": 1,
        })
        mat_rate_lookup[material_uuid] = item["rate"]
        print(f"  [{i}/{len(line_items)}] {item['description']} — {item['quantity']} {item['unit']} @ ${item['rate']}")

    print(f"Line items created: {len(line_items)}")

    # ── set prices (SM8 ignores price on POST; must PUT displayed_amount after) ─
    print("Setting prices...")
    created = sm8_get(
        "/jobmaterial.json",
        api_key,
        params={"$filter": f"job_uuid eq '{sm8_uuid}' and active eq 1"},
    )
    for jm in created:
        rate = mat_rate_lookup.get(jm.get("material_uuid"))
        if rate:
            sm8_put(f"/jobmaterial/{jm['uuid']}.json", api_key, {"displayed_amount": rate})
    print(f"Prices set: {len(created)} items")

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
Line items:   {len(line_items)}
Pipedrive:    moved to DEPOSIT PROCESS
─────────────────────────────────────────
Next: python tools/create_sm8_deposit.py --deal-id {deal_id}
""")


if __name__ == "__main__":
    main()
