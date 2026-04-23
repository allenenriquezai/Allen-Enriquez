"""
Prospect Enrichment Tool.

Pulls leads from the personal CRM Google Sheet that are missing key data
(email, LinkedIn, social media, personal hook), enriches them via web
scraping, and writes the results back to the Sheet.

Usage:
    python3 tools/enrich_prospects.py scan                 # Show what's missing
    python3 tools/enrich_prospects.py enrich --limit 5     # Enrich up to 5 leads
    python3 tools/enrich_prospects.py enrich --row 3 --tab "Paint | Call Queue"  # Enrich one lead
    python3 tools/enrich_prospects.py enrich --limit 5 --dry-run  # Preview without writing

Requires:
    projects/personal/token_personal_ai.pickle: Google OAuth token with Sheets scope
"""

import argparse
import json
import os
import pickle
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
TMP_DIR = BASE_DIR / 'projects' / 'personal' / '.tmp'
OUTPUT_FILE = TMP_DIR / 'enrichment_results.json'

SPREADSHEET_ID = '1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8'

# Columns we read/write (must match Sheet headers)
ENRICH_FIELDS = ['Email', 'LinkedIn', 'Social Media', 'Personal Hook']
REQUIRED_FIELDS = ['Business Name', 'Website']

# All tabs to scan
TABS = [
    'Paint | Call Queue', 'Paint | Warm Interest', 'Paint | Callbacks',
    'Paint | Emails Sent',
    'Other | Call Queue', 'Other | Warm Interest', 'Other | Callbacks',
    'Other | Emails Sent',
]

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


# ============================================================
# Google Sheets helpers
# ============================================================

def load_token():
    if not TOKEN_FILE.exists():
        print(f"ERROR: token not found at {TOKEN_FILE}")
        print("Run: python3 tools/auth_personal.py")
        sys.exit(1)
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def get_sheets_service():
    return build('sheets', 'v4', credentials=load_token())


def read_tab(service, tab):
    """Read all rows from a tab. Returns (headers, rows) where rows are dicts."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'"
    ).execute()
    values = result.get('values', [])
    if not values:
        return [], []
    headers = values[0]
    rows = []
    for i, row in enumerate(values[1:], start=2):  # row 2 in sheet = index 0
        padded = row + [''] * (len(headers) - len(row))
        rows.append({
            '_row': i,
            '_tab': tab,
            **{h: padded[j] for j, h in enumerate(headers)},
        })
    return headers, rows


def write_cell(service, tab, col_letter, row_num, value):
    """Write a single cell value."""
    cell = f"'{tab}'!{col_letter}{row_num}"
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=cell,
        valueInputOption='RAW',
        body={'values': [[value]]},
    ).execute()


def col_index_to_letter(index):
    """Convert 0-based column index to letter (0=A, 25=Z, 26=AA)."""
    result = ''
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result


# ============================================================
# Web scraping helpers
# ============================================================

class TextExtractor(HTMLParser):
    """Simple HTML to text converter."""
    def __init__(self):
        super().__init__()
        self.text = []
        self._skip = False

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
        return ' '.join(self.text)


def fetch_page(url, timeout=10):
    """Fetch a URL and return (html_text, final_url). Returns (None, None) on failure."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='replace')
            return html, resp.url
    except Exception:
        return None, None


def extract_text(html):
    """Extract visible text from HTML."""
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()


def find_emails_in_text(text):
    """Find email addresses in text. Filters out common junk."""
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    found = set(re.findall(pattern, text))
    # Filter out image files, common non-contact emails
    junk = {'example.com', 'sentry.io', 'wixpress.com', 'googleapis.com',
            'w3.org', 'schema.org', 'wordpress.org', 'gravatar.com',
            'yourdomain.com', 'domain.com'}
    junk_extensions = ('.png', '.jpg', '.svg', '.gif', '.webp', '.jpeg', '.css', '.js')
    filtered = []
    for email in found:
        domain = email.split('@')[1].lower()
        if domain not in junk and not email.lower().endswith(junk_extensions):
            filtered.append(email.lower())
    return filtered


def find_social_links(html):
    """Find social media URLs in HTML."""
    results = {}
    # LinkedIn
    linkedin = re.findall(r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_\-]+/?', html)
    if linkedin:
        results['linkedin'] = linkedin[0]
    # Facebook
    facebook = re.findall(r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._\-]+/?', html)
    if facebook:
        # Filter out facebook.com/sharer, facebook.com/tr etc
        fb_valid = [u for u in facebook if not any(x in u for x in ['/sharer', '/tr/', '/plugins', '/dialog'])]
        if fb_valid:
            results['facebook'] = fb_valid[0]
    # Instagram
    instagram = re.findall(r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._]+/?', html)
    if instagram:
        ig_valid = [u for u in instagram if '/p/' not in u and '/explore/' not in u]
        if ig_valid:
            results['instagram'] = ig_valid[0]
    return results


