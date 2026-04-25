"""
EPS Quote Calculator — deterministic pricing engine.

Takes aggregate scope measurements (whole property/floor) and outputs quote_data.json.

Usage (simple — single scope):
    python3 tools/calculate_quote.py \
      --client "John Smith" \
      --address "123 Main St, Brisbane" \
      --job-type "internal repaint" \
      --scope "220sqm walls, 110sqm ceilings, 4 doors, 60lm skirting" \
      --mob 150

Usage (component breakdown — one row per component/service):
    python3 tools/calculate_quote.py \
      --client "John Smith" \
      --address "123 Main St, Brisbane" \
      --job-type "internal repaint" \
      --components projects/eps/.tmp/components.json

    components.json format:
    [
      {"label": "Level 1", "scope": "1020sqm walls, 720sqm ceilings, 340lm skirting, 8 doors"},
      {"label": "Level 2", "scope": "960sqm walls, 680sqm ceilings, 320lm skirting, 9 doors"}
    ]

    Line item descriptions become: "Level 1 — Internal Wall Painting", etc.

    --mob is optional. Omit it entirely if no mobilisation fee applies.

Scope string format (comma-separated, order doesn't matter):
    Xsqm walls              → INT-01 internal walls
    Xsqm ceilings           → INT-02 internal ceilings
    X doors                 → INT-03 doors (both sides)
    Xsqm feature wall       → INT-07 feature wall
    Xsqm patch              → INT-06 patch & prep
    Xlm skirting            → INT-04 skirting boards
    Xlm architraves         → INT-05 architraves
    Xsqm external walls     → EXT-01 external walls low level
    Xsqm external walls >3m → EXT-02 external walls high level
    Xsqm roof               → EXT-06 roof painting
    X garage doors          → EXT-05 garage door
    Xlm fascia              → EXT-03 fascia/eaves/gutters
    Xlm gutters             → EXT-03 fascia/eaves/gutters
    Xlm eaves               → EXT-03 fascia/eaves/gutters
    Xsqm deck               → EXT-04 timber deck
    Xhrs cleaning            → HOUR general cleaning
    Xhrs glass cleaning      → GLASS-WINDOW glass & window cleaning
    Xsqm clean stage 1       → BUILD-01 construction clean stage 1
    Xsqm clean stage 2       → BUILD-02 construction clean stage 2
    Xsqm clean stage 3       → BUILD-03 construction clean stage 3
"""

