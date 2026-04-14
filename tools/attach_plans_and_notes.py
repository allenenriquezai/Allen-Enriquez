"""
attach_plans_and_notes.py — Attach floor plan PDFs to Pipedrive deals and add measurement notes.

For painting deals: adds internal ceilings, internal walls, skirting board, door count.
For cleaning deals: adds internal ceiling area.

Uses vision analysis from briefs to calculate measurements.
Attaches relevant floor plan/architectural PDFs to each deal.

Usage:
    python3 tools/attach_plans_and_notes.py
    python3 tools/attach_plans_and_notes.py --dry-run  # preview without making changes
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "docs"
BRIEFS_DIR = BASE_DIR / "projects" / "eps" / ".tmp" / "estimateone" / "briefs"
ENV_FILE = BASE_DIR / "projects" / "eps" / ".env"

# Pipeline IDs
PIPELINE_CLEAN = 3
PIPELINE_PAINT = 4

# Deal mapping: project_id → list of (deal_id, pipeline_id)
DEAL_MAP = {
    "182097": [
        (1334, PIPELINE_PAINT),   # Hutchinson Builders
        (1338, PIPELINE_PAINT),   # Inten Constructions
        (1339, PIPELINE_PAINT),   # Streetbuild
    ],
    "182025": [
        (1335, PIPELINE_PAINT),   # Total Construction
        (1340, PIPELINE_PAINT),   # CIP Constructions
        (1341, PIPELINE_PAINT),   # FDC Construction
        (1342, PIPELINE_PAINT),   # Tomkins
    ],
    "182062": [
        (1336, PIPELINE_PAINT),   # Newlands Civil
    ],
    "182968": [
        (1337, PIPELINE_CLEAN),   # Bryant - cleaning pipeline
    ],
    "182048": [
        (1343, PIPELINE_CLEAN),   # inSite
        (1344, PIPELINE_CLEAN),   # Melrose
        (1345, PIPELINE_CLEAN),   # Warrell
    ],
    "181702": [
        (1346, PIPELINE_CLEAN),   # Kane Constructions
        (1347, PIPELINE_CLEAN),   # Mettle QLD
    ],
}

# Keywords for relevant PDFs to attach (must match at least one)
ATTACH_KEYWORDS = [
    "floor plan", "elevation", "section", "architectural", "arch",
    "finishes", "fitting", "painting", "cleaning", "scope",
    "apartment", "external works", "demolition",
    "spec", "drawing", "tender documentation",
    "addendum", "preliminar",
]
# Skip these even if they match above
ATTACH_SKIP = [
    "refriger", "condenser", "plantroom", "plant room", "plant deck",
    "generator", "splitter", "refrig", "electrical", "elec",
    "structural", "struct", "hydraulic", "plumbing", "fire",
    "civil", "acoustic", "geotechnical", "geotech", "mechanical",
    "mech-m-", "stormwater", "safety guide", "safety in design",
    "whs", "pre start", "hammertech", "good job",
    "safety expectations", "subcontractorrequirements",
    "contaminated", "drain", "hob layout", "landscape",
    "shadow diagram", "survey", "cover sheet", "transmittal",
    "rfq.pdf", "rft", "rfp", "attar report", "environmental",
    "signage", "esd", "lift",
]

MAX_FILE_SIZE_MB = 45


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_env():
    env = load_env()
    return {
        "api_key": env.get("PIPEDRIVE_API_KEY", ""),
        "domain": env.get("PIPEDRIVE_COMPANY_DOMAIN", ""),
    }


def pipedrive_api(method, endpoint, data=None, env=None):
    """Make a Pipedrive API call."""
    if env is None:
        env = get_env()
    url = f"https://{env['domain']}/api/v1/{endpoint}?api_token={env['api_key']}"
    if method == "GET":
        if data:
            url += "&" + urlencode(data)
        req = Request(url)
    else:
        body = json.dumps(data).encode() if data else b""
        req = Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  API error: {e}", file=sys.stderr)
        return None


def attach_file_to_deal(filepath, deal_id, env):
    """Attach a file to a Pipedrive deal using curl (multipart upload)."""
    url = f"https://{env['domain']}/api/v1/files?api_token={env['api_key']}"
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", url,
         "-F", f"file=@{filepath}",
         "-F", f"deal_id={deal_id}"],
        capture_output=True, text=True, timeout=120
    )
    try:
        resp = json.loads(result.stdout)
        if resp.get("success"):
            return resp["data"]["id"]
        else:
            print(f"  Upload failed for {filepath}: {resp.get('error', 'unknown')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  Upload error: {e}", file=sys.stderr)
        return None


def add_note_to_deal(deal_id, content, env):
    """Add a note to a Pipedrive deal."""
    result = pipedrive_api("POST", "notes", {
        "deal_id": deal_id,
        "content": content,
        "pinned_to_deal_flag": 1,
    }, env)
    if result and result.get("success"):
        return result["data"]["id"]
    return None


def get_relevant_files(project_id):
    """Get relevant PDFs to attach for a project."""
    docs_path = (DOCS_DIR / project_id).resolve()
    if not docs_path.exists():
        return []

    relevant = []
    for f in docs_path.rglob("*.pdf"):
        name_lower = str(f).lower()
        # Skip if matches skip keywords
        if any(kw in name_lower for kw in ATTACH_SKIP):
            continue

        # Must match at least one attach keyword
        if not any(kw in name_lower for kw in ATTACH_KEYWORDS):
            continue

        # Check size
        size_mb = f.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            print(f"  Skipping {f.name} ({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)")
            continue

        relevant.append(f)

    return sorted(relevant)


def calculate_measurements(brief):
    """Calculate painting/cleaning measurements from vision analysis."""
    vision = brief.get("vision_analysis") or {}
    rooms = vision.get("rooms", [])
    levels = vision.get("levels", 1)
    building_type = vision.get("building_type", "unknown")
    ceiling_height_str = vision.get("ceiling_heights", "2.7m")
    wall_types = vision.get("wall_types", [])
    exterior = vision.get("exterior_surfaces", [])
    finishes = vision.get("finishes_noted", [])
    special = vision.get("special_notes", [])

    # Parse ceiling height
    ceiling_height = 2.7  # default
    if ceiling_height_str:
        import re
        m = re.search(r'(\d+\.?\d*)\s*m', str(ceiling_height_str))
        if m:
            ceiling_height = float(m.group(1))
            if ceiling_height > 10:  # probably mm
                ceiling_height = ceiling_height / 1000

    # Calculate areas from rooms
    total_floor_sqm = 0
    known_floor_sqm = 0  # from actual measurements
    room_details = []
    door_count = 0
    apartment_count = 0

    for room in rooms:
        area = room.get("area_sqm")
        name = room.get("name", "Unknown")
        dims = room.get("dimensions", "")
        name_lower = name.lower()

        if "apartment" in name_lower or "unit" in name_lower:
            apartment_count += 1

        if area and area > 0:
            known_floor_sqm += area
            room_details.append(f"  - {name}: {area:.1f} sqm")
        elif dims:
            room_details.append(f"  - {name}: {dims}")
        else:
            room_details.append(f"  - {name}")

        # Estimate doors per room/apartment
        if "apartment" in name_lower or "unit" in name_lower:
            door_count += 5  # front + bedroom + bathroom + kitchen + laundry
        elif "bathroom" in name_lower or "kitchen" in name_lower:
            door_count += 1
        elif "bedroom" in name_lower:
            door_count += 1
        elif "office" in name_lower or "lobby" in name_lower:
            door_count += 2

    # Estimate total floor area
    # If we have apartments, use apartment count × avg size (more reliable than partial sqm data)
    if apartment_count > 0:
        # Average 1-bed apartment ~55sqm, 2-bed ~75sqm
        avg_apt_sqm = 55
        apt_total = apartment_count * avg_apt_sqm
        # Common areas: lobby, corridors, stairs ~20% of apartment area
        common_sqm = apt_total * 0.20
        total_floor_sqm = apt_total + common_sqm + known_floor_sqm
        # Multiply by number of levels for total building area
        if levels > 1:
            # Apartments typically span levels 1+ (ground is often common/parking)
            total_floor_sqm = total_floor_sqm  # already counted per-apartment
    elif known_floor_sqm > 0:
        total_floor_sqm = known_floor_sqm
    else:
        # No data — try building type heuristic
        bt = building_type.lower() if building_type else ""
        if "retail" in bt or "commercial" in bt:
            total_floor_sqm = 500  # conservative retail estimate
        elif "school" in bt or "college" in bt:
            total_floor_sqm = 1200
        elif "residential" in bt:
            total_floor_sqm = 200

    # Calculate painting measurements
    # Internal ceiling area ≈ total floor area
    internal_ceiling_sqm = total_floor_sqm

    # Internal wall area ≈ perimeter × height
    # Rule of thumb: wall area ≈ 2.5 to 3x floor area for residential
    wall_multiplier = 2.8
    internal_wall_sqm = total_floor_sqm * wall_multiplier

    # Skirting ≈ perimeter. For residential, perimeter ≈ sqrt(floor_area) * 4 * 1.3 (for rooms)
    import math
    if total_floor_sqm > 0:
        skirting_lm = math.sqrt(total_floor_sqm) * 4 * 1.3
    else:
        skirting_lm = 0

    return {
        "building_type": building_type,
        "levels": levels,
        "ceiling_height_m": ceiling_height,
        "rooms": room_details,
        "room_count": len(rooms),
        "total_floor_sqm": round(total_floor_sqm, 1),
        "internal_ceiling_sqm": round(internal_ceiling_sqm, 1),
        "internal_wall_sqm": round(internal_wall_sqm, 1),
        "skirting_lm": round(skirting_lm, 1),
        "door_count": door_count,
        "wall_types": wall_types,
        "exterior_surfaces": exterior,
        "finishes_noted": finishes,
        "special_notes": special,
    }


def format_painting_note(project_name, project_id, measurements):
    """Format painting measurement note for Pipedrive."""
    lines = [
        f"<b>🎨 PAINTING MEASUREMENTS — {project_name}</b>",
        f"<i>Project #{project_id} | Auto-analyzed from tender docs</i>",
        "",
        f"<b>Building:</b> {measurements['building_type']} | {measurements['levels']} level(s) | {measurements['ceiling_height_m']}m ceiling height",
        "",
        "<b>── INTERNAL MEASUREMENTS (ESTIMATED) ──</b>",
        f"Internal Ceilings: <b>{measurements['internal_ceiling_sqm']} sqm</b>",
        f"Internal Walls: <b>{measurements['internal_wall_sqm']} sqm</b>",
        f"Skirting Board: <b>{measurements['skirting_lm']} lm</b>",
        f"Doors (estimated): <b>{measurements['door_count']}</b>",
        "",
        f"Total Floor Area: {measurements['total_floor_sqm']} sqm",
        f"Rooms/Areas: {measurements['room_count']}",
    ]

    if measurements["wall_types"]:
        lines.append(f"\n<b>Wall Types:</b> {', '.join(measurements['wall_types'])}")

    if measurements["exterior_surfaces"]:
        lines.append(f"\n<b>── EXTERIOR SURFACES ──</b>")
        for s in measurements["exterior_surfaces"]:
            lines.append(f"  • {s}")

    if measurements["finishes_noted"]:
        lines.append(f"\n<b>── FINISHES FROM DRAWINGS ──</b>")
        for f in measurements["finishes_noted"]:
            lines.append(f"  • {f}")

    if measurements["special_notes"]:
        lines.append(f"\n<b>── NOTES ──</b>")
        for n in measurements["special_notes"][:8]:
            lines.append(f"  • {n}")

    lines.append("\n<i>⚠️ Measurements are AI-estimated from floor plans. Verify on site visit.</i>")
    return "\n".join(lines)


def format_cleaning_note(project_name, project_id, measurements):
    """Format cleaning measurement note for Pipedrive."""
    lines = [
        f"<b>🧹 CLEANING MEASUREMENTS — {project_name}</b>",
        f"<i>Project #{project_id} | Auto-analyzed from tender docs</i>",
        "",
        f"<b>Building:</b> {measurements['building_type']} | {measurements['levels']} level(s)",
        "",
        "<b>── CLEANING AREA (ESTIMATED) ──</b>",
        f"Internal Ceiling Area (= cleanable area): <b>{measurements['internal_ceiling_sqm']} sqm</b>",
        f"Total Floor Area: {measurements['total_floor_sqm']} sqm",
        f"Rooms/Areas: {measurements['room_count']}",
    ]

    if measurements["special_notes"]:
        lines.append(f"\n<b>── NOTES ──</b>")
        for n in measurements["special_notes"][:5]:
            lines.append(f"  • {n}")

    lines.append("\n<i>⚠️ Measurements are AI-estimated from floor plans. Verify on site visit.</i>")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = get_env()
    if not env["api_key"]:
        print("ERROR: PIPEDRIVE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    total_files_attached = 0
    total_notes_added = 0

    for project_id, deals in DEAL_MAP.items():
        brief_path = BRIEFS_DIR / f"{project_id}_brief.json"
        if not brief_path.exists():
            print(f"\n⚠️  No brief for project #{project_id} — skipping")
            continue

        brief = json.loads(brief_path.read_text())
        project_name = brief.get("project_name", f"Project #{project_id}")

        print(f"\n{'='*60}")
        print(f"PROJECT: {project_name} (#{project_id})")
        print(f"{'='*60}")

        # Get relevant PDFs
        relevant_files = get_relevant_files(project_id)
        print(f"  Found {len(relevant_files)} relevant PDFs to attach")

        # Calculate measurements
        measurements = calculate_measurements(brief)
        print(f"  Floor area: {measurements['total_floor_sqm']} sqm | Walls: {measurements['internal_wall_sqm']} sqm | Doors: {measurements['door_count']}")

        for deal_id, pipeline_id in deals:
            is_painting = pipeline_id == PIPELINE_PAINT
            deal_type = "PAINT" if is_painting else "CLEAN"
            print(f"\n  Deal #{deal_id} ({deal_type}):")

            # Attach files
            if relevant_files:
                for f in relevant_files:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    rel = f.relative_to(DOCS_DIR / project_id)
                    if args.dry_run:
                        print(f"    [DRY RUN] Would attach: {rel} ({size_mb:.1f}MB)")
                    else:
                        print(f"    Attaching: {rel} ({size_mb:.1f}MB)...", end=" ", flush=True)
                        file_id = attach_file_to_deal(str(f), deal_id, env)
                        if file_id:
                            print(f"OK (file #{file_id})")
                            total_files_attached += 1
                        else:
                            print("FAILED")
                        time.sleep(0.3)  # rate limit

            # Add measurement note
            if is_painting:
                note = format_painting_note(project_name, project_id, measurements)
            else:
                note = format_cleaning_note(project_name, project_id, measurements)

            if args.dry_run:
                print(f"    [DRY RUN] Would add {deal_type} measurement note")
            else:
                note_id = add_note_to_deal(deal_id, note, env)
                if note_id:
                    print(f"    Added {deal_type} measurement note (#{note_id})")
                    total_notes_added += 1
                else:
                    print(f"    Failed to add note")
                time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"DONE: {total_files_attached} files attached, {total_notes_added} notes added")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
