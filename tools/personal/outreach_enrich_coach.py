"""
Coach-prospect enrichment via Claude Haiku.

Input: outreach_prospects row (dict) populated by scrape_skool/scrape_ig/scrape_linkedin
       with bio + recent_posts already captured.
Output: dict of fields to update — pain_signal, recent_post_topic, sub_segment,
        personal_hook, hook_variant.

Distinct from outreach_enrich.py (which targets PH biz websites). Coach
enrichment runs entirely on social data already captured at discovery time;
no website scraping needed.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

SYSTEM_PROMPT = """You analyse a coach/course-creator's public social profile and decide:

1. SUB_SEGMENT (one of):
   - business-coach (teaches running/scaling biz: agency, freelance->founder, scale-your-service)
   - agency-coach (teaches building marketing/AI/automation agencies)
   - tech-course-creator (no-code, AI, automation, sales-systems courses)
   - community-led (Skool/Circle community is the primary product)

2. PAIN_SIGNAL: One short phrase describing a specific operational pain
   visible in their recent posts (e.g. "drowning in DMs", "no-show rate spiking",
   "onboarding chaos with new cohort", "answering same questions weekly").
   Empty string if no clear pain signal.

3. RECENT_POST_TOPIC: One short phrase summarising what their most recent 1-2
   posts were about (e.g. "agency scaling tactics", "Q1 student wins").

4. HOOK_VARIANT (one of A/B/C):
   - A: business-coach or agency-coach without a clear pain signal
   - B: community-led or tech-course-creator (use Skool community angle)
   - C: any sub-segment WITH a clear pain signal (highest-leverage)

5. PERSONAL_HOOK: A 4-sentence DM in Allen's voice using the chosen variant
   template. Voice rules: 3rd-grade reading level, <10 words/sentence, no jargon,
   warm-direct. Allen installs an AI backend (5 connected pillars) for coaches
   running cohorts. 2-week free pilot is the offer. Sign as "Allen".

Return STRICT JSON, no preamble, no markdown:
{
  "sub_segment": "agency-coach",
  "pain_signal": "drowning in onboarding for new cohort",
  "recent_post_topic": "scaling cohort to 50 students",
  "hook_variant": "C",
  "personal_hook": "Hey Sarah — your post about onboarding chaos hit.\\n\\nI install AI systems that fix exactly that for coaches with audiences. 5 connected pillars, not one-off automations.\\n\\n2-week free pilot, no obligation. If it doesn't help, you walk.\\n\\nWant to see what we'd build?\\n\\n— Allen"
}
"""


def _build_user_prompt(prospect):
    name = prospect.get('name') or 'there'
    parts = [f"Coach name: {name}"]
    if prospect.get('ig_handle'):
        parts.append(f"IG: @{prospect['ig_handle']}")
    if prospect.get('audience_size'):
        parts.append(f"IG audience: {prospect['audience_size']:,}")
    if prospect.get('community_name'):
        parts.append(f"Skool community: {prospect['community_name']} ({prospect.get('community_size') or '?'} members, ${prospect.get('community_price_usd') or '?'}/mo)")
    if prospect.get('bio'):
        parts.append(f"Bio: {prospect['bio'][:500]}")

    posts = prospect.get('recent_posts') or []
    if isinstance(posts, str):
        try:
            posts = json.loads(posts)
        except Exception:
            posts = []
    if posts:
        parts.append("Recent posts (most recent first):")
        for i, p in enumerate(posts[:5], 1):
            text = p.get('text') if isinstance(p, dict) else str(p)
            if text:
                parts.append(f"  {i}. {text[:400]}")

    return '\n'.join(parts)


def _call_haiku(api_key, system, user, max_tokens=600, temperature=0.4):
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


def enrich_coach_prospect(prospect, anthropic_api_key=None):
    """Run Haiku enrichment on a single prospect dict.

    Returns dict of fields to update on the row, or empty dict on failure.
    Never raises; failures log to stderr and return {}.
    """
    api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print('[enrich_coach] missing ANTHROPIC_API_KEY', file=sys.stderr)
        return {}

    bio = prospect.get('bio') or ''
    posts = prospect.get('recent_posts') or prospect.get('recent_posts_json') or ''
    if not bio and not posts:
        return {}

    user = _build_user_prompt(prospect)
    try:
        raw = _call_haiku(api_key, SYSTEM_PROMPT, user)
    except Exception as e:
        print(f"[enrich_coach] haiku error for {prospect.get('name')}: {e}", file=sys.stderr)
        return {}

    parsed = _extract_json(raw)
    if not parsed:
        print(f"[enrich_coach] could not parse JSON for {prospect.get('name')}: {raw[:200]}", file=sys.stderr)
        return {}

    out = {}
    for field in ('sub_segment', 'pain_signal', 'recent_post_topic', 'hook_variant', 'personal_hook'):
        v = parsed.get(field)
        if v is not None:
            out[field] = v
    out['status'] = 'enriched'
    return out


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--prospect-id', type=int, help='enrich one prospect by id')
    p.add_argument('--all', action='store_true', help='enrich all rows where status=discovered')
    p.add_argument('--limit', type=int, default=20)
    args = p.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    from outreach_db import get_prospect, list_prospects, update_prospect

    if args.prospect_id:
        rows = [get_prospect(args.prospect_id)]
    else:
        rows = list_prospects(status='discovered', segment='coaches', limit=args.limit)

    for row in rows:
        if not row:
            continue
        if isinstance(row.get('recent_posts_json'), str):
            try:
                row['recent_posts'] = json.loads(row['recent_posts_json'])
            except Exception:
                row['recent_posts'] = []
        updates = enrich_coach_prospect(row)
        if updates:
            update_prospect(row['id'], updates)
            print(f"[enrich_coach] {row['id']:>4d} {row.get('name'):30s} -> {updates.get('sub_segment')} / {updates.get('hook_variant')}")
        else:
            print(f"[enrich_coach] {row['id']:>4d} {row.get('name'):30s} SKIPPED (no enrichment)")
