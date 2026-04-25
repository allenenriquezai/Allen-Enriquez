"""
estimateone_scraper.py — Scrape EstimateOne for tenders and leads.

Uses Playwright (Chromium) to log in and extract data from app.estimateone.com (login: /auth/login).
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
ENV_PATH = Path(__file__).parent.parent.parent / "projects" / "eps" / ".env"
BASE_URL = "https://app.estimateone.com"
DELAY_MIN = 0.5
DELAY_MAX = 1.5
COOKIE_PATH = Path(__file__).parent.parent.parent / "projects" / "eps" / ".tmp" / "e1_cookies.json"
OUT_DIR = Path(__file__).parent.parent.parent / "projects" / "eps" / ".tmp" / "estimateone"

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
        if "/auth/login" not in page.url and "/login" not in page.url:
            print("Resumed E1 session from cookies")
            return

    print("Logging in...")
    page.goto(f"{BASE_URL}/auth/login", wait_until="domcontentloaded", timeout=20000)
    throttle()
    page.wait_for_selector("input[type='email'], input[name='email']", timeout=20000)
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
        page.wait_for_url(lambda u: "/auth/login" not in u and "/login" not in u, timeout=20000)
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

def apply_trade_filter(page, trades):
    """Apply trade filter on find-tenders page.

    Clicks the Trades filter dropdown, selects specified trades (e.g. Painting,
    Building Cleaning), and waits for results to reload.

    Args:
        trades: list of trade names to filter by (e.g. ["Painting", "Building Cleaning"])
    """
    if not trades:
        return

    print(f"  Applying trade filter: {', '.join(trades)}")

    # Strategy 1: Click the "Trades" filter button/dropdown
    filter_btn = None
    for sel in [
        "button:has-text('Trades')",
        "a:has-text('Trades')",
        "[class*='filter']:has-text('Trades')",
        "div:has-text('Trades') >> visible=true",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                filter_btn = el
                break
        except Exception:
            continue

    if not filter_btn:
        print("    WARNING: Could not find Trades filter button — scraping unfiltered")
        screenshot(page, "trade_filter_not_found")
        return

    filter_btn.click()
    throttle()
    screenshot(page, "trade_filter_opened")

    # Select each trade from the dropdown/checkbox list
    selected = 0
    for trade in trades:
        for sel in [
            f"label:has-text('{trade}')",
            f"span:has-text('{trade}')",
            f"li:has-text('{trade}')",
            f"div:has-text('{trade}') >> visible=true",
            f"input[value='{trade}']",
            f"[class*='option']:has-text('{trade}')",
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    selected += 1
                    throttle(0.3)
                    break
            except Exception:
                continue

    if selected == 0:
        print("    WARNING: Could not select any trades — try --no-headless to debug")
        screenshot(page, "trade_filter_no_selection")
        return

    # Apply / close the filter (some UIs need a confirm click)
    for sel in [
        "button:has-text('Apply')",
        "button:has-text('Done')",
        "button:has-text('OK')",
    ]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                break
        except Exception:
            continue

    # Wait for results to reload
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeout:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    throttle()

    print(f"    Trade filter applied: {selected}/{len(trades)} trades selected")
    screenshot(page, "trade_filter_applied")


def scrape_find_tenders(page, tab="Open", max_pages=20, filter_trades=None):
    """Scrape find-tenders page for Open or Awarded tenders.

    Args:
        filter_trades: optional list of trade names to filter by
                       (e.g. ["Painting", "Building Cleaning"])
    """
    print(f"Scraping find-tenders [{tab}]...")
    page.goto(f"{BASE_URL}/find-tenders", wait_until="domcontentloaded", timeout=20000)
    throttle()

    # Click tab
    tab_el = page.query_selector(f"a:has-text('{tab}'), button:has-text('{tab}')")
    if tab_el:
        tab_el.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        throttle()

    # Reset E1 session filters — E1 persists Trades + Distance across sessions,
    # which hides 551+ tenders. Must reset before scraping to see full list.
    try:
        reset = page.locator("button:has-text('Reset filters'), a:has-text('Reset filters')").first
        if reset.is_visible(timeout=3000):
            reset.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            throttle(1)
            print("  Filters reset")
    except Exception:
        pass

    # Apply trade filter if specified
    if filter_trades:
        apply_trade_filter(page, filter_trades)

    # Wait for SPA to render — networkidle fires before React finishes painting
    try:
        page.wait_for_selector("[class*='projectLink'], [class*='noResults']", timeout=15000)
    except Exception:
        pass

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

        if not _click_next_page(page):
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
                if km <= 150:
                    filtered.append(t)
            else:
                filtered.append(t)  # Keep if no distance info
        all_tenders = filtered
        removed = before - len(all_tenders)
        if removed:
            print(f"  Filtered out {removed} tenders >150km")

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


# --- Document download ---

DOCS_DIR = OUT_DIR / "docs"


def classify_document(filename):
    """Classify a document by filename."""
    name_lower = filename.lower()
    if any(w in name_lower for w in ("plan", "drawing", "floor", "elevation",
                                      "section", "layout", "architectural")):
        return "plan"
    if any(w in name_lower for w in ("spec", "specification", "schedule",
                                      "scope", "painting spec", "cleaning spec")):
        return "spec"
    return "other"


def scrape_tender_detail(page, project_id, project_name=""):
    """Navigate to a tender/lead detail page and extract documents list.

    Tries multiple strategies to find the detail page:
    1. Click project name link from the current page (if on leads/find-tenders)
    2. Direct URL: {BASE_URL}/tenders/{id}
    3. Direct URL: {BASE_URL}/projects/{id}
    """
    clean_id = project_id.replace("#", "").strip()
    print(f"  Opening detail for #{clean_id} ({project_name})...")

    # Strategy 1: Try clicking project link on current page
    detail_found = False
    link = page.query_selector(f"a:has-text('{project_name}')") if project_name else None
    if not link:
        # Try finding by project ID text
        link = page.query_selector(f"a:has-text('#{clean_id}')")
    if not link:
        # Broader search — any link containing the ID
        links = page.query_selector_all("a[href]")
        for l in links:
            href = l.get_attribute("href") or ""
            if clean_id in href:
                link = l
                break

    if link and link.is_visible():
        href = link.get_attribute("href") or ""
        link.click()
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        throttle()
        detail_found = True
        screenshot(page, f"tender_detail_{clean_id}")

    # Strategy 2: Direct URL attempts
    if not detail_found:
        for url_pattern in [f"/tenders/{clean_id}", f"/projects/{clean_id}",
                            f"/tender/{clean_id}", f"/project/{clean_id}"]:
            try:
                page.goto(f"{BASE_URL}{url_pattern}", wait_until="domcontentloaded", timeout=15000)
                throttle()
                # Check if we landed on an error page
                if "not found" not in page.inner_text("body").lower()[:500]:
                    detail_found = True
                    screenshot(page, f"tender_detail_{clean_id}")
                    break
            except PlaywrightTimeout:
                continue

    if not detail_found:
        print(f"    Could not find detail page for #{clean_id}")
        return {"project_id": clean_id, "detail_url": "", "documents": [],
                "express_interest_required": False, "error": "detail page not found"}

    detail_url = page.url
    print(f"    Detail page: {detail_url}")

    # Check for Express Interest gate
    express_btn = page.query_selector(
        "button:has-text('Express Interest'), a:has-text('Express Interest')"
    )
    express_required = bool(express_btn and express_btn.is_visible())

    # Look for document/download section
    documents = []
    # Try common selectors for document lists
    doc_selectors = [
        "a[href*='download']",
        "a[href*='.pdf']",
        "a[href*='/documents/']",
        "a[href*='/files/']",
        "[class*='document'] a",
        "[class*='file'] a",
        "table a[href]",  # docs might be in a table
    ]

    seen_urls = set()
    for sel in doc_selectors:
        links = page.query_selector_all(sel)
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()
            if not href or href in seen_urls:
                continue
            # Skip navigation links
            if any(skip in href for skip in ("/login", "/leads", "/find-tenders",
                                              "/directory", "/noticeboard", "/watchlist",
                                              "javascript:", "#")):
                continue
            seen_urls.add(href)
            doc_type = classify_document(text or href)
            documents.append({
                "name": text or href.split("/")[-1],
                "download_url": href if href.startswith("http") else f"{BASE_URL}{href}",
                "type": doc_type,
            })

    # Also look for a "Documents" tab/section and click it
    docs_tab = page.query_selector(
        "a:has-text('Documents'), button:has-text('Documents'), "
        "[role='tab']:has-text('Documents'), a:has-text('Docs')"
    )
    if docs_tab and docs_tab.is_visible():
        docs_tab.click()
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        throttle()
        screenshot(page, f"tender_docs_tab_{clean_id}")

        # Re-scan for document links after clicking docs tab
        for sel in doc_selectors:
            links = page.query_selector_all(sel)
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()
                if not href or href in seen_urls:
                    continue
                if any(skip in href for skip in ("/login", "/leads", "/find-tenders",
                                                  "javascript:", "#")):
                    continue
                seen_urls.add(href)
                doc_type = classify_document(text or href)
                documents.append({
                    "name": text or href.split("/")[-1],
                    "download_url": href if href.startswith("http") else f"{BASE_URL}{href}",
                    "type": doc_type,
                })

    # Extract trades from the Trades tab
    trades = []
    trades_tab = page.query_selector(
        "a:has-text('Trades'), button:has-text('Trades'), "
        "[role='tab']:has-text('Trades')"
    )
    if trades_tab and trades_tab.is_visible():
        trades_tab.click()
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        throttle()
        screenshot(page, f"tender_trades_tab_{clean_id}")

        # Look for trade names — E1 shows them as a list with checkmarks for "your trades"
        trades_text = page.inner_text("body")[:5000]
        # Common EPS-relevant trade names
        trade_keywords = [
            "Painting", "Building Cleaning", "Cleaning", "Rendering",
            "Protective Coatings", "Waterproofing", "Floor Coverings",
        ]
        for kw in trade_keywords:
            if kw.lower() in trades_text.lower():
                trades.append(kw)

        # Also try to extract all listed trades
        trade_els = page.query_selector_all("[class*='trade'], [class*='Trade']")
        for el in trade_els:
            t = el.inner_text().strip()
            if t and t not in trades and len(t) < 50:
                trades.append(t)

    if trades:
        print(f"    Trades found: {', '.join(trades)}")

    # Extract contact info if visible
    contact = {}
    body_text = page.inner_text("body")[:3000]
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", body_text)
    if email_match:
        contact["email"] = email_match.group(0)
    phone_match = re.search(r"(?:0[2-9]|(?:\+?61\s?))[0-9\s\-]{7,12}", body_text)
    if phone_match:
        contact["phone"] = phone_match.group(0).strip()

    print(f"    Documents found: {len(documents)}")
    if express_required:
        print(f"    Express Interest required (not clicked)")

    return {
        "project_id": clean_id,
        "detail_url": detail_url,
        "documents": documents,
        "trades": trades,
        "contact": contact,
        "express_interest_required": express_required,
    }


def download_tender_documents(page, project_id, documents, output_dir=None):
    """Download document files from a tender detail page.

    Uses Playwright's download event handling.
    Saves to: projects/eps/.tmp/estimateone/docs/{project_id}/
    """
    clean_id = project_id.replace("#", "").strip()
    docs_dir = output_dir or (DOCS_DIR / clean_id)
    docs_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for doc in documents:
        url = doc.get("download_url", "")
        name = doc.get("name", "unknown")
        if not url:
            continue

        print(f"    Downloading: {name}")
        try:
            # Try clicking the link and catching the download event
            link = page.query_selector(f"a[href='{url}'], a[href*='{url.split('/')[-1]}']")
            if link:
                with page.expect_download(timeout=30000) as download_info:
                    link.click()
                dl = download_info.value
                filename = dl.suggested_filename or f"{name}.pdf"
                local_path = docs_dir / filename
                dl.save_as(str(local_path))
            else:
                # Direct download via page navigation
                with page.expect_download(timeout=30000) as download_info:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                dl = download_info.value
                filename = dl.suggested_filename or f"{name}.pdf"
                local_path = docs_dir / filename
                dl.save_as(str(local_path))

            doc["local_path"] = str(local_path)
            doc["downloaded"] = True
            downloaded.append(doc)
            print(f"      Saved: {local_path}")
            throttle()

        except (PlaywrightTimeout, Exception) as e:
            print(f"      Failed: {e}")
            doc["downloaded"] = False
            doc["error"] = str(e)
            downloaded.append(doc)

    print(f"    Downloaded {sum(1 for d in downloaded if d.get('downloaded'))} / {len(documents)} docs")
    return downloaded


def download_lead_packages(page, leads):
    """Download packages from /leads using E1's RFQ download API.

    Flow:
    1. Navigate to /leads, expand each accordion to find download buttons
    2. Extract rfq_id from button data attributes
    3. Call /rfq/{rfq_id}/download API → get downloadUrl (signed S3 link)
    4. Download zip directly via Playwright

    Saves to: projects/eps/.tmp/estimateone/docs/{project_id}/
    """
    print(f"\nDownloading packages for {len(leads)} leads...")
    page.goto(f"{BASE_URL}/leads", wait_until="domcontentloaded", timeout=20000)
    time.sleep(4)  # JS-heavy page

    # E1 uses section#project-id-XXXXX for each lead
    sections = page.query_selector_all("section[id^='project-id-']")
    print(f"  Lead sections found: {len(sections)}")

    # Build a map of project_id → lead for results
    lead_map = {}
    for lead in leads:
        pid = lead.get("project_id", "").replace("#", "").strip()
        if pid:
            lead_map[pid] = lead

    for section in sections:
        section_id = section.get_attribute("id") or ""
        pid = section_id.replace("project-id-", "")
        if not pid:
            continue

        matched_lead = lead_map.get(pid)
        pname = matched_lead.get("project", f"Project #{pid}") if matched_lead else f"Project #{pid}"

        # Check if already downloaded
        docs_dir = DOCS_DIR / pid
        if docs_dir.exists() and any(docs_dir.iterdir()):
            print(f"  #{pid}: already downloaded, skipping")
            if matched_lead:
                matched_lead["documents"] = [
                    {"name": f.name, "local_path": str(f), "type": classify_document(f.name),
                     "downloaded": True}
                    for f in docs_dir.iterdir() if f.is_file()
                ]
            continue

        # Expand accordion to find download buttons
        toggle = section.query_selector("[class*=accordionToggle], [class*=accordionHeader]")
        if toggle:
            toggle.click(force=True)
            time.sleep(2)

        # Find download buttons WITHIN this section
        download_btns = section.query_selector_all("button[aria-label='Download Package']")
        if not download_btns:
            print(f"  #{pid} ({pname}): no download buttons")
            if matched_lead:
                matched_lead["documents"] = []
            # Collapse
            if toggle:
                toggle.click(force=True)
                time.sleep(0.5)
            continue

        docs_dir.mkdir(parents=True, exist_ok=True)
        downloaded = []

        for btn in download_btns:
            rfq_id = btn.get_attribute("data-rfq-id") or ""
            stage_id = btn.get_attribute("data-stage-id") or ""

            if not rfq_id:
                continue

            print(f"  #{pid}: downloading via API (rfq={rfq_id})")

            try:
                # Call E1's download API to get signed URL
                result = page.evaluate(f"""async () => {{
                    const resp = await fetch('/rfq/{rfq_id}/download');
                    return await resp.json();
                }}""")

                if not result.get("success") or not result.get("downloadUrl"):
                    print(f"    API returned no downloadUrl: {result}")
                    downloaded.append({
                        "name": f"package_{rfq_id}",
                        "rfq_id": rfq_id,
                        "downloaded": False,
                        "error": f"No downloadUrl: {result}",
                    })
                    continue

                download_url = result["downloadUrl"]

                # Download the file using Playwright
                with page.expect_download(timeout=60000) as download_info:
                    page.evaluate(f"""() => {{
                        const a = document.createElement('a');
                        a.href = '{download_url}';
                        a.download = '';
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                    }}""")
                dl = download_info.value
                filename = dl.suggested_filename or f"package_{rfq_id}.zip"
                local_path = docs_dir / filename
                dl.save_as(str(local_path))
                print(f"    Saved: {filename}")
                downloaded.append({
                    "name": filename,
                    "local_path": str(local_path),
                    "rfq_id": rfq_id,
                    "stage_id": stage_id,
                    "downloaded": True,
                })

            except Exception as e:
                print(f"    Download failed: {e}")
                downloaded.append({
                    "name": f"package_{rfq_id}",
                    "rfq_id": rfq_id,
                    "downloaded": False,
                    "error": str(e)[:200],
                })

            throttle()

        if matched_lead:
            matched_lead["documents"] = downloaded

        ok = sum(1 for d in downloaded if d.get("downloaded"))
        print(f"  #{pid}: {ok}/{len(downloaded)} packages downloaded")

        # Collapse before next
        if toggle:
            toggle.click(force=True)
            time.sleep(1)

    return leads


# --- Noticeboard Open tender doc download ---

def _dismiss_modal(page):
    """Dismiss any blocking modal (browser warnings, announcements, etc.)."""
    for sel in [
        "button:has-text('Ok')", "button:has-text('Close')", "button:has-text('Got it')",
        "button:has-text('Continue')", "button:has-text('Dismiss')",
        "button:has-text('Use Anyway')", "button:has-text('Proceed')",
        "[class*='modal'] button", "[class*='Modal'] button", "[role='dialog'] button",
    ]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click()
                throttle(0.5)
                return
        except Exception:
            continue


def _find_project_link(page, pname):
    """Return Playwright locator for the projectLink row matching pname, or None."""
    try:
        loc = page.locator("[class*='projectLink']").filter(has_text=pname[:40]).first
        if loc.is_visible(timeout=2000):
            return loc
    except Exception:
        pass
    return None


def _click_next_page(page):
    """Click the Next Page pagination button. Returns True if clicked."""
    for sel in [
        "[class*='paginationItem']:has-text('Next Page')",
        "button:has-text('Next Page')",
        "a:has-text('Next Page')",
    ]:
        try:
            btn = page.locator(sel).first
            cls = btn.get_attribute("class") or ""
            if btn.is_visible(timeout=2000) and "disabled" not in cls:
                btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                throttle()
                return True
        except Exception:
            continue
    return False


def download_noticeboard_packages(page, tenders, download_docs=False):
    """Express interest + optionally download docs for Open tenders via the find-tenders SPA panel.

    Stays on /find-tenders throughout — panel opens on the right when a project row is clicked.
    Per tender: mark interest via row dropdown → optionally click row to open panel → download docs.

    Args:
        page: Playwright page (logged in)
        tenders: list of tender dicts from scrape_find_tenders (must have project_id, project)
        download_docs: if True, open panel after marking interest and attempt doc download
    """
    if not tenders:
        print("\nNo open tenders to process.")
        return tenders

    print(f"\nProcessing {len(tenders)} open tenders (express interest + docs)...")

    page.goto(f"{BASE_URL}/find-tenders", wait_until="networkidle", timeout=30000)
    throttle(1)
    _dismiss_modal(page)

    # Ensure Open tab + reset all filters so all tenders are visible
    for tab_sel in ["button:has-text('Open')", "a:has-text('Open')", "[role='tab']:has-text('Open')"]:
        try:
            tab = page.locator(tab_sel).first
            if tab.is_visible(timeout=2000):
                tab.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                throttle(0.5)
                break
        except Exception:
            continue

    try:
        reset = page.locator("button:has-text('Reset filters'), a:has-text('Reset filters')").first
        if reset.is_visible(timeout=3000):
            reset.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            throttle(1)
            print("  Filters reset")
    except Exception:
        pass

    interested_count = 0

    for tender in tenders:
        pid = tender.get("project_id", "").replace("#", "").strip()
        pname = tender.get("project", f"Project #{pid}")

        if not pid:
            continue

        if tender.get("interested"):
            print(f"  #{pid}: already marked interested, skipping")
            continue

        print(f"\n  #{pid} — {pname}")

        # Find the row for this tender and paginate if needed
        link = _find_project_link(page, pname)
        if not link:
            page.goto(f"{BASE_URL}/find-tenders", wait_until="networkidle", timeout=30000)
            throttle(1)
            for _ in range(30):
                link = _find_project_link(page, pname)
                if link:
                    break
                if not _click_next_page(page):
                    print(f"    #{pid}: reached last page, not found")
                    break
                throttle(0.5)

        if not link:
            print(f"    #{pid}: not found in noticeboard")
            tender["interested"] = False
            continue

        # Get index of this link in the page, find matching interestLevelDropdown
        marked = False
        try:
            idx = link.evaluate(
                "(el) => Array.from(document.querySelectorAll('[class*=\"projectLink\"]')).indexOf(el)"
            )
            interest_dd = page.locator("[class*='interestLevelDropdown']").nth(idx)
            current_text = interest_dd.inner_text(timeout=2000).strip()
            if current_text.lower() not in ("please select", ""):
                print(f"    Already set: {current_text}")
                marked = True
            else:
                interest_dd.click(force=True)
                throttle(0.5)
                opt = page.locator("[class*='option']:has-text('Interested')").first
                if opt.is_visible(timeout=3000):
                    opt.click(force=True)
                    throttle(0.5)
                    print(f"    Marked Interested")
                    marked = True
                    interested_count += 1
                else:
                    # Try any first option
                    opt = page.locator("[class*='option']").first
                    if opt.is_visible(timeout=2000):
                        opt_text = opt.inner_text().strip()
                        opt.click(force=True)
                        throttle(0.5)
                        print(f"    Set to: {opt_text}")
                        marked = True
                        interested_count += 1
                    else:
                        print(f"    No options in dropdown")
        except Exception as e:
            print(f"    Interest dropdown error: {e}")

        tender["interested"] = marked
        tender["documents"] = []

        if download_docs and marked and link:
            try:
                link.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                throttle(1)

                # Panel is a ReactModal slide-pane — wait for it to render
                downloaded = []
                try:
                    page.wait_for_selector(
                        ".ReactModal__Content, .slide-pane__content, [class*='slide-pane']",
                        timeout=8000
                    )
                    throttle(0.5)

                    # Panel opens on Description tab — switch to Builders & Docs tab
                    for tab_sel in [
                        "button:has-text('Builders & Docs')",
                        "button:has-text('Builders')",
                        "a:has-text('Builders & Docs')",
                        "[role='tab']:has-text('Builders')",
                    ]:
                        tab_btn = page.locator(tab_sel).first
                        try:
                            if tab_btn.is_visible(timeout=2000):
                                tab_btn.click(force=True)
                                page.wait_for_load_state("networkidle", timeout=10000)
                                throttle(0.5)
                                break
                        except Exception:
                            continue

                    # Select a package from the React Select dropdown (options portal to body)
                    try:
                        pkg_dropdown = page.locator(
                            "[class*='slide-pane'] [class*='Select__control'], .ReactModal__Content [class*='Select__control']"
                        ).first
                        if pkg_dropdown.is_visible(timeout=3000):
                            pkg_dropdown.click(force=True)
                            throttle(0.5)
                            # Options portalled to document.body — pick first non-placeholder
                            opts = page.locator("[class*='Select__option']").all()
                            if opts:
                                opts[0].click(force=True)
                                throttle(0.5)
                                print(f"    Package selected")
                    except Exception:
                        pass

                    # Try Download / View buttons
                    for dl_sel in [
                        "button:has-text('Download')",
                        "a:has-text('Download')",
                        "button:has-text('View')",
                        "a:has-text('View')",
                        "[class*='slide-pane'] *:has-text('Download')",
                        ".ReactModal__Content *:has-text('Download')",
                    ]:
                        btns = page.locator(dl_sel).all()
                        for btn in btns:
                            try:
                                if btn.is_visible(timeout=1000):
                                    with page.expect_download(timeout=30000) as dl_info:
                                        btn.click(force=True)
                                    dl = dl_info.value
                                    dest = DOCS_DIR / pid / dl.suggested_filename
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    dl.save_as(str(dest))
                                    downloaded.append({"name": dl.suggested_filename, "local_path": str(dest), "downloaded": True})
                                    print(f"    Downloaded: {dl.suggested_filename}")
                            except Exception:
                                continue
                        if downloaded:
                            break

                    if not downloaded:
                        # Log all panel interactive elements for debugging
                        btns_text = []
                        for el in page.locator(".ReactModal__Content *, [class*='slide-pane'] *").all():
                            try:
                                t = el.inner_text(timeout=200).strip()
                                if t and len(t) < 40 and t not in btns_text:
                                    btns_text.append(t)
                            except Exception:
                                pass
                        print(f"    Panel elements: {btns_text[:15]}")

                except Exception as e:
                    print(f"    Panel error: {e}")

                if not downloaded:
                    screenshot(page, f"panel_open_{pid}")
                    print(f"    No packages downloaded — screenshot saved")
                tender["documents"] = downloaded
            except Exception as e:
                print(f"    Doc download error: {e}")

        # Close panel
        try:
            page.keyboard.press("Escape")
            throttle(0.3)
        except Exception:
            pass

    print(f"\nNoticeboard complete: {interested_count} marked Interested")
    return tenders


def process_tender_docs(page, tenders, project_ids=None, auto_express=False):
    """Process a list of tenders — navigate to detail page and download docs.

    Args:
        tenders: list of tender dicts from scrape (must have project_id and project fields)
        project_ids: optional list of specific IDs to process (skip others)
        auto_express: if True, click Express Interest on gated tenders
    """
    if project_ids:
        clean_ids = {pid.replace("#", "").strip() for pid in project_ids}
        tenders = [t for t in tenders if t.get("project_id", "").replace("#", "").strip() in clean_ids]

    print(f"\nProcessing {len(tenders)} tenders for doc download...")
    results = []

    for tender in tenders:
        pid = tender.get("project_id", "").replace("#", "").strip()
        pname = tender.get("project", tender.get("title", ""))

        if not pid:
            continue

        # Check if docs already downloaded
        existing_dir = DOCS_DIR / pid
        if existing_dir.exists() and any(existing_dir.iterdir()):
            print(f"  #{pid}: docs already downloaded, skipping")
            tender["documents"] = [
                {"name": f.name, "local_path": str(f), "type": classify_document(f.name),
                 "downloaded": True}
                for f in existing_dir.iterdir() if f.is_file()
            ]
            results.append(tender)
            continue

        detail = scrape_tender_detail(page, pid, pname)

        if detail.get("express_interest_required") and not auto_express:
            print(f"  #{pid}: Express Interest required — skipping (use --auto-express-interest)")
            tender["documents"] = []
            tender["express_interest_required"] = True
            results.append(tender)
            # Navigate back
            page.go_back()
            throttle()
            continue

        if detail.get("documents"):
            docs = download_tender_documents(page, pid, detail["documents"])
            tender["documents"] = docs
        else:
            tender["documents"] = []

        tender["detail_url"] = detail.get("detail_url", "")
        if detail.get("contact"):
            tender["contact"] = detail["contact"]

        results.append(tender)

        # Navigate back to list
        page.go_back()
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        throttle()

    return results


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

            # Parse trade filter
            filter_trades = [t.strip() for t in args.filter_trades.split(",") if t.strip()] if args.filter_trades else None

            if args.open or args.all:
                results["sections"]["open_tenders"] = scrape_find_tenders(page, "Open", args.max_pages, filter_trades=filter_trades)

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

            # Download docs from tender detail pages
            if args.download_docs:
                project_ids = [p.strip() for p in args.project_ids.split(",") if p.strip()] if args.project_ids else None

                # If no sections were scraped this run, load from latest
                if not results["sections"] and project_ids:
                    latest = OUT_DIR / "e1_latest.json"
                    if latest.exists():
                        prev = json.loads(latest.read_text())
                        results["sections"] = prev.get("sections", {})
                        print(f"Loaded sections from previous scrape for doc download")

                # Process leads — use accordion-based download (no detail page nav)
                if "leads" in results["sections"]:
                    results["sections"]["leads"] = download_lead_packages(
                        page, results["sections"]["leads"],
                    )

                # Then open tenders — use Noticeboard package download
                if "open_tenders" in results["sections"]:
                    open_tenders = results["sections"]["open_tenders"]
                    if project_ids:
                        clean_ids = {pid.replace("#", "").strip() for pid in project_ids}
                        open_tenders = [t for t in open_tenders if t.get("project_id", "").replace("#", "").strip() in clean_ids]
                    results["sections"]["open_tenders"] = download_noticeboard_packages(
                        page, open_tenders, download_docs=True,
                    )

                # Fallback — direct detail-page nav for any project_ids not covered above
                if project_ids:
                    clean_ids = {pid.replace("#", "").strip() for pid in project_ids}
                    covered = set()
                    for section in results["sections"].values():
                        if isinstance(section, list):
                            for t in section:
                                covered.add(t.get("project_id", "").replace("#", "").strip())
                    missing = clean_ids - covered
                    if missing:
                        stub_tenders = [{"project_id": pid, "project": f"Project #{pid}"} for pid in missing]
                        print(f"\nDirect detail-page download for: {missing}")
                        results["sections"]["direct"] = process_tender_docs(
                            page, stub_tenders, project_ids=list(missing),
                            auto_express=args.auto_express_interest,
                        )

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
    parser.add_argument("--download-docs", action="store_true",
                        help="Download documents from tender detail pages")
    parser.add_argument("--project-ids", type=str, default="",
                        help="Comma-separated project IDs to download docs for")
    parser.add_argument("--auto-express-interest", action="store_true",
                        help="Auto-click Express Interest on gated tenders")
    parser.add_argument("--filter-trades", type=str, default="",
                        help="Comma-separated trade names to filter open tenders (e.g. 'Painting,Building Cleaning')")
    args = parser.parse_args()

    if not (args.all or args.open or args.awarded or args.leads or args.watchlist
            or args.directory or args.noticeboard or args.download_docs):
        print("Specify: --all, --open, --awarded, --leads, --watchlist, --noticeboard, or --download-docs")
        sys.exit(1)

    run_scraper(args)


if __name__ == "__main__":
    main()
