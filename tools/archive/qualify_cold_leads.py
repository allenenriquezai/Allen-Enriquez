"""
Qualifies cold call leads from Pipedrive by validating phone numbers,
checking for duplicates, and verifying companies are actual builders.

Reads from the "1. Builders - Allen" filter and labels qualified leads
as "Ready To Call".

Usage:
    python3 tools/qualify_cold_leads.py                    # process all
    python3 tools/qualify_cold_leads.py --dry-run          # preview only
    python3 tools/qualify_cold_leads.py --merge            # auto-merge duplicates
    python3 tools/qualify_cold_leads.py --limit 10         # first 10 only
    python3 tools/qualify_cold_leads.py --verbose          # detailed output

Requires in projects/eps/.env:
    PIPEDRIVE_API_KEY
    PIPEDRIVE_COMPANY_DOMAIN
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / 'projects' / 'eps' / '.env'

# --- Filter & Label IDs ---
FILTER_ID_ALLEN = '13050'
FILTER_ID_ALL = '16439'

LABEL_NEW = '446f1640-1c23-11f1-88de-01cfe75f6478'
LABEL_INVALID = '6fb39830-1c23-11f1-94c7-e924796bd4a9'
LABEL_READY = '461b2440-32fb-11f1-a231-f3329040f9d7'

# Lead labels we WILL process (whitelist) — everything else is skipped
PROCESS_LEAD_LABELS = {
    LABEL_NEW,                                          # COLD - New / No Label
    '49e985b0-1c23-11f1-8f4e-1f90a960d8f6',            # COLD - No Answer 1
    '4e5ee130-1c23-11f1-b6f7-a1af508bf526',            # COLD - No Answer 2
    '6519f8b0-1c23-11f1-88de-01cfe75f6478',            # COLD - No Answer 3
    LABEL_INVALID,                                      # COLD - Invalid Number
}
# Leads with NO label at all are also processed

# Person labels we WILL process (whitelist) — everything else means they're already warm
PROCESS_PERSON_LABELS = {
    176,   # COLD - NEW / NO LABEL
    177,   # COLD - NO ANSWER 1
    178,   # COLD - NO ANSWER 2
    179,   # COLD - NO ANSWER 3
    180,   # Cold - Invalid Number
}
# Persons with NO label are also processed

# Pipedrive custom field keys
PERSON_CATEGORY_FIELD = '1c0093ab0271ffc49307b82d2a00df488ffec957'
PERSON_CATEGORY_BUILDER = '241'  # Pipedrive returns strings

ALLEN_USER_ID = 23603962

PAGE_SIZE = 100
API_DELAY = 0.25  # seconds between API calls


# --- Env & API helpers ---

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def api_get(path, params=None, *, api_key, domain):
    params = params or {}
    params['api_token'] = api_key
    qs = urllib.parse.urlencode(params)
    url = f"https://{domain}/v1{path}?{qs}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limited, waiting 2s...", file=sys.stderr)
            time.sleep(2)
            with urllib.request.urlopen(url) as r:
                data = json.loads(r.read())
        else:
            print(f"ERROR: API GET {path} returned {e.code}", file=sys.stderr)
            return None
    if not data.get('success'):
        print(f"ERROR: API GET {path}: {data}", file=sys.stderr)
        return None
    return data


def api_patch(path, payload, *, api_key, domain):
    url = f"https://{domain}/v1{path}?api_token={api_key}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="PATCH"
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: API PATCH {path} returned {e.code}", file=sys.stderr)
        return None
    if not data.get('success'):
        print(f"ERROR: API PATCH {path}: {data}", file=sys.stderr)
        return None
    return data


def api_put(path, payload, *, api_key, domain):
    url = f"https://{domain}/v1{path}?api_token={api_key}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: API PUT {path} returned {e.code}", file=sys.stderr)
        return None
    if not data.get('success'):
        print(f"ERROR: API PUT {path}: {data}", file=sys.stderr)
        return None
    return data


# --- Validation ---

def normalize_phone(raw):
    """Normalize an Australian phone number to local display format.
    Returns (normalized, None) on success or (None, reason) on failure.

    Output formats:
        Mobile:   04XX XXX XXX
        Landline: 0X XXXX XXXX
        1300:     1300 XXX XXX
        1800:     1800 XXX XXX
    """
    if not raw or not raw.strip():
        return None, "empty"

    # Strip all formatting
    digits = re.sub(r'[^0-9]', '', raw.strip())

    # Strip leading country code
    if digits.startswith('61'):
        rest = digits[2:]
        # 1300/1800 numbers: 61 + 1300/1800 + 6 digits
        if rest.startswith('1300') or rest.startswith('1800'):
            digits = rest
        else:
            digits = '0' + rest
    elif not digits.startswith('0') and not digits.startswith('1300') and not digits.startswith('1800'):
        if len(digits) == 9:
            digits = '0' + digits

    # 1300/1800 numbers: 10 digits (1300/1800 + 6)
    if digits.startswith('1300') or digits.startswith('1800'):
        if len(digits) == 10:
            return f"{digits[:4]} {digits[4:7]} {digits[7:]}", None
        else:
            return None, f"wrong length for 1300/1800 ({raw.strip()})"

    # Must start with 0 now
    if not digits.startswith('0'):
        return None, f"non-AU number ({raw.strip()})"

    # Standard AU numbers: 10 digits (0 + area + 8 digits)
    if len(digits) != 10:
        return None, f"wrong length ({raw.strip()} -> {digits}, expected 10 digits)"

    # Mobile: 04XX XXX XXX
    if digits.startswith('04'):
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}", None

    # Landline: 0X XXXX XXXX
    return f"{digits[:2]} {digits[2:6]} {digits[6:]}", None


def validate_phone(person):
    """Extract and validate primary phone from person record."""
    phones = person.get('phone', [])
    if not phones:
        return None, "no phone on record"

    # Find primary phone, fallback to first
    primary = None
    for p in phones:
        if p.get('primary'):
            primary = p.get('value', '')
            break
    if primary is None:
        primary = phones[0].get('value', '')

    return normalize_phone(primary)


def validate_org_name(name):
    """Check org name is not empty or gibberish."""
    if not name or not name.strip():
        return None, "empty org name"

    clean = name.strip()
    alpha_chars = sum(1 for c in clean if c.isalpha())
    if alpha_chars < 2:
        return None, f"org name too short/no letters ({clean})"

    return clean, None


# --- Duplicate detection ---

def build_person_lead_map(leads):
    """Build a map of person_id -> [(lead_id, title)] to detect duplicate persons."""
    person_leads = {}
    for lead in leads:
        pid = lead.get('person_id')
        if pid:
            lead_id = lead['id']
            title = lead.get('title', 'Unknown')
            person_leads.setdefault(pid, []).append((lead_id, title))
    return person_leads


def normalize_company_name(name):
    """Normalize a company name for fuzzy matching.
    Strips Pty Ltd, PTY, Ltd, Inc, ™, punctuation, extra spaces, lowercases.
    """
    n = name.lower().strip()
    # Remove common suffixes
    for suffix in ['pty ltd', 'pty. ltd.', 'pty', 'ltd', 'inc', 'p/l',
                   'australia', 'group', 'qld', 'nsw', 'vic']:
        n = n.replace(suffix, '')
    # Remove special chars
    n = re.sub(r'[^a-z0-9\s]', '', n)
    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def build_title_map(leads):
    """Build a map of normalized lead title -> [(lead_id, raw_title, person_id)]
    to detect leads for the same company with different names."""
    title_map = {}
    for lead in leads:
        title = lead.get('title', '')
        normalized = normalize_company_name(title)
        if normalized:
            title_map.setdefault(normalized, []).append(
                (lead['id'], title, lead.get('person_id'))
            )
    return title_map


def person_has_deals(person_id, *, api_key, domain):
    """Check if a person has any deals (means we already quoted/are working with them)."""
    time.sleep(API_DELAY)
    data = api_get(f'/persons/{person_id}', api_key=api_key, domain=domain)
    if not data:
        return False
    person = data['data']
    open_deals = person.get('open_deals_count', 0) or 0
    closed_deals = person.get('closed_deals_count', 0) or 0
    won_deals = person.get('won_deals_count', 0) or 0
    return (open_deals + closed_deals + won_deals) > 0


def check_duplicates(phone_normalized, current_person_id, current_lead_id,
                     person_lead_map, *, api_key, domain):
    """Check for duplicates:
    1. Same person linked to multiple leads in the filter
    2. Same phone number on a different person in Pipedrive
    Returns dict with 'multi_lead_ids' and 'phone_person_ids' for merge handling.
    """
    result = {
        'multi_lead_ids': [],    # other lead IDs linked to same person
        'phone_person_ids': [],  # other person IDs with same phone
        'issues': [],            # human-readable issue strings
    }

    # Check 1: person linked to multiple leads
    if current_person_id and current_person_id in person_lead_map:
        entries = person_lead_map[current_person_id]
        if len(entries) > 1:
            for lead_id, title in entries:
                if lead_id != current_lead_id:
                    result['multi_lead_ids'].append((lead_id, title))
            titles = ', '.join(t for _, t in entries)
            result['issues'].append(
                f"person #{current_person_id} linked to {len(entries)} leads: {titles}"
            )

    # Check 2: phone exists on a different person
    if phone_normalized:
        time.sleep(API_DELAY)
        data = api_get('/persons/search', {
            'term': phone_normalized,
            'fields': 'phone',
            'limit': 10,
        }, api_key=api_key, domain=domain)
        if data and data.get('data', {}).get('items'):
            for item in data['data']['items']:
                match = item.get('item', {})
                match_id = match.get('id')
                if match_id and match_id != current_person_id:
                    match_name = match.get('name', 'unknown')
                    result['phone_person_ids'].append((match_id, match_name))
                    result['issues'].append(
                        f"same phone on person #{match_id} ({match_name})"
                    )

    return result


def merge_duplicate_leads(current_lead_id, duplicate_lead_ids, *,
                          api_key, domain, dry_run, verbose):
    """Archive duplicate leads (keep current, archive others).
    Pipedrive has no lead merge API, so we archive duplicates.
    """
    for dup_id, dup_title in duplicate_lead_ids:
        if dry_run:
            print(f"    [DRY RUN] Would archive duplicate lead: {dup_title} ({dup_id})")
            continue
        time.sleep(API_DELAY)
        result = api_patch(f'/leads/{dup_id}', {'is_archived': True},
                           api_key=api_key, domain=domain)
        if result:
            print(f"    Archived duplicate lead: {dup_title} ({dup_id})")
        else:
            print(f"    FAILED to archive lead: {dup_title} ({dup_id})")


def merge_duplicate_persons(keep_person_id, duplicate_person_ids, *,
                            api_key, domain, dry_run, verbose):
    """Merge duplicate persons into the current person using Pipedrive merge API."""
    for dup_id, dup_name in duplicate_person_ids:
        if dry_run:
            print(f"    [DRY RUN] Would merge person #{dup_id} ({dup_name}) into #{keep_person_id}")
            continue
        time.sleep(API_DELAY)
        result = api_put(f'/persons/{keep_person_id}/merge',
                         {'merge_with_id': dup_id},
                         api_key=api_key, domain=domain)
        if result:
            print(f"    Merged person #{dup_id} ({dup_name}) into #{keep_person_id}")
        else:
            print(f"    FAILED to merge person #{dup_id} ({dup_name})")


def set_lead_owner(lead_id, owner_id, *, api_key, domain, dry_run):
    """Set lead owner to Allen."""
    if dry_run:
        return
    time.sleep(API_DELAY)
    api_patch(f'/leads/{lead_id}', {'owner_id': owner_id},
              api_key=api_key, domain=domain)


# --- Web search verification ---

# ICP: Builders who build properties/structures that need cleaning and painting.
# YES: residential builders, commercial builders, fitout/renovation companies
# NO: civil/infrastructure, trades (electrical, plumbing), non-construction businesses

BUILDER_KEYWORDS = [
    'builder', 'building company', 'homes', 'residential',
    'fitout', 'fit-out', 'renovation', 'refurbish', 'joinery',
    'carpentry', 'interior design', 'shopfit', 'house',
    'apartment', 'townhouse', 'property develop',
]

# Words that confirm a construction context (used alongside builder keywords)
CONSTRUCTION_CONTEXT = [
    'construct', 'built', 'build', 'project', 'site',
    'commercial', 'development', 'contractor',
]

# Civil/infrastructure — wrong type of construction
CIVIL_KEYWORDS = [
    'civil', 'earthwork', 'earth work', 'pipeline', 'infrastructure',
    'road', 'bridge', 'mining', 'quarry', 'grading', 'excavat',
    'utilities', 'hydro', 'water treatment', 'sewer', 'drainage',
    'rail', 'asphalt', 'concrete pour', 'paving', 'survey',
]

# Not construction at all
NON_CONSTRUCTION_KEYWORDS = [
    'restaurant', 'cafe', 'coffee', 'salon', 'dentist', 'medical',
    'accounting', 'legal', 'law firm', 'software', 'it services',
    'cleaning', 'recruitment', 'staffing', 'real estate agent',
    'electrical', 'plumbing', 'roofing', 'fencing', 'landscap',
    'gym', 'fitness', 'crossfit', 'pilates', 'yoga', 'personal train',
    'pizza', 'food', 'chef', 'bakery', 'bake', 'smallgoods', 'meat',
    'flooring', 'glass', 'aluminium', 'window', 'door',
    'pool', 'aquatic', 'swimming', 'padel', 'sport',
    'air con', 'aircon', 'hvac', 'refriger',
    'safety', 'inspection', 'consult', 'management',
    'wastewater', 'waste', 'recycl', 'maintenance',
    'photography', 'design studio', 'marketing', 'media',
    'freight', 'transport', 'logistics', 'shipping',
    'church', 'school', 'charity', 'non-profit',
    'insurance', 'finance', 'mortgage', 'broker',
    'decorator', 'paint', 'floor', 'tile', 'tiler',
]


def verify_builder_name(company_name):
    """Quick check based on company name alone."""
    name_lower = company_name.lower()

    # Reject civil/infrastructure
    for word in CIVIL_KEYWORDS:
        if word in name_lower:
            return False, f"civil/infrastructure ('{word}')"

    # Reject non-construction
    for word in NON_CONSTRUCTION_KEYWORDS:
        if word in name_lower:
            return False, f"not a builder ('{word}')"

    # Accept strong builder signals
    for word in BUILDER_KEYWORDS:
        if word in name_lower:
            return True, f"name contains '{word}'"

    # "construct" alone is ambiguous
    if 'construct' in name_lower:
        return None, "'construct' in name — needs web check"

    # "develop" could be property or software
    if 'develop' in name_lower:
        return None, "'develop' in name — needs web check"

    # "project" alone is too vague
    if 'project' in name_lower:
        return None, "'project' in name — needs web check"

    return None, "inconclusive from name"


def web_search(query):
    """Search via DuckDuckGo HTML (no rate limiting like Google)."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode('utf-8', errors='ignore').lower()
    except Exception as e:
        return None


