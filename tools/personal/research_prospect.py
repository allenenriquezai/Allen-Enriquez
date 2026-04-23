"""
Research a prospect for personalized outreach.

Usage:
    python3 tools/research_prospect.py \
        --company "Rivera Painting" \
        --owner "Jaime Rivera" \
        [--city "Charlotte NC"]

    python3 tools/research_prospect.py --batch projects/personal/.tmp/research_batch.json

Output: JSON with research findings written to .tmp/prospect_research.json

Requires: Internet access (web search)
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / '.tmp'
OUTPUT_FILE = TMP_DIR / 'prospect_research.json'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text, self._skip = [], False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)

    def get_text(self):
        return re.sub(r'\s+', ' ', ' '.join(self.text)).strip()


def fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception:
        return None


def search_google(query):
    """Fetch Google search results page and extract snippets."""
    url = 'https://www.google.com/search?' + urllib.parse.urlencode({'q': query})
    html = fetch(url)
    if not html:
        return []
    snippets = []
    # Extract text between <span> tags in search results
    for m in re.finditer(r'<span[^>]*>(.*?)</span>', html, re.S):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if 20 < len(text) < 300 and not text.startswith('http'):
            snippets.append(text)
    return snippets[:20]


def extract_hooks(snippets, company, owner):
    """Pull useful hooks from search snippets."""
    hooks = []
    seen = set()
    patterns = [
        (r'(?:since|established|founded)\s*(\d{4})', lambda m: f"In business since {m.group(1)}"),
        (r'(\d+)\+?\s*years?\s*(?:of\s+)?experience', lambda m: f"{m.group(1)}+ years experience"),
        (r'(family.owned|veteran.owned|woman.owned|locally.owned)', lambda m: m.group(1).replace('.', '-').title()),
        (r'(\d\.\d)\s*(?:star|rating|out of)', lambda m: None),  # handled separately
    ]
    for snippet in snippets:
        low = snippet.lower()
        # Skip irrelevant snippets
        if company.lower().split()[0] not in low and owner.lower().split()[0] not in low:
            continue
        for pat, fmt in patterns:
            m = re.search(pat, snippet, re.I)
            if m and fmt:
                hook = fmt(m)
                if hook not in seen:
                    hooks.append(hook)
                    seen.add(hook)
        # Look for review keywords
        if any(w in low for w in ['review', 'recommend', 'excellent', 'professional']):
            clean = snippet[:100].strip()
            if clean not in seen and len(clean) > 30:
                hooks.append(f"Review mention: {clean}")
                seen.add(clean)
        # Community / awards
        if any(w in low for w in ['award', 'community', 'volunteer', 'sponsor', 'charity']):
            clean = snippet[:100].strip()
            if clean not in seen:
                hooks.append(f"Community: {clean}")
                seen.add(clean)
    return hooks[:5]


def extract_rating(snippets):
    """Try to find Google rating from snippets."""
    for s in snippets:
        m = re.search(r'(\d\.\d)\s*(?:\(\s*(\d+)\s*\))?', s)
        if m:
            rating = m.group(1)
            count = m.group(2) or ''
            if 1.0 <= float(rating) <= 5.0:
                return rating, int(count) if count else None
    return None, None


def extract_website(snippets, html_raw=''):
    """Try to find company website from search results."""
    if html_raw:
        urls = re.findall(r'href="(https?://[^"]+)"', html_raw)
        for u in urls:
            if 'google' not in u and 'youtube' not in u and 'facebook' not in u:
                return u.split('&')[0]
    return None


def research_one(company, owner, city='Charlotte NC'):
    """Research a single prospect. Returns result dict."""
    result = {'company': company, 'owner': owner, 'hooks': [], 'google_rating': None,
              'review_count': None, 'website': None, 'suggested_opener': None, 'errors': []}

    # Search 1: Company
    q1 = f'"{company}" "{city}" painting'
    snippets1 = search_google(q1)
    if not snippets1:
        result['errors'].append('Company search returned no results (may be rate-limited)')

    # Search 2: Owner
    q2 = f'"{owner}" "{company}" painting'
    snippets2 = search_google(q2)
    time.sleep(1)  # polite delay

    all_snippets = snippets1 + snippets2
    result['hooks'] = extract_hooks(all_snippets, company, owner)
    rating, count = extract_rating(all_snippets)
    if rating:
        result['google_rating'] = rating
        result['review_count'] = count
        result['hooks'].insert(0, f"Google rated {rating}" + (f" ({count} reviews)" if count else ""))

    # Build suggested opener
    first_name = owner.split()[0] if owner else 'there'
    if result['hooks']:
        best = result['hooks'][0]
        result['suggested_opener'] = f"{first_name}, {best.lower()} — that's impressive."
    else:
        result['suggested_opener'] = f"{first_name}, been seeing {company} around Charlotte — solid reputation."

    return result


def main():
    parser = argparse.ArgumentParser(description='Research prospects for outreach')
    parser.add_argument('--company', help='Company name')
    parser.add_argument('--owner', help='Owner / decision maker name')
    parser.add_argument('--city', default='Charlotte NC', help='City (default: Charlotte NC)')
    parser.add_argument('--batch', help='Path to JSON file with list of {company, owner} objects')
    args = parser.parse_args()

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"ERROR: batch file not found: {batch_file}")
            sys.exit(1)
        with open(batch_file) as f:
            prospects = json.load(f)
        for i, p in enumerate(prospects[:15]):
            print(f"[{i+1}/{min(len(prospects),15)}] Researching {p['company']}...")
            results.append(research_one(p['company'], p.get('owner', ''), args.city))
            if i < len(prospects) - 1:
                time.sleep(2)
    elif args.company:
        results.append(research_one(args.company, args.owner or '', args.city))
    else:
        parser.print_help()
        sys.exit(1)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {OUTPUT_FILE}")
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
