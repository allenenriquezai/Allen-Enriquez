"""
Upload a file to Google Drive under the "Enriquez OS / Files" folder
using Allen's personal account token.

Usage (CLI):
    python3 tools/drive_upload.py /path/to/file.pdf [--caption "desc"] [--tags "a,b"]

Programmatic:
    from drive_upload import upload_to_drive
    result = upload_to_drive('/path/to/file.pdf', caption='...', tags=['a','b'])
    # -> {'file_id': '...', 'web_url': 'https://drive.google.com/...', 'filename': 'file.pdf'}
"""

import argparse
import mimetypes
import os
import pickle
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'
DRIVE_FOLDER_NAME = 'Enriquez OS Files'


def _get_creds():
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f'Personal token not found at {TOKEN_FILE}')
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def _get_or_create_folder(drive, name):
    """Find the Drive folder by name, or create it at root."""
    q = (
        f"name='{name}' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false"
    )
    resp = drive.files().list(q=q, spaces='drive', fields='files(id,name)').execute()
    folders = resp.get('files', [])
    if folders:
        return folders[0]['id']
    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    created = drive.files().create(body=meta, fields='id').execute()
    return created['id']


def upload_to_drive(file_path, caption=None, tags=None):
    """Upload a local file to Drive, return metadata dict.

    Returns: {'file_id', 'web_url', 'filename', 'mime_type', 'size'}
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    creds = _get_creds()
    drive = build('drive', 'v3', credentials=creds)
    folder_id = _get_or_create_folder(drive, DRIVE_FOLDER_NAME)

    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or 'application/octet-stream'

    metadata = {'name': path.name, 'parents': [folder_id]}
    if caption or tags:
        desc_parts = []
        if caption:
            desc_parts.append(caption)
        if tags:
            desc_parts.append('tags: ' + ','.join(tags))
        metadata['description'] = ' | '.join(desc_parts)

    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=path.stat().st_size > 5 * 1024 * 1024)
    resp = drive.files().create(
        body=metadata,
        media_body=media,
        fields='id, webViewLink, size, mimeType, name',
    ).execute()

    # Make it accessible to anyone with the link (read-only) — Allen's default for his own files.
    drive.permissions().create(
        fileId=resp['id'],
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()

    return {
        'file_id': resp['id'],
        'web_url': resp['webViewLink'],
        'filename': resp['name'],
        'mime_type': resp.get('mimeType', mime_type),
        'size': int(resp.get('size', 0)) if resp.get('size') else path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Path to local file')
    parser.add_argument('--caption', default=None)
    parser.add_argument('--tags', default=None, help='Comma-separated tags')
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(',')] if args.tags else None
    result = upload_to_drive(args.file, caption=args.caption, tags=tags)
    print(f"Uploaded: {result['filename']}")
    print(f"File ID:  {result['file_id']}")
    print(f"URL:      {result['web_url']}")


if __name__ == '__main__':
    main()