def verify_builder_web(company_name):
    """Web search to verify company builds structures we can clean/paint.
    Requires POSITIVE evidence. Returns (True/False/None, reason).
    """
    # Name check already done by caller — this is the web search step
    html = web_search(f"{company_name} construction builder Brisbane")
    if not html:
        return None, "web search failed"

    builder_score = sum(1 for w in BUILDER_KEYWORDS if w in html)
    context_score = sum(1 for w in CONSTRUCTION_CONTEXT if w in html)
    civil_score = sum(1 for w in CIVIL_KEYWORDS if w in html)

    # Only count strong non-builder signals
    strong_non = [
        'restaurant', 'cafe', 'gym', 'fitness', 'pizza', 'chef',
        'pilates', 'yoga', 'salon', 'dentist', 'medical',
        'smallgoods', 'bakery', 'padel', 'swimming',
    ]
    non_score = sum(1 for w in strong_non if w in html)

    # Civil dominates
    if civil_score >= 3 and builder_score <= 1:
        return False, f"web: civil (civil: {civil_score}, builder: {builder_score})"

    # Clearly non-construction
    if non_score >= 2 and builder_score == 0:
        return False, f"web: not construction (non: {non_score})"

    # Strong builder evidence
    if builder_score >= 3:
        return True, f"web confirms builder (builder: {builder_score}, context: {context_score})"
    if builder_score >= 2 and context_score >= 2:
        return True, f"web confirms builder (builder: {builder_score}, context: {context_score})"

    # Construction context with some builder signal and no red flags
    if context_score >= 4 and builder_score >= 1 and civil_score <= 1 and non_score == 0:
        return True, f"web likely builder (builder: {builder_score}, context: {context_score})"

    # High construction context alone (clearly a construction company)
    if context_score >= 5 and civil_score <= 1 and non_score == 0:
        return True, f"web: construction company (context: {context_score})"

    # Not enough evidence
    return False, f"insufficient evidence (builder: {builder_score}, context: {context_score}, civil: {civil_score}, non: {non_score})"


