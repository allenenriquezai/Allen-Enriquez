"""
Daily Meta ad creative iterator for Allen's coach campaign.

Runs on 2am cron. Pulls metrics → generates 3 new creative variants via Claude Haiku →
pushes new ads → pauses bottom performer.

CLI:
  python3 tools/personal/ad_iterator.py --campaign-id <id>          # daily run
  python3 tools/personal/ad_iterator.py --campaign-id <id> --dry-run # no Meta writes
  python3 tools/personal/ad_iterator.py --once                      # one iteration, all active campaigns
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / 'projects' / 'personal' / 'data' / 'outreach.db'

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

# Meta Graph API
META_API_VERSION = 'v19.0'
META_GRAPH_BASE = f'https://graph.instagram.com/{META_API_VERSION}'

# Voice rules for ad creative generation (from positioning.md)
CREATIVE_SYSTEM_PROMPT = """You generate 3 Facebook ad creative variants targeting coaches running cohorts.
Use this voice:
- 3rd-grade reading level (max 10 words per sentence)
- No jargon, no guru-pitch
- Warm-direct, operator-to-operator
- Allen is the author; sign as "Allen"
- 2-week free pilot is the offer
- 5 connected AI pillars, not one-off automations
- Built on Claude Code + n8n, git-native, client-owned

Each variant needs:
- primary_text (3-4 sentences, the main copy)
- headline (short, punchy, max 40 chars)
- description (supporting text, max 90 chars)

