"""
Updates a Pipedrive deal field — folder link, doc link, or deal value.

Usage:
    python3 tools/update_pipedrive_deal.py --deal-id "123" --field folder --url "https://drive.google.com/..."
    python3 tools/update_pipedrive_deal.py --deal-id "123" --field doc    --url "https://docs.google.com/..."
    python3 tools/update_pipedrive_deal.py --deal-id "123" --field value  --value "2000"

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY
    PIPEDRIVE_FOLDER_FIELD_KEY  (hash for "Quote Folder Link")
    PIPEDRIVE_DOC_FIELD_KEY     (hash for "Draft Quote Doc Link")
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def update_deal(deal_id: str, field_key: str, url_value: str, api_key: str, domain: str) -> dict:
    endpoint = f"https://{domain}/v1/deals/{deal_id}?api_token={api_key}"
    payload = json.dumps({field_key: url_value}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT"
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    if not data.get('success'):
        print(f"ERROR: Pipedrive API returned: {data}", file=sys.stderr)
        sys.exit(1)
    return data['data']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deal-id', required=True, help='Pipedrive deal ID')
    parser.add_argument('--field',   required=True, choices=['folder', 'doc', 'value'],
                        help='Which field to write: folder, doc, or value (deal value in AUD)')
    parser.add_argument('--url',     default='', help='URL to write (for folder/doc fields)')
    parser.add_argument('--value',   default='', help='Deal value in AUD (for value field)')
    args = parser.parse_args()

    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY', '')
    domain  = env.get('PIPEDRIVE_COMPANY_DOMAIN', 'api.pipedrive.com')

    if not api_key:
        print("ERROR: PIPEDRIVE_API_KEY not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)

    if args.field == 'value':
        if not args.value:
            print("ERROR: --value required when --field is value", file=sys.stderr)
            sys.exit(1)
        deal = update_deal(args.deal_id, 'value', args.value, api_key, domain)
        print(f"Updated deal #{deal['id']}: {deal.get('title', '')}")
        print(f"Deal value set: ${args.value}")
        return

    if not args.url:
        print("ERROR: --url required when --field is folder or doc", file=sys.stderr)
        sys.exit(1)

    if args.field == 'folder':
        field_key = env.get('PIPEDRIVE_FOLDER_FIELD_KEY', '')
        field_label = 'Quote Folder Link'
    else:
        field_key = env.get('PIPEDRIVE_DOC_FIELD_KEY', '')
        field_label = 'Draft Quote Doc Link'

    if not field_key:
        print(f"ERROR: PIPEDRIVE_{'FOLDER' if args.field == 'folder' else 'DOC'}_FIELD_KEY not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)

    deal = update_deal(args.deal_id, field_key, args.url, api_key, domain)
    print(f"Updated deal #{deal['id']}: {deal.get('title', '')}")
    print(f"{field_label} written: {args.url}")


if __name__ == '__main__':
    main()
