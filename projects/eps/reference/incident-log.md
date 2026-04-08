# EPS Incident Log

Track agent/tool mistakes, root causes, and fixes so we continuously improve.

## Format

Each entry: date, what went wrong, root cause, fix applied, prevention action.

---

## 2026-04-08 — Cold call notes posted to all 18 leads instead of 5

**What happened:** eps-cold-calls agent posted "Cold Call — Asked For Email" formatted notes to all 18 leads in the Recently Called filter, including 13 that were No Answer or Invalid Number.

**Root cause:** The agent didn't use `process_cold_calls.py fetch` to get actual activity types. Instead it assumed all leads in the filter were connected calls and fabricated notes for all of them. The `get_latest_activity()` function in the script also has a weakness — it picks the first matching cold-type activity, which can return stale data if multiple activities exist.

**Impact:** 13 leads got incorrect pinned notes. Had to manually delete all 13 notes and re-process the 5 actual connected leads with correct call outcomes.

**Fix applied:**
- Deleted 13 bad notes via Pipedrive API
- Re-posted correct notes for 5 connected leads (3 corrected from "Asked For Email" to "Not Interested")
- Drafted emails only for the 2 leads that actually need them (Renascent QLD, Intebuild)

**Prevention:**
- [ ] Update eps-cold-calls agent to ALWAYS run `process_cold_calls.py fetch` first and use the batch JSON — never fabricate activity types
- [ ] Add validation in the agent: cross-check activity type before posting notes
- [ ] Consider adding a `--connected-only` flag to `process_cold_calls.py` that filters out No Answer / Invalid Number leads automatically
