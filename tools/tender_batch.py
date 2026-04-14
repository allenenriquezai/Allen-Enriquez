"""
tender_batch.py — Daily tender pipeline automation.

Orchestrates the full tender campaign:
1. Scrape E1 (leads + open tenders filtered by Painting/Building Cleaning)
2. Download docs for new tenders
3. Analyze specs with Haiku
4. Create Pipedrive CRM records (org → person → deal)
5. Push results to Google Sheet
6. Report what's new

Runs standalone — no Claude Code context burned.

Usage:
    python3 tools/tender_batch.py                    # Full daily pipeline
    python3 tools/tender_batch.py --scrape-only      # Just scrape + filter, no CRM
    python3 tools/tender_batch.py --analyze-only      # Analyze already-downloaded docs
    python3 tools/tender_batch.py --crm-only          # Create CRM records from briefs
    python3 tools/tender_batch.py --project-ids 182998,183001  # Process specific tenders
    python3 tools/tender_batch.py --dry-run           # Show what would happen, no changes
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- Paths ---
ROOT = Path(__file__).parent.parent
TOOLS = ROOT / "tools"
TMP = ROOT / "projects" / "eps" / ".tmp"
E1_DIR = TMP / "estimateone"
DOCS_DIR = E1_DIR / "docs"
BRIEFS_DIR = E1_DIR / "briefs"
LATEST = E1_DIR / "e1_latest.json"

# EPS trades we care about
EPS_TRADES = ["Painting", "Building Cleaning"]

# Pipeline IDs
PIPELINE_CLEAN = 3
PIPELINE_PAINT = 4
STAGE_QUOTE_IN_PROGRESS_CLEAN = 31
STAGE_QUOTE_IN_PROGRESS_PAINT = 35


def run_cmd(cmd, dry_run=False):
    """Run a command and return (success, stdout)."""
    print(f"  $ {' '.join(cmd)}")
    if dry_run:
        print("    [DRY RUN — skipped]")
        return True, ""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr[:500]}")
            return False, result.stderr
        return True, result.stdout
    except subprocess.TimeoutExpired:
        print("    ERROR: Command timed out (300s)")
        return False, "timeout"
    except Exception as e:
        print(f"    ERROR: {e}")
        return False, str(e)


def step_scrape(args):
    """Step 1: Scrape E1 with trade filter."""
    print("\n=== STEP 1: SCRAPE E1 ===")

    cmd = [
        "python3", str(TOOLS / "estimateone_scraper.py"),
        "--leads", "--open",
        "--filter-trades", ",".join(EPS_TRADES),
    ]
    if args.download_docs:
        cmd.append("--download-docs")
        cmd.append("--auto-express-interest")
    if not args.headless:
        cmd.append("--no-headless")

    ok, output = run_cmd(cmd, args.dry_run)
    if not ok:
        print("  Scrape failed. Check logs.")
        return False

    print("  Scrape complete.")
    return True


def step_analyze(args, project_ids=None):
    """Step 2: Analyze downloaded docs."""
    print("\n=== STEP 2: ANALYZE SPECS ===")

    if not DOCS_DIR.exists():
        print("  No docs directory — nothing to analyze.")
        return []

    # Find projects with downloaded docs but no brief yet
    briefs = []
    for proj_dir in sorted(DOCS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        pid = proj_dir.name
        if project_ids and pid not in project_ids:
            continue

        brief_file = BRIEFS_DIR / f"{pid}_brief.json"
        if brief_file.exists() and not args.force:
            print(f"  #{pid}: brief exists, skipping (use --force to re-analyze)")
            briefs.append(json.loads(brief_file.read_text()))
            continue

        has_docs = any(f.suffix.lower() == ".pdf" for f in proj_dir.iterdir())
        if not has_docs:
            print(f"  #{pid}: no PDFs found, skipping")
            continue

        print(f"  #{pid}: analyzing...")
        cmd = ["python3", str(TOOLS / "analyze_tender_docs.py"), "--project-id", pid]
        ok, output = run_cmd(cmd, args.dry_run)
        if ok and brief_file.exists():
            briefs.append(json.loads(brief_file.read_text()))
        elif ok and args.dry_run:
            briefs.append({"project_id": pid, "dry_run": True})

    print(f"  Analyzed: {len(briefs)} tenders")
    return briefs


def step_crm(args, briefs=None):
    """Step 3: Create Pipedrive CRM records from briefs."""
    print("\n=== STEP 3: CREATE CRM RECORDS ===")

    if not briefs:
        # Load briefs from disk
        briefs = []
        if BRIEFS_DIR.exists():
            for bf in sorted(BRIEFS_DIR.glob("*_brief.json")):
                briefs.append(json.loads(bf.read_text()))

    if not briefs:
        print("  No briefs to process.")
        return []

    # Load latest scrape for builder/contact info
    e1_data = {}
    if LATEST.exists():
        data = json.loads(LATEST.read_text())
        sections = data.get("sections", {})
        for section in ["leads", "open_tenders"]:
            for tender in sections.get(section, []):
                pid = tender.get("project_id", "").replace("#", "")
                if pid:
                    e1_data[pid] = tender

    created = []
    for brief in briefs:
        pid = brief.get("project_id", "")
        pname = brief.get("project_name", f"Project #{pid}")
        trades = brief.get("trades_required", [])

        if not trades:
            print(f"  #{pid}: no trades identified, skipping CRM")
            continue

        # Get builder info from E1 data
        e1_info = e1_data.get(pid, {})
        builder = e1_info.get("builder", "")
        contact = e1_info.get("contact", {})

        if not builder:
            print(f"  #{pid}: no builder info, skipping CRM")
            continue

        print(f"  #{pid} ({pname}): {builder} — trades: {', '.join(trades)}")

        # Create org
        cmd = [
            "python3", str(TOOLS / "pipedrive_create.py"),
            "--action", "create-org",
            "--name", builder,
            "--address", "Brisbane QLD",
        ]
        ok, output = run_cmd(cmd, args.dry_run)
        org_id = None
        if ok and not args.dry_run:
            try:
                result = json.loads(output)
                org_id = result.get("id")
                print(f"    Org: {builder} (ID: {org_id}, new: {result.get('created', '?')})")
            except json.JSONDecodeError:
                print(f"    WARNING: Could not parse org creation output")

        # Create person if contact info available
        person_id = None
        contact_name = contact.get("name", "")
        contact_email = contact.get("email", "")
        contact_phone = contact.get("phone", "")

        if org_id and (contact_name or contact_email):
            cmd = [
                "python3", str(TOOLS / "pipedrive_create.py"),
                "--action", "create-person",
                "--name", contact_name or f"{builder} Contact",
                "--org-id", str(org_id),
            ]
            if contact_email:
                cmd.extend(["--email", contact_email])
            if contact_phone:
                cmd.extend(["--phone", contact_phone])

            ok, output = run_cmd(cmd, args.dry_run)
            if ok and not args.dry_run:
                try:
                    result = json.loads(output)
                    person_id = result.get("id")
                except json.JSONDecodeError:
                    pass

        # Create deal per trade
        for trade in trades:
            trade_lower = trade.lower()
            if "paint" in trade_lower or "coating" in trade_lower or "render" in trade_lower:
                pipeline_id = PIPELINE_PAINT
                stage_id = STAGE_QUOTE_IN_PROGRESS_PAINT
                deal_title = f"{pname} - Painting"
            elif "clean" in trade_lower:
                pipeline_id = PIPELINE_CLEAN
                stage_id = STAGE_QUOTE_IN_PROGRESS_CLEAN
                deal_title = f"{pname} - Cleaning"
            else:
                print(f"    Skipping trade '{trade}' — not painting or cleaning")
                continue

            cmd = [
                "python3", str(TOOLS / "pipedrive_create.py"),
                "--action", "create-deal",
                "--title", deal_title,
                "--pipeline-id", str(pipeline_id),
                "--stage-id", str(stage_id),
            ]
            if org_id:
                cmd.extend(["--org-id", str(org_id)])

            ok, output = run_cmd(cmd, args.dry_run)
            if ok and not args.dry_run:
                try:
                    result = json.loads(output)
                    deal_id = result.get("id")
                    print(f"    Deal: {deal_title} (ID: {deal_id})")
                    created.append({
                        "project_id": pid,
                        "deal_id": deal_id,
                        "deal_title": deal_title,
                        "pipeline_id": pipeline_id,
                        "org_id": org_id,
                    })
                except json.JSONDecodeError:
                    pass

    print(f"  CRM records created: {len(created)} deals")
    return created


def step_sheet(args):
    """Step 4: Push to Google Sheet."""
    print("\n=== STEP 4: PUSH TO SHEET ===")

    cmd = ["python3", str(TOOLS / "e1_to_sheet.py")]
    ok, output = run_cmd(cmd, args.dry_run)
    if ok:
        print("  Sheet updated.")
    return ok


def step_report(args):
    """Step 5: Generate summary report."""
    print("\n=== REPORT ===")

    if not LATEST.exists():
        print("  No scrape data to report on.")
        return

    data = json.loads(LATEST.read_text())
    sections = data.get("sections", {})
    ts = data.get("scraped_at", "unknown")

    leads = sections.get("leads", [])
    open_t = sections.get("open_tenders", [])

    # Count leads with painting/cleaning packages
    relevant_leads = [l for l in leads if any(
        t.lower() in l.get("package", "").lower()
        for t in ["paint", "clean"]
    )]

    # Count briefs
    brief_count = len(list(BRIEFS_DIR.glob("*_brief.json"))) if BRIEFS_DIR.exists() else 0

    print(f"\n{'='*50}")
    print(f"  EPS TENDER REPORT — {ts}")
    print(f"{'='*50}")
    print(f"  Leads (invited):     {len(leads)} total, {len(relevant_leads)} painting/cleaning")
    print(f"  Open tenders:        {len(open_t)} (filtered by trades)")
    print(f"  Briefs generated:    {brief_count}")
    print(f"{'='*50}")

    if relevant_leads:
        print(f"\n  Relevant leads:")
        for l in relevant_leads:
            print(f"    #{l.get('project_id', '?')} | {l.get('project', '?')} | {l.get('builder', '?')} | {l.get('package', '?')}")


def main():
    parser = argparse.ArgumentParser(description="EPS Tender Campaign — Daily Batch")
    parser.add_argument("--scrape-only", action="store_true", help="Just scrape, no CRM/analysis")
    parser.add_argument("--analyze-only", action="store_true", help="Analyze already-downloaded docs")
    parser.add_argument("--crm-only", action="store_true", help="Create CRM records from existing briefs")
    parser.add_argument("--project-ids", type=str, default="",
                        help="Comma-separated project IDs to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, no changes")
    parser.add_argument("--force", action="store_true", help="Force re-analyze existing briefs")
    parser.add_argument("--download-docs", action="store_true", default=True,
                        help="Download tender documents (default: on)")
    parser.add_argument("--no-download-docs", action="store_false", dest="download_docs",
                        help="Skip doc download")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    project_ids = [p.strip().replace("#", "") for p in args.project_ids.split(",") if p.strip()] if args.project_ids else None

    print(f"EPS Tender Batch — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if args.dry_run:
        print("*** DRY RUN — no changes will be made ***")

    if args.scrape_only:
        step_scrape(args)
        step_report(args)
        return

    if args.analyze_only:
        step_analyze(args, project_ids)
        return

    if args.crm_only:
        step_crm(args)
        return

    # Full pipeline
    if step_scrape(args):
        briefs = step_analyze(args, project_ids)
        if briefs:
            step_crm(args, briefs)
        step_sheet(args)
    step_report(args)


if __name__ == "__main__":
    main()