# --- Lead processing ---

def qualify_lead(lead, person_lead_map, title_map, *, api_key, domain, dry_run, merge, verbose, keep_owner=False):
    """Run all qualification checks on a single lead.
    Returns (result_code, detail) where result_code is one of:
    'ready', 'skipped', 'invalid_phone', 'duplicate', 'merged', 'not_builder',
    'no_person', 'no_org', 'error'
    """
    lead_id = lead['id']
    title = lead.get('title', 'Unknown')
    label_ids = lead.get('label_ids', [])

    # 1. Check lead label — only process if no label or in whitelist
    if label_ids:
        if not any(lid in PROCESS_LEAD_LABELS for lid in label_ids):
            return 'skipped', 'lead already warm/worked'

    person_id = lead.get('person_id')

    if not person_id:
        return 'no_person', 'no contact person linked'

    # Fetch person
    time.sleep(API_DELAY)
    person_data = api_get(f'/persons/{person_id}', api_key=api_key, domain=domain)
    if not person_data:
        return 'error', 'could not fetch person'
    person = person_data['data']

    # 1b. Check person label — only process if no label or in whitelist
    person_label_ids = person.get('label_ids', []) or []
    if person_label_ids:
        if not any(plid in PROCESS_PERSON_LABELS for plid in person_label_ids):
            return 'skipped', 'person already warm/worked'

    # 2. Validate phone
    phone_normalized, phone_err = validate_phone(person)
    if phone_err:
        if not dry_run:
            api_patch(f'/leads/{lead_id}', {'label_ids': [LABEL_INVALID]},
                      api_key=api_key, domain=domain)
        if verbose:
            print(f"  Phone invalid: {phone_err}")
        return 'invalid_phone', phone_err

    if verbose:
        print(f"  Phone OK: {phone_normalized}")

    # 2a. Update phone format in Pipedrive if it changed
    raw_phone = None
    for p in person.get('phone', []):
        if p.get('primary'):
            raw_phone = p.get('value', '')
            break
    if raw_phone is None and person.get('phone'):
        raw_phone = person['phone'][0].get('value', '')

    if raw_phone and raw_phone.strip() != phone_normalized:
        if not dry_run:
            time.sleep(API_DELAY)
            api_put(f'/persons/{person_id}',
                    {'phone': [{'value': phone_normalized, 'primary': True, 'label': 'work'}]},
                    api_key=api_key, domain=domain)
        if verbose:
            print(f"  Phone reformatted: {raw_phone.strip()} -> {phone_normalized}")

    # 2b. Check if person already has deals — archive the lead (they're not cold)
    open_deals = person.get('open_deals_count', 0) or 0
    closed_deals = person.get('closed_deals_count', 0) or 0
    won_deals = person.get('won_deals_count', 0) or 0
    total_deals = open_deals + closed_deals + won_deals
    if total_deals > 0:
        if not dry_run:
            time.sleep(API_DELAY)
            api_patch(f'/leads/{lead_id}', {'is_archived': True},
                      api_key=api_key, domain=domain)
        if verbose:
            print(f"  Has {total_deals} deal(s) — archived lead (keeping deal)")
        return 'has_deals', f"person has {total_deals} deal(s) — lead archived"

    if verbose:
        print("  No deals (truly cold)")

    # 3. Validate company name (lead title = company name)
    clean_org, org_err = validate_org_name(title)
    if org_err:
        if verbose:
            print(f"  Company name invalid: {org_err}")
        return 'no_org', org_err

    if verbose:
        print(f"  Company: {clean_org}")

    # 3b. Check for same-company leads (e.g., "Azure Build Pty" vs "Azure Build")
    norm_title = normalize_company_name(title)
    if norm_title in title_map:
        matches = title_map[norm_title]
        if len(matches) > 1:
            other_leads = [(lid, t) for lid, t, pid in matches if lid != lead_id]
            if other_leads and merge:
                if verbose:
                    print(f"  Same company, different leads — archiving duplicates...")
                merge_duplicate_leads(lead_id, other_leads,
                                      api_key=api_key, domain=domain,
                                      dry_run=dry_run, verbose=verbose)
            elif other_leads:
                others = ', '.join(f'"{t}"' for _, t in other_leads)
                if verbose:
                    print(f"  Same company leads: {others}")

    # 4. Check duplicates
    dupes = check_duplicates(
        phone_normalized, person_id, lead_id, person_lead_map,
        api_key=api_key, domain=domain,
    )

    has_dupes = dupes['multi_lead_ids'] or dupes['phone_person_ids']

    if has_dupes and merge:
        # Merge mode: fix duplicates instead of skipping
        if dupes['phone_person_ids']:
            if verbose:
                print(f"  Merging duplicate persons...")
            merge_duplicate_persons(
                person_id, dupes['phone_person_ids'],
                api_key=api_key, domain=domain,
                dry_run=dry_run, verbose=verbose,
            )
        if dupes['multi_lead_ids']:
            if verbose:
                print(f"  Archiving duplicate leads...")
            merge_duplicate_leads(
                lead_id, dupes['multi_lead_ids'],
                api_key=api_key, domain=domain,
                dry_run=dry_run, verbose=verbose,
            )
        # Set ownership to Allen on both lead and person (unless --keep-owner)
        if not keep_owner:
            if verbose:
                print(f"  Setting owner to Allen...")
            if not dry_run:
                set_lead_owner(lead_id, ALLEN_USER_ID,
                               api_key=api_key, domain=domain, dry_run=dry_run)
                time.sleep(API_DELAY)
                api_put(f'/persons/{person_id}',
                        {'owner_id': ALLEN_USER_ID},
                        api_key=api_key, domain=domain)
            else:
                print(f"    [DRY RUN] Would set lead + person owner to Allen")
    elif has_dupes:
        # No merge flag — just report
        detail = '; '.join(dupes['issues'])
        if verbose:
            print(f"  Duplicate found: {detail}")
        return 'duplicate', detail

    if not has_dupes and verbose:
        print("  No duplicates")

    # 5. Verify builder — name check first, web search only if inconclusive

    # Step 1: Name check (instant, catches obvious yes/no)
    is_builder, builder_detail = verify_builder_name(clean_org)
    if is_builder is False:
        if not dry_run:
            time.sleep(API_DELAY)
            api_patch(f'/leads/{lead_id}', {'is_archived': True},
                      api_key=api_key, domain=domain)
        if verbose:
            print(f"  Not a builder: {builder_detail} — archived")
        return 'not_builder', builder_detail

    if is_builder is True:
        if verbose:
            print(f"  Builder confirmed: {builder_detail}")

    # Step 2: If name inconclusive, web search to verify
    if is_builder is None:
        web_result, web_detail = verify_builder_web(clean_org)

        if web_result is True:
            is_builder = True
            if verbose:
                print(f"  Builder confirmed: {web_detail}")
        elif web_result is False:
            if not dry_run:
                time.sleep(API_DELAY)
                api_patch(f'/leads/{lead_id}', {'is_archived': True},
                          api_key=api_key, domain=domain)
            if verbose:
                print(f"  Not a builder: {web_detail} — archived")
            return 'not_builder', web_detail
        else:
            # Web search failed/inconclusive — Pipedrive category says builder, trust it
            is_builder = True
            if verbose:
                print(f"  Builder accepted (Pipedrive category, web inconclusive: {web_detail})")

    if verbose:
        print("  All checks passed!")

    # 6. Label as Ready To Call + set owner (unless --keep-owner)
    if not dry_run:
        time.sleep(API_DELAY)
        patch_data = {'label_ids': [LABEL_READY]}
        if not keep_owner:
            patch_data['owner_id'] = ALLEN_USER_ID
        api_patch(f'/leads/{lead_id}', patch_data, api_key=api_key, domain=domain)
        if not keep_owner:
            time.sleep(API_DELAY)
            api_put(f'/persons/{person_id}',
                    {'owner_id': ALLEN_USER_ID},
                    api_key=api_key, domain=domain)

    result_code = 'merged' if has_dupes else 'ready'
    detail = 'merged + qualified' if has_dupes else 'qualified'
    return result_code, detail