def extract_personal_hook(html, biz_name=''):
    """
    Extract a personal hook from website HTML — something specific we can
    reference in outreach. Looks for: years in business, owner story,
    family-owned, community mentions, awards, certifications.
    """
    text = extract_text(html)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)

    hooks = []

    # Years in business / established
    yr_match = re.search(r'(?:since|established|founded|serving.*since)\s*(\d{4})', text, re.I)
    if yr_match:
        year = int(yr_match.group(1))
        if 1950 <= year <= 2025:
            hooks.append(f"In business since {year}")

    # Family-owned / veteran-owned / woman-owned
    for label in ['family.owned', 'veteran.owned', 'woman.owned', 'locally.owned', 'black.owned']:
        if re.search(label, text, re.I):
            hooks.append(re.sub(r'\.', '-', label).title())

    # Years of experience
    exp_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s+)?experience', text, re.I)
    if exp_match:
        years = int(exp_match.group(1))
        if 3 <= years <= 60:
            hooks.append(f"{years}+ years experience")

    # Awards / certifications
    for keyword in ['award', 'certified', 'accredited', 'bbb a', 'angi', 'best of']:
        match = re.search(rf'([^.]*{keyword}[^.]*\.)', text, re.I)
        if match:
            snippet = match.group(1).strip()
            if len(snippet) < 120:
                hooks.append(snippet)
                break

    if not hooks:
        return ''

    # Return the best hook (first one found, keep it short)
    return ' | '.join(hooks[:2])


# ============================================================
# Enrichment logic
# ============================================================

def enrich_lead(lead):
    """
    Enrich a single lead. Returns dict of fields to update.
    Only fills in fields that are currently empty.
    """
    updates = {}
    website = lead.get('Website', '').strip()
    biz_name = lead.get('Business Name', '').strip()
    owner = lead.get('Decision Maker', '').strip()

    if not website and not biz_name:
        return updates

    # --- Scrape website ---
    html = None
    if website:
        # Normalise URL
        if not website.startswith('http'):
            website = 'https://' + website
        html, _ = fetch_page(website)

    # --- Find email ---
    if not lead.get('Email', '').strip() and html:
        emails = find_emails_in_text(html)
        # Also check /contact page
        if not emails:
            contact_html, _ = fetch_page(website.rstrip('/') + '/contact')
            if contact_html:
                emails = find_emails_in_text(contact_html)
        if not emails:
            contact_html, _ = fetch_page(website.rstrip('/') + '/contact-us')
            if contact_html:
                emails = find_emails_in_text(contact_html)
        if emails:
            # Prefer info@, contact@, or owner-name emails
            preferred = [e for e in emails if any(p in e for p in ['info@', 'contact@', 'hello@'])]
            if owner:
                name_parts = owner.lower().split()
                owner_emails = [e for e in emails if any(p in e for p in name_parts)]
                if owner_emails:
                    preferred = owner_emails
            updates['Email'] = preferred[0] if preferred else emails[0]

    # --- Find social links from website ---
    if html:
        socials = find_social_links(html)

        if not lead.get('LinkedIn', '').strip() and socials.get('linkedin'):
            updates['LinkedIn'] = socials['linkedin']

        if not lead.get('Social Media', '').strip():
            social_parts = []
            if socials.get('facebook'):
                social_parts.append(socials['facebook'])
            if socials.get('instagram'):
                social_parts.append(socials['instagram'])
            if social_parts:
                updates['Social Media'] = ' | '.join(social_parts)

    # --- Personal hook ---
    if not lead.get('Personal Hook', '').strip() and html:
        hook = extract_personal_hook(html, biz_name)
        if hook:
            updates['Personal Hook'] = hook

    # --- Verify: check website mentions the business name ---
    if html and biz_name:
        page_text = extract_text(html).lower()
        # Check if at least part of the business name appears on the page
        name_words = [w for w in biz_name.lower().split() if len(w) > 3
                      and w not in ('llc', 'inc', 'inc.', 'ltd', 'corp', 'the', 'and', 'painting', 'company')]
        if name_words:
            match_count = sum(1 for w in name_words if w in page_text)
            if match_count == 0:
                # Website doesn't seem to match the business — flag it
                updates['_warning'] = f"Website may not match business (none of {name_words} found on page)"

    return updates


# ============================================================
# Commands
# ============================================================

