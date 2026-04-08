"""
Quality gate validator for Enriquez OS components (agents, workflows, skills).

Runs deterministic checks on a file and returns JSON pass/fail.

Usage:
    python3 tools/gate_check.py .claude/agents/eps-cold-calls.md
    python3 tools/gate_check.py projects/eps/workflows/create-quote.md
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# --- Limits ---
LIMITS = {
    'agents': 200,
    'workflows': 250,
    'skills': 100,
}

SOFT_LIMITS = {
    'agents': 150,
    'workflows': 200,
    'skills': 80,
}

REQUIRED_FRONTMATTER = {
    'agents': ['name', 'description', 'model', 'tools'],
    'skills': ['description'],
    'workflows': [],
}

API_KEY_PATTERNS = [
    r'(?:api[_-]?key|token|secret)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}',
    r'PIPEDRIVE_API_KEY\s*=\s*[A-Za-z0-9]',
    r'sk-[A-Za-z0-9]{20,}',
]

FETCH_KEYWORDS = ['fetch', 'api_get', 'curl', 'urllib', 'process_cold_calls.py fetch']
POST_KEYWORDS = ['post', 'api_post', 'send', 'pinned_to', 'method="POST"']


def detect_type(filepath):
    """Detect component type from path."""
    s = str(filepath)
    if '/agents/' in s:
        return 'agents'
    if '/workflows/' in s:
        return 'workflows'
    if '/skills/' in s:
        return 'skills'
    return 'unknown'


def parse_frontmatter(content):
    """Extract YAML frontmatter fields."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, val = line.split(':', 1)
            fields[key.strip()] = val.strip()
    return fields


def check_file(filepath):
    """Run all checks on a file. Returns (pass, issues)."""
    path = Path(filepath)
    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        return False, [f"File not found: {path}"]

    content = path.read_text()
    lines = content.splitlines()
    line_count = len(lines)
    comp_type = detect_type(path)
    issues = []

    # 1. Line count (hard limit = fail, soft limit = warning)
    hard = LIMITS.get(comp_type, 200)
    soft = SOFT_LIMITS.get(comp_type, 150)
    if line_count > hard:
        issues.append(f"FAIL: {line_count} lines exceeds hard limit of {hard} for {comp_type} — must split")
    elif line_count > soft:
        issues.append(f"WARNING: {line_count} lines exceeds target of {soft} for {comp_type} — consider splitting if not single-purpose")

    # 2. Frontmatter
    required = REQUIRED_FRONTMATTER.get(comp_type, [])
    if required:
        fm = parse_frontmatter(content)
        for field in required:
            if field not in fm or not fm[field]:
                issues.append(f"Missing frontmatter: {field}")

    # 3. Hardcoded secrets
    for pattern in API_KEY_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Possible hardcoded secret (pattern: {pattern[:30]}...)")
            break

    # 4. Tool references exist
    tool_refs = re.findall(r'tools/([A-Za-z0-9_]+\.py)', content)
    for tool in set(tool_refs):
        tool_path = BASE_DIR / 'tools' / tool
        if not tool_path.exists():
            issues.append(f"Referenced tool missing: tools/{tool}")

    # 5. Fetch-before-post (agents only)
    if comp_type == 'agents':
        content_lower = content.lower()
        has_post = any(kw in content_lower for kw in POST_KEYWORDS)
        has_fetch = any(kw in content_lower for kw in FETCH_KEYWORDS)
        if has_post and not has_fetch:
            issues.append("Posts/sends data but no fetch/read step found — agents must fetch before posting")

    failures = [i for i in issues if not i.startswith('WARNING')]
    passed = len(failures) == 0

    return passed, issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/gate_check.py <file_path>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    passed, issues = check_file(filepath)

    result = {
        "file": filepath,
        "type": detect_type(filepath),
        "line_count": len(Path(filepath if Path(filepath).is_absolute() else BASE_DIR / filepath).read_text().splitlines()),
        "pass": passed,
        "issues": issues,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
