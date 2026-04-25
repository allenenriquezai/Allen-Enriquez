"""
Creates a Google Drive folder for an EPS quote and copies the division template into it.

Usage:
    python3 tools/create_quote_folder.py --deal-id 1076 --service-type "3 Stage Construction Cleaning" --client "Allen Enriquez" --organization "Smith Constructions" --division clean
    python3 tools/create_quote_folder.py --deal-id 1077 --service-type "Internal Painting" --client "Jane Smith" --division paint

Folder and doc name format: {deal_id} - {service_type} Quote - {organization or client}

Output:
    Prints the new document ID and URL.
"""

import argparse
import json
import os
import pickle
import sys
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')
PRICING_CONFIG = os.path.join(BASE_DIR, 'projects', 'eps', 'config', 'pricing.json')


def get_creds():
    if not os.path.exists(TOKEN_FILE):
        print("ERROR: EPS token not found. Run: python3 tools/auth_eps.py", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def create_client_folder(drive, parent_id, folder_name):
    """Create the client-specific subfolder under EPS Quotes."""
    body = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = drive.files().create(body=body, fields='id,webViewLink').execute()
    return folder['id'], folder['webViewLink']


def copy_template(drive, template_id, folder_id, doc_name):
    """Copy the quote template into the client folder."""
    body = {
        'name': doc_name,
        'parents': [folder_id]
    }
    copied = drive.files().copy(fileId=template_id, body=body, fields='id,webViewLink').execute()
    return copied['id'], copied['webViewLink']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deal-id',      required=True, help='Pipedrive deal ID')
    parser.add_argument('--service-type', required=True, help='Human-readable service type, e.g. "3 Stage Construction Cleaning"')
    parser.add_argument('--client',       required=True, help='Client full name (used if no organization)')
    parser.add_argument('--organization', default='',   help='Organization name (preferred over client name if provided)')
    parser.add_argument('--division',     required=True, choices=['paint', 'clean'],
                        help='Business division: paint or clean')
    parser.add_argument('--format',       choices=['doc', 'sheet'], default='doc',
                        help='Output format: doc (Google Doc) or sheet (Google Sheet)')
    parser.add_argument('--folder-id',   default='',
                        help='Existing Drive folder ID — skip folder creation if provided')
    args = parser.parse_args()

    with open(PRICING_CONFIG) as f:
        config = json.load(f)

    parent_folder_id = config.get('eps_quotes_folder_id', '')
    if not parent_folder_id:
        print("ERROR: eps_quotes_folder_id not set in pricing.json", file=sys.stderr)
        sys.exit(1)

    if args.format == 'sheet':
        templates = config.get('sheet_templates', {})
    else:
        templates = config.get('templates', {})
    template_id = templates.get(args.division, '')
    if not template_id or template_id.startswith('REPLACE_'):
        print(f"ERROR: template for division '{args.division}' not set in pricing.json", file=sys.stderr)
        sys.exit(1)

    creds = get_creds()
    drive = build('drive', 'v3', credentials=creds)

    display_name = args.organization if args.organization else args.client
    quote_name = f"{args.deal_id} - {args.service_type} Quote - {display_name}"
    folder_name = quote_name
    doc_name = quote_name

    if args.folder_id:
        client_folder_id = args.folder_id
        folder_url = f"https://drive.google.com/drive/folders/{args.folder_id}"
        folder_created = False
    else:
        client_folder_id, folder_url = create_client_folder(drive, parent_folder_id, folder_name)
        folder_created = True

    doc_id, doc_url = copy_template(drive, template_id, client_folder_id, doc_name)

    print(doc_id)
    print(doc_url)
    print(f"FOLDER: {folder_url}")
    if folder_created:
        print("FOLDER_NEW: true")


if __name__ == '__main__':
    main()
