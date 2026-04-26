"""
Flask Blueprint for the SQLite-backed Outreach kanban view.

Adds /outreach (kanban UI) + /api/outreach/* (card actions) +
/api/ad-leads/intake (Tally webhook receiver). All operations read/write
projects/personal/data/outreach.db via tools/personal/outreach_db.py.

Mounted into the existing crm_kanban Flask app:
    from outreach_routes import bp as outreach_bp
    app.register_blueprint(outreach_bp)
"""

import json
import sys
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / 'tools' / 'personal'))

import outreach_db  # noqa: E402

bp = Blueprint('outreach', __name__)

STAGE_ORDER = [
    'enriched', 'queued', 'sent', 'replied',
    'discovery_booked', 'no_reply', 'not_now', 'optout',
    'ad-lead',
]
STAGE_LABELS = {
    'enriched': 'Ready to send',
    'queued': "Today's batch",
    'sent': 'Sent',
    'replied': 'Replied',
    'discovery_booked': 'Call booked',
    'no_reply': 'No reply',
    'not_now': 'Not now',
    'optout': 'Opt out',
    'ad-lead': 'Inbound (ads)',
}

VALID_REPLIES = {'INTERESTED', 'NOT_INTERESTED', 'QUESTION', 'OPTOUT', 'OTHER'}


def _decorate_row(row):
    """Parse JSON cols + add UI-friendly fields."""
    out = dict(row)
    posts = out.get('recent_posts_json')
    if posts:
        try:
            out['recent_posts'] = json.loads(posts)
        except Exception:
            out['recent_posts'] = []
    else:
        out['recent_posts'] = []
    out.pop('recent_posts_json', None)
    out.pop('raw_payload_json', None)
    if out.get('ig_handle'):
        out['ig_profile_url'] = f"https://instagram.com/{out['ig_handle']}/"
    return out


@bp.route('/outreach')
def outreach_page():
    segment = request.args.get('segment', 'coaches')
    geo = request.args.get('geo', 'all')

    columns = {stage: [] for stage in STAGE_ORDER}
    rows = outreach_db.list_prospects(segment=segment, geo=geo, limit=500)
    counts_by_status = {}
    for r in rows:
        status = r.get('status') or 'enriched'
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
        if status in columns:
            columns[status].append(_decorate_row(r))

    stats = {
        'total': len(rows),
        'enriched': counts_by_status.get('enriched', 0),
        'queued': counts_by_status.get('queued', 0),
        'sent': counts_by_status.get('sent', 0),
        'replied': counts_by_status.get('replied', 0),
        'ad_leads': counts_by_status.get('ad-lead', 0),
    }

    return render_template(
        'outreach.html',
        columns=columns,
        stats=stats,
        stage_order=STAGE_ORDER,
        stage_labels=STAGE_LABELS,
        segment=segment,
        geo=geo,
    )


@bp.route('/api/outreach/cards')
def api_cards():
    status = request.args.get('status', 'enriched')
    segment = request.args.get('segment', 'coaches')
    geo = request.args.get('geo', 'all')
    limit = int(request.args.get('limit', 50))
    rows = outreach_db.list_prospects(status=status, segment=segment, geo=geo, limit=limit)
    return jsonify({'cards': [_decorate_row(r) for r in rows]})


@bp.route('/api/outreach/move', methods=['POST'])
def api_move():
    """Drag-drop card to a new stage column."""
    data = request.json or {}
    pid = int(data.get('id', 0))
    target = data.get('target_status')
    if not pid or target not in STAGE_LABELS:
        return jsonify({'ok': False, 'error': 'bad ids/status'}), 400
    outreach_db.update_prospect(pid, {'status': target})
    return jsonify({'ok': True})


@bp.route('/api/outreach/mark-sent', methods=['POST'])
def api_mark_sent():
    data = request.json or {}
    ids = data.get('ids') or []
    if isinstance(ids, int):
        ids = [ids]
    for pid in ids:
        try:
            outreach_db.update_prospect(int(pid), {'status': 'sent'})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e), 'failed_id': pid}), 500
    return jsonify({'ok': True, 'count': len(ids)})


@bp.route('/api/outreach/mark-replied', methods=['POST'])
def api_mark_replied():
    data = request.json or {}
    pid = int(data.get('id', 0))
    classification = data.get('classification')
    text = data.get('text', '')
    if not pid or classification not in VALID_REPLIES:
        return jsonify({'ok': False, 'error': 'bad id/classification'}), 400
    outreach_db.update_prospect(pid, {
        'status': 'replied',
        'reply_classification': classification,
        'reply_text': text,
    })
    return jsonify({'ok': True})


@bp.route('/api/outreach/edit-hook', methods=['POST'])
def api_edit_hook():
    """Persist edited DM text before send so analytics know what was actually sent."""
    data = request.json or {}
    pid = int(data.get('id', 0))
    new_hook = data.get('personal_hook')
    if not pid or new_hook is None:
        return jsonify({'ok': False, 'error': 'bad id/hook'}), 400
    outreach_db.update_prospect(pid, {'personal_hook': new_hook})
    return jsonify({'ok': True})


@bp.route('/api/ad-leads/intake', methods=['POST'])
def api_ad_lead_intake():
    """Receive Tally form-fill webhook. Lands as outreach_prospects row with status=ad-lead."""
    data = request.json or {}

    # Tally webhook shape: {"data": {"fields": [{"label": ..., "value": ...}], ...}}
    fields = {}
    for f in (data.get('data') or {}).get('fields') or []:
        label = (f.get('label') or '').lower().replace(' ', '_').replace('?', '').replace("'", '')
        fields[label] = f.get('value')

    name = fields.get('name') or fields.get('full_name') or 'Unknown'
    ig_handle = (fields.get('ig_handle') or fields.get('instagram') or '').lstrip('@') or None
    pain = fields.get('whats_eating_your_time') or fields.get('pain') or fields.get('biggest_time-suck')

    prospect = {
        'segment': 'coaches',
        'name': name,
        'ig_handle': ig_handle,
        'ig_url': f"https://instagram.com/{ig_handle}/" if ig_handle else None,
        'source': 'ad-landing',
        'source_query': 'tally-webhook',
        'pain_signal': pain,
        'status': 'ad-lead',
        'raw_payload': data,
    }
    pid = outreach_db.insert_prospect(prospect)
    return jsonify({'ok': True, 'id': pid})
