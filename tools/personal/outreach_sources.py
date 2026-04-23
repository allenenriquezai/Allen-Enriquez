"""
outreach_sources.py — Prospect discovery sources for the PH outbound pipeline.

Imported by tools/outreach.py. Each discover_* function returns a list of
prospect dicts matching the Prospects sheet schema. All network calls are
wrapped in try/except so a single failing source never crashes a discovery run.

Sources:
    discover_google_places  — Google Places API (New) text search
    discover_businesslist   — BusinessList.ph category pages (Playwright)
    discover_jobstreet      — JobStreet PH job search -> company (requests+bs4 or Playwright)
    discover_kalibrr        — Kalibrr job search -> company (requests+bs4 or Playwright)
    discover_fb_inbox       — Plaintext FB prospect inbox (Allen hand-curated)

Plus dedupe_prospects(new, existing) to filter against the Sheet.

Rate limits (polite by default):
    - Google Places:   no explicit sleep; API-rate-limited on Google's side.
    - BusinessList.ph: 1.5s between pages.
    - JobStreet:       2s between requests, max 3 pages per term.
    - Kalibrr:         2s between requests, max 3 pages per term.
    - FB inbox:        file read only, no network.

Dependencies: requests, beautifulsoup4 (optional, graceful fallback),
playwright (optional, graceful fallback). All already in the repo's env.
"""

from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

PH_TZ = timezone(timedelta(hours=8))

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


def _today_ph() -> str:
    return datetime.now(PH_TZ).strftime("%Y-%m-%d")


def _blank_prospect(segment: str, source: str, tier: str = "2") -> dict:
    return {
        "Date Added": _today_ph(),
        "Name": "",
        "Company": "",
        "Platform": "Web",
        "Profile URL": "",
        "Website": "",
        "Email": "",
        "Phone": "",
        "FB URL": "",
        "IG URL": "",
        "Segment": segment,
        "Tier": tier,
        "Status": "new",
        "Source": source,
    }


def _normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip().rstrip("/")
    if not u:
        return ""
    if not u.lower().startswith(("http://", "https://")):
        u = "https://" + u
    return u.lower()


def _normalize_company(c: str) -> str:
    if not c:
        return ""
    c = c.strip().lower()
    c = re.sub(r"\s+", " ", c)
    c = re.sub(r"[\.,]", "", c)
    for suf in (" inc", " corp", " corporation", " ltd", " llc", " co", " company"):
        if c.endswith(suf):
            c = c[: -len(suf)].strip()
    return c


# ============================================================
# Google Places API (New)
# ============================================================

def discover_google_places(
    api_key: str,
    queries: list[str],
    segment: str,
    limit: int = 50,
) -> list[dict]:
    """Query Google Places API (New) Text Search and return prospect dicts.

    Uses POST https://places.googleapis.com/v1/places:searchText with a field
    mask limiting the response to what we need (keeps cost down).

    Rate limit: Google enforces quota server-side. No explicit sleep added.
    Returns []: if api_key is empty, requests missing, or all calls fail.
    """
    if not api_key:
        print("[places] GOOGLE_PLACES_API_KEY empty — skipping.")
        return []
    try:
        import requests
    except ImportError:
        print("[places] 'requests' not installed — skipping.")
        return []

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.websiteUri,"
            "places.internationalPhoneNumber,places.id"
        ),
    }

    out: list[dict] = []
    seen_place_ids: set[str] = set()
    for q in queries:
        if len(out) >= limit:
            break
        try:
            resp = requests.post(
                url, headers=headers, json={"textQuery": q}, timeout=20
            )
            if resp.status_code != 200:
                print(f"[places] HTTP {resp.status_code} for {q!r}: {resp.text[:200]}")
                continue
            data = resp.json()
        except Exception as e:
            print(f"[places] error on {q!r}: {e}")
            continue

        for place in data.get("places", []):
            if len(out) >= limit:
                break
            pid = place.get("id", "")
            if not pid or pid in seen_place_ids:
                continue
            seen_place_ids.add(pid)

            name = place.get("displayName", {}).get("text", "") if isinstance(
                place.get("displayName"), dict
            ) else str(place.get("displayName", ""))
            website = place.get("websiteUri", "") or ""
            phone = place.get("internationalPhoneNumber", "") or ""

            p = _blank_prospect(segment, "google_places")
            p["Company"] = name
            p["Name"] = name
            p["Website"] = website
            p["Phone"] = phone
            p["Profile URL"] = f"https://www.google.com/maps/place/?q=place_id:{pid}"
            out.append(p)

    print(f"[places] {len(out)} prospects from {len(queries)} queries.")
    return out


