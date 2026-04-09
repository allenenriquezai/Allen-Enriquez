# Enriquez OS — Decision Archive

Entries moved from `DECISIONS.md` during structural cleanup. Full detail preserved for reference.

---

## 2026-04-09 — Dashboard v2: Full rewrite + orchestrator chat

**Problem:** Dashboard was mobile-only (cramped on web), habits were outdated (14 items, wrong categories), chat agent had minimal tools (no personal Gmail, no awareness of full system), Learn tab showed raw article links with no summaries, chat broke on multi-turn tool use conversations.

**Change:** Rewrote `tools/dashboard/` — 9 files modified, 3 deleted. New 21-item habit config with auto-migration. Responsive layout (mobile + desktop). Chat widget floats as FAB (bottom-sheet mobile, right-drawer desktop). Chat agent upgraded to full orchestrator (13 tools, all workflows/agents in system prompt). Learn tab lazy-loads Claude Haiku summaries. Fixed agentic loop bug (check content for tool_use blocks, not stop_reason; sanitize orphaned tool_use in history).

**Why:** Allen uses the dashboard on both phone and desktop. Mobile-only layout wasted screen space on web. Chat agent was too limited — couldn't access personal Gmail or know about most tools. The tool_use bug caused 400 errors on multi-turn conversations (user says "go" after draft confirmation).

**Criteria:** Speed: + (responsive layout, lazy summaries) | Cost: = (still Haiku, ~$0.01/msg) | Accuracy: + (fixed chat bug, real Gmail access) | Scale: + (desktop support, full tool registry)

---

## 2026-04-09 — OS Review: 10-finding fix batch

**Problem:** Full system audit found: agent over line limit (cold calls 182 lines), broken skill reference (call-notes → deleted agent), workflows over limit, stale memory, duplicate briefing emails (3x/day), personal emails sent with unfilled [placeholder] brackets, no deposit skill, 12 dead tools.

**Change:**
- `eps-cold-calls.md`: 182 → 135 lines. Moved note + email templates to `cold-call-templates.md` workflow. Added 2 safety guards (mandatory fetch, 0-connected stop).
- `call-notes/SKILL.md`: Fixed agent reference `eps-crm-notes` → `eps-call-notes`.
- `create-quote.md`: 219 → 199 lines. `calculate-line-items.md`: 207 → 197 lines. Removed duplicate rules + blank lines.
- `measure-floor-plan.md`: Removed reference to non-existent `togal_measure.py`.
- Deleted 3 stale memory files (duplicates of current entries).
- `morning_briefing.py` + `ai_learning_brief.py`: Default flipped from send-email to generate-data-only. `--send` flag added for opt-in email.
- `briefing_action_loop.py`: Auto-queues inquiry items when no email reply. Skips chase/stale (need approval).
- Created `/deposit` skill — pushes job description + line items to SM8.
- Added `check_placeholders()` to `personal_crm.py` draft command — catches `[Name]`, `[companyName]` etc.
- Incident log: 2 of 3 prevention items checked off.
- Orphan audit: 12 dead tools identified for future archival.

**Why:** System integrity first — broken references and oversized files degrade agent reliability. The cold calls fabrication incident (Apr 8) was the highest-risk finding. Briefing redesign aligns with dashboard-first direction (dashboard already shows the same data live). Placeholder check prevents embarrassing outbound emails.

**Criteria:** Speed: + (dashboard brief is instant vs waiting for email) | Cost: + (no email API calls on default briefing) | Accuracy: + (safety guards prevent data fabrication, placeholder check prevents bad emails) | Scale: = (no change)

---

## 2026-04-09 — Design principles + decision log system

**Problem:** No persistent record of why the system is built the way it is. Each session starts fresh. Audit findings had no context on prior decisions. No consistent criteria for evaluating architectural choices.

**Change:**
- Added "Design Principles" section to `CLAUDE.md` — 4 criteria ranked: Speed > Cost > Accuracy > Scalability (accuracy floor: 95%).
- Added "Decision Log" section to `CLAUDE.md` — rule to write `DECISIONS.md` entry after system modifications.
- Created `DECISIONS.md` at project root.
- Updated `/wrap` skill to auto-write decision log entries.

**Why:** Allen wants every future session to understand the reasoning behind past choices, not just what files exist. The 4 criteria give a consistent framework for trade-off decisions. The log prevents repeating solved problems and provides audit trail.

**Criteria:** Speed: = | Cost: = | Accuracy: + (decisions are documented, not lost) | Scale: + (new sessions onboard faster with context)

---

## 2026-04-09 — Personal brand sprint: 3 agents + content-led GTM

**Problem:** Allen had 690 CRM leads with 1.3% conversion. No email sending, no automated follow-up, no content presence, no case study. Warm leads going cold from manual follow-up. Cold calling as only acquisition channel doesn't scale.

