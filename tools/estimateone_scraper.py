"""
estimateone_scraper.py — Scrape EstimateOne for tenders and leads.

Uses Playwright (Chromium) to log in and extract data from app.estimateone.com.
Outputs structured JSON to projects/eps/.tmp/estimateone/.

Scrape targets:
  - Open tenders: available tenders (app.estimateone.com/find-tenders → Open)
  - Awarded: recently awarded projects (find-tenders → Awarded)
  - Leads: tender invitations sent to EPS (/leads)
  - Watchlist: tenders EPS is tracking (/watchlist)
  - Noticeboard: announcements (/noticeboard)

Usage:
    python tools/estimateone_scraper.py --all
    python tools/estimateone_scraper.py --open
    python tools/estimateone_scraper.py --awarded
    python tools/estimateone_scraper.py --leads --watchlist

Flags:
    --all           Scrape everything
    --open          Open tenders
    --awarded       Awarded projects
    --leads         Tender invitations to EPS
    --watchlist     Tenders EPS is watching
    --noticeboard   Noticeboard
    --headless      Run headless (default). Use --no-headless to see browser.
    --max-pages     Max pagination pages per section (default: 20)
    --output        Output dir (default: projects/eps/.tmp/estimateone)
"""

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# --- Config ---
ENV_PATH = Path(__file__).parent.parent / "projects" / "eps" / ".env"
BASE_URL = "https://app.estimateone.com"
DELAY_MIN = 0.5
DELAY_MAX = 1.5
COOKIE_PATH = Path(__file__).parent.parent / "projects" / "eps" / ".tmp" / "e1_cookies.json"
OUT_DIR = Path(__file__).parent.parent / "projects" / "eps" / ".tmp" / "estimateone"

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CATEGORIES = {
    "Commercial", "Residential", "Civil", "Education", "Refurbishment",
    "Industrial", "Health", "Retail", "Government", "Mixed Use",
    "Hospitality", "Aged Care", "Infrastructure", "Fitout", "Fit-out",
    "Recreation", "Defence",
}


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


_env = load_env()
E1_EMAIL = _env.get("E1_EMAIL", "")
E1_PASSWORD = _env.get("E1_PASSWORD", "")


def throttle(lo=None):
    time.sleep(random.uniform(lo or DELAY_MIN, DELAY_MAX))


def save_cookies(ctx):
    COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_PATH.write_text(json.dumps(ctx.cookies(), indent=2))


def load_cookies(ctx):
    if COOKIE_PATH.exists() and (time.time() - COOKIE_PATH.stat().st_mtime) / 3600 < 12:
        ctx.add_cookies(json.loads(COOKIE_PATH.read_text()))
        return True
    return False


def screenshot(page, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT_DIR / f"debug_{name}.png"))


# --- Login ---

def login(page, ctx):
    if not E1_EMAIL or not E1_PASSWORD or "PLACEHOLDER" in (E1_EMAIL, E1_PASSWORD):
        print("ERROR: Set E1_EMAIL and E1_PASSWORD in projects/eps/.env")
        sys.exit(1)

    if load_cookies(ctx):
        page.goto(f"{BASE_URL}/find-tenders", wait_until="domcontentloaded", timeout=20000)
        throttle()
        if "/login" not in page.url:
            print("Resumed E1 session from cookies")
            return

    print("Logging in...")
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=20000)
    throttle()
    page.wait_for_selector("input[type='email'], input[name='email']", timeout=10000)
    page.fill("input[type='email'], input[name='email']", E1_EMAIL)
    throttle(0.5)
    page.fill("input[type='password'], input[name='password']", E1_PASSWORD)
    throttle(0.5)

    # Wait for submit button to become enabled (E1 validates form first)
    try:
        page.wait_for_selector("button[type='submit']:not([disabled])", timeout=5000)
        page.click("button[type='submit']:not([disabled])")
    except PlaywrightTimeout:
        # Button may auto-submit or we can press Enter
        page.keyboard.press("Enter")

    try:
        page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
    except PlaywrightTimeout:
        screenshot(page, "login_failed")
        print("ERROR: Login failed")
        sys.exit(1)

    page.wait_for_load_state("domcontentloaded", timeout=10000)
    throttle()

    # Dismiss any modal that appears after login (E1 shows announcements)
    try:
        modal_btn = page.wait_for_selector(
            "button:has-text('Ok'), button:has-text('Close'), button:has-text('Got it'), "
            ".modal button, [class*='modal'] button",
            timeout=3000
        )
        if modal_btn and modal_btn.is_visible():
            modal_btn.click()
            throttle(0.5)
    except PlaywrightTimeout:
        pass  # No modal

    save_cookies(ctx)
    print("Login OK")