# ============================================================
# BusinessList.ph (Playwright)
# ============================================================

CATEGORY_MAP = {
    "recruitment": "recruitment-agencies",
    "real_estate": "real-estate-agents",
}
DEFAULT_CITIES = ["manila", "cebu", "quezon-city", "makati", "davao"]


def discover_businesslist(
    categories: list[str],
    cities: list[str],
    segment: str,
    limit: int = 50,
) -> list[dict]:
    """Scrape BusinessList.ph category+city pages via Playwright.

    URL: https://www.businesslist.ph/category/<category>/<city>
    categories: list of canonical keys e.g. ['recruitment']. Mapped via
        CATEGORY_MAP. Unmapped values are passed through unchanged (so callers
        can supply raw slugs directly if needed).
    cities: city slugs (e.g. 'manila'). Defaults used if empty.

    Rate limit: 1.5s between page navigations. User-agent rotated per page.
    Returns []: if Playwright not installed.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("[businesslist] Playwright not installed — skipping. pip install playwright && playwright install chromium")
        return []

    if not cities:
        cities = DEFAULT_CITIES
    slugs = [CATEGORY_MAP.get(c, c) for c in categories]

    out: list[dict] = []
    seen_keys: set[str] = set()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for slug in slugs:
                    if len(out) >= limit:
                        break
                    for city in cities:
                        if len(out) >= limit:
                            break
                        url = f"https://www.businesslist.ph/category/{slug}/{city}"
                        ctx = browser.new_context(
                            user_agent=random.choice(USER_AGENTS),
                            viewport={"width": 1366, "height": 900},
                        )
                        page = ctx.new_page()
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=20000)
                            time.sleep(1.5)
                            # BusinessList renders results in .company blocks; be
                            # defensive across layout variants.
                            cards = page.query_selector_all(
                                ".company, .company_list .company, .companyList .item"
                            )
                            for card in cards:
                                if len(out) >= limit:
                                    break
                                name = ""
                                website = ""
                                phone = ""
                                addr = ""
                                profile_url = ""

                                h_el = card.query_selector("h3 a, h2 a, .name a, a.name")
                                if h_el:
                                    name = (h_el.inner_text() or "").strip()
                                    href = h_el.get_attribute("href") or ""
                                    if href:
                                        profile_url = urljoin(url, href)

                                phone_el = card.query_selector(".phone, .tel, [class*='phone']")
                                if phone_el:
                                    phone = (phone_el.inner_text() or "").strip()

                                addr_el = card.query_selector(".address, .adr, [class*='address']")
                                if addr_el:
                                    addr = (addr_el.inner_text() or "").strip()

                                web_el = card.query_selector("a.website, a[href^='http']:not([href*='businesslist.ph'])")
                                if web_el:
                                    website = (web_el.get_attribute("href") or "").strip()

                                if not name:
                                    continue
                                key = _normalize_company(name)
                                if key in seen_keys:
                                    continue
                                seen_keys.add(key)

                                p = _blank_prospect(segment, "businesslist")
                                p["Company"] = name
                                p["Name"] = name
                                p["Website"] = website
                                p["Phone"] = phone
                                p["Profile URL"] = profile_url
                                if addr:
                                    p["_address"] = addr
                                out.append(p)
                        except PWTimeout:
                            print(f"[businesslist] timeout on {url}")
                        except Exception as e:
                            print(f"[businesslist] error on {url}: {e}")
                        finally:
                            ctx.close()
                        time.sleep(1.5)
            finally:
                browser.close()
    except Exception as e:
        print(f"[businesslist] fatal: {e}")

    print(f"[businesslist] {len(out)} prospects.")
    return out


# ============================================================
# HTTP helper for JobStreet + Kalibrr
# ============================================================

def _get_html(url: str, timeout: int = 15):
    """Polite GET returning (status_code, text) or (None, None) on error."""
    try:
        import requests
    except ImportError:
        return None, None
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        print(f"[http] error on {url}: {e}")
        return None, None


# ============================================================
# JobStreet PH
# ============================================================

def discover_jobstreet(
    search_terms: list[str],
    segment: str,
    limit: int = 50,
) -> list[dict]:
    """Scrape JobStreet PH job search results for hiring companies.

    URL: https://www.jobstreet.com.ph/jobs?keywords=<term>&page=<n>
    Hiring = budget signal, so Source = 'jobstreet_hiring'.

    Rate limit: 2s between requests, max 3 pages per term.
    Selectors may drift — if company name extraction fails, function returns
    fewer results rather than crashing.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[jobstreet] beautifulsoup4 not installed — skipping.")
        return []

    out: list[dict] = []
    seen_keys: set[str] = set()

    for term in search_terms:
        if len(out) >= limit:
            break
        for page in range(1, 4):
            if len(out) >= limit:
                break
            url = f"https://www.jobstreet.com.ph/jobs?keywords={quote_plus(term)}&page={page}"
            status, html = _get_html(url)
            time.sleep(2.0)
            if not html or status != 200:
                if status:
                    print(f"[jobstreet] HTTP {status} page {page} for {term!r}")
                continue
            try:
                soup = BeautifulSoup(html, "html.parser")
            except Exception as e:
                print(f"[jobstreet] parse error: {e}")
                continue

            # JobStreet renders job cards with data-automation attributes.
            company_nodes = soup.select("[data-automation='jobCompany'], a[data-automation='jobCompany']")
            for node in company_nodes:
                if len(out) >= limit:
                    break
                name = node.get_text(strip=True)
                if not name:
                    continue
                key = _normalize_company(name)
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)

                href = node.get("href", "") or ""
                profile_url = urljoin("https://www.jobstreet.com.ph", href) if href else ""

                p = _blank_prospect(segment, "jobstreet_hiring")
                p["Company"] = name
                p["Name"] = name
                p["Profile URL"] = profile_url
                out.append(p)

    print(f"[jobstreet] {len(out)} prospects from {len(search_terms)} terms.")
    return out


