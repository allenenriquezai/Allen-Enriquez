"""
analyze_tender_docs.py — Analyze downloaded tender documents to generate a structured brief.

Reads PDFs from projects/eps/.tmp/estimateone/docs/{project_id}/
Extracts text from specs, classifies documents, and uses Claude to identify
scope, trades, areas, dates, and special conditions.

Usage:
    python3 tools/analyze_tender_docs.py --project-id 182998
    python3 tools/analyze_tender_docs.py --project-id 182998 --project-name "SMBI Youth Centre"
    python3 tools/analyze_tender_docs.py --project-id 182998 --force  # re-analyze even if brief exists

Outputs:
    projects/eps/.tmp/estimateone/briefs/{project_id}_brief.json

Requires:
    ANTHROPIC_API_KEY environment variable (or in projects/eps/.env)
    pdfplumber (pip install pdfplumber)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "docs"
BRIEFS_DIR = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "briefs"
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"

# Max text to send to Claude (chars) — keep under token limits
MAX_SPEC_TEXT = 80000


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        key = load_env().get("ANTHROPIC_API_KEY", "")
    return key


def extract_pdf_text(pdf_path):
    """Extract text from a PDF using pdfplumber."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        print("WARNING: pdfplumber not installed. Install with: pip install pdfplumber",
              file=sys.stderr)
        return ""
    except Exception as e:
        print(f"WARNING: Failed to extract text from {pdf_path}: {e}", file=sys.stderr)
        return ""


def classify_document(filename, text_content=""):
    """Classify a document as plan, spec, or other."""
    name_lower = filename.lower()

    # Name-based classification
    if any(w in name_lower for w in ("plan", "drawing", "floor", "elevation",
                                      "section", "layout", "architectural",
                                      "site plan", "roof plan")):
        return "plan"
    if any(w in name_lower for w in ("spec", "specification", "schedule",
                                      "scope", "painting", "cleaning",
                                      "trade", "preliminaries")):
        return "spec"

    # Content-based fallback
    if text_content:
        text_lower = text_content[:2000].lower()
        if any(w in text_lower for w in ("scope of work", "specification",
                                          "paint system", "cleaning requirement",
                                          "surface preparation", "number of coats")):
            return "spec"

    return "other"


ANALYSIS_PROMPT = """You are analyzing a commercial tender specification for a painting and cleaning subcontractor (EPS Painting & Cleaning, Brisbane, Australia).

Extract the following from this specification text. Be precise — only include information explicitly stated in the document.

1. **trades_required**: Which trades are needed? Array of "painting" and/or "cleaning". Only include if the spec explicitly mentions painting or cleaning work.
2. **scope_summary**: 2-3 sentence plain English summary of the painting and/or cleaning scope.
3. **areas_mentioned**: Any specific areas or measurements mentioned in text. Array of objects: {"description": str, "area_sqm": number or null}.
4. **key_dates**: Important dates (tender close, project start, completion). Array of objects: {"description": str, "date": str}.
5. **special_conditions**: Access restrictions, working hours, safety requirements, etc. Array of strings.
6. **paint_spec**: Paint specifications if mentioned. Object: {"type": str, "brand": str, "coats": number} or null.
7. **cleaning_stages**: Number of cleaning stages required (1, 2, or 3) or null if not applicable.
8. **estimated_value**: Your rough estimate of the painting/cleaning value based on the scope. String like "$15,000 - $25,000" or null.

Respond in JSON format ONLY. No markdown, no explanation.

SPECIFICATION TEXT:
{spec_text}"""


def analyze_specs_with_claude(spec_text, project_name):
    """Send spec text to Claude for structured extraction."""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Truncate if too long
    if len(spec_text) > MAX_SPEC_TEXT:
        spec_text = spec_text[:MAX_SPEC_TEXT] + "\n\n[TRUNCATED — document continues]"

    prompt = ANALYSIS_PROMPT.format(spec_text=spec_text)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        print(f"WARNING: Claude response was not valid JSON: {e}", file=sys.stderr)
        print(f"Raw response: {text[:500]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Claude API call failed: {e}", file=sys.stderr)
        return None


