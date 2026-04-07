# Workflow: Prospect Research

## Objective
Find and compile owner-operated residential cleaning companies in a target city, filtered and ready for outreach.

## Target
- City: Charlotte, North Carolina
- Area codes: 704, 980
- Goal: 20 qualified prospects per run

## Inputs
- Target city (default: Charlotte, NC)
- Target count (default: 20)

## Process

### Step 1 — Search Sources
Search the following one at a time:
- Google Maps: "residential cleaning company Charlotte NC"
- Google Maps: "house cleaning service Charlotte NC"
- Google Maps: "maid service Charlotte NC"
- Web search: "independent cleaning company Charlotte NC"

### Step 2 — Filter Each Result
KEEP if all of these are true:
- Independently owned (not a franchise)
- Google reviews: between 10 and 200
- Google rating: between 4.0 and 4.9
- Has a working phone number

REMOVE if any of these match:
- Franchise name: Molly Maid, Jan-Pro, Merry Maids, ServiceMaster, Two Maids, The Maids, Coverall
- Fewer than 10 reviews
- No phone number found

### Step 3 — Collect Data Per Company
- Business Name
- Phone Number
- City
- Website URL
- Owner Name (check About page or Google)
- Service Areas (check website)
- Google Rating
- Number of Reviews

### Step 4 — Verify Data
- Cross-check at least 5 phone numbers against the company website
- If more than 20% of numbers don't match, stop and report before saving

### Step 5 — Output
- Write to Google Sheet (use tools/write_prospects.py or tools/append_prospects.py)
- Or save as CSV to .tmp/ for manual review before importing

## Summary to Print When Done
- Total companies found
- Total kept after filtering
- Total removed and why
- Any data quality issues