# --- Main ---

def fetch_all_leads(*, api_key, domain, limit, filter_id):
    """Fetch leads from the filter with pagination."""
    all_leads = []
    start = 0
    while True:
        data = api_get('/leads', {
            'filter_id': filter_id,
            'limit': PAGE_SIZE,
            'start': start,
        }, api_key=api_key, domain=domain)
        if not data or not data.get('data'):
            break
        all_leads.extend(data['data'])
        pagination = data.get('additional_data', {}).get('pagination', {})
        if not pagination.get('more_items_in_collection'):
            break
        start = pagination['next_start']
        if limit and len(all_leads) >= limit:
            all_leads = all_leads[:limit]
            break
        time.sleep(API_DELAY)
    return all_leads


def main():
    parser = argparse.ArgumentParser(
        description="Qualify cold call leads from Pipedrive"
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without making changes')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max leads to process (0 = all)')
    parser.add_argument('--merge', action='store_true',
                        help='Auto-merge duplicates (archive extra leads, merge persons)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed info per lead')
    parser.add_argument('--all-owners', action='store_true',
                        help='Process all owners (not just Allen)')
    parser.add_argument('--keep-owner', action='store_true',
                        help='Keep original lead/person owner (don\'t reassign to Allen)')
    args = parser.parse_args()

    env = load_env()
    api_key = env.get('PIPEDRIVE_API_KEY', '')
    domain = env.get('PIPEDRIVE_COMPANY_DOMAIN', '')

    if not api_key:
        print("ERROR: PIPEDRIVE_API_KEY not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)
    if not domain:
        print("ERROR: PIPEDRIVE_COMPANY_DOMAIN not set in projects/eps/.env", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN — no changes will be made ===\n")

    # Fetch leads
    filter_id = FILTER_ID_ALL if args.all_owners else FILTER_ID_ALLEN
    filter_name = "All Builders - Cold Outreach" if args.all_owners else "Builders - Allen"
    print(f"Fetching leads from filter: {filter_name} ({filter_id})...")
    leads = fetch_all_leads(api_key=api_key, domain=domain, limit=args.limit, filter_id=filter_id)
    print(f"Found {len(leads)} leads\n")

    if not leads:
        print("No leads to process.")
        return

    # Build maps for duplicate detection
    person_lead_map = build_person_lead_map(leads)
    title_map = build_title_map(leads)

    # Process each lead
    counts = {
        'ready': 0, 'merged': 0, 'skipped': 0, 'invalid_phone': 0,
        'has_deals': 0, 'duplicate': 0, 'not_builder': 0, 'no_person': 0,
        'no_org': 0, 'error': 0,
    }
    issues = []

    for i, lead in enumerate(leads, 1):
        title = lead.get('title', 'Unknown')
        prefix = f"[{i}/{len(leads)}]"

        if args.verbose:
            print(f"{prefix} {title}")

        result, detail = qualify_lead(
            lead, person_lead_map, title_map,
            api_key=api_key, domain=domain,
            dry_run=args.dry_run, merge=args.merge, verbose=args.verbose,
            keep_owner=args.keep_owner,
        )

        counts[result] = counts.get(result, 0) + 1

        if result in ('ready', 'merged'):
            action = "[DRY RUN] Would label" if args.dry_run else "Labeled"
            extra = " (after merge)" if result == 'merged' else ""
            print(f"{prefix} {title} — {action} Ready To Call{extra}")
        elif result == 'skipped':
            if args.verbose:
                print(f"{prefix} {title} — skipped ({detail})")
        else:
            issues.append((title, result, detail))
            if not args.verbose:
                print(f"{prefix} {title} — {result}: {detail}")

        if args.verbose:
            print()

    # Summary
    print("\n=== Cold Lead Qualification ===")
    print(f"Processed:          {len(leads)}")
    print(f"  Ready To Call:    {counts['ready']}")
    print(f"  Merged + Ready:   {counts['merged']}")
    print(f"  Skipped:          {counts['skipped']}")
    print(f"  Invalid phone:    {counts['invalid_phone']}")
    print(f"  Has deals:        {counts['has_deals']}")
    print(f"  Duplicate:        {counts['duplicate']}")
    print(f"  Not a builder:    {counts['not_builder']}")
    print(f"  No person:        {counts['no_person']}")
    print(f"  No org:           {counts['no_org']}")
    print(f"  Error:            {counts['error']}")

    if issues:
        print(f"\nISSUES ({len(issues)}):")
        for title, result, detail in issues:
            print(f"  - \"{title}\" — {result}: {detail}")


if __name__ == '__main__':
    main()
