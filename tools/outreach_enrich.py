"""
Prospect enrichment module for the PH outreach system.

Called from tools/outreach.py cmd_enrich. Takes a prospect row (status=new)
and fills missing fields by scraping the website, querying optional email
finder APIs (Snov, Hunter), pulling public FB Graph data, and generating
a one-sentence personal hook via Claude Haiku.

All network calls are defensive — errors are caught, logged to stderr,
and the enricher continues with whatever it has.

Public API:
    enrich_from_website(website) -> dict
    enrich_from_snov(domain, api_key) -> dict
    enrich_from_hunter(domain, api_key) -> dict
    enrich_from_fb_graph(fb_url, access_token) -> dict
    generate_personal_hook(prospect, anthropic_api_key) -> str
    enrich_prospect(row, env) -> dict
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser


USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
WEBSITE_FETCH_DELAY = 1.5
HAIKU_MODEL = 'claude-haiku-4-5-20251001'


# ============================================================
# Web scraping helpers (ported from tools/enrich_prospects.py)
# ============================================================

class _TextExtractor(HTMLParser):
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
    """Fetch a URL with a polite User-Agent. Returns (html, final_url) or (None, None)."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='replace')
            return html, resp.url
    except Exception as e:
        print(f"[enrich] fetch_page error {url}: {e}", file=sys.stderr)
        return None, None


def extract_text(html):
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.get_text()


def find_emails_in_text(text):
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    found = set(re.findall(pattern, text))
    junk = {'example.com', 'sentry.io', 'wixpress.com', 'googleapis.com',
            'w3.org', 'schema.org', 'wordpress.org', 'gravatar.com',
            'yourdomain.com', 'domain.com'}
    junk_ext = ('.png', '.jpg', '.svg', '.gif', '.webp', '.jpeg', '.css', '.js')
    out = []
    for email in found:
        domain = email.split('@')[1].lower()
        if domain in junk or email.lower().endswith(junk_ext):
            continue
        out.append(email.lower())
    return out


def find_social_links(html):
    results = {}
    linkedin = re.findall(
        r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_\-]+/?', html)
    if linkedin:
        results['linkedin'] = linkedin[0]
    facebook = re.findall(
        r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._\-]+/?', html)
    if facebook:
        fb_valid = [u for u in facebook
                    if not any(x in u for x in ['/sharer', '/tr/', '/plugins', '/dialog'])]
        if fb_valid:
            results['facebook'] = fb_valid[0]
    instagram = re.findall(
        r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._]+/?', html)
    if instagram:
        ig_valid = [u for u in instagram if '/p/' not in u and '/explore/' not in u]
        if ig_valid:
            results['instagram'] = ig_valid[0]
    return results


def _normalise_website(website):
    website = website.strip()
    if not website:
        return ''
    if not website.startswith(('http://', 'https://')):
        website = 'https://' + website
    return website.rstrip('/')


def _domain_from_website(website):
    try:
        url = _normalise_website(website)
        if not url:
            return ''
        netloc = urllib.parse.urlparse(url).netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc.lower()
    except Exception:
        return ''


def _prefer_email(emails, owner=''):
    """Rank emails: owner name match > info/contact/hello > first."""
    if not emails:
        return ''
    owner_parts = [p for p in owner.lower().split() if len(p) > 2]
    if owner_parts:
        owner_hits = [e for e in emails if any(p in e.split('@')[0] for p in owner_parts)]
        if owner_hits:
            return owner_hits[0]
    generic = [e for e in emails if any(p in e for p in ('info@', 'contact@', 'hello@', 'admin@'))]
    if generic:
        return generic[0]
    return emails[0]


# ============================================================
# Website enrichment
# ============================================================

