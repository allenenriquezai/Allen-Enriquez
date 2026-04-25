"""
Reads the "Quote Folder Link" custom field from a Pipedrive deal.
Outputs the Google Drive folder ID (extracted from the URL), or blank if not set.

Usage:
    python3 tools/get_deal_folder.py --deal-id 1076

Output:
    Prints folder ID to stdout (blank line if not set).
    Errors go to stderr.
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
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


def extract_folder_id(drive_url: str) -> str:
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', drive_url)
    return m.group(1) if m else ''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deal-id', required=True, help='Pipedrive deal ID')
    args = parser.parse_args()

    env = load_env()
    api_key          = env.get('PIPEDRIVE_API_KEY', '')
    domain           = env.get('PIPEDRIVE_COMPANY_DOMAIN', 'api.pipedrive.com')
    folder_field_key = env.get('PIPEDRIVE_FOLDER_FIELD_KEY', '')

    if not api_key:
        print("ERROR: PIPEDRIVE_API_KEY not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)
    if not folder_field_key:
        print("ERROR: PIPEDRIVE_FOLDER_FIELD_KEY not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)

    url = f"https://{domain}/v1/deals/{args.deal_id}?api_token={api_key}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        if not data.get('success'):
            print(f"ERROR: Pipedrive API: {data}", file=sys.stderr)
            sys.exit(1)
        folder_url = data['data'].get(folder_field_key) or ''
        folder_id  = extract_folder_id(folder_url) if folder_url else ''
        print(folder_id)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
