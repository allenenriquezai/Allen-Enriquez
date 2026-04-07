# Workflow: Scrape BBB Leads

## Objective
Scrape painting contractor leads from BBB.org across North Carolina cities.

## Inputs
- Target cities: hardcoded in `tools/scraper.py` (35 NC cities)
- Pages per city: 15

## Tool
```
python tools/scraper.py
```

## Outputs
- `~/Desktop/bbb_leads_nc.csv`
- Columns: business_name, owner_name, phone, email, address, years_in_business, entity_type, bbb_rating, profile_url

## Notes
- Uses Playwright headless browser (no auth needed)
- Deduplicates by normalized URL
- Random delays 2–5.5s between requests to avoid rate limiting
- Run time: long (35 cities × 15 pages × profile scraping)
