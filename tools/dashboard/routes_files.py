"""
Vault > Files — upload binary files to Google Drive, index locally.

Allen's PC stays clean of clutter:
- Text (markdown, JSON) lives in projects/personal/
- Binaries (PDF, image, video, audio) live in Google Drive (folder "Enriquez OS Files")
- projects/personal/files/INDEX.md catalogs every upload so Claude can find them

Endpoints:
  POST /api/vault/files/upload    multipart form (file, tags, caption)
  GET  /api/vault/files/list      read the INDEX.md catalog

Register in app.py:
    from routes_files import files_bp
    app.register_blueprint(files_bp)
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drive_upload import upload_to_drive

files_bp = Blueprint('files', __name__)

INDEX_FILE = Path(__file__).resolve().parent.parent.parent / 'projects' / 'personal' / 'files' / 'INDEX.md'
MAX_UPLOAD_MB = 50
TABLE_HEADER = '| filename | drive_url | drive_id | tags | caption | uploaded |'
TABLE_DIVIDER = '|---|---|---|---|---|---|'


def _ensure_index():
    if INDEX_FILE.exists():
        return
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        '# File Uploads — Drive Catalog\n\n'
        'Binaries live in Google Drive under the folder **"Enriquez OS Files"**. '
        'This file is the local catalog so Claude and Allen can find them.\n\n'
        f'{TABLE_HEADER}\n{TABLE_DIVIDER}\n'
    )


def _append_row(row: str):
    _ensure_index()
    with open(INDEX_FILE, 'a') as f:
        f.write(row + '\n')


def _read_rows():
    """Return list of dicts for each catalog row."""
    _ensure_index()
    rows = []
    in_table = False
    for line in INDEX_FILE.read_text().splitlines():
        if line.strip().startswith('|---'):
            in_table = True
            continue
        if not in_table or not line.strip().startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 6:
            continue
        rows.append({
            'filename': cells[0],
            'drive_url': cells[1],
            'drive_id': cells[2],
            'tags': cells[3],
            'caption': cells[4],
            'uploaded': cells[5],
        })
    return rows


def _escape_cell(text):
    if text is None:
        return ''
    return str(text).replace('|', '\\|').replace('\n', ' ').strip()


@files_bp.route('/api/vault/files/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file in request'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'ok': False, 'error': 'Empty filename'}), 400

    caption = request.form.get('caption', '').strip()
    tags_raw = request.form.get('tags', '').strip()
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

    # Write to a temp file so drive_upload can stream from disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(f.filename).suffix) as tmp:
        f.save(tmp.name)
        size_mb = Path(tmp.name).stat().st_size / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            Path(tmp.name).unlink(missing_ok=True)
            return jsonify({'ok': False, 'error': f'File too large ({size_mb:.1f}MB). Max {MAX_UPLOAD_MB}MB.'}), 400

        # Rename the temp file to preserve original name (Drive uses source name)
        renamed = Path(tmp.name).parent / f.filename
        Path(tmp.name).rename(renamed)

        try:
            result = upload_to_drive(str(renamed), caption=caption or None, tags=tags or None)
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Drive upload failed: {e}'}), 500
        finally:
            renamed.unlink(missing_ok=True)

    row = '| {fn} | {url} | {id} | {tags} | {cap} | {up} |'.format(
        fn=_escape_cell(result['filename']),
        url=_escape_cell(result['web_url']),
        id=_escape_cell(result['file_id']),
        tags=_escape_cell(','.join(tags) if tags else ''),
        cap=_escape_cell(caption),
        up=datetime.now().strftime('%Y-%m-%d %H:%M'),
    )
    _append_row(row)

    return jsonify({
        'ok': True,
        'filename': result['filename'],
        'drive_url': result['web_url'],
        'drive_id': result['file_id'],
        'size': result['size'],
    })


@files_bp.route('/api/vault/files/list')
def list_files():
    rows = _read_rows()
    rows.reverse()  # newest first
    return jsonify({'ok': True, 'files': rows})