# --- Text-based tender parser ---

def parse_tender_text(raw_text):
    """Parse the raw text dump of the find-tenders page into structured entries.

    Each tender block in the raw text looks like:
        Project Name
        #ID Address
        $Budget    Distance    Category
        Builder1
        Due Date
        Builder2
        Due Date
        Added Date
        Please Select  (watchlist dropdown)
    """
    # Pre-process: split tab-separated values into separate lines
    expanded = []
    for line in raw_text.split("\n"):
        parts = line.split("\t")
        for part in parts:
            p = part.strip()
            if p:
                expanded.append(p)
    lines = expanded
    tenders = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip navigation, filter, and header lines
        if not line or line in ("", "Prev Page", "Next Page") or "Please Select" in line:
            i += 1
            continue
        if any(skip in line for skip in ("Hawthorne QLD", "Company profile", "Harold Cruz",
                                          "Essential Property", "Noticeboard", "Leads",
                                          "Activity", "Watchlist", "Directory", "Settings",
                                          "Recent Searches", "Open", "Awarded", "Closed",
                                          "Map view", "Budget", "Trades", "Distance",
                                          "Category", "Interest", "more filters",
                                          "Contains a keyword", "Reset filters",
                                          "Displaying results", "are hidden",
                                          "There are", "open tenders",
                                          "Denotes that", "Project\t", "Max Budget",
                                          "Added Within", "Any time", "Quotes Due Within",
                                          "Only Show", "Docs Available", "No Docs")):
            i += 1
            continue

        # Detect a project name — it's a line followed by a line with #ID
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

        # Check if next line starts with a 6-digit project ID (e.g. "182998")
        id_match = re.match(r"^(\d{6})(.*)", next_line)
        if id_match:
            tender = {
                "project": line,
                "project_id": f"#{id_match.group(1)}",
                "address": id_match.group(2).strip(),
                "budget": "",
                "distance": "",
                "category": "",
                "builders": [],
                "quotes_due": "",
                "added": "",
            }
            i += 2  # Skip project name + ID line

            # Now parse remaining fields until we hit the next project or end
            while i < len(lines):
                l = lines[i].strip()
                if not l or "Please Select" in l:
                    i += 1
                    continue

                # Check if this is the start of a new tender (next line has 6-digit ID)
                peek = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if re.match(r"^\d{6}", peek) and l and "$" not in l and "km" not in l.lower():
                    break  # New tender starts here

                # Budget
                if "$" in l and not tender["budget"]:
                    tender["budget"] = l
                    i += 1
                    continue

                # Distance
                km_match = re.search(r"(\d+)\s*km", l, re.IGNORECASE)
                if km_match and not tender["distance"]:
                    tender["distance"] = f"{km_match.group(1)} km"
                    i += 1
                    continue

                # Category
                if l in CATEGORIES and not tender["category"]:
                    tender["category"] = l
                    i += 1
                    continue

                # Date — "28 Apr", "1 May", "10 Apr 26", "in 4 days", "Tomorrow"
                if (any(m in l for m in MONTHS) or l in ("Tomorrow", "Today") or "in " in l and "day" in l):
                    if not tender["quotes_due"]:
                        tender["quotes_due"] = l
                    else:
                        tender["added"] = l
                    i += 1
                    continue

                # Builder name — anything else that's a short text
                if len(l) > 1 and len(l) < 60 and l not in ("Prev Page", "Next Page"):
                    tender["builders"].append(l)
                    i += 1
                    continue

                i += 1

            # Clean up builders — last entries might be dates
            clean_builders = []
            for b in tender["builders"]:
                if any(m in b for m in MONTHS) or b in ("Tomorrow", "Today") or ("in " in b and "day" in b):
                    if not tender["added"]:
                        tender["added"] = b
                else:
                    clean_builders.append(b)
            tender["builders"] = clean_builders
            tender["builder"] = clean_builders[0] if clean_builders else ""

            tenders.append(tender)
        else:
            i += 1

    return tenders


