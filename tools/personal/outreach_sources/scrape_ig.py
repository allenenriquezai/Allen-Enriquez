"""
Instagram hashtag discovery scraper — GraphQL endpoints only.

Strategy:
  1. Hit /api/v1/tags/web_info/?tag_name=X for each hashtag → walk JSON for user.username
  2. Dedupe handles, then hit /api/v1/users/web_profile_info/?username=X per handle
  3. Filter by MIN_FOLLOWERS, parse geo, return prospect dicts

No DOM scraping. Persistent Chrome profile provides cookies + x-ig-app-id auth.

CLI:
    python3 -m outreach_sources.scrape_ig --limit 15 --no-headless --print
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from outreach_sources._browser import platform_browser

HASHTAGS = [
    'agencyowner', 'agencylaunch', 'scaleyouragency',
    'cohortbasedcourse', 'skoolcommunity', 'communityled',
    'coursecreator', 'salescoach', 'highticketcoach',
]

# Bio keywords that flag fitness/wellness coaches (off-ICP for B2B AI installs)
BIO_EXCLUDE = (
    'fitness', 'dietitian', 'nutrition', 'workout', 'personal trainer', ' pt ',
    'weight loss', 'macros', 'meal plan', 'bodybuilding', 'powerlifting',
)

MIN_FOLLOWERS = 5000
MAX_HASHTAGS = 6
MAX_PROFILES_FETCHED = 80
IG_APP_ID = '936619743392459'


def _parse_followers(value):
    if isinstance(value, int):
        return value
    if not value:
        return 0
    try:
        return int(str(value).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0


def _parse_geo(bio_text):
    if not bio_text:
        return None
    bio_lower = bio_text.lower()
    if any(x in bio_lower for x in ['australia', 'perth', 'melbourne', 'sydney', 'brisbane', '🇦🇺']):
        return 'AU'
    if any(x in bio_lower for x in ['united states', 'usa', 'new york', 'los angeles', 'chicago', '🇺🇸']):
        return 'US'
    if any(x in bio_lower for x in ['united kingdom', 'uk ', 'london', 'manchester', '🇬🇧']):
        return 'UK'
    if any(x in bio_lower for x in ['canada', 'toronto', 'vancouver', 'calgary', '🇨🇦']):
        return 'CA'
    if any(x in bio_lower for x in ['philippines', 'manila', '🇵🇭']):
        return 'PH'
    return None


def _fetch_hashtag_handles(page, hashtag):
    """Hit tags/web_info, walk JSON, return list of unique usernames."""
    js = """async (tag) => {
        const r = await fetch(`https://i.instagram.com/api/v1/tags/web_info/?tag_name=${encodeURIComponent(tag)}`, {
            headers: {'x-ig-app-id': '%s'},
            credentials: 'include',
        });
        if (!r.ok) return {error: r.status};
        const d = await r.json();
        const owners = new Set();
        function walk(obj) {
            if (!obj || typeof obj !== 'object') return;
            if (obj.user && obj.user.username) owners.add(obj.user.username);
            for (const k of Object.keys(obj)) walk(obj[k]);
        }
        walk(d.data && d.data.top);
        walk(d.data && d.data.recent);
        return {handles: Array.from(owners)};
    }""" % IG_APP_ID
    try:
        result = page.evaluate(js, hashtag)
        if result.get('error'):
            return []
        return result.get('handles', [])
    except Exception as e:
        print(f"[scrape_ig] tag fetch {hashtag} failed: {e}", file=sys.stderr)
        return []


def _fetch_profile(page, handle):
    """Hit web_profile_info, return parsed user dict or None."""
    js = """async (h) => {
        const r = await fetch(`https://i.instagram.com/api/v1/users/web_profile_info/?username=${encodeURIComponent(h)}`, {
            headers: {'x-ig-app-id': '%s'},
            credentials: 'include',
        });
        if (!r.ok) return {error: r.status};
        return await r.json();
    }""" % IG_APP_ID
    try:
        return page.evaluate(js, handle)
    except Exception as e:
        return {'error': str(e)}


def _build_prospect(data, handle, hashtag):
    if not data or data.get('error'):
        return None
    user = (data.get('data') or {}).get('user') or {}
    if not user:
        return None
    followers = _parse_followers((user.get('edge_followed_by') or {}).get('count'))
    if followers < MIN_FOLLOWERS:
        return None
    biography = user.get('biography') or ''
    bio_lower = biography.lower()
    if any(kw in bio_lower for kw in BIO_EXCLUDE):
        return None
    pic_url = user.get('profile_pic_url_hd') or user.get('profile_pic_url') or ''
    full_name = user.get('full_name') or handle
    is_business = user.get('is_business_account', False)

    posts = []
    edges = ((user.get('edge_owner_to_timeline_media') or {}).get('edges') or [])[:5]
    for i, edge in enumerate(edges, 1):
        node = edge.get('node') or {}
        caption_edges = (node.get('edge_media_to_caption') or {}).get('edges') or []
        text = ''
        if caption_edges:
            text = ((caption_edges[0].get('node') or {}).get('text') or '')[:500]
        shortcode = node.get('shortcode') or ''
        posts.append({
            'position': i,
            'text': text,
            'url': f'https://www.instagram.com/p/{shortcode}/' if shortcode else '',
            'likes': (node.get('edge_liked_by') or {}).get('count', 0),
        })

    return {
        'name': full_name,
        'ig_handle': handle,
        'ig_url': f'https://www.instagram.com/{handle}/',
        'bio': biography[:1000],
        'audience_size': followers,
        'profile_pic_url': pic_url,
        'recent_posts': posts,
        'geo': _parse_geo(biography),
        'source': 'ig',
        'source_query': hashtag,
        'segment': 'coaches',
        'raw_payload': {
            'is_business_account': is_business,
            'full_name': full_name,
        },
    }


def scrape_ig(limit=15, geo='all', headless=True):
    out = []
    seen_handles = set()
    profiles_fetched = 0

    with platform_browser('ig', headless=headless) as page:
        # Need to be on instagram.com for fetch() to send cookies for the api domain
        page.goto('https://www.instagram.com/', timeout=30000)
        time.sleep(2)

        for hashtag in HASHTAGS[:MAX_HASHTAGS]:
            if len(out) >= limit or profiles_fetched >= MAX_PROFILES_FETCHED:
                break

            handles = _fetch_hashtag_handles(page, hashtag)
            print(f"[scrape_ig] #{hashtag}: {len(handles)} handles")

            for handle in handles:
                if len(out) >= limit or profiles_fetched >= MAX_PROFILES_FETCHED:
                    break
                if handle in seen_handles:
                    continue
                seen_handles.add(handle)

                data = _fetch_profile(page, handle)
                profiles_fetched += 1
                time.sleep(1.2)

                prospect = _build_prospect(data, handle, hashtag)
                if prospect:
                    out.append(prospect)
                    print(f"[scrape_ig]   + {handle} ({prospect['audience_size']:,}f, geo={prospect['geo']})")

            time.sleep(1.5)

    print(f"[scrape_ig] returning {len(out)} prospects ({profiles_fetched} profiles fetched, {len(seen_handles)} unique handles)")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=15)
    p.add_argument('--geo', default='all')
    p.add_argument('--no-headless', action='store_true')
    p.add_argument('--print', action='store_true')
    p.add_argument('--insert', action='store_true')
    args = p.parse_args()

    try:
        rows = scrape_ig(limit=args.limit, geo=args.geo, headless=not args.no_headless)
    except Exception as e:
        print(f"[scrape_ig] error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.print:
        for r in rows:
            print(json.dumps({k: v for k, v in r.items() if k != 'raw_payload'}, indent=2))
    if args.insert:
        from outreach_db import insert_prospect
        n = sum(1 for r in rows if insert_prospect(r))
        print(f"[scrape_ig] inserted/deduped: {n} of {len(rows)}")


if __name__ == '__main__':
    main()
