"""
analyze_tender_docs.py — Analyze downloaded tender documents to generate a structured brief.

Reads PDFs from projects/eps/.tmp/estimateone/docs/{project_id}/
Extracts text from specs, uses Claude Vision for floor plans/drawings,
classifies documents, and identifies scope, trades, areas, dates, and special conditions.

Usage:
    python3 tools/analyze_tender_docs.py --project-id 182998
    python3 tools/analyze_tender_docs.py --project-id 182998 --project-name "SMBI Youth Centre"
    python3 tools/analyze_tender_docs.py --project-id 182998 --force  # re-analyze even if brief exists

Outputs:
    projects/eps/.tmp/estimateone/briefs/{project_id}_brief.json

Requires:
    ANTHROPIC_API_KEY environment variable (or in projects/eps/.env)
    pdfplumber (pip install pdfplumber)
    pdf2image (pip install pdf2image) + poppler (brew install poppler)
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "docs"
BRIEFS_DIR = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "briefs"
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"

# Max text to send to Claude (chars)
MAX_SPEC_TEXT = 80000
# Max pages to send as images for vision analysis
MAX_VISION_PAGES = 12
# Max image dimension (pixels) — keeps token cost down
VISION_IMG_SIZE = 1024

# Keywords for filtering relevant files/folders
RELEVANT_KEYWORDS = {
    "architectural", "arch", "spec", "specification", "paint", "painting",
    "clean", "cleaning", "finish", "finishes", "floor plan", "elevation",
    "section", "schedule", "scope", "preliminaries", "addendum", "addenda",
    "tender", "rfq", "rfp", "drawing", "perspective", "demolition",
    "fitting", "apartment", "roof plan", "external works",
}
SKIP_KEYWORDS = {
    "electrical", "elec", "hydraulic", "hydraulics", "plumbing",
    "mechanical", "mech", "fire", "civil", "structural", "struct",
    "acoustic", "esd", "lift", "geotechnical", "geotech",
    "contaminated", "survey", "environmental", "stormwater",
    "safety guide", "whs schedule", "pre start pack",
}


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


def is_relevant_file(filepath):
    """Check if file/path is relevant for painting/cleaning analysis."""
    path_lower = str(filepath).lower()
    # Skip if path contains skip keywords
    for kw in SKIP_KEYWORDS:
        if kw in path_lower:
            return False
    # Include if path contains relevant keywords
    for kw in RELEVANT_KEYWORDS:
        if kw in path_lower:
            return True
    # Include PDFs in root or unknown folders (might be relevant)
    return filepath.suffix.lower() == ".pdf"


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


def pdf_to_images(pdf_path, max_pages=MAX_VISION_PAGES):
    """Convert PDF pages to base64-encoded JPEG images for Claude Vision."""
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        import io

        images = convert_from_path(
            str(pdf_path),
            last_page=max_pages,
            dpi=150,
        )

        result = []
        for i, img in enumerate(images):
            # Resize if too large
            w, h = img.size
            if max(w, h) > VISION_IMG_SIZE:
                ratio = VISION_IMG_SIZE / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            result.append(b64)

        return result
    except ImportError as e:
        print(f"WARNING: Missing library for PDF vision: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"WARNING: Failed to convert {pdf_path} to images: {e}", file=sys.stderr)
        return []


def classify_document(filename, text_content=""):
    """Classify a document as plan, spec, finishes_schedule, or other."""
    name_lower = filename.lower()

    # Finishes schedule — high value for painting scope
    if any(w in name_lower for w in ("finish", "fitting", "paint schedule",
                                      "colour schedule", "color schedule")):
        return "finishes_schedule"

    # Plans/drawings
    if any(w in name_lower for w in ("plan", "drawing", "floor", "elevation",
                                      "section", "layout", "architectural",
                                      "site plan", "roof plan", "perspective",
                                      "demolition", "apartment type", "external works")):
        return "plan"

    # Specs
    if any(w in name_lower for w in ("spec", "specification", "schedule",
                                      "scope", "painting", "cleaning",
                                      "trade", "preliminaries", "addendum")):
        return "spec"

    # Content-based fallback
    if text_content:
        text_lower = text_content[:2000].lower()
        if any(w in text_lower for w in ("scope of work", "specification",
                                          "paint system", "cleaning requirement",
                                          "surface preparation", "number of coats")):
            return "spec"
        if any(w in text_lower for w in ("finishes schedule", "paint finish",
                                          "colour schedule", "wall finish")):
            return "finishes_schedule"

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


VISION_PROMPT = """You are analyzing architectural drawings/floor plans for a painting and cleaning subcontractor (EPS Painting & Cleaning, Brisbane, Australia).

From these drawings, extract everything relevant to quoting painting and cleaning work:

