# QA

Last line of defence before anything reaches a client. Nothing goes out without passing.

---

## How it works

1. Identify output type (quote data, quote email, follow-up email, other)
2. Run the relevant SOP below — every check, no skipping
3. Post QA report + draft to Pipedrive as a pinned note
4. Return verdict

For quote emails: run BOTH SOPs.

**Tool:** `python3 tools/qa_quote.py`

---

## SOP 1: Quote Structure

Validates `quote_data.json` — data integrity, math, required sections.

```bash
python3 tools/qa_quote.py --data-only
```

### Checks

**1. Required fields** — all present and non-empty:

| Field | Rule |
|---|---|
| `client` | Real name — reject "Client Name", "Name", "Your Name" |
| `address` | Real address — reject "Client Address", "Address" |
| `job_type` | e.g. "Construction Cleaning", "Residential Painting" |
| `quote_date` | Date the quote is issued |
| `email` | Client email |

**2. Job description sections** — all 7, in order:
1. JOB SUMMARY
2. SCOPE OF WORK (or "SCOPE OF WORK – QUOTE INCLUSIONS")
3. CLEANING METHOD
4. INCLUSIONS
5. EXCLUSIONS (or "QUOTE EXCLUSIONS")
6. GUARANTEES
7. BOOKING & PAYMENT TERMS (or "PAYMENT TERMS")

Minimum: 100 characters total.

**3. Line item math:**

| Check | Rule | Tolerance |
|---|---|---|
| Subtotal | Sum of `line_items[].subtotal` = stated `subtotal` | Exact |
| GST | 10% of subtotal | +/- $0.02 |
| Total | subtotal + GST | +/- $0.02 |

**4. Component split** (warning only): If >50% of line items share the same description, warn: "Consider per-unit breakdown."

### Verdict
- FAIL: any issue in checks 1-3
- PASS WITH WARNINGS: only check 4 warnings
- PASS: clean

---

## SOP 2: Email

Validates any client-facing email.

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

For follow-ups or emails without a quote: run checks manually.

### Checks

**1. Unfilled placeholders** — regex: `\[[A-Za-z_][A-Za-z_0-9 ]*\]`. Any match = FAIL.

**2. Word count:**

| Type | Max |
|---|---|
| Quote email | 180 (warn at 200) |
| Follow-up | 120 |

**3. Tone match:**

| Client | Tone |
|---|---|
| Residential | Warm, personal, reference their situation |
| Builders | Professional, brief, direct — no small talk |

**4. Subject line** — must be specific. Reject generic: "Your Quote", "Following Up", "EPS Quote".

**5. Formatting** — flag: double-spacing, stray HTML tags, empty bullets, trailing whitespace.

**6. Residential concern fields** — `residential_painting`, `residential_cleaning`, `bond_clean` templates require `--concern-1` and `--concern-2`. Missing = FAIL.

**7. Deal ID** — if missing, warn (not a blocker): "No deal ID — email won't link to Pipedrive."

### Verdict
- FAIL: unfilled placeholders (1) or missing concerns (6)
- PASS WITH WARNINGS: soft issues only (2, 3, 4, 5, 7)
- PASS: clean

---

## Output format

```
QA STATUS: PASSED / PASSED WITH WARNINGS / FAILED

Issues (must fix):
- ...

Warnings:
- ...

Preference flags:
- ...
```

---

## Preference learning

After any email is sent, ask Allen: "Any edits you made before sending? I'll save the preference."

If Allen gives a change, add a new rule to this file under the section below:

### Saved preferences

_(append here as rules are learned)_

Before every QA run, check the Saved preferences section above and flag violations.

---

## Hard rules

- Never skip a check
- Never mark PASSED with unfilled placeholders
- Never mark PASSED with wrong math
- Only show Allen drafts after QA passes
- Load credentials from `eps/.env`
