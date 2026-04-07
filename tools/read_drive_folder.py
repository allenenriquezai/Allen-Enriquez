"""
List files in a Google Drive folder and print the text content of any Google Docs.

Usage:
    python3 tools/read_drive_folder.py --folder-id FOLDER_ID [--output FILE]

Output is printed to stdout or saved to a file.
"""

import os
import sys
import pickle
import argparse
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'eps', 'token_eps.pickle')


def get_creds():
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def list_files(drive_service, folder_id):
    results = []
    page_token = None
    while True:
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token
        ).execute()
        results.extend(response.get('files', []))
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return results


def read_doc(docs_service, doc_id):
    doc = docs_service.documents().get(documentId=doc_id).execute()
    text_parts = []
    for element in doc.get('body', {}).get('content', []):
        para = element.get('paragraph')
        if not para:
            continue
        for run in para.get('elements', []):
            text_run = run.get('textRun')
            if text_run:
                text_parts.append(text_run.get('content', ''))
    return ''.join(text_parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder-id', required=True)
    parser.add_argument('--output', help='Save output to this file path')
    args = parser.parse_args()

    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    files = list_files(drive_service, args.folder_id)

    lines = []
    lines.append(f"Folder ID: {args.folder_id}")
    lines.append(f"Files found: {len(files)}\n")

    def process_files(files, depth=0):
        indent = '  ' * depth
        for f in files:
            lines.append(f"{indent}--- {f['name']} ({f['mimeType']}) ---")
            if f['mimeType'] == 'application/vnd.google-apps.document':
                content = read_doc(docs_service, f['id'])
                lines.append(content.strip())
            elif f['mimeType'] == 'application/vnd.google-apps.folder':
                sub_files = list_files(drive_service, f['id'])
                process_files(sub_files, depth + 1)
            else:
                lines.append(f"{indent}[Non-Doc file — skipped]")
            lines.append('')

    process_files(files)

    output = '\n'.join(lines)

    if args.output:
        with open(args.output, 'w') as fp:
            fp.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
