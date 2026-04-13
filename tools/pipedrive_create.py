"""
pipedrive_create.py — Create and search Pipedrive organizations, persons, deals, and stages.

Usage:
    python3 tools/pipedrive_create.py --action search-org --name "Quadric"
    python3 tools/pipedrive_create.py --action create-org --name "ATG" --address "Brisbane QLD"
    python3 tools/pipedrive_create.py --action create-person --name "John Smith" --org-id 123 --phone "07 3210 0024"
    python3 tools/pipedrive_create.py --action create-deal --title "Project - Painting" --org-id 123 --pipeline-id 4 --stage-id 35
    python3 tools/pipedrive_create.py --action list-stages --pipeline-id 3
    python3 tools/pipedrive_create.py --action create-stage --name "QUOTE IN PROGRESS" --pipeline-id 3 --order 1

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY
    PIPEDRIVE_COMPANY_DOMAIN
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def api_request(method, path, payload=None, *, api_key, domain, retries=2):
    """Unified Pipedrive API request with 429 retry."""
    url = f"https://{domain}/api/v1{path}"
    sep = "&" if "?" in url else "?"
    url += f"{sep}api_token={api_key}"

    data = json.dumps(payload).encode() if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as r:
                resp = json.loads(r.read())
            if not resp.get("success"):
                print(f"ERROR: API returned: {resp}", file=sys.stderr)
                sys.exit(1)
            return resp
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = int(e.headers.get("Retry-After", 2))
                time.sleep(wait)
                continue
            body = e.read().decode() if e.fp else ""
            print(f"ERROR: HTTP {e.code} on {method} {path}: {body}", file=sys.stderr)
            sys.exit(1)


# --- Normalization ---

def normalize_name(name):
    """Strip common suffixes for comparison."""
    n = name.lower().strip()
    for suffix in ["pty ltd", "pty", "ltd", "(qld)", "(brisbane)", "(nq)",
                    "(corporate services)", "(queensland)"]:
        n = n.replace(suffix, "")
    n = re.sub(r"\s+", " ", n).strip()
    return n


def names_match(a, b):
    """Check if two org names are effectively the same."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter = min(len(na), len(nb))
    if shorter >= 4 and (na in nb or nb in na):
        return True
    return False


# --- Search ---

def search_organizations(term, *, api_key, domain):
    resp = api_request("GET", f"/organizations/search?term={urllib.parse.quote(term)}&limit=10",
                       api_key=api_key, domain=domain)
    items = resp.get("data", {}).get("items", []) or []
    return [{"id": it["item"]["id"], "name": it["item"]["name"],
             "address": it["item"].get("address", "")} for it in items]


def search_persons(term, *, api_key, domain):
    resp = api_request("GET", f"/persons/search?term={urllib.parse.quote(term)}&limit=10",
                       api_key=api_key, domain=domain)
    items = resp.get("data", {}).get("items", []) or []
    return [{"id": it["item"]["id"], "name": it["item"]["name"],
             "org_id": it["item"].get("organization", {}).get("id") if it["item"].get("organization") else None}
            for it in items]


def search_deals(term, *, api_key, domain):
    resp = api_request("GET", f"/deals/search?term={urllib.parse.quote(term)}&limit=10",
                       api_key=api_key, domain=domain)
    items = resp.get("data", {}).get("items", []) or []
    return [{"id": it["item"]["id"], "title": it["item"]["title"],
             "stage_id": it["item"].get("stage_id"),
             "pipeline_id": it["item"].get("pipeline_id")} for it in items]


# --- Create ---

def create_organization(name, address=None, *, api_key, domain):
    """Search first (dedup), then create if no match.
    Searches with both the full name and the core name (stripped of Pty Ltd etc.)
    to catch variations like 'Quadric Pty Ltd' vs 'Quadric Pty'."""
    core = normalize_name(name)
    search_terms = [name]
    if core != name.lower().strip():
        search_terms.append(core)

    seen_ids = set()
    for term in search_terms:
        existing = search_organizations(term, api_key=api_key, domain=domain)
        for org in existing:
            if org["id"] in seen_ids:
                continue
            seen_ids.add(org["id"])
            if names_match(name, org["name"]):
                print(f"Existing org found: #{org['id']} {org['name']}")
                return {"id": org["id"], "name": org["name"], "created": False}

    payload = {"name": name}
    if address:
        payload["address"] = address

    resp = api_request("POST", "/organizations", payload, api_key=api_key, domain=domain)
    org = resp["data"]
    print(f"Created org: #{org['id']} {org['name']}")
    return {"id": org["id"], "name": org["name"], "created": True}


def create_person(name, org_id=None, email=None, phone=None, *, api_key, domain):
    """Create a person, optionally linked to an org."""
    payload = {"name": name}
    if org_id:
        payload["org_id"] = org_id
    if email:
        payload["email"] = [{"value": email, "primary": True}]
    if phone:
        payload["phone"] = [{"value": phone, "primary": True}]

    resp = api_request("POST", "/persons", payload, api_key=api_key, domain=domain)
    person = resp["data"]
    print(f"Created person: #{person['id']} {person['name']}")
    return {"id": person["id"], "name": person["name"], "created": True}


def create_deal(title, org_id=None, person_id=None, pipeline_id=None,
                stage_id=None, value=None, *, api_key, domain):
    """Create a deal in a specific pipeline/stage."""
    payload = {"title": title}
    if org_id:
        payload["org_id"] = org_id
    if person_id:
        payload["person_id"] = person_id
    if pipeline_id:
        payload["pipeline_id"] = pipeline_id
    if stage_id:
        payload["stage_id"] = stage_id
    if value:
        payload["value"] = value
        payload["currency"] = "AUD"

    resp = api_request("POST", "/deals", payload, api_key=api_key, domain=domain)
    deal = resp["data"]
    print(f"Created deal: #{deal['id']} {deal['title']}")
    return {"id": deal["id"], "title": deal["title"], "created": True}