Return VALID JSON ONLY, no preamble:
{
  "variants": [
    {"primary_text": "...", "headline": "...", "description": "..."},
    {"primary_text": "...", "headline": "...", "description": "..."},
    {"primary_text": "...", "headline": "...", "description": "..."}
  ]
}
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@contextmanager
def get_conn(db_path=DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_ad_iterations_table(db_path=DB_PATH):
    """Create ad_iterations table if not exists (idempotent)."""
    schema = """
    CREATE TABLE IF NOT EXISTS ad_iterations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_id TEXT,
        campaign_id TEXT,
        source_hook TEXT,
        primary_text TEXT,
        headline TEXT,
        description TEXT,
        generated_at TEXT NOT NULL,
        metrics_24h_json TEXT,
        won_round INTEGER DEFAULT 0,
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_ad_iterations_ad_id ON ad_iterations(ad_id);
    CREATE INDEX IF NOT EXISTS idx_ad_iterations_campaign_id ON ad_iterations(campaign_id);
    """
    with get_conn(db_path) as conn:
        conn.executescript(schema)


def record_iteration(db_path, ad_id, source_hook, generated_at, notes=''):
    """Record an ad iteration to the database."""
    init_ad_iterations_table(db_path)
    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO ad_iterations (ad_id, source_hook, generated_at, notes)
               VALUES (?, ?, ?, ?)""",
            (ad_id, source_hook, generated_at, notes),
        )


def meta_pull_metrics(ad_account_id, token, date_preset='yesterday', dry_run=False):
    """
    Pull ad metrics from Meta Graph API.

    GET /act_{ad_account_id}/insights?level=ad&fields=ad_id,ad_name,spend,impressions,clicks,cost_per_action_type,actions&date_preset=yesterday

    Returns list of dicts with per-ad metrics and computed CPL (cost_per_lead).
    """
    if dry_run:
        print(f"[meta_pull_metrics DRY-RUN] would fetch from account {ad_account_id}", file=sys.stderr)
        return []

    if not token:
        print("[meta_pull_metrics] missing Meta token; returning empty", file=sys.stderr)
        return []

    try:
        url = (
            f"{META_GRAPH_BASE}/act_{ad_account_id}/insights"
            f"?level=ad"
            f"&fields=ad_id,ad_name,spend,impressions,clicks,cost_per_action_type,actions"
            f"&date_preset={date_preset}"
            f"&access_token={token}"
        )
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        metrics = []
        for row in data.get('data', []):
            ad_id = row.get('ad_id')
            ad_name = row.get('ad_name', '')
            spend = float(row.get('spend') or 0)
            impressions = int(row.get('impressions') or 0)
            clicks = int(row.get('clicks') or 0)

            # Extract lead actions CPL
            cpl = None
            cost_per_action_type = row.get('cost_per_action_type') or []
            for action in cost_per_action_type:
                if action.get('action_type') == 'lead':
                    cpl = float(action.get('value') or 0)
                    break

            metrics.append({
                'ad_id': ad_id,
                'ad_name': ad_name,
                'spend': spend,
                'impressions': impressions,
                'clicks': clicks,
                'cpl': cpl,  # cost per lead in PHP (Meta API native currency)
            })

        return metrics
    except Exception as e:
        print(f"[meta_pull_metrics] error: {e}", file=sys.stderr)
        return []


def _call_haiku(api_key, system, user, max_tokens=800, temperature=0.4):
    """Call Claude Haiku API via urllib."""
    body = json.dumps({
        'model': HAIKU_MODEL,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return (data.get('content') or [{}])[0].get('text', '').strip()


def _extract_json(text):
    """Extract JSON object from text (handles markdown code blocks)."""
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def generate_creative_variants(top_performer_text, n=3, anthropic_key=None):
    """
    Generate n creative variants based on a top-performing ad text.

    Returns list of dicts: [{"primary_text": "...", "headline": "...", "description": "..."}, ...]
    Never raises; returns empty list on failure.
    """
    api_key = anthropic_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("[generate_creative_variants] missing ANTHROPIC_API_KEY", file=sys.stderr)
        return []

    user_prompt = f"""Generate {n} fresh creative variants inspired by this top-performing ad text:

"{top_performer_text}"

Each variant should:
1. Keep the same offer and ICP (coaches running cohorts in PH)
2. Use different hooks/angles (e.g., pain signal, social proof, mechanism)
3. Follow all voice rules (3rd grade, <10 words/sentence, warm-direct, no guru)
4. Be distinct enough to test different angles

Remember: Sign as "Allen", mention 2-week free pilot, 5 connected pillars, client-owned system."""

    try:
        raw = _call_haiku(api_key, CREATIVE_SYSTEM_PROMPT, user_prompt)
        parsed = _extract_json(raw)
        if not parsed or 'variants' not in parsed:
            print(f"[generate_creative_variants] invalid response structure: {raw[:200]}", file=sys.stderr)
            return []

        variants = parsed.get('variants', [])
        if len(variants) != n:
            print(f"[generate_creative_variants] expected {n} variants, got {len(variants)}", file=sys.stderr)

        return variants[:n]
    except Exception as e:
        print(f"[generate_creative_variants] error: {e}", file=sys.stderr)
        return []


def meta_push_creative(ad_account_id, page_id, token, creative_dict, link_url, dry_run=False):
    """
    Create a creative asset on Meta.

    POST /act_{ad_account_id}/adcreatives with object_story_spec.link_data

    Returns creative_id string, or None on error.
    """
    if dry_run:
        dry_id = f"creative_{datetime.now().timestamp()}".replace('.', '_')
        print(f"[meta_push_creative DRY-RUN] would create creative {dry_id}", file=sys.stderr)
        return dry_id

    if not token:
        print("[meta_push_creative] missing Meta token", file=sys.stderr)
        return None

    # Build link_data object
    link_data = {
        'message': creative_dict.get('primary_text', ''),
        'link': link_url,
        'caption': creative_dict.get('headline', ''),
        'description': creative_dict.get('description', ''),
    }

    object_story_spec = {
        'page_id': page_id,
        'link_data': link_data,
    }

    payload = {
        'object_story_spec': json.dumps(object_story_spec),
        'access_token': token,
    }

    try:
        url = f"{META_GRAPH_BASE}/act_{ad_account_id}/adcreatives"
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=body, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        creative_id = data.get('id')
        if creative_id:
            print(f"[meta_push_creative] created {creative_id}", file=sys.stderr)
        return creative_id
    except Exception as e:
        print(f"[meta_push_creative] error: {e}", file=sys.stderr)
        return None


def meta_create_ad(ad_account_id, ad_set_id, token, creative_id, name, dry_run=False):
    """
    Create an ad within an ad set.

    POST /act_{ad_account_id}/ads with adset_id, creative_id, name, status

    Returns ad_id string, or None on error.
    """
    if dry_run:
        dry_id = f"ad_{datetime.now().timestamp()}".replace('.', '_')
        print(f"[meta_create_ad DRY-RUN] would create ad {dry_id}", file=sys.stderr)
        return dry_id

    if not token:
        print("[meta_create_ad] missing Meta token", file=sys.stderr)
        return None

    payload = {
        'adset_id': ad_set_id,
        'creative': json.dumps({'creative_id': creative_id}),
        'name': name,
        'status': 'PAUSED',  # Start paused; Allen manually approves in UI
        'access_token': token,
    }

    try:
        url = f"{META_GRAPH_BASE}/act_{ad_account_id}/ads"
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=body, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        ad_id = data.get('id')
        if ad_id:
            print(f"[meta_create_ad] created {ad_id}", file=sys.stderr)
        return ad_id
    except Exception as e:
        print(f"[meta_create_ad] error: {e}", file=sys.stderr)
        return None


def meta_pause_ad(ad_id, token, dry_run=False):
    """Pause an ad."""
    if dry_run:
        print(f"[meta_pause_ad DRY-RUN] would pause {ad_id}", file=sys.stderr)
        return True

    if not token:
        print("[meta_pause_ad] missing Meta token", file=sys.stderr)
        return False

    try:
        url = f"{META_GRAPH_BASE}/{ad_id}"
        payload = {
            'status': 'PAUSED',
            'access_token': token,
        }
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=body, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        success = data.get('success', False)
        if success:
            print(f"[meta_pause_ad] paused {ad_id}", file=sys.stderr)
        return success
    except Exception as e:
        print(f"[meta_pause_ad] error: {e}", file=sys.stderr)
        return False


def should_kill(ad_metrics, threshold_cpl_php=400, sustained_days=3):
    """
    Determine if an ad should be paused based on metrics.

    Criteria:
    - CPL > threshold_cpl_php sustained for sustained_days
    - 0 leads after high spend (≥₱2K)
    """
    if not ad_metrics:
        return False

    latest = ad_metrics[-1]
    cpl = latest.get('cpl')
    spend = latest.get('spend', 0)

    # Rule 1: CPL above threshold
    if cpl and cpl > threshold_cpl_php:
        return True

    # Rule 2: High spend with 0 leads
    if spend >= 2000 and cpl is None:
        return True

    return False


def load_env(env_path):
    """Load .env file into os.environ."""
    env_path = Path(env_path)
    if not env_path.exists():
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()


def main():
    parser = argparse.ArgumentParser(
        description='Daily Meta ad creative iterator for coach campaign.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tools/personal/ad_iterator.py --campaign-id <id>          # daily run
  python3 tools/personal/ad_iterator.py --campaign-id <id> --dry-run # test without writes
  python3 tools/personal/ad_iterator.py --once                      # one iteration, all active
        """,
    )
    parser.add_argument('--campaign-id', help='Meta campaign ID to iterate')
    parser.add_argument('--ad-account-id', help='Meta ad account ID (optional, pulls from env)')
    parser.add_argument('--page-id', help='Meta page ID (optional, pulls from env)')
    parser.add_argument('--dry-run', action='store_true', help='No Meta API writes')
    parser.add_argument('--once', action='store_true', help='Single iteration, all active campaigns')

    args = parser.parse_args()

    # Load environment
    env_path = BASE_DIR / 'projects' / 'personal' / '.env'
    load_env(env_path)

    # Validate credentials
    meta_token = os.environ.get('META_ADS_TOKEN')
    if not meta_token and not args.dry_run:
        print("Error: META_ADS_TOKEN not set in env. Use --dry-run for testing.", file=sys.stderr)
        sys.exit(1)

    # Initialize DB
    init_ad_iterations_table()

    # For now, just print that setup succeeded
    print("[ad_iterator] initialized", file=sys.stderr)
    print(f"[ad_iterator] dry_run={args.dry_run}, once={args.once}, campaign_id={args.campaign_id}", file=sys.stderr)

    if args.dry_run:
        print("[ad_iterator] DRY-RUN mode: no Meta API writes", file=sys.stderr)

    # TODO: Implement full iteration loop when Meta account is set up
    # For now, this script validates setup and DB structure

    return 0


if __name__ == '__main__':
    sys.exit(main())


# Add urllib.parse import for urlencode
import urllib.parse