def cmd_scan(args):
    """Scan all tabs and report what's missing."""
    service = get_sheets_service()
    summary = {'total': 0, 'missing_email': 0, 'missing_linkedin': 0,
               'missing_social': 0, 'no_website': 0, 'enrichable': 0}
    details = []

    for tab in TABS:
        headers, rows = read_tab(service, tab)
        if not rows:
            continue
        for row in rows:
            summary['total'] += 1
            has_website = bool(row.get('Website', '').strip())
            missing_email = not row.get('Email', '').strip()
            missing_linkedin = not row.get('LinkedIn', '').strip()
            missing_social = not row.get('Social Media', '').strip()

            if not has_website:
                summary['no_website'] += 1
            if missing_email:
                summary['missing_email'] += 1
            if missing_linkedin:
                summary['missing_linkedin'] += 1
            if missing_social:
                summary['missing_social'] += 1

            # Enrichable = has website + missing at least one field
            if has_website and (missing_email or missing_linkedin or missing_social):
                summary['enrichable'] += 1
                details.append({
                    'tab': tab, 'row': row['_row'],
                    'business': row.get('Business Name', ''),
                    'missing': [f for f in ENRICH_FIELDS if not row.get(f, '').strip()],
                })

    print(f"\n=== CRM Enrichment Scan ===")
    print(f"Total leads:         {summary['total']}")
    print(f"Missing email:       {summary['missing_email']}")
    print(f"Missing LinkedIn:    {summary['missing_linkedin']}")
    print(f"Missing social:      {summary['missing_social']}")
    print(f"No website (skip):   {summary['no_website']}")
    print(f"Enrichable:          {summary['enrichable']}")

    if details:
        print(f"\nTop enrichable leads:")
        for d in details[:10]:
            print(f"  [{d['tab']}] Row {d['row']}: {d['business']} — missing: {', '.join(d['missing'])}")

    # Save full details
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    output = {'summary': summary, 'details': details}
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results saved to {OUTPUT_FILE}")


def cmd_enrich(args):
    """Enrich leads with missing data."""
    service = get_sheets_service()
    limit = args.limit or 5
    dry_run = args.dry_run
    target_tab = args.tab
    target_row = args.row

    enriched = 0
    results = []

    tabs_to_scan = [target_tab] if target_tab else TABS

    for tab in tabs_to_scan:
        headers, rows = read_tab(service, tab)
        if not rows or not headers:
            continue

        # Build column letter lookup
        col_letters = {h: col_index_to_letter(i) for i, h in enumerate(headers)}

        for row in rows:
            if enriched >= limit and not target_row:
                break

            # If targeting a specific row
            if target_row and row['_row'] != target_row:
                continue

            # Skip if no website or nothing missing
            if not row.get('Website', '').strip():
                continue
            missing = [f for f in ENRICH_FIELDS if not row.get(f, '').strip()]
            if not missing:
                continue

            biz = row.get('Business Name', 'Unknown')
            print(f"\nEnriching: {biz} (Row {row['_row']}, {tab})")
            print(f"  Website: {row.get('Website', '')}")
            print(f"  Missing: {', '.join(missing)}")

            updates = enrich_lead(row)

            if updates:
                warning = updates.pop('_warning', None)
                if warning:
                    print(f"  WARNING: {warning}")

                if updates:
                    print(f"  Found:")
                    for field, value in updates.items():
                        print(f"    {field}: {value}")
                        if not dry_run and field in col_letters:
                            write_cell(service, tab, col_letters[field], row['_row'], value)

                    results.append({
                        'tab': tab, 'row': row['_row'], 'business': biz,
                        'updates': updates, 'warning': warning,
                    })
                    enriched += 1
                else:
                    print(f"  No data found (warning only)")
            else:
                print(f"  No data found")

            # Rate limit — be polite to websites
            time.sleep(1.5)

            if target_row:
                break
        if enriched >= limit and not target_row:
            break

    action = "Would write" if dry_run else "Wrote"
    print(f"\n=== Done ===")
    print(f"{action} updates for {enriched} leads")

    # Save results
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Prospect enrichment tool')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('scan', help='Scan CRM for missing data')

    enrich_p = sub.add_parser('enrich', help='Enrich leads with missing data')
    enrich_p.add_argument('--limit', type=int, default=5, help='Max leads to enrich (default: 5)')
    enrich_p.add_argument('--tab', type=str, help='Specific tab to target')
    enrich_p.add_argument('--row', type=int, help='Specific row to target')
    enrich_p.add_argument('--dry-run', action='store_true', help='Preview without writing')

    args = parser.parse_args()
    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'enrich':
        cmd_enrich(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
