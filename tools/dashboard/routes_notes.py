"""
Library routes — Notion-like CRUD for notes, projects, and links.

Files live in projects/personal/library/ as markdown.
- notes/      one .md per note (frontmatter + body)
- projects/   one .md per project (frontmatter + body)
- links/      single links.md (markdown sections + bullet list)

Single source of truth = the files. AI can read them directly.

# In app.py, add:
# from routes_notes import notes_bp
# app.register_blueprint(notes_bp)
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from flask import Blueprint, jsonify, request

notes_bp = Blueprint('notes', __name__)

# ============================================================
# Paths + collection config
# ============================================================

LIBRARY_DIR = Path(__file__).parent.parent.parent / 'projects' / 'personal' / 'library'
COLLECTIONS = ('notes', 'projects', 'links')
FILE_COLLECTIONS = ('notes', 'projects')  # one file per item
LINKS_FILE = LIBRARY_DIR / 'links' / 'links.md'


def _collection_dir(collection: str) -> Path:
    return LIBRARY_DIR / collection


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ============================================================
# Slugify + filename helpers
# ============================================================

def slugify(text: str) -> str:
    """Lowercase, replace non-alphanumeric with -, collapse, strip."""
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text or 'untitled'


def _unique_slug(collection: str, base_slug: str) -> str:
    """Find a unique slug by appending -2, -3, etc. if file exists."""
    folder = _collection_dir(collection)
    _ensure_dir(folder)
    candidate = base_slug
    i = 2
    while (folder / f'{candidate}.md').exists():
        candidate = f'{base_slug}-{i}'
        i += 1
    return candidate


# ============================================================
# Frontmatter parser (no external deps)
# ============================================================

_FM_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', re.DOTALL)


def parse_frontmatter(raw: str):
    """Parse simple YAML-ish frontmatter. Returns (metadata, body)."""
    m = _FM_RE.match(raw or '')
    if not m:
        return {}, raw or ''
    fm_text, body = m.group(1), m.group(2)
    meta = {}
    for line in fm_text.splitlines():
        if not line.strip() or ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()
        value = value.strip()
        # Lists in [a, b, c] form
        if value.startswith('[') and value.endswith(']'):
            inner = value[1:-1].strip()
            if not inner:
                meta[key] = []
            else:
                meta[key] = [
                    p.strip().strip('"').strip("'")
                    for p in inner.split(',')
                    if p.strip()
                ]
        else:
            # Strip surrounding quotes
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            meta[key] = value
    return meta, body


def dump_frontmatter(meta: dict, body: str) -> str:
    """Serialize metadata + body back to a markdown file string."""
    lines = ['---']
    for k, v in meta.items():
        if isinstance(v, list):
            inner = ', '.join(str(x) for x in v)
            lines.append(f'{k}: [{inner}]')
        else:
            lines.append(f'{k}: {v}')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines) + (body or '')


# ============================================================
# Item helpers (notes + projects)
# ============================================================

def _item_path(collection: str, item_id: str) -> Path:
    return _collection_dir(collection) / f'{item_id}.md'


def _read_item(collection: str, item_id: str):
    path = _item_path(collection, item_id)
    if not path.exists():
        return None
    raw = path.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(raw)
    return {
        'id': item_id,
        'title': meta.get('title', item_id),
        'created': meta.get('created', ''),
        'updated': meta.get('updated', ''),
        'tags': meta.get('tags', []) if isinstance(meta.get('tags'), list) else [],
        'body': body,
        'frontmatter': meta,
        'raw': raw,
    }


def _snippet(body: str, n: int = 120) -> str:
    text = (body or '').strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:n]


def _list_items(collection: str):
    folder = _collection_dir(collection)
    _ensure_dir(folder)
    items = []
    for path in sorted(folder.glob('*.md')):
        item_id = path.stem
        item = _read_item(collection, item_id)
        if not item:
            continue
        items.append({
            'id': item['id'],
            'title': item['title'],
            'created': item['created'],
            'updated': item['updated'],
            'tags': item['tags'],
            'snippet': _snippet(item['body']),
        })
    # Newest updated first
    items.sort(key=lambda x: x.get('updated') or x.get('created') or '', reverse=True)
    return items


# ============================================================
# Links file helpers (single links.md)
# ============================================================

# Each link rendered as:
# - [Title](url) — note text
# Sections are H2 headers (## Section Name)

_LINK_LINE_RE = re.compile(r'^-\s+(?:\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)|<(?P<bare>[^>]+)>)(?:\s+[—-]\s+(?P<note>.+))?\s*$')


def _read_links_file() -> str:
    if not LINKS_FILE.exists():
        return ''
    return LINKS_FILE.read_text(encoding='utf-8')


def _write_links_file(content: str):
    _ensure_dir(LINKS_FILE.parent)
    LINKS_FILE.write_text(content, encoding='utf-8')


def _parse_links():
    """Parse links.md into a flat list. Each entry has section, title, url, note, index."""
    raw = _read_links_file()
    links = []
    section = ''
    idx = 0
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith('## '):
            section = s[3:].strip()
            continue
        m = _LINK_LINE_RE.match(s)
        if not m:
            continue
        title = m.group('title') or ''
        url = m.group('url') or m.group('bare') or ''
        note = (m.group('note') or '').strip()
        if not url:
            continue
        links.append({
            'index': idx,
            'section': section,
            'title': title or url,
            'url': url,
            'note': note,
        })
        idx += 1
    return links


def _render_links(links):
    """Render links list back to markdown, grouped by section in original order."""
    sections = {}
    order = []
    for link in links:
        sec = link.get('section') or 'Uncategorized'
        if sec not in sections:
            sections[sec] = []
            order.append(sec)
        sections[sec].append(link)

    out_lines = ['# Links', '']
    for sec in order:
        out_lines.append(f'## {sec}')
        out_lines.append('')
        for link in sections[sec]:
            title = link.get('title') or link['url']
            note = link.get('note', '')
            line = f'- [{title}]({link["url"]})'
            if note:
                line += f' — {note}'
            out_lines.append(line)
        out_lines.append('')
    return '\n'.join(out_lines)


# ============================================================
# Validation
# ============================================================

def _bad(error: str, status: int = 400):
    return jsonify({'ok': False, 'error': error}), status


def _validate_collection(collection: str):
    if collection not in COLLECTIONS:
        return _bad('invalid_collection')
    return None


# ============================================================
# Routes — list / get / create / update / delete
# ============================================================

@notes_bp.route('/api/library/<collection>', methods=['GET'])
def api_library_list(collection):
    err = _validate_collection(collection)
    if err:
        return err

    if collection == 'links':
        return jsonify({'ok': True, 'links': _parse_links()})

    return jsonify({'ok': True, 'items': _list_items(collection)})


@notes_bp.route('/api/library/<collection>/<item_id>', methods=['GET'])
def api_library_get(collection, item_id):
    err = _validate_collection(collection)
    if err:
        return err
    if collection == 'links':
        return _bad('use_index_for_links_delete', 400)

    item = _read_item(collection, item_id)
    if not item:
        return _bad('not_found', 404)
    return jsonify({'ok': True, 'item': item})


@notes_bp.route('/api/library/<collection>', methods=['POST'])
def api_library_create(collection):
    err = _validate_collection(collection)
    if err:
        return err

    data = request.json or {}

    if collection == 'links':
        url = (data.get('url') or '').strip()
        if not url:
            return _bad('missing_url')
        title = (data.get('title') or '').strip() or url
        note = (data.get('note') or '').strip()
        section = (data.get('section') or 'Uncategorized').strip() or 'Uncategorized'

        links = _parse_links()
        links.append({
            'section': section,
            'title': title,
            'url': url,
            'note': note,
        })
        _write_links_file(_render_links(links))
        return jsonify({
            'ok': True,
            'link': {
                'index': len(links) - 1,
                'section': section,
                'title': title,
                'url': url,
                'note': note,
            },
        })

    # notes / projects
    title = (data.get('title') or '').strip()
    body = data.get('body') or ''
    tags = data.get('tags') or []
    if not title:
        return _bad('missing_title')
    if not isinstance(tags, list):
        return _bad('tags_must_be_list')

    base_slug = slugify(title)
    item_id = _unique_slug(collection, base_slug)
    now = _now_iso()
    meta = {
        'title': title,
        'created': now,
        'updated': now,
        'tags': tags,
    }
    raw = dump_frontmatter(meta, body)
    path = _item_path(collection, item_id)
    _ensure_dir(path.parent)
    path.write_text(raw, encoding='utf-8')

    return jsonify({
        'ok': True,
        'item': {
            'id': item_id,
            'title': title,
            'created': now,
            'updated': now,
            'tags': tags,
            'snippet': _snippet(body),
        },
    })


@notes_bp.route('/api/library/<collection>/<item_id>', methods=['PUT'])
def api_library_update(collection, item_id):
    err = _validate_collection(collection)
    if err:
        return err
    if collection == 'links':
        return _bad('links_update_unsupported', 400)

    data = request.json or {}
    item = _read_item(collection, item_id)
    if not item:
        return _bad('not_found', 404)

    meta = dict(item['frontmatter'])
    body = item['body']

    if 'title' in data and data['title']:
        meta['title'] = str(data['title']).strip()
    if 'body' in data:
        body = data['body'] or ''
    if 'tags' in data:
        if not isinstance(data['tags'], list):
            return _bad('tags_must_be_list')
        meta['tags'] = data['tags']

    if 'created' not in meta or not meta['created']:
        meta['created'] = _now_iso()
    meta['updated'] = _now_iso()

    raw = dump_frontmatter(meta, body)
    _item_path(collection, item_id).write_text(raw, encoding='utf-8')

    return jsonify({
        'ok': True,
        'item': {
            'id': item_id,
            'title': meta.get('title', item_id),
            'created': meta['created'],
            'updated': meta['updated'],
            'tags': meta.get('tags', []),
            'snippet': _snippet(body),
        },
    })


@notes_bp.route('/api/library/<collection>/<item_id>', methods=['DELETE'])
def api_library_delete(collection, item_id):
    err = _validate_collection(collection)
    if err:
        return err

    if collection == 'links':
        # item_id is the index here
        try:
            index = int(item_id)
        except (TypeError, ValueError):
            return _bad('invalid_index', 400)
        links = _parse_links()
        if index < 0 or index >= len(links):
            return _bad('not_found', 404)
        removed = links.pop(index)
        _write_links_file(_render_links(links))
        return jsonify({'ok': True, 'removed': removed})

    path = _item_path(collection, item_id)
    if not path.exists():
        return _bad('not_found', 404)
    path.unlink()
    return jsonify({'ok': True, 'id': item_id})
