"""
LinkedIn cohort/agency-coach scraper.

Searches LinkedIn for coaches/founders running cohort-based or community-led
programs. Captures profile data: name, headline, bio, follower count, recent posts.

Output: list of prospect dicts ready for outreach_db.insert_prospect.

Usage (programmatic):
    from outreach_sources.scrape_linkedin import scrape_linkedin
    rows = scrape_linkedin(limit=5, geo='all')

CLI:
    python3 -m outreach_sources.scrape_linkedin --limit 5 [--no-headless] [--print] [--insert]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent.parent))

from outreach_sources._browser import platform_browser

# LinkedIn People search queries — rotated per run
SEARCH_QUERIES = [
    'cohort coach',
    'agency owner cohort',
    'scale your agency',
    'coaching business automation',
]

# Geo patterns to extract from profile location
GEO_MAP = {
    'au': 'AU',
    'australia': 'AU',
    'us': 'US',
    'usa': 'US',
    'united states': 'US',
    'uk': 'UK',
    'united kingdom': 'UK',
    'canada': 'CA',
    'ca': 'CA',
    'philippines': 'PH',
    'ph': 'PH',
}

# Signals to look for in headline/about
COACH_SIGNALS = ['coach', 'founder', 'ceo', 'agency owner', 'course creator', 'instructor']
PROGRAM_SIGNALS = ['cohort', 'skool', 'community', 'students', 'members', 'mastermind']


def _extract_geo(location_text):
    """Extract geo code from location string (AU/US/UK/CA/PH or None)."""
    if not location_text:
        return None
    loc_lower = location_text.lower().strip()
    for key, code in GEO_MAP.items():
        if key in loc_lower:
            return code
    return None


def _has_coach_signals(text):
    """Check if text contains coach-related keywords."""
    if not text:
        return False
    text_lower = text.lower()
    return any(sig in text_lower for sig in COACH_SIGNALS)


def _has_program_signals(text):
    """Check if text contains community/cohort-related keywords."""
    if not text:
        return False
    text_lower = text.lower()
    return any(sig in text_lower for sig in PROGRAM_SIGNALS)


def _parse_follower_count(text):
    """Extract follower count from profile text like '1,234 followers' or '2.5K followers'."""
    if not text:
        return 0
    # Match patterns: '1,234 followers', '2.5K followers', etc.
    m = re.search(r'([\d,.]+\s*[kKmM]?)\s*(?:followers?|connections?)', text)
    if not m:
        return 0
    num_str = m.group(1).replace(',', '').strip()
    try:
        n = float(num_str)
        if 'k' in num_str.lower():
            n *= 1000
        elif 'm' in num_str.lower():
            n *= 1_000_000
        return int(n)
    except ValueError:
        return 0


def _parse_main_lines(main_text):
    """Parse <main> innerText: line 0 = name, headline = line after '· Nth'/'· You', then location, etc."""
    lines = [l for l in (main_text or '').split('\n') if l.strip()]
    name = lines[0].strip() if lines else ''
    headline = ''
    location = ''
    # Find headline = first non-degree non-name long line
    for i, line in enumerate(lines[1:], 1):
        s = line.strip()
        if s.startswith('·') or s in ('1st', '2nd', '3rd', 'You'):
            continue
        if len(s) > 15:
            headline = s
            # Location is usually the next non-bullet line
            for nxt in lines[i + 1:]:
                t = nxt.strip()
                if t == '·' or t.startswith('·'):
                    continue
                if t and 'connect' not in t.lower() and 'message' not in t.lower():
                    location = t
                    break
            break
    return name, headline, location


def _get_profile_data(page, profile_url):
    """Navigate to a profile URL and scrape name, headline, location, about, followers."""
    try:
        page.goto(profile_url, timeout=20000, wait_until='domcontentloaded')
        time.sleep(3)
    except Exception as e:
        print(f"[scrape_linkedin] profile load failed for {profile_url}: {e}", file=sys.stderr)
        return None

    if 'login' in page.url.lower() or 'authwall' in page.url.lower():
        return None

    main_text = page.evaluate('document.querySelector("main")?.innerText || ""')
    if not main_text:
        return None

    name, headline, location = _parse_main_lines(main_text)

    # About section — find <section> whose <h2> contains "about"
    about = page.evaluate("""
        () => {
            for (const s of document.querySelectorAll('section')) {
                const h = s.querySelector('h2');
                if (h && h.textContent.toLowerCase().includes('about')) {
                    return s.innerText.replace(/^About\\s*/i, '').trim().slice(0, 2000);
                }
            }
            return '';
        }
    """)

    # Followers — search main text for "N followers" or "N connections"
    followers = _parse_follower_count(main_text)

    return {
        'name': name,
        'headline': headline,
        'location': location,
        'about': about or '',
        'followers': followers,
        'recent_posts': [],
    }


def scrape_linkedin(limit=5, geo='all', headless=True):
    """Returns list of prospect dicts matching coach-ICP filter.

    Each dict has: name, linkedin_url, geo, audience_size (follower count),
    bio (headline + about), recent_posts, source='linkedin', source_query,
    segment='coaches', sub_segment.
    """
    out = []
    seen_urls = set()
    profile_count = 0
    max_profile_views = 30  # LinkedIn throttling threshold

    with platform_browser('linkedin', headless=headless) as page:
        for query in SEARCH_QUERIES:
            if len(out) >= limit or profile_count >= max_profile_views:
                break

            # Navigate to LinkedIn People search
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(query)}"
            try:
                page.goto(search_url, timeout=30000)
                page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception as e:
                print(f"[scrape_linkedin] search load failed for '{query}': {e}", file=sys.stderr)
                continue

            # Check for login redirect
            if 'login' in page.url.lower():
                print(f"[scrape_linkedin] logged out — saved session may have expired", file=sys.stderr)
                return []

            time.sleep(2)

            # Scroll to load result cards
            for _ in range(2):
                page.mouse.wheel(0, 1500)
                time.sleep(1)

            # Extract search result cards: walk up from /in/ link to first ancestor that
            # contains text >100 chars AND exactly one /in/ link (avoids overlap from
            # "mutual connection" sub-anchors pointing to other profiles).
            try:
                cards = page.eval_on_selector_all(
                    'a[href*="/in/"]',
                    """elements => {
                        const seen = new Set();
                        const out = [];
                        for (const a of elements) {
                            const href = a.getAttribute('href') || '';
                            const url = href.startsWith('http') ? href.split('?')[0] : `https://www.linkedin.com${href.split('?')[0]}`;
                            if (seen.has(url)) continue;
                            let p = a;
                            for (let i = 0; i < 8; i++) {
                                p = p.parentElement;
                                if (!p) break;
                                const text = (p.innerText || '').trim();
                                const inLinks = p.querySelectorAll('a[href*="/in/"]').length;
                                if (text.length > 100 && inLinks === 1) {
                                    seen.add(url);
                                    out.push({ url, text: text.slice(0, 2000) });
                                    break;
                                }
                            }
                        }
                        return out;
                    }"""
                )
            except Exception as e:
                print(f"[scrape_linkedin] card extraction failed for '{query}': {e}", file=sys.stderr)
                cards = []

            for card in cards:
                if len(out) >= limit or profile_count >= max_profile_views:
                    break

                profile_url = card.get('url')
                card_text = card.get('text') or ''

                # Normalize URL
                if profile_url and not profile_url.startswith('http'):
                    profile_url = f"https://www.linkedin.com{profile_url}"

                if profile_url in seen_urls:
                    continue
                seen_urls.add(profile_url)

                # Filter signals from card text: must have coach-like role
                if not _has_coach_signals(card_text):
                    continue

                # Track program signal from card text (cheap pre-fetch)
                lines = [l.strip() for l in card_text.split('\n') if l.strip()]
                has_program = _has_program_signals(card_text)

                # Fetch profile — name/headline/location/about all come from profile page
                profile_count += 1
                profile_data = _get_profile_data(page, profile_url)
                if not profile_data or not profile_data.get('name'):
                    continue

                time.sleep(5)  # Throttle between profile views

                name = profile_data['name']
                full_bio = ' '.join([
                    profile_data.get('headline') or '',
                    profile_data.get('about') or '',
                ]).strip()
                if not has_program:
                    has_program = _has_program_signals(full_bio)

                extracted_geo = _extract_geo(profile_data.get('location') or '')
                if geo != 'all' and extracted_geo != geo:
                    if extracted_geo:
                        continue

                # Determine sub_segment — community-led wins when program signals present
                sub_segment = None
                if has_program and ('cohort' in full_bio.lower() or 'skool' in full_bio.lower() or 'community' in full_bio.lower()):
                    sub_segment = 'community-led'
                elif 'agency' in full_bio.lower():
                    sub_segment = 'agency-coach'
                elif 'course' in full_bio.lower() or 'automation' in full_bio.lower():
                    sub_segment = 'tech-course-creator'
                elif has_program:
                    sub_segment = 'business-coach-program'
                else:
                    sub_segment = 'unqualified'

                out.append({
                    'name': name,
                    'linkedin_url': profile_url,
                    'geo': extracted_geo,
                    'audience_size': profile_data['followers'],
                    'bio': full_bio[:1000],
                    'recent_posts': profile_data.get('recent_posts'),
                    'source': 'linkedin',
                    'source_query': query,
                    'segment': 'coaches',
                    'sub_segment': sub_segment,
                    'raw_payload': {
                        'card_text': card_text,
                        'headline': profile_data.get('headline'),
                        'about': profile_data.get('about'),
                    },
                })

            time.sleep(3)

    print(f"[scrape_linkedin] returning {len(out)} prospects ({profile_count} profiles fetched)")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=5)
    p.add_argument('--geo', default='all')
    p.add_argument('--no-headless', action='store_true')
    p.add_argument('--print', action='store_true')
    p.add_argument('--insert', action='store_true', help='also insert into outreach.db')
    args = p.parse_args()

    rows = scrape_linkedin(limit=args.limit, geo=args.geo, headless=not args.no_headless)
    if args.print:
        for r in rows:
            print(json.dumps({k: v for k, v in r.items() if k != 'raw_payload'}, indent=2))
    if args.insert:
        from outreach_db import insert_prospect
        n = sum(1 for r in rows if insert_prospect(r))
        print(f"[scrape_linkedin] inserted/deduped: {n} of {len(rows)}")


if __name__ == '__main__':
    main()