def enrich_from_website(website: str) -> dict:
    """Scrape homepage + /contact + /about. Returns any of:
    email, fb_url, ig_url, linkedin_url, website_blurb."""
    out = {}
    base = _normalise_website(website)
    if not base:
        return out

    paths = ['', '/contact', '/contact-us', '/about', '/about-us']
    combined_html = ''
    blurb_source = ''
    seen_urls = set()

    for i, path in enumerate(paths):
        url = base + path if path else base
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if i > 0:
            time.sleep(WEBSITE_FETCH_DELAY)
        html, _ = fetch_page(url)
        if not html:
            continue
        combined_html += '\n' + html
        if not blurb_source and path in ('', '/about', '/about-us'):
            blurb_source = html

    if not combined_html:
        return out

    emails = find_emails_in_text(combined_html)
    if emails:
        out['email'] = _prefer_email(emails)

    socials = find_social_links(combined_html)
    if socials.get('facebook'):
        out['fb_url'] = socials['facebook']
    if socials.get('instagram'):
        out['ig_url'] = socials['instagram']
    if socials.get('linkedin'):
        out['linkedin_url'] = socials['linkedin']

    blurb_html = blurb_source or combined_html
    text = extract_text(blurb_html)
    text = re.sub(r'\s+', ' ', text).strip()
    if text:
        out['website_blurb'] = text[:500]

    return out


# ============================================================
# Snov.io (OAuth → email search)
# ============================================================

def _snov_access_token(client_id, client_secret):
    body = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }).encode()
    req = urllib.request.Request(
        'https://api.snov.io/v1/oauth/access_token',
        data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get('access_token', '')


def enrich_from_snov(domain: str, api_key: str) -> dict:
    """Snov.io email finder. api_key here is the OAuth client_secret paired
    with SNOV_CLIENT_ID from env — falls back to treating api_key as
    SNOV_CLIENT_ID:SNOV_CLIENT_SECRET if combined. Returns {} if any error."""
    if not api_key or not domain:
        return {}
    try:
        import os
        client_id = os.environ.get('SNOV_CLIENT_ID', '')
        client_secret = os.environ.get('SNOV_CLIENT_SECRET', '') or api_key
        if ':' in api_key and not client_id:
            client_id, client_secret = api_key.split(':', 1)
        if not client_id or not client_secret:
            return {}

        token = _snov_access_token(client_id, client_secret)
        if not token:
            return {}

        qs = urllib.parse.urlencode({'domain': domain, 'access_token': token})
        url = f'https://api.snov.io/v1/get-emails-from-url?{qs}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())

        emails = []
        if isinstance(data, dict):
            for key in ('emails', 'data'):
                val = data.get(key)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            e = item.get('email') or item.get('value')
                            if e:
                                emails.append(e)
                        elif isinstance(item, str):
                            emails.append(item)
        if emails:
            return {'email': emails[0].lower()}
        return {}
    except Exception as e:
        print(f"[enrich] snov error {domain}: {e}", file=sys.stderr)
        return {}


# ============================================================
# Hunter.io
# ============================================================

def enrich_from_hunter(domain: str, api_key: str) -> dict:
    """Hunter.io domain-search. Returns {'email': first_found} or {}."""
    if not api_key or not domain:
        return {}
    try:
        qs = urllib.parse.urlencode({'domain': domain, 'api_key': api_key, 'limit': 5})
        url = f'https://api.hunter.io/v2/domain-search?{qs}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        emails = (data.get('data') or {}).get('emails') or []
        for item in emails:
            if isinstance(item, dict) and item.get('value'):
                return {'email': item['value'].lower()}
        return {}
    except Exception as e:
        print(f"[enrich] hunter error {domain}: {e}", file=sys.stderr)
        return {}


# ============================================================
# Facebook Graph API (public page data)
# ============================================================

def _fb_page_id_from_url(fb_url):
    if not fb_url:
        return ''
    try:
        path = urllib.parse.urlparse(fb_url).path.strip('/')
        if not path:
            return ''
        # Handle /pg/<name>, /profile.php?id=<id>, plain /<name>
        if path.startswith('pg/'):
            path = path[3:]
        first = path.split('/')[0]
        if first == 'profile.php':
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(fb_url).query)
            return qs.get('id', [''])[0]
        return first
    except Exception:
        return ''


