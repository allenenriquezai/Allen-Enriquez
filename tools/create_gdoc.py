"""
Create a Google Doc on Allen's personal account and populate it with content.

Usage:
    python3 tools/create_gdoc.py --title "Doc Title" --content-file "path/to/content.md"
    python3 tools/create_gdoc.py --title "Doc Title" --content "Inline text"
"""

import argparse
import os
import pickle
import sys
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, 'projects', 'personal', 'token_personal.pickle')


def get_creds():
    if not os.path.exists(TOKEN_FILE):
        print("ERROR: Personal token not found.", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def move_to_folder(creds, file_id, folder_name):
    """Find a folder by name and move the file into it."""
    drive = build('drive', 'v3', credentials=creds)
    # Search for folder
    results = drive.files().list(
        q=f"name contains '{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    folders = results.get('files', [])
    if not folders:
        print(f"WARNING: Folder '{folder_name}' not found. Doc stays in root.", file=sys.stderr)
        return
    folder_id = folders[0]['id']
    # Get current parents and move
    file = drive.files().get(fileId=file_id, fields='parents').execute()
    prev_parents = ','.join(file.get('parents', []))
    drive.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=prev_parents,
        fields='id, parents'
    ).execute()
    print(f"Moved to folder: {folders[0]['name']}", file=sys.stderr)


def create_doc(title, content, folder=None):
    creds = get_creds()
    docs = build('docs', 'v1', credentials=creds)

    # Create blank doc
    doc = docs.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

    # Move to folder if specified
    if folder:
        move_to_folder(creds, doc_id, folder)

    if not content.strip():
        print(doc_url)
        return doc_url

    # Parse markdown-ish content into Google Docs requests
    requests = []
    lines = content.split('\n')
    # Insert in reverse isn't needed — we insert at index 1 sequentially
    idx = 1  # Google Docs body starts at index 1

    for line in lines:
        # Determine style
        if line.startswith('# '):
            text = line[2:] + '\n'
            style = 'HEADING_1'
        elif line.startswith('## '):
            text = line[3:] + '\n'
            style = 'HEADING_2'
        elif line.startswith('### '):
            text = line[4:] + '\n'
            style = 'HEADING_3'
        elif line.startswith('---'):
            text = '━' * 50 + '\n'
            style = 'NORMAL_TEXT'
        else:
            text = line + '\n'
            style = 'NORMAL_TEXT'

        # Insert text
        requests.append({
            'insertText': {
                'location': {'index': idx},
                'text': text
            }
        })

        # Apply heading style
        end_idx = idx + len(text)
        requests.append({
            'updateParagraphStyle': {
                'range': {'startIndex': idx, 'endIndex': end_idx},
                'paragraphStyle': {'namedStyleType': style},
                'fields': 'namedStyleType'
            }
        })

        # Bold lines that start with ** (after stripping)
        stripped = line.strip()
        if stripped.startswith('**') and '**' in stripped[2:]:
            # Find bold segments and apply bold
            pass  # Keep it simple — manual formatting in doc

        idx = end_idx

    # Execute in batches (Google Docs API limit)
    batch_size = 100
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        docs.documents().batchUpdate(documentId=doc_id, body={'requests': batch}).execute()

    print(doc_url)
    return doc_url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--title', required=True)
    parser.add_argument('--content-file', help='Path to .md file with content')
    parser.add_argument('--content', help='Inline content string', default='')
    parser.add_argument('--folder', help='Google Drive folder name to move doc into')
    args = parser.parse_args()

    if args.content_file:
        with open(args.content_file) as f:
            content = f.read()
    else:
        content = args.content

    url = create_doc(args.title, content, folder=args.folder)
    print(f"Created: {url}")