import argparse
import json
import os
import re
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRICING_CONFIG = os.path.join(BASE_DIR, 'projects', 'eps', 'config', 'pricing.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'projects', 'eps', '.tmp', 'quote_data.json')

DAY_RATE_KEYWORDS = ['stairwell', 'vaulted ceiling', 'heritage', 'severe damage', 'scaffolding required']


def load_pricing():
    with open(PRICING_CONFIG) as f:
        return json.load(f)


def parse_scope(scope_str):
    """
    Parse a free-text scope string into a list of (surface_key, quantity) tuples.
    Handles sqm, lm, and count (doors, garage doors).
    """
    items = []
    scope_lower = scope_str.lower()

    # Check for day-rate flags
    flags = [kw for kw in DAY_RATE_KEYWORDS if kw in scope_lower]

    # Each pattern: (regex, surface_key)
    patterns = [
        # Internal
        (r'(\d+(?:\.\d+)?)\s*sqm\s+(?:internal\s+)?walls?(?!\s*>)', 'INT-01'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+ceilings?',                       'INT-02'),
        (r'(\d+(?:\.\d+)?)\s+doors?(?!\s*garage)',                    'INT-03'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+feature\s+wall',                  'INT-07'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+patch',                           'INT-06'),
        (r'(\d+(?:\.\d+)?)\s*lm\s+skirting',                         'INT-04'),
        (r'(\d+(?:\.\d+)?)\s*lm\s+architraves?',                     'INT-05'),
        # External
        (r'(\d+(?:\.\d+)?)\s*sqm\s+external\s+walls\s*>?\s*3m',     'EXT-02'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+external\s+walls(?!\s*>?\s*3m)', 'EXT-01'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+roof',                            'EXT-06'),
        (r'(\d+(?:\.\d+)?)\s+garage\s+doors?',                       'EXT-05'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+deck',                            'EXT-04'),
        (r'(\d+(?:\.\d+)?)\s*lm\s+(?:fascia|gutters?|eaves?)',       'EXT-03'),
        # Cleaning — specific before general
        (r'(\d+(?:\.\d+)?)\s*(?:hrs?|hours?)\s+(?:glass|window)\s+clean(?:ing)?', 'GLASS-WINDOW'),
        (r'(\d+(?:\.\d+)?)\s*(?:hrs?|hours?)\s+(?:general\s+)?clean(?:ing)?', 'HOUR'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+(?:construction\s+)?clean\s+stage\s*1', 'BUILD-01'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+(?:construction\s+)?clean\s+stage\s*2', 'BUILD-02'),
        (r'(\d+(?:\.\d+)?)\s*sqm\s+(?:construction\s+)?clean\s+stage\s*3', 'BUILD-03'),
    ]

    for pattern, key in patterns:
        match = re.search(pattern, scope_lower)
        if match:
            qty = float(match.group(1))
            items.append((key, qty))

    return items, flags


def build_line_items(parsed_items, pricing, mob_amount=None, label=None):
    """Build priced line items from parsed scope.
    If label is provided, prefix each description: '{label} — {name}'.
    """
    rates = pricing['rates']
    rate_lookup = {}
    for category in rates.values():
        for key, val in category.items():
            rate_lookup[key] = val

    line_items = []

    for key, qty in parsed_items:
        if key not in rate_lookup:
            print(f"WARNING: unknown rate key {key}, skipping", file=sys.stderr)
            continue
        r = rate_lookup[key]
        unit = r['unit']
        rate = r['rate']
        subtotal = round(qty * rate, 2)
        description = f"{label} — {r['name']}" if label else r['name']

        line_items.append({
            'code': r['code'],
            'description': description,
            'quantity': qty,
            'rate': rate,
            'unit': unit,
            'subtotal': subtotal,
        })

    # Mobilisation fee — only if requested
    if mob_amount is not None:
        line_items.append({
            'code': 'EPSMOB',
            'description': 'Mobilisation Fee',
            'quantity': 1,
            'rate': mob_amount,
            'unit': 'item',
            'subtotal': round(mob_amount, 2),
        })

    return line_items


def build_line_items_from_components(components, pricing, mob_amount=None):
    """Build component-based line items from a list of {label, scope} dicts."""
    all_items = []
    all_flags = []
    for component in components:
        label = component['label']
        parsed, flags = parse_scope(component['scope'])
        all_flags.extend(flags)
        items = build_line_items(parsed, pricing, label=label)
        all_items.extend(items)

    if mob_amount is not None:
        all_items.append({
            'code': 'EPSMOB',
            'description': 'Mobilisation Fee',
            'quantity': 1,
            'rate': mob_amount,
            'unit': 'item',
            'subtotal': round(mob_amount, 2),
        })

    return all_items, all_flags


def calculate_totals(line_items, gst_rate):
    subtotal = round(sum(i['subtotal'] for i in line_items), 2)
    gst = round(subtotal * gst_rate, 2)
    total = round(subtotal + gst, 2)
    return subtotal, gst, total


def generate_job_description(parsed_items, job_type, flags):
    """Generate plain-English bullet points describing the work."""
    rate_to_desc = {
        'INT-01': 'Paint all internal walls with two coats of premium paint',
        'INT-02': 'Paint all ceilings flat white',
        'INT-03': 'Paint all doors both sides including frames',
        'INT-04': 'Paint all skirting boards',
        'INT-05': 'Paint all architraves',
        'INT-06': 'Minor patching and surface preparation included throughout',
        'INT-07': 'Feature wall painted with premium finish',
        'EXT-01': 'Paint all external walls — low level (up to 3m)',
        'EXT-02': 'Paint all external walls — high level (3m+)',
        'EXT-03': 'Paint fascia, eaves and gutters',
        'EXT-04': 'Sand and repaint timber deck',
        'EXT-05': 'Paint garage door(s)',
        'EXT-06': 'Paint roof (tile/metal)',
        'HOUR': 'General cleaning at hourly rate',
        'GLASS-WINDOW': 'Glass and window cleaning',
        'BUILD-01': 'Construction clean — Stage 1 (post-frame rough clean)',
        'BUILD-02': 'Construction clean — Stage 2 (pre-paint detail clean)',
        'BUILD-03': 'Construction clean — Stage 3 (final/PCI handover clean)',
    }

    keys_present = {k for k, _ in parsed_items}
    bullets = [rate_to_desc[k] for k in rate_to_desc if k in keys_present]

    if flags:
        bullets.append(f'Note: day rate may apply — {", ".join(flags)}')

    return bullets


def print_summary(line_items, subtotal, gst, total):
    print()
    print('LINE ITEMS')
    print('─' * 62)
    for item in line_items:
        qty_str = f"{item['quantity']:.1f} {item['unit']}"
        rate_str = f"${item['rate']:.2f}/{item['unit']}"
        print(f"{item['code']:<22} {item['description'][:25]:<26} {qty_str:>12}  {rate_str:>12}  ${item['subtotal']:>9.2f}")
    print('─' * 62)
    print(f"{'Subtotal':>63}  ${subtotal:>9.2f}")
    print(f"{'GST (10%)':>63}  ${gst:>9.2f}")
    print(f"{'TOTAL':>63}  ${total:>9.2f}")
    print()


def main():
    parser = argparse.ArgumentParser(description='EPS Quote Calculator')
    parser.add_argument('--client',     required=True, help='Client name')
    parser.add_argument('--address',    required=True, help='Property address')
    parser.add_argument('--job-type',   required=True, help='Job type description')
    scope_group = parser.add_mutually_exclusive_group(required=True)
    scope_group.add_argument('--scope',      help='Aggregate scope string (simple jobs)')
    scope_group.add_argument('--components', help='Path to components JSON file (multi-level/unit jobs)')
    parser.add_argument('--mob',        type=float, default=None,
                        help='Mobilisation fee amount (omit to exclude)')
    parser.add_argument('--multiplier', type=float, default=None,
                        help='Apply a multiplier to all rates, e.g. 1.15 for +15%%')
    parser.add_argument('--override',   type=str,   default=None,
                        help='Override specific rates: "INT-01:25,INT-02:24"')
    parser.add_argument('--job-description', type=str, default=None,
                        help='JSON array of bullet strings; skips auto-generation if provided')
    parser.add_argument('--date',       default=str(date.today()), help='Quote date (YYYY-MM-DD)')
    args = parser.parse_args()

    pricing = load_pricing()

    # Apply rate overrides
    if args.multiplier or args.override:
        item_overrides = {}
        if args.override:
            for part in args.override.split(','):
                key, val = part.strip().split(':')
                item_overrides[key.strip().upper()] = float(val.strip())

        for category in pricing['rates'].values():
            for key, rate_def in category.items():
                if key in item_overrides:
                    rate_def['rate'] = item_overrides[key]
                elif args.multiplier:
                    rate_def['rate'] = round(rate_def['rate'] * args.multiplier, 2)

    if args.components:
        components_path = os.path.join(BASE_DIR, args.components) if not os.path.isabs(args.components) else args.components
        with open(components_path) as f:
            components = json.load(f)
        line_items, flags = build_line_items_from_components(components, pricing, mob_amount=args.mob)
        # For job description, aggregate all parsed items across components
        all_parsed = []
        for c in components:
            parsed, _ = parse_scope(c['scope'])
            all_parsed.extend(parsed)
        parsed_items = list({k: (k, v) for k, v in all_parsed}.values())  # dedupe by key
    else:
        parsed_items, flags = parse_scope(args.scope)
        if not parsed_items:
            print("ERROR: Could not parse any line items from scope string.", file=sys.stderr)
            print("Example: '220sqm walls, 110sqm ceilings, 4 doors, 60lm skirting'", file=sys.stderr)
            sys.exit(1)
        line_items = build_line_items(parsed_items, pricing, mob_amount=args.mob)

    if flags:
        print(f"WARNING: Day-rate conditions detected: {', '.join(flags)}", file=sys.stderr)
        print("Consider quoting by day rate instead of sqm.", file=sys.stderr)

    subtotal, gst, total = calculate_totals(line_items, pricing['gst_rate'])
    if args.job_description:
        job_description = json.loads(args.job_description)
    else:
        job_description = generate_job_description(parsed_items, args.job_type, flags)

    quote_data = {
        'client':       args.client,
        'address':      args.address,
        'job_type':     args.job_type,
        'quote_date':   args.date,
        'job_description': job_description,
        'line_items':   line_items,
        'subtotal':     subtotal,
        'gst':          gst,
        'total':        total,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(quote_data, f, indent=2)

    print_summary(line_items, subtotal, gst, total)
    print(f"Quote data saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