1. **rooms**: List of rooms/areas visible with approximate dimensions if shown. Array of objects: {"name": str, "dimensions": str or null, "area_sqm": number or null}
2. **total_area_sqm**: Estimated total paintable/cleanable area if you can calculate it, or null.
3. **building_type**: Type of building (residential, commercial, retail, industrial, etc.)
4. **levels**: Number of levels/floors shown.
5. **wall_types**: Types of walls visible (plasterboard, concrete, brick, etc.) Array of strings.
6. **ceiling_heights**: Ceiling heights if shown. String or null.
7. **exterior_surfaces**: Exterior surfaces requiring paint (fascia, eaves, cladding, render, etc.) Array of strings.
8. **special_notes**: Anything else relevant to painting/cleaning scope (heritage elements, high access areas, etc.) Array of strings.
9. **finishes_noted**: Any paint finishes, colours, or specifications noted on the drawings. Array of strings.

Respond in JSON format ONLY. No markdown, no explanation."""


def extract_painting_sections(spec_text, max_chars=MAX_SPEC_TEXT):
    """Extract painting/cleaning-relevant sections from a large spec.

    Instead of blindly truncating, search for relevant sections and extract those.
    """
    if len(spec_text) <= max_chars:
        return spec_text

    keywords = [
        "painting", "paint", "cleaning", "clean", "finish", "finishes",
        "surface preparation", "primer", "undercoat", "topcoat", "coats",
        "colour", "color", "dulux", "taubmans", "wattyl",
        "scope of work", "preliminaries", "general requirements",
        "building cleaning", "final clean", "builders clean",
        "wall finish", "ceiling finish", "floor finish",
        "internal painting", "external painting",
    ]

    lines = spec_text.split("\n")
    relevant_chunks = []
    context_window = 15  # lines before/after a keyword match

    matched_lines = set()
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            for j in range(max(0, i - context_window), min(len(lines), i + context_window + 1)):
                matched_lines.add(j)

    # Build chunks from matched line ranges
    if matched_lines:
        sorted_lines = sorted(matched_lines)
        chunk_start = sorted_lines[0]
        prev = sorted_lines[0]
        for idx in sorted_lines[1:]:
            if idx - prev > 3:  # gap — new chunk
                relevant_chunks.append("\n".join(lines[chunk_start:prev + 1]))
                chunk_start = idx
            prev = idx
        relevant_chunks.append("\n".join(lines[chunk_start:prev + 1]))

    extracted = "\n\n---\n\n".join(relevant_chunks)

    if not extracted.strip():
        # Fallback: first + last chunks
        extracted = spec_text[:max_chars // 2] + "\n\n[...MIDDLE TRUNCATED...]\n\n" + spec_text[-(max_chars // 2):]

    # Still cap it
    if len(extracted) > max_chars:
        extracted = extracted[:max_chars] + "\n\n[TRUNCATED — extracted sections too large]"

    print(f"  Extracted {len(extracted)} chars of relevant sections from {len(spec_text)} char spec")
    return extracted


def parse_claude_json(text):
    """Parse JSON from Claude response, handling common quirks."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first complete JSON object
        depth = 0
        start = text.find("{")
        if start == -1:
            return None
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
        return None


def analyze_specs_with_claude(spec_text, project_name):
    """Send spec text to Claude for structured extraction."""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Smart extraction instead of blind truncation
    spec_text = extract_painting_sections(spec_text)

    prompt = ANALYSIS_PROMPT.replace("{spec_text}", spec_text)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        result = parse_claude_json(text)
        if result is None:
            print(f"WARNING: Could not parse Claude response as JSON", file=sys.stderr)
            print(f"Raw response (first 500 chars): {text[:500]}", file=sys.stderr)
        return result
    except Exception as e:
        print(f"ERROR: Claude API call failed: {e}", file=sys.stderr)
        return None


def analyze_plans_with_vision(image_b64_list, filenames, project_name):
    """Send floor plan images to Claude Vision for spatial analysis."""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Build content with images
    content = []
    content.append({
        "type": "text",
        "text": f"Project: {project_name}\nFiles: {', '.join(filenames)}\n\nAnalyze these architectural drawings for painting/cleaning scope:"
    })

    for b64 in image_b64_list:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            }
        })

    content.append({
        "type": "text",
        "text": VISION_PROMPT
    })

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{"role": "user", "content": content}],
        )
        text = response.content[0].text.strip()
        result = parse_claude_json(text)
        if result is None:
            print(f"WARNING: Could not parse Vision response as JSON", file=sys.stderr)
            print(f"Raw response (first 500 chars): {text[:500]}", file=sys.stderr)
        return result
    except Exception as e:
        print(f"ERROR: Vision API call failed: {e}", file=sys.stderr)
        return None


