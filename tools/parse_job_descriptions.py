"""
Parse job_descriptions_raw.txt and split into individual markdown files
in projects/eps/job_descriptions/, one per service type.

Usage:
    python3 tools/parse_job_descriptions.py
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, 'projects', 'eps', '.tmp', 'job_descriptions_raw.txt')
OUT_DIR = os.path.join(BASE_DIR, 'projects', 'eps', 'job_descriptions')

# Map Drive doc names to service type filenames
DOC_NAME_MAP = {
    'BOND CLEAN': 'bond_clean',
    '3-STAGE CONSTRUCTION CLEANING': 'construction_cleaning_3_stage',
    '2-STAGE CONSTRUCTION CLEANING': 'construction_cleaning_2_stage',
    '1 STAGE / FINAL CONSTRUCTION CLEANING': 'construction_cleaning_1_stage',
    'COMMERCIAL - REGULAR CLEANING': 'commercial_regular_cleaning',
    'COMMERCIAL ONE-OFF CLEANING': 'commercial_oneoff_cleaning',
    'RESIDENTIAL - REGULAR CLEANING': 'residential_regular_cleaning',
    'RESIDENTIAL - ONE OFF CLEANING': 'residential_oneoff_cleaning',
    'INTERNAL PAINTING': 'internal_painting',
    'EXTERNAL PAINTING': 'external_painting',
    'ROOF PAINTING': 'roof_painting',
    'MULTIPLE PAINTING': 'multiple_painting',
}

os.makedirs(OUT_DIR, exist_ok=True)

with open(RAW_FILE, 'r') as f:
    raw = f.read()

# Split on document headers (indented or not)
doc_pattern = re.compile(r'^\s*---\s+(.*?)\s+\(application/vnd\.google-apps\.document\)\s+---\s*$', re.MULTILINE)
matches = list(doc_pattern.finditer(raw))

docs = {}
for i, match in enumerate(matches):
    name = match.group(1).strip()
    start = match.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
    content = raw[start:end].strip()
    # Strip trailing empty separator lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    docs[name] = content

written = []
for doc_name, content in docs.items():
    # Match to service type
    slug = None
    for key, val in DOC_NAME_MAP.items():
        if key in doc_name.upper():
            slug = val
            break
    if not slug:
        print(f"  SKIP (no mapping): {doc_name}")
        continue

    out_path = os.path.join(OUT_DIR, f"{slug}.md")
    # Strip the header block (Prepared For / Address / Date) — keep from JOB SUMMARY down
    # Find where useful content starts
    summary_match = re.search(r'(JOB SUMMARY|SCOPE OF WORK)', content)
    if summary_match:
        body = content[summary_match.start():]
    else:
        body = content

    md = f"# {doc_name.title()}\n\n<!-- source: Google Drive -->\n\n{body}\n\n---\n\n## Personalisation Prompts\n- Client situation (who they are, why they're getting this done)\n- Emotional drivers (e.g. selling, new home, builder handover pressure)\n- Any scope specifics not covered by standard inclusions\n"

    with open(out_path, 'w') as f:
        f.write(md)
    written.append(slug)
    print(f"  Written: {slug}.md")

print(f"\nDone. {len(written)} files written.")
