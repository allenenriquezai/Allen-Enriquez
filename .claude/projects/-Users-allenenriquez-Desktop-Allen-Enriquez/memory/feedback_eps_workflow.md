---
name: EPS Project — Workflow Preferences
description: How Allen prefers to work on EPS automation tasks
type: feedback
---

Ask about rates at the start of every quote workflow — Allen sometimes wants default rates, sometimes a multiplier across the board, sometimes specific overrides per line item. Never assume default.

**Why:** Quote pricing varies by job complexity and client. The rate selection step is part of the standard workflow.

**How to apply:** At the start of /eps-quote, always ask: "What rates? Default / multiplier (e.g. +15%) / custom overrides (e.g. INT-01:25)?"

---

Don't calculate room-by-room for painting quotes. Use aggregate whole-property measurements per floor (e.g. total wall centreline sqm, total ceiling sqm).

**Why:** That's how EPS actually measures — wall centreline for the whole building, not per room.

**How to apply:** When taking scope input, ask for total sqm per surface type, not per room.

---

For multi-component jobs (townhouses, floors, levels, buildings), always use `--components` mode — never aggregate into a single `--scope` string.

**Why:** Allen wants line items split per component so the quote shows "Townhouse 1 — External Wall Painting", etc. — not one aggregated row.

**How to apply:** Any time the job has named units (townhouse, floor, level, building, apartment), create a components.json and use `--components`. Single-location jobs can still use `--scope`.

---

Job description must be the FULL structured content from the job description template (all sections: JOB SUMMARY, PROJECT DETAILS, SCOPE OF WORK, PREPARATION, INCLUSIONS, WARRANTIES, EXCLUSIONS, PAYMENT TERMS). Not just a few bullets.

**Why:** The `[jobDescription]` placeholder in the Google Doc covers the entire JOB SPECIFICS section. Allen expects the full 7-section breakdown matching the template file structure.

**How to apply:** Stage 0 — compose ALL sections from `projects/eps/job_descriptions/<type>.md` as a JSON array of lines (one string per line, with `• ` for bullets and blank strings for spacing). Pass via `--job-description '[...]'`. JOB SUMMARY = 2-3 bullets max about the specific client situation. Sections 2-7 are mostly static from the template. `fill_quote_template.py` joins with `\n` only — Claude must include `• ` in bullet text.

---

Mobilisation fee is optional and variable — never auto-include it.

**Why:** Not all jobs have a mob fee, and the amount varies.

**How to apply:** Only add mob fee if Allen explicitly includes it (`--mob AMOUNT`). Never default to the $100 in pricing.json.