# --- Page scrapers ---

def scrape_find_tenders(page, tab="Open", max_pages=20):
    """Scrape find-tenders page for Open or Awarded tenders."""
    print(f"Scraping find-tenders [{tab}]...")
    page.goto(f"{BASE_URL}/find-tenders", wait_until="domcontentloaded", timeout=20000)
    throttle()

    # Click tab
    tab_el = page.query_selector(f"a:has-text('{tab}'), button:has-text('{tab}')")
    if tab_el:
        tab_el.click()
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        throttle()

    screenshot(page, f"find_tenders_{tab.lower()}")

    all_tenders = []
    for pg in range(1, max_pages + 1):
        # Get raw text from the page body
        raw = page.inner_text("body")
        tenders = parse_tender_text(raw)

        if not tenders:
            if pg == 1:
                print(f"  Page {pg}: 0 tenders parsed — saving raw dump")
                return [{"raw_page": raw[:5000], "note": f"Parser found 0 tenders on {tab} page"}]
            break

        all_tenders.extend(tenders)
        print(f"  Page {pg}: {len(tenders)} tenders")

        # Pagination — E1 uses custom paginationItem elements (not <a> links)
        next_page = pg + 1
        next_link = None
        for sel in [
            f"[class*='paginationItem']:text-is('{next_page}')",
            "[class*='paginationItem']:has-text('Next Page')",
            f"*:text-is('{next_page}')",
            "*:has-text('Next Page')",
        ]:
            candidate = page.query_selector(sel)
            if candidate and candidate.is_visible():
                # Don't click disabled items
                cls = candidate.get_attribute("class") or ""
                if "disabled" not in cls:
                    next_link = candidate
                    break

        if next_link and next_link.is_visible():
            next_link.click()
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            throttle()
        else:
            break

    # Filter out tenders >120km for Open (keep all for Awarded)
    if tab == "Open":
        before = len(all_tenders)
        filtered = []
        for t in all_tenders:
            dist = t.get("distance", "")
            km_match = re.search(r"(\d+)", dist)
            if km_match:
                km = int(km_match.group(1))
                if km <= 120:
                    filtered.append(t)
            else:
                filtered.append(t)  # Keep if no distance info
        all_tenders = filtered
        removed = before - len(all_tenders)
        if removed:
            print(f"  Filtered out {removed} tenders >120km")

    print(f"  Total [{tab}]: {len(all_tenders)}")
    return all_tenders