def enrich_from_fb_graph(fb_url: str, access_token: str) -> dict:
    """Fetch public FB page data. Returns dict of found fields."""
    if not fb_url or not access_token:
        return {}
    page_id = _fb_page_id_from_url(fb_url)
    if not page_id:
        return {}
    try:
        fields = 'about,category,description,emails,phone,website'
        qs = urllib.parse.urlencode({'fields': fields, 'access_token': access_token})
        url = f'https://graph.facebook.com/v18.0/{urllib.parse.quote(page_id)}?{qs}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        out = {}
        if data.get('about'):
            out['fb_about'] = data['about']
        if data.get('category'):
            out['fb_category'] = data['category']
        if data.get('description'):
            out['fb_description'] = data['description']
        emails = data.get('emails') or []
        if emails:
            out['email'] = emails[0].lower()
        if data.get('phone'):
            out['phone'] = data['phone']
        if data.get('website'):
            out['website'] = data['website']
        return out
    except Exception as e:
        print(f"[enrich] fb_graph error {fb_url}: {e}", file=sys.stderr)
        return {}


# ============================================================
# Personal hook via Claude Haiku
# ============================================================

HOOK_SYSTEM_PROMPT = (
    "Allen Enriquez helps PH businesses automate sales with AI. He needs a "
    "1-sentence specific hook about this prospect he can reference in a "
    "cold outreach message. The hook must be based ONLY on facts in the "
    "context provided. NEVER fabricate. If there is not enough info, "
    "return an empty string."
)


def _build_hook_user_prompt(prospect):
    lines = ["Here is what we know about this prospect:"]
    mapping = [
        ('Company name', prospect.get('Company Name') or prospect.get('Business Name')),
        ('Segment', prospect.get('Segment')),
        ('Website', prospect.get('Website')),
        ('Website blurb', prospect.get('website_blurb') or prospect.get('Website Blurb')),
        ('FB about', prospect.get('fb_about') or prospect.get('FB About')),
        ('FB category', prospect.get('fb_category') or prospect.get('FB Category')),
        ('FB description', prospect.get('fb_description') or prospect.get('FB Description')),
        ('Notes', prospect.get('Notes')),
    ]
    for label, value in mapping:
        if value and str(value).strip():
            lines.append(f"- {label}: {str(value).strip()}")

    lines.append("")
    lines.append(
        "Write ONE specific sentence (max 20 words) that Allen can reference.")
    lines.append(
        'Example good: "Santos Recruiters has been running PH staffing since '
        '2012 and posts 30+ VA jobs a week on JobStreet."')
    lines.append(
        'Example bad: "Santos Recruiters is a great company." (generic)')
    lines.append("If nothing specific, return empty string.")
    return '\n'.join(lines)


