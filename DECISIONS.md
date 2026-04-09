# Enriquez OS — Decision Log

System design decisions, why they were made, and how they score on design criteria.

**Rules:**
- Log architectural/design decisions only — not routine tasks or data updates
- Keep "Change" to 2-3 conceptual bullets — `git log` has the file-by-file detail
- Archive entries older than 2 weeks to `DECISIONS-archive.md`

---

## Open Items

Consolidated from all entries. Remove when done.

**Dashboard**
- [ ] Visual polish pass ("make it look like a real app")
- [ ] Approval UI (GO/SKIP in Brief tab) — deferred to web & mobile app session
- [x] Test Learn tab end-to-end (first generation + Next Lesson)
- [ ] Version static assets for cache busting
- [ ] Consider upgrading chat model (Haiku → Sonnet)

**EPS**
- [ ] Fix 3 failing skills (pdf too long, deposit validation, webapp-testing script ref)

**Personal Brand**
- [ ] Wire follow-up agent to `update-note` subcommand
- [ ] Automate phone cleanup in `personal_crm.py cleanup`
- [ ] Nightly cleanup: auto-move emailed leads Call Queue → Emails Sent
- [ ] Course outline, landing page/funnel, Facebook ad templates
- [ ] Generate and QA Day 1 content scripts
- [ ] Phase 2: AI-assisted video editing
- [ ] Evaluate GSD skill usage — prune unused

---

## 2026-04-10 — WAT framework: on-demand agent loading + context audit

**Problem:** 12 agents in `.claude/agents/` auto-loaded ~40KB (~10K tokens) into every session. Not scalable — adding more agents makes every session heavier.

**Change:**
- Moved all agents to `projects/*/agents/` (loaded on demand by skills, not at startup)
- Updated 5 skills to spawn general-purpose Agents that read prompt files
- Deleted 3 heavy skills (pdf/xlsx/docx ~20KB) and 7 stale memory files
- Created `/os-audit` skill to detect context bloat with thresholds
- CLAUDE.md: SAT → WAT framework

**Why:** Claude Code auto-loads everything in `.claude/agents/` and `.claude/skills/` into every session's system prompt. Moving agents out eliminates the scaling problem — 30 agents would cost 0 tokens at startup instead of ~100KB. On-demand loading via skills means agents only load in sessions that need them.

**Criteria:** Speed: + | Cost: ++ | Accuracy: = | Scale: ++

**Next:** Test all skills end-to-end to confirm on-demand pattern works. Trim remaining large skills (find-skills 4.9KB, webapp-testing 3KB).

---

## 2026-04-10 — Learn tab fixes + Brief disk cache + kid-level language

**Problem:** Learn tab showed Claude refusal messages as summaries (scraper fed bad content). Work Brief slow on every cold start (10+ Pipedrive API calls, in-memory cache lost on restart). Learning language too technical.

**Change:** Added refusal detection in `call_claude()`. Improved scraper with 5 extraction strategies. Added disk-based cache persistence for all briefs. Updated all learning prompts to 10-year-old reading level.

**Why:** Refusal detection is cheaper than re-prompting (root cause is bad scrape). Disk cache gives instant cold-start loads while background refresh keeps data fresh. Kid-level language per Allen's explicit request.

**Criteria:** Speed: ++ | Cost: = | Accuracy: + | Scale: =

---

## 2026-04-10 — Dashboard v4: SQLite cache + AJAX nav + scraper fix

**Problem:** Every dashboard read/write hit Google Sheets API (200-500ms). Habits tab navigation did full page reload. Learn tab scraper grabbed raw HTML instead of article content.

**Change:** Added SQLite cache layer with WAL mode + background sync to Sheets every 60s. Replaced page reloads with AJAX + pushState. Rewrote scraper to extract `<p>` content from `<article>`/`<main>` tags.

**Why:** SQLite + background sync gives <1ms reads while keeping Sheets as source of truth. Scraper uses `<p>` extraction because article content lives in paragraphs — nav/boilerplate don't.

**Criteria:** Speed: ++ | Cost: = | Accuracy: + | Scale: +

---

## 2026-04-10 — Skill gate limits + update-note + connected-only filter

**Problem:** 17 new skills ungated. CRM tool couldn't update individual fields (blocking follow-up agent). Cold call processor wasted tokens on no-answer leads.

**Change:** Gated 17 skills (14 pass, 3 fail). Bumped skill line limit 100→200 hard / 80→100 soft. Added generic `update-note` subcommand to CRM tool. Added `--connected-only` filter to cold call processor.

**Why:** Limit 100 was too tight for template-heavy skills (xlsx 160, docx 192). `update-note` unblocks follow-up agent. `--connected-only` cuts batch size.

**Criteria:** Speed: + | Cost: + | Accuracy: = | Scale: +

---

## 2026-04-10 — CRM Kanban: Phone 2 + display/edit toggle

**Problem:** Multiple phone numbers crammed into one field. Modal contact fields always editable — couldn't tap to dial.

**Change:** Added Phone 2 column. Rewrote modal with display/edit toggle — clickable links by default, pencil icon to edit.

**Why:** Allen inputs contact info during live calls and needs one-tap dial. Display-first matches read-heavy usage.

**Criteria:** Speed: + | Cost: = | Accuracy: = | Scale: =

---

## 2026-04-10 — Dashboard v3: outreach stats, timezone, cache strategy

**Problem:** No cold outreach visibility on Home tab. Server dates used UTC (wrong day in Philippines). Brief/Learn hit APIs on every load.

**Change:** Added personal + EPS outreach stats (today/week). All datetimes → PH timezone (UTC+8). Stale-while-revalidate caching for Brief/Learn. Learn state persisted to disk with manual advance.

**Why:** Stale-while-revalidate gives instant loads AND fresh data. Learn only changes on manual advance — no reason to re-fetch.

**Criteria:** Speed: ++ | Cost: + | Accuracy: + | Scale: =

---

## 2026-04-10 — Cleaning calculator + dead tool archive + GSD prune

**Problem:** Quote calculator only handled painting. 10 dead tools cluttered `tools/`. 74 GSD skills globally, ~half unused.

**Change:** Added 5 cleaning rate patterns to calculator. Archived 10 dead tools to `tools/archive/`. Pruned 37 unused GSD skills.

**Why:** Cleaning rates existed in `pricing.json` but weren't wired. Archive over delete preserves history. GSD pruned after 1 week of usage data.

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +

---

## 2026-04-10 — Gmail compose scope + CRM Phone 2 propagation

**Problem:** Gmail token lacked compose scope (couldn't create drafts). Phone 2 header defined in code but never propagated to sheet.

**Change:** Added `gmail.compose` scope. Propagated Phone 2 header to all 12 CRM tabs.

**Why:** Allen reviews drafts before sending — `gmail.send` can't create drafts.

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +

---

## 2026-04-10 — GSD + Superpowers installation

**Problem:** No structured framework for multi-file builds. Long sessions lose context. No verification protocol.

**Change:** Installed GSD globally (68 skills). Cherry-picked 5 Superpowers skills. Added Build Mode auto-trigger to CLAUDE.md (3+ file builds only).

**Why:** GSD prevents context rot on complex builds. Cherry-picked over full install — Superpowers session-start hook hijacks every session. Verification-before-completion enforces evidence (aligns with 95% accuracy floor).

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +

---

> Entries before 2026-04-10 archived in [DECISIONS-archive.md](DECISIONS-archive.md)