def parse_leads_text(raw_text):
    """Parse leads page — each lead is a project block + builder sub-table.

    Structure per lead:
        Project Name
        [Awarded project] [Overdue] [Due in X Days]
        #ID • Location • Distance
        Open - Tender
        $Budget
        Category
        Builder | Source | Package | Team Member | Document Status | Quotes Due | Quote Response
        <data row>
        [View other builders]
        [Other builder names]
    """
    lines = []
    for line in raw_text.split("\n"):
        for part in line.split("\t"):
            p = part.strip()
            if p:
                lines.append(p)

    leads = []
    i = 0
    skip_nav = {
        "Hawthorne QLD", "Company profile", "Harold Cruz",
        "Essential Property Solutions Pty Ltd", "Noticeboard", "Activity",
        "Directory", "Settings", "Active", "Submitted", "Archive",
        "All Filters", "Reset", "Expand All", "Collapse All",
        "Leads Sort", "Keywords", "Projects per page", "Builder", "Source",
        "Package", "Team Member", "Document Status", "Quotes Due",
        "Quote Response", "Actions",
    }

    while i < len(lines):
        line = lines[i]

        # Skip nav/header lines
        if line in skip_nav or line.startswith("Track your wins") or line.startswith("Quotes due"):
            i += 1
            continue
        if any(s in line for s in ("views", "Show awarded", "of 8 Project", "of 9 Project",
                                    "Project Leads:", "per page", "Leads 8", "Leads 9",
                                    "Watchlist", "Quote status for", "NEW")):
            i += 1
            continue

        # Detect a lead — look for project ID pattern (#XXXXXX) within next few lines
        found_id = False
        for j in range(i, min(i + 5, len(lines))):
            if re.match(r"^#\d{6}$", lines[j]):
                found_id = True
                break

        if not found_id:
            i += 1
            continue

        lead = {
            "project": line,
            "project_id": "",
            "location": "",
            "distance": "",
            "budget": "",
            "category": "",
            "status": "",
            "builder": "",
            "source": "",
            "package": "",
            "quotes_due": "",
            "quote_response": "",
            "doc_status": "",
            "other_builders": [],
            "flags": [],
        }
        i += 1

        # Parse following lines for this lead
        while i < len(lines):
            l = lines[i]

            # Skip repeated headers
            if l in skip_nav:
                i += 1
                continue

            # Project ID
            if re.match(r"^#\d{6}$", l):
                lead["project_id"] = l
                i += 1
                continue

            # Flags
            if l in ("Awarded project", "Overdue"):
                lead["flags"].append(l)
                i += 1
                continue
            if l.startswith("Due in "):
                lead["flags"].append(l)
                i += 1
                continue

            # Bullet separator (•)
            if l == "•":
                i += 1
                continue

            # Location — suburb + state
            if re.match(r"^[A-Z][a-z].*(QLD|NSW|VIC|SA|WA|TAS|NT|ACT)$", l):
                lead["location"] = l
                i += 1
                continue

            # Distance
            km_match = re.match(r"^(\d+)\s*km$", l)
            if km_match:
                lead["distance"] = f"{km_match.group(1)} km"
                i += 1
                continue

            # Open/Tender status
            if l.startswith("Open -") or l.startswith("Closed"):
                lead["status"] = l
                i += 1
                continue

            # Budget
            if l.startswith("$") and not lead["budget"]:
                lead["budget"] = l
                i += 1
                continue

            # Category
            if l in CATEGORIES or l in ("Industrial (Heavy)",):
                lead["category"] = l
                i += 1
                continue

            # Builder name — after category, before next known pattern
            # Heuristic: it's a company name if it doesn't match other patterns
            if (not lead["builder"] and len(l) > 3 and not l.startswith("$")
                and not l.startswith("#") and "km" not in l
                and l not in ("Current", "Not Accessed", "Out of Date", "Quoted",
                              "Select...", "Invitation", "Noticeboard")
                and not any(m in l for m in MONTHS)
                and "Quote status" not in l and "View other" not in l
                and "Awarded builder" not in l and "Viewed by" not in l):
                lead["builder"] = l
                i += 1
                continue

            # Source
            if l in ("Noticeboard", "Invitation"):
                lead["source"] = l
                i += 1
                continue

            # Package (trade)
            if l in ("Painting", "Cleaning", "Painting & Rendering", "3900 Final Clean"):
                lead["package"] = l
                i += 1
                continue
            # Catch other package names
            if lead["builder"] and not lead["package"] and l not in ("Harold Cruz",) and not any(m in l for m in MONTHS):
                if len(l) < 40 and l not in ("Current", "Not Accessed", "Out of Date"):
                    lead["package"] = l
                    i += 1
                    continue

            # Doc status
            if l in ("Current", "Not Accessed", "Out of Date"):
                lead["doc_status"] = l
                i += 1
                continue

            # Date
            if any(m in l for m in MONTHS):
                if not lead["quotes_due"]:
                    lead["quotes_due"] = l
                i += 1
                continue

            # Quote response
            if l in ("Quoted", "Select..."):
                lead["quote_response"] = l
                i += 1
                continue

            # "Awarded builder" prefix
            if "Awarded builder" in l:
                i += 1
                continue

            # "Viewed by Builder" info
            if "Viewed by" in l:
                lead["flags"].append(l)
                i += 1
                continue

            # "View other builders" + builder list
            if "View other builders" in l:
                i += 1
                # Next line(s) may be other builder names (comma separated)
                while i < len(lines):
                    bl = lines[i]
                    if re.match(r"^#\d{6}$", bl if i + 1 < len(lines) else ""):
                        break
                    # Check if next line could be a new project name
                    peek_id = False
                    for k in range(i, min(i + 5, len(lines))):
                        if re.match(r"^#\d{6}$", lines[k]):
                            peek_id = True
                            break
                    if peek_id and not bl.startswith("$") and "km" not in bl and bl not in CATEGORIES:
                        # Could be next project or builder list
                        # If it contains commas, it's a builder list
                        if "," in bl:
                            lead["other_builders"] = [b.strip() for b in bl.split(",")]
                            i += 1
                        else:
                            break
                    else:
                        if "," in bl and len(bl) > 5:
                            lead["other_builders"] = [b.strip() for b in bl.split(",")]
                            i += 1
                        else:
                            break
                break

            # If we hit a line that looks like the start of a new lead, break
            # (a project name followed by an ID within 5 lines)
            peek_id = False
            for k in range(i + 1, min(i + 5, len(lines))):
                if k < len(lines) and re.match(r"^#\d{6}$", lines[k]):
                    peek_id = True
                    break
            if peek_id:
                break

            i += 1

        leads.append(lead)

    return leads