def generate_personal_hook(prospect: dict, anthropic_api_key: str) -> str:
    """Claude Haiku generates a 1-sentence personal hook from prospect context.
    Returns '' on missing key, insufficient info, refusal, or error."""
    if not anthropic_api_key:
        return ''

    user_prompt = _build_hook_user_prompt(prospect)
    # If the only info is company name / segment with no substance, bail early.
    context_lines = [l for l in user_prompt.split('\n') if l.startswith('- ')]
    substantive = [l for l in context_lines
                   if not l.startswith('- Company name:')
                   and not l.startswith('- Segment:')
                   and not l.startswith('- Website:')]
    if not substantive:
        return ''

    body = json.dumps({
        'model': HAIKU_MODEL,
        'max_tokens': 150,
        'temperature': 0.5,
        'system': HOOK_SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': user_prompt}],
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': anthropic_api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        text = (data.get('content') or [{}])[0].get('text', '').strip()
        if not text:
            return ''
        # Strip quotes/markdown artefacts
        text = text.strip().strip('"').strip("'").strip()
        # Reject obvious refusals
        lower = text.lower()
        refusal_markers = ("i don't have", 'i do not have', 'not enough',
                           'insufficient', 'cannot generate', "can't generate",
                           'unable to')
        if any(m in lower for m in refusal_markers):
            return ''
        # Hard cap — if Haiku rambled, keep only the first sentence.
        first_sentence = re.split(r'(?<=[.!?])\s', text, maxsplit=1)[0]
        if len(first_sentence.split()) > 30:
            return ''
        return first_sentence
    except Exception as e:
        print(f"[enrich] haiku error: {e}", file=sys.stderr)
        return ''


# ============================================================
# Orchestrator
# ============================================================

def _existing(row, field):
    return bool(str(row.get(field, '') or '').strip())


def enrich_prospect(row: dict, env: dict) -> dict:
    """Run all enrichers for one prospect row. Returns dict of sheet
    column -> value for fields that should be written. Never overwrites
    existing non-empty values."""
    env = env or {}
    updates = {}
    context = dict(row)  # accumulate everything we learn for Haiku

    website = str(row.get('Website', '') or '').strip()
    fb_url_existing = str(row.get('FB URL', '') or '').strip()
    ig_url_existing = str(row.get('IG URL', '') or '').strip()
    email_existing = str(row.get('Email', '') or '').strip()
    phone_existing = str(row.get('Phone', '') or '').strip()
    notes_existing = str(row.get('Notes', '') or '').strip()

    # --- 1. Website scrape ---
    if website and (not email_existing or not fb_url_existing or not ig_url_existing):
        site_data = enrich_from_website(website)
        if site_data.get('email') and not email_existing:
            updates['Email'] = site_data['email']
            email_existing = site_data['email']
        if site_data.get('fb_url') and not fb_url_existing:
            updates['FB URL'] = site_data['fb_url']
            fb_url_existing = site_data['fb_url']
        if site_data.get('ig_url') and not ig_url_existing:
            updates['IG URL'] = site_data['ig_url']
            ig_url_existing = site_data['ig_url']
        if site_data.get('linkedin_url'):
            # LinkedIn stored inside Notes per spec
            linkedin = site_data['linkedin_url']
            if linkedin not in notes_existing:
                new_notes = (notes_existing + '\n' if notes_existing else '') + f'LinkedIn: {linkedin}'
                updates['Notes'] = new_notes
                notes_existing = new_notes
        if site_data.get('website_blurb'):
            context['website_blurb'] = site_data['website_blurb']

    # --- 2. Snov.io email finder ---
    if not email_existing and website:
        domain = _domain_from_website(website)
        snov_key = env.get('SNOV_API_KEY') or env.get('SNOV_CLIENT_SECRET') or ''
        if domain and snov_key:
            snov_data = enrich_from_snov(domain, snov_key)
            if snov_data.get('email'):
                updates['Email'] = snov_data['email']
                email_existing = snov_data['email']

    # --- 3. Hunter.io fallback ---
    if not email_existing and website:
        domain = _domain_from_website(website)
        hunter_key = env.get('HUNTER_API_KEY') or ''
        if domain and hunter_key:
            hunter_data = enrich_from_hunter(domain, hunter_key)
            if hunter_data.get('email'):
                updates['Email'] = hunter_data['email']
                email_existing = hunter_data['email']

    # --- 4. FB Graph ---
    if fb_url_existing:
        fb_token = env.get('FB_GRAPH_TOKEN') or ''
        if fb_token:
            fb_data = enrich_from_fb_graph(fb_url_existing, fb_token)
            if fb_data.get('email') and not email_existing:
                updates['Email'] = fb_data['email']
                email_existing = fb_data['email']
            if fb_data.get('phone') and not phone_existing:
                updates['Phone'] = fb_data['phone']
                phone_existing = fb_data['phone']
            for k in ('fb_about', 'fb_category', 'fb_description'):
                if fb_data.get(k):
                    context[k] = fb_data[k]

    # --- 5. Personal hook (last) ---
    if not _existing(row, 'Personal Hook'):
        anthropic_key = env.get('ANTHROPIC_API_KEY') or ''
        hook = generate_personal_hook(context, anthropic_key)
        if hook:
            updates['Personal Hook'] = hook

    # --- Status ---
    updates['Status'] = 'enriched'
    return updates
