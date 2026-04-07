import asyncio
import csv
import random
import re
from pathlib import Path
from urllib.parse import quote_plus

from playwright.async_api import async_playwright

OUTPUT_PATH = Path.home() / "Desktop" / "bbb_leads_nc.csv"
BASE_URL = "https://www.bbb.org"
SEARCH_TEMPLATE = (
    "https://www.bbb.org/search"
    "?find_country=USA"
    "&find_text=painting+contractors"
    "&find_loc={location}"
    "&page={page}"
)
PAGES_PER_CITY = 15

NC_CITIES = [
    # Charlotte metro
    "Charlotte, NC",
    "Concord, NC",
    "Gastonia, NC",
    "Mooresville, NC",
    "Kannapolis, NC",
    "Monroe, NC",
    "Matthews, NC",
    "Huntersville, NC",
    "Cornelius, NC",
    # Raleigh / Triangle
    "Raleigh, NC",
    "Durham, NC",
    "Cary, NC",
    "Apex, NC",
    "Garner, NC",
    "Wake Forest, NC",
    "Chapel Hill, NC",
    "Clayton, NC",
    # Triad
    "Greensboro, NC",
    "Winston-Salem, NC",
    "High Point, NC",
    "Burlington, NC",
    # Coastal / Eastern NC
    "Wilmington, NC",
    "Jacksonville, NC",
    "Greenville, NC",
    "Rocky Mount, NC",
    "Wilson, NC",
    "Goldsboro, NC",
    "Kinston, NC",
    "New Bern, NC",
    "Lumberton, NC",
    # Western / Mountains
    "Asheville, NC",
    "Hendersonville, NC",
    "Hickory, NC",
    "Statesville, NC",
    # Other
    "Fayetteville, NC",
    "Sanford, NC",
]

FIELDNAMES = [
    "business_name",
    "owner_name",
    "phone",
    "email",
    "address",
    "years_in_business",
    "entity_type",
    "bbb_rating",
    "profile_url",
]


def normalize_url(url: str) -> str:
    """Strip /addressId/XXXXX suffix and return a canonical URL for dedup."""
    return re.sub(r"/addressId/\d+$", "", url.rstrip("/"))


def dedup_key(url: str) -> str:
    """Extract the business slug (last path segment) as a city-agnostic dedup key.

    BBB lists the same business under different city paths:
      /us/nc/charlotte/profile/painting/acme-12345
      /us/nc/raleigh/profile/painting/acme-12345
    Both should map to the same key: 'acme-12345'.
    """
    clean = normalize_url(url)
    return clean.rstrip("/").split("/")[-1] if clean else clean


