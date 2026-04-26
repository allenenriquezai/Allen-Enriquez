"""
Skool community discovery scraper.

Browses https://www.skool.com/discovery and captures community cards
matching coach-ICP filter rules:
  - Categories: Business / Marketing / Tech / Education
  - >=2K members OR >=$30/mo paid

Output: list of prospect dicts ready for outreach_db.insert_prospect.

The Skool discovery page is mostly public (no login required) but a saved
session helps avoid throttling. Run with --interactive once to seed state.

Usage (programmatic):
    from outreach_sources.scrape_skool import scrape_skool
    rows = scrape_skool(limit=10, geo='all')

CLI:
    python3 -m outreach_sources.scrape_skool --limit 10
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from outreach_sources._browser import platform_browser

DISCOVERY_URL = 'https://www.skool.com/discovery'

# Category filter — Skool discovery page has tabs at the top
TARGET_CATEGORIES = ['Business', 'Sales', 'Tech', 'Education']

MIN_MEMBERS = 2000
MIN_PRICE_USD = 30


def _parse_members(text):
    """Skool shows '2.5k Members' or '850 Members' etc."""
    if not text:
        return 0
    m = re.search(r'([\d,.]+)\s*([kKmM]?)', text)
    if not m:
        return 0
    num_str, suffix = m.group(1).replace(',', ''), m.group(2).lower()
    try:
        n = float(num_str)
    except ValueError:
        return 0
    if suffix == 'k':
        n *= 1000
    elif suffix == 'm':
        n *= 1_000_000
    return int(n)


def _parse_price(text):
    """Skool shows '$97 / month' or 'Free'."""
    if not text:
        return 0
    if 'free' in text.lower():
        return 0
    m = re.search(r'\$?\s*([\d,]+)', text)
    if not m:
        return 0
    return int(m.group(1).replace(',', ''))


def scrape_skool(limit=10, geo='all', headless=True):
    """Returns list of prospect dicts (segment defaulted by caller).

    Each dict has: name (owner), skool_url, community_name, community_size,
    community_price_usd, source='skool', source_query=<category>, sub_segment.
    """
    out = []
    seen_urls = set()

    with platform_browser('skool', headless=headless) as page:
        for category in TARGET_CATEGORIES:
            if len(out) >= limit:
                break
            url = DISCOVERY_URL  # Skool no longer supports ?c= category filter; one feed
            try:
                page.goto(url, timeout=30000)
                page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception as e:
                print(f"[scrape_skool] load failed: {e}", file=sys.stderr)
                break

            for _ in range(5):
                page.mouse.wheel(0, 2000)
                time.sleep(1.2)

            # Community cards: <a href="/<slug>/about?utm_..."> with parent containing members/price text
            cards = page.eval_on_selector_all(
                'a[href*="/about?"]',
                """elements => elements
                    .filter(a => {
                        const href = a.getAttribute('href') || '';
                        return href.startsWith('/') && href.includes('/about?utm') && !href.startsWith('/discovery');
                    })
                    .map(a => ({
                        href: a.getAttribute('href'),
                        text: (a.innerText || '').slice(0, 1500),
                    }))
                """
            )
            seen_local = set()
            cards = [c for c in cards if c['href'] not in seen_local and not seen_local.add(c['href'])]

            for card in cards:
                if len(out) >= limit:
                    break
                href = card.get('href') or ''
                full_url = f"https://www.skool.com{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                text = card.get('text') or ''
                members_m = re.search(r'([\d.,]+\s*[kKmM]?)\s*Members', text)
                price_m = re.search(r'(Free|\$[\d,]+\s*/\s*month)', text, re.IGNORECASE)

                members = _parse_members(members_m.group(1)) if members_m else 0
                price = _parse_price(price_m.group(1)) if price_m else 0

                # Filter rule: >=2K members OR >=$30/mo
                if members < MIN_MEMBERS and price < MIN_PRICE_USD:
                    continue

                # Skool card format: '#N\nName\nDescription\nXk Members  •  $Y/month'
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines and lines[0].startswith('#') and lines[0][1:].strip().isdigit():
                    lines = lines[1:]
                community_name = lines[0] if lines else href.split('/')[1] if '/' in href else href

                # Owner extraction is unreliable from card; defer to per-community page
                owner_name = ''
                owner_url = ''

                sub_segment = 'community-led' if price >= MIN_PRICE_USD else None
                if 'agency' in community_name.lower() or 'agency' in text.lower()[:500]:
                    sub_segment = 'agency-coach'

                out.append({
                    'name': owner_name or community_name,
                    'skool_url': full_url,
                    'community_name': community_name,
                    'community_size': members,
                    'community_price_usd': price,
                    'sub_segment': sub_segment,
                    'source': 'skool',
                    'source_query': category,
                    'bio': text[:1000],
                    'raw_payload': {'card_text': text, 'href': href},
                    'segment': 'coaches',
                })
            time.sleep(2)

    print(f"[scrape_skool] returning {len(out)} prospects (filter: ≥{MIN_MEMBERS} members or ≥${MIN_PRICE_USD}/mo)")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=10)
    p.add_argument('--geo', default='all')
    p.add_argument('--no-headless', action='store_true')
    p.add_argument('--print', action='store_true')
    p.add_argument('--insert', action='store_true', help='also insert into outreach.db')
    args = p.parse_args()

    rows = scrape_skool(limit=args.limit, geo=args.geo, headless=not args.no_headless)
    if args.print:
        for r in rows:
            print(json.dumps({k: v for k, v in r.items() if k != 'raw_payload'}, indent=2))
    if args.insert:
        from outreach_db import insert_prospect
        n = sum(1 for r in rows if insert_prospect(r))
        print(f"[scrape_skool] inserted/deduped: {n} of {len(rows)}")


if __name__ == '__main__':
    main()
