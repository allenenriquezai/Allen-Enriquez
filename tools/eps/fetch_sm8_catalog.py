"""
fetch_sm8_catalog.py — Fetch SM8 material/product catalog from both accounts.

Usage:
    python tools/fetch_sm8_catalog.py

Saves: projects/eps/config/sm8_catalog.json
Structure: {"EPS Clean": [...items...], "EPS Paint": [...items...]}
SM8 item code field: assumed 'item_number' — verify by inspecting saved JSON.
"""

import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
EPS_DIR = ROOT / "projects" / "eps"
CATALOG_PATH = EPS_DIR / "config" / "sm8_catalog.json"

load_dotenv(EPS_DIR / ".env")

SM8_API_KEY_CLEAN = os.getenv("SM8_API_KEY_CLEAN")
SM8_API_KEY_PAINT = os.getenv("SM8_API_KEY_PAINT")
SM8_BASE_URL = "https://api.servicem8.com/api_1.0"

ACCOUNTS = {"EPS Clean": SM8_API_KEY_CLEAN, "EPS Paint": SM8_API_KEY_PAINT}


def sm8_get(path, api_key, params=None):
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    r = requests.get(f"{SM8_BASE_URL}{path}", headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def main():
    catalog = {}

    for account_name, api_key in ACCOUNTS.items():
        if not api_key:
            env_var = "SM8_API_KEY_CLEAN" if "Clean" in account_name else "SM8_API_KEY_PAINT"
            print(f"WARNING: {env_var} not set — skipping {account_name}")
            catalog[account_name] = []
            continue

        print(f"Fetching catalog from {account_name}...")
        try:
            items = sm8_get("/material.json", api_key)
        except Exception as e:
            print(f"  ERROR: {e}")
            catalog[account_name] = []
            continue

        # SM8 soft-deletes: active can be int 1, string "1", or bool True
        active = [i for i in items if str(i.get("active", "0")) in ("1", "true", "True")]
        catalog[account_name] = active
        print(f"  {len(active)} active items (of {len(items)} total)")

        if active:
            print(f"  Fields: {list(active[0].keys())}")
            for item in active[:3]:
                code = item.get("item_number", item.get("uuid", "NO-CODE-FIELD"))
                print(f"    code={code!r}  name={item.get('name', '?')!r}")

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog, f, indent=2)

    print(f"""
─────────────────────────────────────────
SM8 Catalog Saved
─────────────────────────────────────────""")
    for account_name, items in catalog.items():
        print(f"{account_name}: {len(items)} items")
    print(f"""File: {CATALOG_PATH}
─────────────────────────────────────────
NEXT STEPS:
1. Open projects/eps/config/sm8_catalog.json
2. Confirm code field is 'item_number' (update CATALOG_CODE_FIELD in push_sm8_job.py if not)
3. Run push_sm8_job.py as normal — it will auto-load the catalog
─────────────────────────────────────────""")


if __name__ == "__main__":
    main()