def scrape_leads(page, max_pages=20):
    """Scrape /leads — tender invitations to EPS."""
    print("Scraping leads...")
    page.goto(f"{BASE_URL}/leads", wait_until="domcontentloaded", timeout=20000)
    time.sleep(4)  # Leads page is JS-heavy
    screenshot(page, "leads")

    raw = page.inner_text("body")
    leads = parse_leads_text(raw)

    if leads:
        print(f"  Leads: {len(leads)}")
        return leads

    # Fallback
    print("  Leads: raw dump")
    return [{"raw_page": raw[:5000], "note": "Leads page — raw dump"}]


def scrape_watchlist(page, max_pages=20):
    """Scrape /watchlist."""
    print("Scraping watchlist...")
    page.goto(f"{BASE_URL}/watchlist", wait_until="domcontentloaded", timeout=20000)
    throttle()
    screenshot(page, "watchlist")

    raw = page.inner_text("body")
    tenders = parse_tender_text(raw)
    if tenders:
        print(f"  Watchlist: {len(tenders)}")
        return tenders

    return [{"raw_page": raw[:5000], "note": "Watchlist — raw dump"}]


def scrape_directory(page, max_pages=20):
    """Scrape /db — builder directory for cold calling campaign.

    Table columns: Builder | Phone | Fax | Location | Dist. | # Current Tenders | # Awarded Tenders
    """
    print("Scraping builder directory...")
    page.goto(f"{BASE_URL}/db", wait_until="domcontentloaded", timeout=20000)
    throttle()

    # Set distance filter to 200km
    dist_select = page.query_selector("select[name='distance']")
    if dist_select:
        page.select_option("select[name='distance']", value="200000")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        throttle()
        print("  Distance filter set to 200km")

    screenshot(page, "directory")

    all_builders = []
    for pg in range(1, max_pages + 1):
        # Parse table rows using DOM — 8 fixed columns per row:
        # [star] [name] [phone] [fax] [location] [distance] [current] [awarded]
        rows = page.query_selector_all("table tbody tr")
        if not rows:
            break

        builders_on_page = []
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 8:
                continue

            texts = [c.inner_text().strip() for c in cells]
            name = texts[1]
            if not name or len(name) < 2:
                continue

            # Get builder detail URL if available
            link = cells[1].query_selector("a[href]")
            url = link.get_attribute("href") if link else ""

            builder = {
                "name": name,
                "phone": texts[2],
                "fax": texts[3],
                "location": texts[4],
                "distance": texts[5],
                "current_tenders": int(texts[6]) if texts[6].isdigit() else 0,
                "awarded_tenders": int(texts[7]) if texts[7].isdigit() else 0,
                "url": url,
            }
            builders_on_page.append(builder)

        if not builders_on_page:
            break

        all_builders.extend(builders_on_page)
        print(f"  Directory page {pg}: {len(builders_on_page)} builders")

        # Pagination — directory uses <a> tags for page numbers
        next_page = pg + 1
        next_link = None
        for sel in [
            f"a:text-is('{next_page}')",
            "a:has-text('Next Page')",
            f"[class*='paginationItem']:text-is('{next_page}')",
            "[class*='paginationItem']:has-text('Next Page')",
        ]:
            candidate = page.query_selector(sel)
            if candidate and candidate.is_visible():
                cls = candidate.get_attribute("class") or ""
                if "disabled" not in cls:
                    next_link = candidate
                    break

        if next_link:
            next_link.click()
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            throttle()
        else:
            break

    # Filter to ≤200km for builder directory (wider net for cold calling)
    before = len(all_builders)
    filtered = []
    for b in all_builders:
        dist = b.get("distance", "")
        km_match = re.search(r"(\d+)", dist)
        if km_match:
            if int(km_match.group(1)) <= 200:
                filtered.append(b)
        else:
            filtered.append(b)
    all_builders = filtered
    removed = before - len(all_builders)
    if removed:
        print(f"  Filtered out {removed} builders >200km")

    print(f"  Total builders: {len(all_builders)}")
    return all_builders