# ============================================================
# Kalibrr
# ============================================================

def discover_kalibrr(
    search_terms: list[str],
    segment: str,
    limit: int = 50,
) -> list[dict]:
    """Scrape Kalibrr job search results for hiring companies.

    URL: https://www.kalibrr.com/home/te/<term>
    Rate limit: 2s between requests, max 3 pages per term.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[kalibrr] beautifulsoup4 not installed — skipping.")
        return []

    out: list[dict] = []
    seen_keys: set[str] = set()

    for term in search_terms:
        if len(out) >= limit:
            break
        slug = quote_plus(term.strip().replace(" ", "-"))
        for page in range(1, 4):
            if len(out) >= limit:
                break
            url = f"https://www.kalibrr.com/home/te/{slug}/{page}" if page > 1 else f"https://www.kalibrr.com/home/te/{slug}"
            status, html = _get_html(url)
            time.sleep(2.0)
            if not html or status != 200:
                if status:
                    print(f"[kalibrr] HTTP {status} page {page} for {term!r}")
                continue
            try:
                soup = BeautifulSoup(html, "html.parser")
            except Exception as e:
                print(f"[kalibrr] parse error: {e}")
                continue

            # Kalibrr job cards link to /c/<company-slug>/jobs/... — harvest the
            # company slug and title from those anchors.
            for a in soup.find_all("a", href=True):
                if len(out) >= limit:
                    break
                href = a["href"]
                m = re.match(r"^/c/([^/]+)/jobs/", href)
                if not m:
                    continue
                slug_c = m.group(1)
                # Look for a sibling/ancestor node with the company display name.
                name_node = a.find(attrs={"class": re.compile("company", re.I)})
                name = name_node.get_text(strip=True) if name_node else slug_c.replace("-", " ").title()
                if not name:
                    continue
                key = _normalize_company(name)
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)

                p = _blank_prospect(segment, "kalibrr")
                p["Company"] = name
                p["Name"] = name
                p["Profile URL"] = f"https://www.kalibrr.com/c/{slug_c}"
                out.append(p)

    print(f"[kalibrr] {len(out)} prospects from {len(search_terms)} terms.")
    return out


# ============================================================
# FB prospect inbox (hand-curated by Allen -> Tier 1)
# ============================================================

_FB_META_RE = re.compile(r"\|\s*(Segment|Note)\s*:\s*([^|]+)", re.I)


def discover_fb_inbox(
    inbox_file: Path,
    segment_default: str = "unknown",
) -> list[dict]:
    """Parse Allen's plaintext FB prospect inbox.

    Each non-empty, non-comment line is one prospect. Formats:
        https://facebook.com/someone
        https://facebook.com/someone | Segment: recruitment | Note: saw in VA Training PH

    These are hand-curated — Tier='1'. After successful read, the file is
    renamed to <name>.processed.YYYY-MM-DD.txt so the same lines aren't
    re-ingested on the next run. The original path is left empty (caller
    may recreate it).
    """
    inbox_file = Path(inbox_file)
    if not inbox_file.exists():
        print(f"[fb_inbox] no inbox at {inbox_file} — skipping.")
        return []

    out: list[dict] = []
    try:
        lines = inbox_file.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        print(f"[fb_inbox] read error: {e}")
        return []

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        url_part = line.split("|", 1)[0].strip()
        if not url_part.lower().startswith(("http://", "https://")):
            url_part = "https://" + url_part

        seg = segment_default
        note = ""
        for key, val in _FB_META_RE.findall(line):
            if key.lower() == "segment":
                seg = val.strip().lower().replace(" ", "_") or segment_default
            elif key.lower() == "note":
                note = val.strip()

        # Derive a display name from the URL path when no explicit name given.
        try:
            path = urlparse(url_part).path.strip("/")
            name_guess = path.split("/")[0].replace(".", " ").replace("-", " ").title() if path else ""
        except Exception:
            name_guess = ""

        p = _blank_prospect(seg, "fb_inbox", tier="1")
        p["Platform"] = "Facebook"
        p["FB URL"] = url_part
        p["Profile URL"] = url_part
        p["Name"] = name_guess
        if note:
            p["_note"] = note
        out.append(p)

    # Archive the file so we don't re-ingest. Don't delete — Allen's rule.
    if out:
        try:
            stamp = _today_ph()
            archived = inbox_file.with_name(
                f"{inbox_file.stem}.processed.{stamp}{inbox_file.suffix}"
            )
            # If an archive for today already exists, append a counter.
            i = 2
            while archived.exists():
                archived = inbox_file.with_name(
                    f"{inbox_file.stem}.processed.{stamp}.{i}{inbox_file.suffix}"
                )
                i += 1
            inbox_file.rename(archived)
        except Exception as e:
            print(f"[fb_inbox] archive rename failed: {e}")

    print(f"[fb_inbox] {len(out)} prospects.")
    return out


# ============================================================
# Dedupe
# ============================================================

def dedupe_prospects(new: list[dict], existing_rows: list[dict]) -> list[dict]:
    """Return prospects from `new` that don't match anything in `existing_rows`.

    Match keys: normalized Company OR normalized Website OR FB URL. Any one
    match means the prospect is considered a duplicate and dropped.
    Also dedupes `new` against itself.
    """
    existing_companies: set[str] = set()
    existing_websites: set[str] = set()
    existing_fb: set[str] = set()

    for row in existing_rows or []:
        c = _normalize_company(row.get("Company", ""))
        if c:
            existing_companies.add(c)
        w = _normalize_url(row.get("Website", ""))
        if w:
            existing_websites.add(w)
        fb = _normalize_url(row.get("FB URL", ""))
        if fb:
            existing_fb.add(fb)

    kept: list[dict] = []
    for p in new:
        c = _normalize_company(p.get("Company", ""))
        w = _normalize_url(p.get("Website", ""))
        fb = _normalize_url(p.get("FB URL", ""))

        if c and c in existing_companies:
            continue
        if w and w in existing_websites:
            continue
        if fb and fb in existing_fb:
            continue

        if c:
            existing_companies.add(c)
        if w:
            existing_websites.add(w)
        if fb:
            existing_fb.add(fb)
        kept.append(p)

    return kept
