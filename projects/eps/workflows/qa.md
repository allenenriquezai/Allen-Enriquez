
# EPS QA Skill

Two SOPs below. The eps-qa-agent reads the relevant one based on what it's checking.
For quote emails: run both (quote structure + email).

---

## SOP 1: Quote Structure

Validates `quote_data.json` — data integrity, math, required sections.

### Tool
```bash
python3 tools/qa_quote.py --data-only
```
Runs checks 1-4 automatically. If the tool can't run, do them manually.

### Checks

**1. Required fields** — all must be present and non-empty:

| Field | Rule |
|---|---|
| `client` | Real name from Pipedrive — reject "Client Name", "Name", "Your Name" |
| `address` | Real address from Pipedrive — reject "Client Address", "Address" |
| `job_type` | e.g. "Construction Cleaning", "Residential Painting" |
| `quote_date` | Date the quote is issued |
| `email` | Client email address |

**2. Job description sections** — must contain all 7, in order:
1. JOB SUMMARY
2. SCOPE OF WORK (or "SCOPE OF WORK – QUOTE INCLUSIONS")
3. CLEANING METHOD
4. INCLUSIONS
5. EXCLUSIONS (or "QUOTE EXCLUSIONS")
6. GUARANTEES
7. BOOKING & PAYMENT TERMS (or "PAYMENT TERMS")

Minimum length: 100 characters total.

**3. Line item math:**

| Check | Rule | Tolerance |
|---|---|---|
| Subtotal | Sum of all `line_items[].subtotal` = stated `subtotal` | Exact |
| GST | `gst` = 10% of `subtotal` | +/- $0.02 |
| Total | `total` = `subtotal` + `gst` | +/- $0.02 |

**4. Component split** (warning only):
If more than half of line items share the same description, warn:
> "Line items may not be split by component — consider per-unit breakdown"

### Verdict
- **FAIL** if any check in 1-3 has issues
- **PASS WITH WARNINGS** if only warnings (check 4)
- **PASS** if clean
- Never mark PASSED if line item math is wrong

---

## SOP 2: Email

Validates any client-facing email — quote emails, follow-ups, or ad-hoc.

### Tool (for quote emails)
```bash
python3 tools/qa_quote.py \
  --template "quotes/<key>" \
  --first-name "Name" \
  --to "email@example.com" \
  --situation "..." \
  --opener "..." \
  --bonus "..." \
  --deal-id "123" \
  --doc-url "GOOGLE_DOC_URL"
```
For follow-ups or other emails without a quote: run the checks below manually.

### Checks

**1. Unfilled placeholders** — scan for `[placeholder]` pattern (regex: `\[[A-Za-z_][A-Za-z_0-9 ]*\]`).
Any unfilled placeholder = **FAIL**. No exceptions.

**2. Word count:**

| Email type | Max words |
|---|---|
| Quote email | 180 (warn at 200) |
| Follow-up email | 120 |

**3. Tone match:**

| Client type | Expected tone |
|---|---|
| Residential (homeowners) | Warm, personal, reference their specific situation |
| Builders / commercial | Professional, brief, direct — no small talk |

**4. Subject line** — must be specific. Reject generic subjects like "Your Quote", "Following Up", "EPS Quote".

**5. Formatting** — flag any of:
- Double-spacing between paragraphs
- Stray HTML tags in plain-text emails
- Empty bullet points
- Trailing whitespace

**6. Residential concern fields** — if template is `residential_painting`, `residential_cleaning`, or `bond_clean`:
- `--concern-1` and `--concern-2` are required
- Missing concerns = **FAIL**

**7. Deal ID** — if missing, warn (not a blocker):
> "No deal ID — email won't be linked to a Pipedrive deal"

### Verdict
- **FAIL** if unfilled placeholders (check 1) or missing concerns (check 6)
- **PASS WITH WARNINGS** if only warnings (checks 2, 7) or soft flags (checks 3-5)
- **PASS** if clean
- Never mark PASSED if unfilled placeholders exist