def scrape_noticeboard(page):
    """Scrape /noticeboard."""
    print("Scraping noticeboard...")
    page.goto(f"{BASE_URL}/noticeboard", wait_until="domcontentloaded", timeout=20000)
    throttle()
    screenshot(page, "noticeboard")

    raw = page.inner_text("body")
    return [{"full_text": raw[:5000], "note": "Noticeboard content"}]


# --- Output ---

def save_output(data, filename):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    path.write_text(json.dumps(data, indent=2, default=str))
    print(f"Saved: {path}")


# --- Main ---

def run_scraper(args):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.new_page()

        try:
            login(page, ctx)
            results = {"scraped_at": timestamp, "sections": {}}

            if args.open or args.all:
                results["sections"]["open_tenders"] = scrape_find_tenders(page, "Open", args.max_pages)

            if args.awarded or args.all:
                results["sections"]["awarded"] = scrape_find_tenders(page, "Awarded", args.max_pages)

            if args.leads or args.all:
                results["sections"]["leads"] = scrape_leads(page, args.max_pages)

            if args.watchlist or args.all:
                results["sections"]["watchlist"] = scrape_watchlist(page, args.max_pages)

            if args.directory or args.all:
                results["sections"]["directory"] = scrape_directory(page, args.max_pages)

            if args.noticeboard or args.all:
                results["sections"]["noticeboard"] = scrape_noticeboard(page)

            save_output(results, f"e1_scrape_{timestamp}.json")
            save_output(results, "e1_latest.json")

            counts = {k: len(v) if isinstance(v, list) else 1 for k, v in results["sections"].items()}
            print(f"\nDone. {counts}")
            return results

        except Exception as e:
            print(f"ERROR: {e}")
            screenshot(page, f"error_{timestamp}")
            raise
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="Scrape EstimateOne")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--open", action="store_true", help="Open tenders")
    parser.add_argument("--awarded", action="store_true", help="Awarded projects")
    parser.add_argument("--leads", action="store_true", help="Tender invitations")
    parser.add_argument("--watchlist", action="store_true", help="Watched tenders")
    parser.add_argument("--directory", action="store_true", help="Builder directory")
    parser.add_argument("--noticeboard", action="store_true", help="Noticeboard")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--output", type=str, default="projects/eps/.tmp/estimateone")
    args = parser.parse_args()

    if not (args.all or args.open or args.awarded or args.leads or args.watchlist or args.directory or args.noticeboard):
        print("Specify: --all, --open, --awarded, --leads, --watchlist, or --noticeboard")
        sys.exit(1)

    run_scraper(args)


if __name__ == "__main__":
    main()
