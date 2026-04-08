"""
sync_sm8_catalog.py — Sync EPS item codes into the SM8 product catalog.

Usage:
    python tools/sync_sm8_catalog.py          # dry run (shows what would be created)
    python tools/sync_sm8_catalog.py --apply  # actually create items in SM8

What it does:
    1. Reads item codes + rates from projects/eps/config/pricing.json
    2. Fetches current SM8 catalog from both accounts
    3. Creates any items that don't already exist (matched by item_number / code)
    4. Skips items with no fixed rate ($0 / custom)
    5. Refreshes projects/eps/config/sm8_catalog.json after applying

Routing:
    EPSCLEAN-*  → EPS Clean SM8 account
    EPSPAINT-*  → EPS Paint SM8 account
    EPSMOB      → both accounts
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
EPS_DIR = ROOT / "projects" / "eps"
CATALOG_PATH = EPS_DIR / "config" / "sm8_catalog.json"
PRICING_PATH = EPS_DIR / "config" / "pricing.json"

load_dotenv(EPS_DIR / ".env")

SM8_API_KEY_CLEAN = os.getenv("SM8_API_KEY_CLEAN")
SM8_API_KEY_PAINT = os.getenv("SM8_API_KEY_PAINT")
SM8_BASE_URL = "https://api.servicem8.com/api_1.0"

ACCOUNTS = {
    "EPS Clean": SM8_API_KEY_CLEAN,
    "EPS Paint": SM8_API_KEY_PAINT,
}


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
    return r.json()


def load_our_items():
    """
    Build list of {code, name, rate, unit, account} from pricing.json.
    Skips items with rate = 0 (no fixed price).
    Returns two lists: clean_items, paint_items.
    """
    with open(PRICING_PATH) as f:
        pricing = json.load(f)

    rates = pricing["rates"]

    clean_items = []
    for key, item in rates["cleaning"].items():
        if item["rate"] > 0:
            clean_items.append({
                "code": item["code"],
                "name": item["name"],
                "rate": item["rate"],
                "unit": item["unit"],
            })

    paint_items = []
    for section in ["internal", "external", "day_rate"]:
        for key, item in rates[section].items():
            if item["rate"] > 0:
                paint_items.append({
                    "code": item["code"],
                    "name": item["name"],
                    "rate": item["rate"],
                    "unit": item["unit"],
                })

    # EPSMOB goes to both accounts
    mob = {"code": "EPSMOB", "name": "Mobilisation Fee", "rate": 100, "unit": "item"}
    clean_items.append(mob)
    paint_items.append(mob)

    return clean_items, paint_items


def fetch_existing_codes(api_key):
    """Return set of item_number values already in SM8 for this account."""
    try:
        items = sm8_get("/material.json", api_key)
    except Exception as e:
        print(f"  ERROR fetching catalog: {e}")
        return set()
    return {i.get("item_number", "").strip() for i in items if i.get("item_number")}


def sync_account(account_name, api_key, items, apply):
    print(f"\n{'─'*45}")
    print(f"{account_name}")
    print(f"{'─'*45}")

    existing_codes = fetch_existing_codes(api_key)
    print(f"Existing item codes in SM8: {len(existing_codes)}")

    to_create = [i for i in items if i["code"] not in existing_codes]
    already_there = [i for i in items if i["code"] in existing_codes]

    print(f"Our items:    {len(items)}")
    print(f"Already in SM8: {len(already_there)}")
    print(f"To create:    {len(to_create)}")

    if already_there:
        print("\nAlready exists (skip):")
        for item in already_there:
            print(f"  ✓ {item['code']} — {item['name']}")

    if not to_create:
        print("\nNothing to create.")
        return 0

    print(f"\n{'[DRY RUN] ' if not apply else ''}Items to create:")
    created = 0
    for item in to_create:
        print(f"  + {item['code']} — {item['name']} @ ${item['rate']}/{item['unit']}", end="")
        if apply:
            payload = {
                "name": item["name"],
                "item_number": item["code"],
                "price": str(item["rate"]),
                "active": 1,
                "price_includes_taxes": 0,  # rates are ex-GST
            }
            try:
                sm8_post("/material.json", api_key, payload)
                print(" ✓")
                created += 1
            except Exception as e:
                print(f" ERROR: {e}")
        else:
            print()

    return created


def refresh_catalog():
    """Re-fetch and save sm8_catalog.json after sync."""
    catalog = {}
    for account_name, api_key in ACCOUNTS.items():
        if not api_key:
            catalog[account_name] = []
            continue
        try:
            items = sm8_get("/material.json", api_key)
            active = [i for i in items if str(i.get("active", "0")) in ("1", "true", "True")]
            catalog[account_name] = active
        except Exception as e:
            print(f"  WARNING: Could not refresh {account_name}: {e}")
            catalog[account_name] = []

    with open(CATALOG_PATH, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"\nCatalog refreshed: {CATALOG_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually create items (default: dry run)")
    args = parser.parse_args()

    if not args.apply:
        print("DRY RUN — pass --apply to create items in SM8\n")

    clean_items, paint_items = load_our_items()

    total_created = 0

    for account_name, api_key, items in [
        ("EPS Clean", SM8_API_KEY_CLEAN, clean_items),
        ("EPS Paint", SM8_API_KEY_PAINT, paint_items),
    ]:
        if not api_key:
            env_var = "SM8_API_KEY_CLEAN" if "Clean" in account_name else "SM8_API_KEY_PAINT"
            print(f"\nWARNING: {env_var} not set — skipping {account_name}")
            continue
        created = sync_account(account_name, api_key, items, args.apply)
        total_created += created

    print(f"\n{'─'*45}")
    if args.apply:
        print(f"Done. {total_created} item(s) created.")
        if total_created > 0:
            print("Refreshing local catalog...")
            refresh_catalog()
    else:
        print("Dry run complete. Run with --apply to create items.")
    print(f"{'─'*45}")


if __name__ == "__main__":
    main()
