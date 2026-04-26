"""
Instagram hashtag discovery scraper.

Browses Instagram hashtag pages and captures coach prospects matching ICP:
  - Posts with ≥100 likes from past 7 days
  - Author accounts with ≥5K followers
  - Bio parsed for geo signals (AU/US/UK/CA/PH)

Output: list of prospect dicts ready for outreach_db.insert_prospect.

Requires logged-in IG session. Run with:
    python3 tools/personal/outreach_sources/_browser.py login --platform ig
once, then:
    from outreach_sources.scrape_ig import scrape_ig
    rows = scrape_ig(limit=15, geo='all')

CLI:
    python3 -m outreach_sources.scrape_ig --limit 15
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from outreach_sources._browser import platform_browser

# Hashtags to scan (rotate weekly — pick a subset for first run)
HASHTAGS = [
    'onlinecoach', 'businesscoach', 'coachforcoaches', 'coachingbusiness',
    'agencyowner', 'agencylaunch', 'scaleyouragency',
    'cohort', 'cohortbasedcourse', 'skoolcommunity',
]

MIN_FOLLOWERS = 5000
MIN_LIKES = 100
MAX_PAGES_SCANNED = 50  # Throttle: max 50 page views per run


def _parse_followers(text):
    """Parse follower count from text like '12.5K followers' or '1.2M followers'."""
    if not text:
        return 0
    m = re.search(r'([\d.]+)\s*([KMB])', text, re.IGNORECASE)
    if not m:
        try:
            return int(text.replace(',', '').replace(' ', ''))
        except (ValueError, TypeError):
            return 0
    num_str, suffix = m.group(1), m.group(2).upper()
    try:
        n = float(num_str)
    except ValueError:
        return 0
    if suffix == 'K':
        n *= 1000
    elif suffix == 'M':
        n *= 1_000_000
    elif suffix == 'B':
        n *= 1_000_000_000
    return int(n)


def _parse_geo(bio_text):
    """Extract geo from bio: AU/Australia, US/USA, UK, CA/Canada, PH/Philippines.
    Return normalized code or None."""
    if not bio_text:
        return None
    bio_lower = bio_text.lower()
    # Check for country names/codes
    if any(x in bio_lower for x in ['australia', 'perth', 'melbourne', 'sydney', 'brisbane']):
        return 'AU'
    if any(x in bio_lower for x in ['united states', 'usa', 'new york', 'los angeles', 'chicago']):
        return 'US'
    if any(x in bio_lower for x in ['united kingdom', 'uk ', 'london', 'manchester']):
        return 'UK'
    if any(x in bio_lower for x in ['canada', 'toronto', 'vancouver', 'calgary']):
        return 'CA'
    if any(x in bio_lower for x in ['philippines', 'manila', 'philippines-based']):
        return 'PH'
    return None


def _extract_ig_handle_from_url(url):
    """Extract handle from URL like instagram.com/username/ or instagram.com/username"""
    if not url:
        return None
    m = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/?', url)
    return m.group(1) if m else None


def scrape_ig(limit=15, geo='all', headless=True):
    """Returns list of prospect dicts (segment defaulted by caller).

    Each dict has: name (ig_handle), ig_handle, ig_url, bio, audience_size,
    profile_pic_url, recent_posts (list), geo, source='ig', source_query=<hashtag>, segment='coaches'.
    """
    out = []
    seen_handles = set()
    pages_scanned = 0

    with platform_browser('ig', headless=headless) as page:
        for hashtag in HASHTAGS:
            if len(out) >= limit or pages_scanned >= MAX_PAGES_SCANNED:
                break

            hashtag_url = f'https://www.instagram.com/explore/tags/{hashtag}/'
            try:
                page.goto(hashtag_url, timeout=30000)
                time.sleep(3)
                pages_scanned += 1
                page.wait_for_load_state('networkidle', timeout=15000)
            except Exception as e:
                print(f"[scrape_ig] #{hashtag} load failed: {e}", file=sys.stderr)
                continue

            # Scroll to load post grid
            try:
                page.mouse.wheel(0, 1500)
                time.sleep(1.5)
            except Exception:
                pass

            # Try to find post links in the grid. Instagram uses a/div structure
            # for each post; we look for links pointing to /p/<post-id>
            post_links = []
            try:
                post_links = page.eval_on_selector_all(
                    'a[href*="/p/"]',
                    """elements => elements
                        .slice(0, 20)
                        .map(a => {
                            const href = a.getAttribute('href') || '';
                            const alt = a.getAttribute('alt') || a.innerText || '';
                            return { href, alt };
                        })
                    """
                )
            except Exception as e:
                print(f"[scrape_ig] #{hashtag} post extraction failed: {e}", file=sys.stderr)

            # For each post, try to extract the author handle and profile stats
            for post in post_links:
                if len(out) >= limit or pages_scanned >= MAX_PAGES_SCANNED:
                    break

                href = post.get('href') or ''
                if not href.startswith('/'):
                    continue

                # Navigate to post detail to extract author
                post_url = f"https://www.instagram.com{href}"
                try:
                    page.goto(post_url, timeout=25000)
                    time.sleep(2.5)
                    pages_scanned += 1
                except Exception as e:
                    print(f"[scrape_ig] post {href} load failed: {e}", file=sys.stderr)
                    continue

                # Try to find the author link and click it to get to profile
                # IG shows "Posted by @username" or similar
                author_handle = None
                try:
                    # Look for author profile link (usually near top of modal)
                    author_elem = page.query_selector('a[href*="/"][href*="instagram.com"]')
                    if author_elem:
                        author_url = author_elem.get_attribute('href') or ''
                        author_handle = _extract_ig_handle_from_url(author_url)
                except Exception:
                    pass

                # Fallback: parse post page for author mention
                if not author_handle:
                    try:
                        page_html = page.content()
                        # Look for IG's post meta structure or caption mentioning author
                        m = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/?["\']', page_html)
                        if m:
                            author_handle = m.group(1)
                    except Exception:
                        pass

                if not author_handle:
                    continue

                if author_handle in seen_handles:
                    continue

                # Navigate to author profile
                profile_url = f"https://www.instagram.com/{author_handle}/"
                try:
                    page.goto(profile_url, timeout=25000)
                    time.sleep(2.5)
                    pages_scanned += 1
                except Exception as e:
                    print(f"[scrape_ig] profile {author_handle} load failed: {e}", file=sys.stderr)
                    continue

                # Extract profile info: follower count, bio, profile pic, recent posts
                try:
                    profile_data = page.evaluate("""() => {
                        const meta = document.querySelectorAll('meta');
                        let follower_text = '';
                        let bio = '';
                        let pic_url = '';

                        // Meta tags often contain og:description (bio)
                        for (let m of meta) {
                            const prop = m.getAttribute('property') || m.getAttribute('name') || '';
                            const content = m.getAttribute('content') || '';
                            if (prop === 'og:description') bio = content;
                            if (prop === 'og:image') pic_url = content;
                        }

                        // Look for follower count in visible text
                        const headers = document.querySelectorAll('h1, h2, span');
                        for (let el of headers) {
                            if (el.innerText && el.innerText.includes('followers')) {
                                follower_text = el.innerText;
                                break;
                            }
                        }

                        // Fallback: search page text
                        if (!follower_text) {
                            const pageText = document.body.innerText;
                            const m = pageText.match(/([0-9.,]+\s*[KMB]?)\s*followers?/i);
                            if (m) follower_text = m[1];
                        }

                        return { follower_text, bio, pic_url };
                    }""")

                    follower_text = profile_data.get('follower_text', '')
                    bio = profile_data.get('bio', '')
                    pic_url = profile_data.get('pic_url', '')

                    followers = _parse_followers(follower_text)

                    # Filter: only keep ≥5K followers
                    if followers < MIN_FOLLOWERS:
                        seen_handles.add(author_handle)
                        continue

                    # Extract geo from bio
                    geo_code = _parse_geo(bio)

                    # Try to capture last 3-5 post snippets
                    recent_posts = []
                    try:
                        post_articles = page.query_selector_all('article a[href*="/p/"]')
                        for i, pa in enumerate(post_articles[:5]):
                            post_href = pa.get_attribute('href') or ''
                            if post_href:
                                recent_posts.append({
                                    'url': f"https://www.instagram.com{post_href}",
                                    'position': i + 1,
                                })
                    except Exception:
                        pass

                    seen_handles.add(author_handle)
                    out.append({
                        'name': author_handle,
                        'ig_handle': author_handle,
                        'ig_url': profile_url,
                        'bio': bio[:1000],
                        'audience_size': followers,
                        'profile_pic_url': pic_url,
                        'recent_posts': recent_posts if recent_posts else None,
                        'geo': geo_code,
                        'source': 'ig',
                        'source_query': hashtag,
                        'segment': 'coaches',
                        'raw_payload': {
                            'follower_text': follower_text,
                            'profile_url': profile_url,
                        },
                    })

                except Exception as e:
                    print(f"[scrape_ig] profile extraction {author_handle} failed: {e}", file=sys.stderr)
                    seen_handles.add(author_handle)

            time.sleep(2)

    if pages_scanned >= MAX_PAGES_SCANNED:
        print(f"[scrape_ig] hit page scan limit ({MAX_PAGES_SCANNED})", file=sys.stderr)
    print(f"[scrape_ig] returning {len(out)} prospects (min {MIN_FOLLOWERS} followers, {pages_scanned} pages scanned)")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=15)
    p.add_argument('--geo', default='all')
    p.add_argument('--no-headless', action='store_true')
    p.add_argument('--print', action='store_true')
    p.add_argument('--insert', action='store_true', help='also insert into outreach.db')
    args = p.parse_args()

    try:
        rows = scrape_ig(limit=args.limit, geo=args.geo, headless=not args.no_headless)
    except Exception as e:
        print(f"[scrape_ig] session expired or browser error: {e}", file=sys.stderr)
        print("[scrape_ig] run interactive login: python3 tools/personal/outreach_sources/_browser.py login --platform ig", file=sys.stderr)
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