**Change:**
- Wired email sending in `personal_crm.py` (`--send` flag)
- Rewrote outreach template: outcome-led, 47 words, specific CTA
- Created EPS case study (`projects/personal/case-studies/eps-quote-automation.md`)
- Built 3 new agents: `personal-followup-agent` (3-touch sequence), `personal-research-agent` (auto-enrich prospects), `personal-content-agent` (LinkedIn posts, video scripts)
- Built 3 new tools: `send_personal_email.py`, `research_prospect.py`, `generate_content.py`
- Built 2 new workflows: `follow-up-sequence.md`, `content-calendar.md`
- Created `/content` skill
- GTM pivot: YouTube course + Facebook ads replacing cold calling as primary channel
- ICP expanded from painting companies to architects, realtors, business owners, VAs

**Why:** Cold calling is linear (1 call = 1 prospect). Content + ads is exponential (1 video = thousands). The OS itself is both the product and the marketing — every feature built is a video topic. Free course builds trust, done-for-you setup removes friction, monthly subscription is the monetization.

**Criteria:** Speed: + (content scales faster than calls) | Cost: + (organic YouTube + targeted ads vs hours of cold calling) | Accuracy: + (QA on all outbound, placeholder checks) | Scale: ++ (content-led acquisition is infinitely scalable)

---

## 2026-04-09 — Marketing department: 4 agents + 30-day campaign system

**Problem:** No marketing infrastructure. Content agent only handled LinkedIn. No campaign planning, tracking, style enforcement, or QA for marketing output. Allen wants 2 reels/day + 1 YouTube/day for 30 days — needs a full production pipeline.

**Change:**
- Created org structure (`projects/personal/org/departments.md`) — 5 departments mapped
- Created 3 new agents: `personal-content-manager` (orchestrator), `personal-style-researcher` (style analysis), `personal-marketing-qa` (QA gate)
- Upgraded `personal-content-agent` — now handles reels, YouTube, FB posts, LinkedIn in Hormozi style
- Created 2 new tools: `content_tracker.py` (30-day campaign tracker), `research_content_style.py` (content pattern analysis)
- Upgraded `generate_content.py` — added `--type reel`, `--type youtube`, `--type fb-group-post`, `--batch-day N`
- Created 3 new workflows: `marketing-campaign.md` (full 30-day topic map), `content-formats.md` (per-format rules), `fb-group-outreach.md` (FB group strategy)
- Created `hormozi-style-guide.md` — voice rules, hook patterns, word banks, Filipino audience notes
- Upgraded `/content` skill — routes planning→manager, writing→copywriter, research→researcher, QA→qa
- Initialized 30-day campaign tracker (90 content pieces)

**Why:** Allen's GTM is content-led (Hormozi style). 3 pieces/day for 30 days = 90 scripts. Without a pipeline (plan → write → QA → track), this cadence is unsustainable. 4 agents is minimal: manager plans, copywriter writes, researcher maintains voice, QA enforces quality. One copywriter handles all formats (format rules live in workflow files, not agents) to keep agent count low. Style guide built from known Hormozi principles — no expensive web scraping. Filipino market as initial test shapes language and cultural framing.

**Criteria:** Speed: + (batch-day generates all 3 daily pieces in one command) | Cost: + (all agents on Haiku, style guide from knowledge not API calls) | Accuracy: + (dedicated QA agent, style guide enforcement, format checklists) | Scale: + (tracker handles any campaign length, department structure supports future teams)

---

## 2026-04-09 — CRM Kanban: editable cards, drag-lock, dedup, Meeting Booked stage

**Problem:** CRM Kanban board had 3 issues: (1) drag-and-drop could fire twice during lag, duplicating leads across sheet tabs, (2) contact fields (DM, phone, email, website) were read-only in the modal — couldn't input data during calls, (3) no Meeting Booked stage — booked leads lumped into Warm Interest, (4) 167 duplicate rows across all tabs from prior bulk imports + drag bugs, (5) sort didn't prioritise recently called leads.

**Change:**
- `tools/crm_kanban/app.py` — added `meeting_booked` stage (9th column), fixed sort (most recently called first, undated leads sink), added header alias handling for `Decision Maker`/`Owner Name / DM` in update endpoint
- `tools/crm_kanban/templates/index.html` — contact fields now editable inputs, green phone dial button, column widths for 9 columns, `?v=2` cache buster
- `tools/crm_kanban/static/app.js` — `isMoving` lock disables all card dragging during API call, editable contact fields wired to saveCard(), auto-sets Date Called on outcome change, phone dial link updates live
- Google Sheet — deleted 167 duplicate rows (kept copy with most data for each pair)

**Why:** The duplicate bug was the highest risk — it corrupted CRM data and could cause double-calls. Lock approach chosen over debounce because it's simpler and guarantees no concurrent moves. Editable fields needed because Allen inputs contact info during live calls. Meeting Booked as separate stage gives clear pipeline visibility. Date Called auto-update ensures sort stays accurate without manual entry.

**Criteria:** Speed: + (editable fields save a tab-switch to Sheets) | Cost: = | Accuracy: + (drag lock prevents dupes, 167 dupes cleaned) | Scale: =