# --- Leads ---

def create_lead(title, person_id=None, org_id=None, label_ids=None,
                expected_close_date=None, *, api_key, domain):
    """Create a lead in Pipedrive's Leads inbox (for cold outreach)."""
    payload = {"title": title}
    if person_id:
        payload["person_id"] = person_id
    if org_id:
        payload["organization_id"] = org_id
    if label_ids:
        payload["label_ids"] = label_ids
    if expected_close_date:
        payload["expected_close_date"] = expected_close_date

    resp = api_request("POST", "/leads", payload, api_key=api_key, domain=domain)
    lead = resp["data"]
    print(f"Created lead: #{lead['id']} {lead['title']}")
    return {"id": lead["id"], "title": lead["title"], "created": True}


# --- Stages ---

def list_stages(pipeline_id, *, api_key, domain):
    """List all stages in a pipeline."""
    resp = api_request("GET", f"/stages?pipeline_id={pipeline_id}",
                       api_key=api_key, domain=domain)
    stages = resp.get("data", []) or []
    stages.sort(key=lambda s: s.get("order_nr", 0))
    result = []
    for s in stages:
        result.append({"id": s["id"], "name": s["name"], "order": s["order_nr"],
                        "pipeline_id": s["pipeline_id"],
                        "deals_count": s.get("deals_summary", {}).get("total_count", 0)})
    return result


def create_stage(name, pipeline_id, order=None, *, api_key, domain):
    """Create a new stage in a pipeline."""
    payload = {"name": name, "pipeline_id": pipeline_id}
    if order is not None:
        payload["order_nr"] = order

    resp = api_request("POST", "/stages", payload, api_key=api_key, domain=domain)
    stage = resp["data"]
    print(f"Created stage: #{stage['id']} {stage['name']} (pipeline {pipeline_id})")
    return {"id": stage["id"], "name": stage["name"], "order": stage.get("order_nr"),
            "created": True}


def update_stage(stage_id, order=None, name=None, *, api_key, domain):
    """Update a stage's order or name."""
    payload = {}
    if order is not None:
        payload["order_nr"] = order
    if name:
        payload["name"] = name
    if not payload:
        return

    resp = api_request("PUT", f"/stages/{stage_id}", payload, api_key=api_key, domain=domain)
    stage = resp["data"]
    print(f"Updated stage: #{stage['id']} {stage['name']} (order: {stage.get('order_nr')})")
    return {"id": stage["id"], "name": stage["name"], "order": stage.get("order_nr")}


def delete_stage(stage_id, *, api_key, domain):
    """Delete a stage (only if no deals in it)."""
    resp = api_request("DELETE", f"/stages/{stage_id}", api_key=api_key, domain=domain)
    print(f"Deleted stage: #{stage_id}")
    return {"id": stage_id, "deleted": True}


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Create/search Pipedrive entities")
    parser.add_argument("--action", required=True,
                        choices=["search-org", "search-person", "search-deal",
                                 "create-org", "create-person", "create-deal",
                                 "create-lead",
                                 "list-stages", "create-stage", "update-stage", "delete-stage"])
    parser.add_argument("--name", help="Entity name")
    parser.add_argument("--title", help="Deal title")
    parser.add_argument("--address", help="Organization address")
    parser.add_argument("--org-id", type=int, help="Organization ID")
    parser.add_argument("--person-id", type=int, help="Person ID")
    parser.add_argument("--pipeline-id", type=int, help="Pipeline ID")
    parser.add_argument("--stage-id", type=int, help="Stage ID")
    parser.add_argument("--email", help="Person email")
    parser.add_argument("--phone", help="Person phone")
    parser.add_argument("--value", type=float, help="Deal value (AUD)")
    parser.add_argument("--order", type=int, help="Stage order number")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("PIPEDRIVE_API_KEY", "")
    domain = env.get("PIPEDRIVE_COMPANY_DOMAIN", "")

    if not api_key or not domain:
        print("ERROR: PIPEDRIVE_API_KEY and PIPEDRIVE_COMPANY_DOMAIN must be set in projects/eps/.env",
              file=sys.stderr)
        sys.exit(1)

    creds = {"api_key": api_key, "domain": domain}

    if args.action == "search-org":
        result = search_organizations(args.name, **creds)
    elif args.action == "search-person":
        result = search_persons(args.name, **creds)
    elif args.action == "search-deal":
        result = search_deals(args.name or args.title, **creds)
    elif args.action == "create-org":
        result = create_organization(args.name, args.address, **creds)
    elif args.action == "create-person":
        result = create_person(args.name, args.org_id, args.email, args.phone, **creds)
    elif args.action == "create-deal":
        result = create_deal(args.title, args.org_id, args.person_id,
                             args.pipeline_id, args.stage_id, args.value, **creds)
    elif args.action == "create-lead":
        result = create_lead(args.title, args.person_id, args.org_id, **creds)
    elif args.action == "list-stages":
        result = list_stages(args.pipeline_id, **creds)
    elif args.action == "create-stage":
        result = create_stage(args.name, args.pipeline_id, args.order, **creds)
    elif args.action == "update-stage":
        result = update_stage(args.stage_id, args.order, args.name, **creds)
    elif args.action == "delete-stage":
        result = delete_stage(args.stage_id, **creds)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