def generate_brief(project_id, project_name="", docs_dir=None):
    """Process all docs in a project directory and generate a brief."""
    docs_path = docs_dir or (DOCS_DIR / project_id)

    if not docs_path.exists():
        print(f"ERROR: No docs directory found at {docs_path}", file=sys.stderr)
        return None

    all_files = [f for f in docs_path.rglob("*") if f.is_file()]
    if not all_files:
        print(f"ERROR: No files in {docs_path}", file=sys.stderr)
        return None

    # Filter to relevant files only
    files = [f for f in all_files if is_relevant_file(f)]
    skipped = len(all_files) - len(files)

    print(f"Found {len(all_files)} total files, {len(files)} relevant, {skipped} skipped")
    print(f"Analyzing project #{project_id}...")

    # Classify and extract
    plan_files = []
    spec_files = []
    finishes_files = []
    other_files = []
    all_spec_text = []
    plan_images = []  # (b64, filename) tuples
    plan_filenames = []

    for f in sorted(files):
        rel_path = f.relative_to(docs_path)
        text = extract_pdf_text(f) if f.suffix.lower() == ".pdf" else ""
        doc_type = classify_document(f.name, text)

        if doc_type == "finishes_schedule":
            finishes_files.append(str(rel_path))
            # Finishes schedules — try both text and vision
            if text:
                all_spec_text.append(f"--- FINISHES SCHEDULE: {f.name} ---\n{text}")
                print(f"  {rel_path} → finishes schedule ({len(text)} chars)")
            else:
                # Image-based finishes schedule — high priority for vision
                images = pdf_to_images(f, max_pages=4)
                if images:
                    plan_images.extend(images)
                    plan_filenames.append(str(rel_path))
                    print(f"  {rel_path} → finishes schedule (vision: {len(images)} pages)")
                else:
                    print(f"  {rel_path} → finishes schedule (no content extractable)")

        elif doc_type == "plan":
            plan_files.append(str(rel_path))
            # Convert key plan pages to images for vision
            # Prioritize: floor plans, elevations, sections (skip perspectives/3D)
            path_lower = str(rel_path).lower()
            is_priority = any(w in path_lower for w in (
                "floor plan", "elevation", "section", "external works",
                "apartment type", "demolition", "roof plan",
                "architectural", "arch_", "arch ",
            ))
            if is_priority and len(plan_images) < MAX_VISION_PAGES:
                images = pdf_to_images(f, max_pages=2)
                if images:
                    plan_images.extend(images[:2])
                    plan_filenames.append(str(rel_path))
                    print(f"  {rel_path} → plan (vision: {len(images[:2])} pages)")
                else:
                    print(f"  {rel_path} → plan (no images extractable)")
            else:
                print(f"  {rel_path} → plan (skipped — {'low priority' if not is_priority else 'vision limit reached'})")

        elif doc_type == "spec":
            spec_files.append(str(rel_path))
            if text:
                all_spec_text.append(f"--- {f.name} ---\n{text}")
                print(f"  {rel_path} → spec ({len(text)} chars)")
            else:
                print(f"  {rel_path} → spec (no text extractable)")
        else:
            other_files.append(str(rel_path))
            if text:
                text_lower = text[:2000].lower()
                if any(w in text_lower for w in ("paint", "clean", "scope", "specification",
                                                   "finish", "colour", "color")):
                    all_spec_text.append(f"--- {f.name} ---\n{text}")
                    print(f"  {rel_path} → other (contains relevant text, including)")
                else:
                    print(f"  {rel_path} → other (skipped)")
            else:
                print(f"  {rel_path} → other (no text)")

    # Build brief
    brief = {
        "project_id": project_id,
        "project_name": project_name,
        "analyzed_at": datetime.now().isoformat(),
        "total_files": len(all_files),
        "relevant_files": len(files),
        "skipped_files": skipped,
        "has_plans": len(plan_files) > 0,
        "has_finishes_schedule": len(finishes_files) > 0,
        "plan_files": plan_files,
        "finishes_files": finishes_files,
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
        "vision_analysis": None,
        "confidence": "low",
    }

    # Analyze specs with Claude text
    combined_text = "\n\n".join(all_spec_text)
    if combined_text.strip():
        print(f"\nSending {len(combined_text)} chars to Claude for text analysis...")
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
            print("  Text analysis complete.")

    # Analyze plans with Claude Vision
    if plan_images:
        # Cap at MAX_VISION_PAGES
        images_to_send = plan_images[:MAX_VISION_PAGES]
        print(f"\nSending {len(images_to_send)} plan pages to Claude Vision...")
        vision = analyze_plans_with_vision(images_to_send, plan_filenames, project_name)
        if vision:
            brief["vision_analysis"] = vision
            # Merge vision areas into areas_mentioned if text analysis didn't find any
            if not brief["areas_mentioned"] and vision.get("rooms"):
                brief["areas_mentioned"] = [
                    {"description": r.get("name", ""), "area_sqm": r.get("area_sqm")}
                    for r in vision["rooms"]
                ]
            # Upgrade confidence if we got vision data
            if brief["confidence"] == "low":
                brief["confidence"] = "medium"
            print("  Vision analysis complete.")
        else:
            print("  Vision analysis failed.")
    else:
        if plan_files:
            brief["scope_summary"] = (brief["scope_summary"] or "") + " Plans available but no vision analysis (no priority drawings found)."

    if not combined_text.strip() and not plan_images:
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