def generate_brief(project_id, project_name="", docs_dir=None):
    """Process all docs in a project directory and generate a brief."""
    docs_path = docs_dir or (DOCS_DIR / project_id)

    if not docs_path.exists():
        print(f"ERROR: No docs directory found at {docs_path}", file=sys.stderr)
        return None

    files = [f for f in docs_path.iterdir() if f.is_file()]
    if not files:
        print(f"ERROR: No files in {docs_path}", file=sys.stderr)
        return None

    print(f"Analyzing {len(files)} documents for project #{project_id}...")

    # Classify and extract text
    plan_files = []
    spec_files = []
    other_files = []
    all_spec_text = []

    for f in sorted(files):
        text = extract_pdf_text(f) if f.suffix.lower() == ".pdf" else ""
        doc_type = classify_document(f.name, text)

        if doc_type == "plan":
            plan_files.append(f.name)
            print(f"  {f.name} → plan (image-based, for measurement workflow)")
        elif doc_type == "spec":
            spec_files.append(f.name)
            if text:
                all_spec_text.append(f"--- {f.name} ---\n{text}")
                print(f"  {f.name} → spec ({len(text)} chars extracted)")
            else:
                print(f"  {f.name} → spec (no text extractable — image-only)")
        else:
            other_files.append(f.name)
            if text:
                # Check if it might contain useful scope info
                text_lower = text[:2000].lower()
                if any(w in text_lower for w in ("paint", "clean", "scope", "specification")):
                    all_spec_text.append(f"--- {f.name} ---\n{text}")
                    print(f"  {f.name} → other (contains relevant text, including in analysis)")
                else:
                    print(f"  {f.name} → other (skipped)")
            else:
                print(f"  {f.name} → other (no text)")

    # Build brief
    brief = {
        "project_id": project_id,
        "project_name": project_name,
        "analyzed_at": datetime.now().isoformat(),
        "has_plans": len(plan_files) > 0,
        "plan_files": plan_files,
        "spec_files": spec_files,
        "other_files": other_files,
        "trades_required": [],
        "scope_summary": "",
        "areas_mentioned": [],
        "key_dates": [],
        "special_conditions": [],
        "paint_spec": None,
        "cleaning_stages": None,
        "estimated_value": None,
        "confidence": "low",
    }

    # Analyze specs with Claude if we have text
    combined_text = "\n\n".join(all_spec_text)
    if combined_text.strip():
        print(f"\nSending {len(combined_text)} chars to Claude for analysis...")
        analysis = analyze_specs_with_claude(combined_text, project_name)
        if analysis:
            brief["trades_required"] = analysis.get("trades_required", [])
            brief["scope_summary"] = analysis.get("scope_summary", "")
            brief["areas_mentioned"] = analysis.get("areas_mentioned", [])
            brief["key_dates"] = analysis.get("key_dates", [])
            brief["special_conditions"] = analysis.get("special_conditions", [])
            brief["paint_spec"] = analysis.get("paint_spec")
            brief["cleaning_stages"] = analysis.get("cleaning_stages")
            brief["estimated_value"] = analysis.get("estimated_value")
            brief["confidence"] = "high" if brief["trades_required"] else "medium"
            print("  Analysis complete.")
        else:
            brief["confidence"] = "low"
            brief["scope_summary"] = "Analysis failed — manual review needed"
    else:
        if plan_files:
            brief["scope_summary"] = "Plans available but no spec text extracted. Run measurement workflow on plans for scope."
            brief["confidence"] = "medium"
        else:
            brief["scope_summary"] = "No readable documents found. Manual review needed."

    # Save brief
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    brief_path = BRIEFS_DIR / f"{project_id}_brief.json"
    brief_path.write_text(json.dumps(brief, indent=2))
    print(f"\nBrief saved: {brief_path}")

    return brief


def main():
    parser = argparse.ArgumentParser(description="Analyze tender documents")
    parser.add_argument("--project-id", required=True, help="E1 project ID (e.g. 182998)")
    parser.add_argument("--project-name", default="", help="Project name for context")
    parser.add_argument("--docs-dir", help="Override docs directory path")
    parser.add_argument("--force", action="store_true", help="Re-analyze even if brief exists")
    args = parser.parse_args()

    clean_id = args.project_id.replace("#", "").strip()

    # Check cache
    brief_path = BRIEFS_DIR / f"{clean_id}_brief.json"
    if brief_path.exists() and not args.force:
        print(f"Brief already exists: {brief_path}")
        print(f"Use --force to re-analyze")
        brief = json.loads(brief_path.read_text())
        print(json.dumps(brief, indent=2))
        return

    docs_dir = Path(args.docs_dir) if args.docs_dir else None
    brief = generate_brief(clean_id, args.project_name, docs_dir)

    if brief:
        print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