async def random_delay(min_s=2.0, max_s=5.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def scrape_profile(page, url: str) -> dict:
    """Visit a BBB business profile and extract detailed info."""
    data = {
        "owner_name": "",
        "phone": "",
        "email": "",
        "address": "",
        "years_in_business": "",
        "entity_type": "",
    }
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await random_delay(1.5, 3.5)

        content = await page.content()

        # Phone
        phone_el = await page.query_selector('[data-testid="phone-number"]')
        if not phone_el:
            phone_el = await page.query_selector('a[href^="tel:"]')
        if phone_el:
            data["phone"] = (await phone_el.inner_text()).strip()

        # Email — often hidden behind a mailto link
        email_el = await page.query_selector('a[href^="mailto:"]')
        if email_el:
            href = await email_el.get_attribute("href")
            data["email"] = href.replace("mailto:", "").strip()

        # Address
        addr_el = await page.query_selector('[data-testid="business-address"]')
        if not addr_el:
            addr_el = await page.query_selector("address")
        if addr_el:
            data["address"] = " ".join((await addr_el.inner_text()).split())

        # Details section — years in business, entity type, owner name
        dt_els = await page.query_selector_all("dt")
        dd_els = await page.query_selector_all("dd")
        for dt, dd in zip(dt_els, dd_els):
            label = (await dt.inner_text()).strip().lower()
            value = (await dd.inner_text()).strip()
            if "year" in label and "business" in label:
                data["years_in_business"] = value
            elif "type of entity" in label or "entity type" in label:
                data["entity_type"] = value
            elif "owner" in label or "principal" in label or "contact" in label:
                if not data["owner_name"]:
                    data["owner_name"] = value

        # Fallback: scan page text for owner patterns
        if not data["owner_name"]:
            match = re.search(
                r"(?:Owner|Principal|Contact)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
                content,
            )
            if match:
                data["owner_name"] = match.group(1)

    except Exception as exc:
        print(f"  [warn] Error scraping profile {url}: {exc}")

    return data


async def scrape_search_page(page, city: str, page_num: int) -> list[dict]:
    """Scrape one page of search results for a given city."""
    url = SEARCH_TEMPLATE.format(location=quote_plus(city), page=page_num)
    print(f"  [{city}] page {page_num}: {url}")
    leads = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await random_delay(2.0, 4.0)

        await page.wait_for_selector(
            '[data-testid="search-result-card"], .result-card, .MuiCard-root',
            timeout=15000,
        )
    except Exception as exc:
        print(f"  [warn] Could not load {city} page {page_num}: {exc}")
        return leads

    cards = await page.query_selector_all('[data-testid="search-result-card"]')
    if not cards:
        cards = await page.query_selector_all("div.result-card")
    # Intentionally no bare a[href*="/profile/"] fallback — that selector
    # matches nav/sidebar links and causes the same business to repeat.

    for card in cards:
        lead: dict = {f: "" for f in FIELDNAMES}

        try:
            # Profile URL
            link_el = await card.query_selector('a[href*="/profile/"]')
            if not link_el:
                href = await card.get_attribute("href")
                if href and "/profile/" in href:
                    lead["profile_url"] = BASE_URL + href if href.startswith("/") else href
            else:
                href = await link_el.get_attribute("href")
                lead["profile_url"] = BASE_URL + href if href.startswith("/") else href

            # Business name
            name_el = await card.query_selector(
                '[data-testid="business-name"], h3, h4, .business-name'
            )
            if name_el:
                lead["business_name"] = (await name_el.inner_text()).strip()

            # Rating
            rating_el = await card.query_selector(
                '[data-testid="rating"], [aria-label*="rating"], .bbb-rating'
            )
            if rating_el:
                lead["bbb_rating"] = (await rating_el.inner_text()).strip()
            else:
                rating_img = await card.query_selector('img[alt*="rating"], img[alt*="Rating"]')
                if rating_img:
                    alt = await rating_img.get_attribute("alt")
                    match = re.search(r"([A-F][+-]?)", alt or "")
                    if match:
                        lead["bbb_rating"] = match.group(1)

        except Exception as exc:
            print(f"  [warn] Error parsing card: {exc}")
            continue

        if lead["profile_url"]:
            leads.append(lead)

    return leads


async def main():
    print(f"Starting BBB scraper — painting contractors across NC ({len(NC_CITIES)} cities)")
    print(f"Output: {OUTPUT_PATH}\n")

    # keyed by normalized URL for dedup
    seen: dict[str, dict] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        search_page = await context.new_page()

        for city_idx, city in enumerate(NC_CITIES, 1):
            print(f"\n[{city_idx}/{len(NC_CITIES)}] Searching: {city}")
            city_new = 0
            for page_num in range(1, PAGES_PER_CITY + 1):
                leads = await scrape_search_page(search_page, city, page_num)
                for lead in leads:
                    key = dedup_key(lead["profile_url"])
                    if key and key not in seen:
                        seen[key] = lead
                        city_new += 1
                if len(leads) < 16:
                    # Fewer than a full page — no more results for this city
                    break
                if page_num < PAGES_PER_CITY:
                    await random_delay(2.0, 4.0)
            print(f"  +{city_new} new leads (total unique: {len(seen)})")
            if city_idx < len(NC_CITIES):
                await random_delay(3.0, 5.0)

        await search_page.close()

        # Visit profiles and write CSV incrementally
        all_leads = list(seen.values())
        total = len(all_leads)
        print(f"\n{total} unique listings found. Visiting each profile...\n")

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

            profile_page = await context.new_page()
            for idx, lead in enumerate(all_leads, 1):
                if not lead["profile_url"]:
                    continue
                print(f"[{idx}/{total}] {lead.get('business_name', 'Unknown')} — {lead['profile_url']}")
                details = await scrape_profile(profile_page, normalize_url(lead["profile_url"]))
                lead.update(details)
                writer.writerow(lead)
                f.flush()
                await random_delay(2.5, 5.5)

            await profile_page.close()

        await browser.close()

    print(f"\nDone. {total} records saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
