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
- [x] Visual polish pass ("make it look like a real app")
- [ ] Approval UI (GO/SKIP in Brief tab) — deferred to web & mobile app session
- [x] Test Learn tab end-to-end (first generation + Next Lesson)
- [ ] Version static assets for cache busting
- [ ] Consider upgrading chat model (Haiku → Sonnet)

**EPS**
- [ ] Fix 3 failing skills (pdf too long, deposit validation, webapp-testing script ref)
- [ ] WhatsApp: permanent Cloudflare tunnel + permanent access token
- [ ] WhatsApp: test with real team member, tune agent prompt
- [ ] EstimateOne: enrich top builders (ABN lookup / Google search for contact person, email)
- [ ] EstimateOne: cross-check builders vs Pipedrive, flag new for cold calling
- [ ] EstimateOne: install daily 6AM launchd automation
- [ ] CRM sync: Pipedrive ↔ SM8 daily reconciliation
- [ ] Team dashboard: pipeline view with SM8 status overlay

**Personal Brand**
- [ ] Wire follow-up agent to `update-note` subcommand
- [ ] Automate phone cleanup in `personal_crm.py cleanup`
- [ ] Nightly cleanup: auto-move emailed leads Call Queue → Emails Sent
- [ ] Course outline, landing page/funnel, Facebook ad templates
- [ ] Generate and QA Day 1 content scripts
- [ ] Phase 2: AI-assisted video editing
- [ ] Evaluate GSD skill usage — prune unused

- [ ] Build `/outreach` skill as entry point for outreach agent
- [ ] Test outreach agent with a real prospect

---

## 2026-04-11 — Company restructure: 5 departments + self-improving loops
**Problem:** Personal brand had scattered agents with no organizational structure, no feedback loops, no intel system. Agents couldn't learn from each other or improve over time. No delivery department for when clients actually pay.
**Change:** Restructured into 5 departments (Intelligence, Content Production, Sales, Delivery, Brand Manager QA gate). Created 8 new agents (4 intelligence + 4 delivery). Built 7 living intel doc templates in `reference/intel/`. Built 3 operational tools (intel_freshness, content_buffer, followup_checker). Rewrote `/start` skill with Push Allen dashboard. Updated CLAUDE.md with new design principles. Generated 6-page company structure PDF. Archived 3 redundant agents.
**Why:** Modeled after Hormozi/Martel operations — setters (AI) qualify, closers (Allen) close. Self-improving loops (content performance, sales→marketing feedback, intelligence, review gate ratchet) ensure the system gets better without Allen touching it. All agents read intel docs before work — shared context means department outputs feed each other. Brand Manager as universal QA gate with 3 tiers prevents bad output at scale.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: ++
**Next:** Build Phase 2 automations (competitor sweep, ICP pulse, performance scorecard, playbook ratchet). Commit 50+ uncommitted files. Brainstorm content production plan.

## 2026-04-11 — Brand agent + landing page + lead magnet
**Problem:** Brand context scattered across 6+ files (memory, outreach.md, style guide, content formats, ManyChat, CLAUDE.md). No landing page or lead magnet to convert content viewers into email subscribers. No funnel between "watches video" and "talks to Allen."
**Change:** Created `projects/personal/agents/personal-brand-agent.md` (single source of truth), landing page HTML (Hormozi dark theme, mobile-first), 8-page lead magnet PDF ("5 AI Automations That Save 10+ Hours a Week"), PDF generator script
**Why:** Brand agent over scattered files — any skill loads one file instead of six. Universal lead magnet framing over VA-specific — content serves both VAs (testimonial targets) and business owners (paying clients). Kit free tier over Mailchimp — 10K contacts vs 500. GitHub Pages over Carrd — no branding, custom domain, full control.
**Criteria:** Speed: + | Cost: + | Accuracy: + | Scale: +
**Next:** Allen reviews deliverables. Set up Kit. Deploy to GitHub Pages. Wire into ManyChat flows + outreach templates.

## 2026-04-11 — Carousel image generator tool
**Problem:** No fast way to generate static carousel PNGs for content distribution (IG, FB, LinkedIn)
**Change:** Created `tools/generate_carousel.py` (Pillow-based CLI) + added Carousel format spec to `projects/personal/workflows/content-formats.md`
**Why:** Pillow is free, offline, no API costs vs premium design tools. Two built-in styles (dark Hormozi + light Nate Herk) cover both brand voices. Copy is user-editable via file input (no LLM dependency). System fonts avoid dependency management. Placeholder copy + `--copy-file` flag lets future content agents fill in the text without changing the tool.
**Criteria:** Speed: + | Cost: + | Accuracy: = | Scale: +
**Next:** Wire to content agent; test with real carousel production

## 2026-04-11 — ManyChat inbound automation workflow
**Problem:** Allen posts content on FB/IG but needs to manually DM people who comment with keywords. Scales poorly at high volume.
**Change:** Created `projects/personal/workflows/manychat-setup.md` — step-by-step SOP for ManyChat comment-to-DM automation on free tier
**Why:** ManyChat free tier ($0) handles comment triggers, DM automation, and keyword matching. Aligned 5 flows to content pillars + outreach.md segments (AI, VA, AUTOMATE, HOW, FREE). Pre-wrote DM copy in Hormozi voice for each. Allen copies/pastes + swaps links only — no manual DM work after setup. Upgrade trigger at 100+ contacts (justifies $15/month Pro).
**Criteria:** Speed: + | Cost: + | Accuracy: + | Scale: +
**Next:** Test first flow on live post; track keyword conversion rates; assess Pro tier ROI at 100+ contacts
**Criteria:** Speed: + (instant PNG generation, no Figma/Canva) | Cost: + (free, no API) | Accuracy: + (PIL rendering is deterministic) | Scale: + (works for 1 carousel or 20)
**Next:** Build content agent that writes Hormozi-voice slide copy and feeds --copy-file to this tool. Consider adding optional overlays (gradient, image BG) if demand exists.

## 2026-04-11 — DM outreach research agent
**Problem:** No system for researching prospects and drafting personalised DMs — Allen was doing it manually
**Change:** Created `projects/personal/agents/personal-outreach-agent.md` — researches prospect via web search, classifies by ICP segment + tier, drafts Touch 1-3 messages using outreach.md templates, logs to JSONL
**Why:** Agent-only (no tool script) because the workflow is research + writing, not data processing. Templates stay in outreach.md so the agent prompt stays lean. JSONL tracking over DB because it's append-only and grep-friendly at this scale.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Build `/outreach` skill, test with real prospect, consider batch mode for group member lists

## 2026-04-11 — Dashboard overhaul: visual polish, checklist reorg, data consistency

**Problem:** Dashboard looked like a prototype — small text, tight spacing, wrong currency (USD not PHP), checklist categories didn't match Allen's daily flow, Home tab habits count was out of sync with Habits tab (Sheets vs SQLite source mismatch).

**Change:**
- Visual polish across all tabs: wider container, bigger text, rounded cards with borders, PHP currency
- Checklist reorganized into 5 categories matching daily flow (morning → EPS → workout → home → evening)
- Home tab checklist reads from SQLite (same source as Habits tab) instead of Google Sheets
- Week start changed to Sunday across all routes
- Chat system prompt rewritten for bias-to-action
- Removed "Spent" stat from Home top row

**Why:** Dashboard serves dual purpose — Allen's daily tool AND demo content for personal brand. Visual quality matters for both. SQLite as single source of truth eliminates the 60s sync lag that made Home and Habits show different numbers. Sunday week start matches Allen's actual week rhythm.

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: =
**Next:** Continue visual polish based on Allen's feedback. Version static assets for proper cache busting (currently bumping sw.js manually).

---

## 2026-04-10 — Personal brand pivot + marketing playbook

**Problem:** Personal brand strategy targeted Charlotte NC painting companies. Market turned out to be mostly Spanish-speaking, older, low tech-savviness — hard to sell to. No content or outreach system was live.

**Change:**
- Pivoted ICP to Philippines (VAs, professionals, business owners) as primary, US cold outreach as secondary
- Updated `projects/personal/CLAUDE.md` — new ICP, new strategy, new offer
- Rewrote `content-calendar.md` and `marketing-campaign.md` — YouTube-first, one-automation-per-video
- Added "stress test ideas" as first behavior rule in `CLAUDE.md`
- Generated consolidated marketing playbook PDF and emailed to Allen

**Why:** PH market is more tech-aware, Allen speaks the language, and the content-led approach (teach for free, convert viewers) is a better GTM than cold calling old-school business owners. The pivot preserves US outreach as a secondary channel.

**Criteria:** Speed: + | Cost: = | Accuracy: = | Scale: +
**Next:** Run ICP researcher to validate segment ranking. Generate Day 1-3 scripts. Start filming.

---

## 2026-04-10 — Outreach system + ICP researcher

**Problem:** No structured outreach system for personal brand. Cold calling was default but doesn't scale. No way to prioritize which prospect segments to target first.

**Change:**
- Created `projects/personal/workflows/outreach.md` — 3-tier outreach SOP (influencers → VAs/small biz → network), 3 primary channels (FB DMs → IG DMs → phone), templates, safe limits, tracking
- Created `projects/personal/agents/personal-icp-researcher.md` — scores segments on need/budget/urgency/reachability
- Updated `projects/personal/org/departments.md` with new workflow + agent

**Why:** Facebook and Instagram DMs scale — Allen can hire VAs to message on his behalf. Phone calls don't scale (only Allen's voice). Influencers/creators targeted first because they have audiences AND buying power. ICP researcher validates this with data before committing outreach effort.

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: ++
**Next:** Run ICP researcher to validate segment ranking. QA outreach templates.

---

## 2026-04-10 — ICP research + outreach v4 with segment strategy

**Problem:** Outreach SOP had generic tiers but no data-backed segment targeting. Didn't know which segments to prioritize, what to say to each, or what the launch sequence should be.

**Change:**
- Ran ICP researcher agent — scored 8 segments across need/budget/urgency/reachability using web-verified data
- Rewrote `projects/personal/workflows/outreach.md` — segment-ranked, segment-specific templates, week-by-week launch plan, message angles per segment
- Added bias-to-action as top design principle in `CLAUDE.md`
- Generated Outreach Playbook v4 PDF and emailed to Allen

**Why:** Generic outreach wastes effort. Filipino VAs scored highest (34/40) because the need is existential (AI replacing basic VAs), urgency is panic-level, and reachability is 10/10 via FB groups. Real estate agents and recruitment agencies tied at 31/40. US service businesses scored high on need/budget but tank on reachability (4/10) — content play, not outreach. Data drives targeting.

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** QA outreach templates before deployment. Film first content. Launch both together.

---

## 2026-04-10 — System-wide learning engine

**Problem:** Sessions are stateless — no way to compound operational learnings. Same corrections repeated, no pattern detection, no measurable improvement over time.

**Change:**
- Three-tier learning system: raw log (`shared/learnings/log.jsonl`) → domain playbooks (`shared/learnings/playbook-*.md`) → promoted to CLAUDE.md/memory/skills
- `/wrap` silently extracts 1-5 observations per session
- `/os-review` distills patterns weekly, flags repeat corrections
- `/os-audit` tracks playbook size to prevent bloat
- Playbooks loaded on demand only — zero startup context cost

**Why:** Memory files capture preferences but not operational patterns. DECISIONS.md captures architecture but not "this approach works better." Needed a structured layer between raw experience and system rules. Playbooks are the middle tier — curated enough to be useful, lean enough to not bloat context.

**Criteria:** Speed: = | Cost: = | Accuracy: + | Scale: ++
**Next:** Run for 2 weeks, check if correction rate decreases. First /os-review will distill initial patterns.

---

## 2026-04-10 — WhatsApp Business API integration

**Problem:** Allen's team sends inquiries and questions via WhatsApp. Allen is the bottleneck — many questions the team could answer themselves.

**Change:**
- Connected Allen's spare SIM (+63 966 173 2979) as WhatsApp Business number via Meta Cloud API
- Built `tools/whatsapp.py` (send), `tools/whatsapp_webhook.py` (receive), `tools/whatsapp_agent.py` (auto-reply via Haiku)
- Agent classifies: AUTO_REPLY (deal lookups), DRAFT_ACTION (reschedules → queue for Allen), ESCALATE (new clients, money, urgent)
- Trilingual (EN/TL/ES), direct + friendly tone, EPS-only data access

**Why:** Personal WhatsApp has no API. WhatsApp Business Cloud API is official and free (1K conversations/mo). Haiku for classification costs ~$0.30/mo for 5 users. Conservative escalation protects against wrong answers.

**Criteria:** Speed: ++ | Cost: + | Accuracy: = | Scale: +
**Next:** Permanent Cloudflare tunnel + permanent access token. Test with real team member. Tune prompt based on actual message patterns.

---

## 2026-04-10 — Pipedrive activity tool for fast daily triage

**Problem:** Fetching Pipedrive activities via subagent took ~2min and burned excessive tokens. Allen needs daily activity checks — must be fast and cheap.

**Change:**
- Built `tools/pipedrive_activities.py` — direct CLI for fetch/filter/bulk-update activities
- Supports `--date`, `--subject`, `--type`, `--move-to`, `--done/--undone` flags
- Uses existing `crm_monitor.py` API patterns with pagination + ±1 day window workaround for Pipedrive date filter quirk

**Why:** Subagent approach (spin up agent → curl calls → paginate) was ~2min per lookup. Direct tool call is ~5sec. For a daily task this is unacceptable latency. Reused existing API helpers from crm_monitor rather than adding dependencies.

**Criteria:** Speed: + | Cost: + | Accuracy: = | Scale: +
**Next:** Add mark-done + create-follow-up to the tool. Build daily triage flow: fetch → categorise AI vs Allen → draft batch → approve → execute.

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

## 2026-04-10 — Site Visit Scheduling Agent

**Problem:** Site visit scheduling was fully manual — check Pipedrive deal, move to correct stage, wait for n8n to create SM8 job card, check Giovanni/Vanessa's calendar separately, then book on SM8. No single flow to handle it.

**Change:** Built `tools/schedule_sm8_visit.py` (3-calendar check + SM8 booking), `projects/eps/agents/eps-site-visit-agent.md` (full orchestration), `.claude/skills/site-visit/SKILL.md` (entry point). Updated agent registry in `projects/eps/CLAUDE.md`.

**Why:** Three separate sources of truth for staff availability (SM8 Paint, SM8 Clean, Google Calendar) were never checked together. Used `purchase_order_number` as the Pipedrive↔SM8 link (reliable, set by n8n) instead of the Pipedrive custom field (often empty). Recurring calendar events treated as soft blocks because Gio/Vanessa's calendars are all time blocks, not appointments — without this, every slot shows as conflicted.

**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +

**Next:** Test full Tenders→EPS pipeline move path. Test notes-to-SM8 push with real discovery call data.

---

## 2026-04-11 — Excalidraw skills: PNG visuals + editable diagrams

**Problem:** No way to generate visuals or diagrams from within Claude Code. Content creation requires visual aids for YouTube/social media, and technical docs need editable diagrams.

**Change:**
- Installed two complementary skills: `excalidraw-visuals` (PNG via kie.ai API) and `excalidraw-diagram` (editable JSON, free)
- Script + style reference + style guide placed in `scripts/` and `brand-assets/`
- Outputs routed to `.tmp/visuals/` and `.tmp/diagrams/` — not project folders

**Why:** Two skills because they serve different needs. PNG visuals are polished and final (social media, thumbnails) but cost ~$0.02-0.09 and aren't editable. JSON diagrams are free and fully editable in excalidraw.com but less polished. Both useful for content pipeline. Kept as skills/tools, not a project — they're utilities, not a workstream.

**Criteria:** Speed: + | Cost: = | Accuracy: = | Scale: +
**Next:** Allen adds KIE_AI_API_KEY to `.env`. Test both skills with real generation.

---

## 2026-04-11 — EstimateOne AI Agent

**Problem:** No automated way to track tenders, awarded projects, or builders on EstimateOne. Team had to manually check the platform. Missing tender opportunities and not cold calling builders systematically.

**Change:** Built full E1 scraper + Google Sheet pipeline:
- `tools/estimateone_scraper.py` — Playwright login + scrape (open tenders, awarded, leads, watchlist, builder directory)
- `tools/e1_to_sheet.py` — push to 6-tab Google Sheet as "tender inbox"
- `projects/eps/agents/eps-estimateone-agent.md` — agent prompt
- `automation/com.enriquezOS.estimateone-scraper.plist` — daily 6AM launchd

**Why:** E1 has no API. Considered email parsing (only partial data) vs Playwright scraper (full access). Chose scraper — gets everything including builder directory (13K+ builders). Sheet over Pipedrive because not every tender is worth a deal — sheet is the review layer. Text parsing for tenders (reliable), DOM parsing for builder directory (fixed column structure, no junk).

**Criteria:** Speed: + | Cost: + ($0, runs locally) | Accuracy: + (DOM parser for builders, text parser for tenders) | Scale: + (handles 13K builders, 500+ pages)

**Next:** Enrich top builders with contact details. Cross-check vs Pipedrive. Install daily automation. Fix leads parser edge cases.

---

## 2026-04-11 — Video editing agent + pipeline

**Problem:** No automated editing workflow. Allen would need to manually edit raw footage in CapCut or similar — slow, repetitive, not scalable.

**Change:** Built `tools/edit_video.py` (CLI pipeline), `projects/personal/agents/personal-video-editor.md` (interactive agent), updated `content-formats.md` with Hormozi editing specs, generated synthetic SFX in `tools/assets/sfx/`.

**Why:** Full local stack (FFmpeg + Whisper + auto-editor) over cloud editing APIs — zero ongoing cost, no API limits, runs offline. Synthetic SFX generation over downloading from pixabay — removes external dependency. ASS subtitles over SRT — supports the Hormozi caption style (font, color, positioning). Crop-based zoom over zoompan filter — more predictable behavior for punch-in effect.

**Criteria:** Speed: + (one command runs full pipeline) | Cost: + ($0, all local) | Accuracy: = (needs real-footage testing to tune) | Scale: + (handles any length, batch-ready)

**Next:** Test on real footage. Tune silence threshold and zoom detection. Consider `/edit-video` skill entry point.

---

> Entries before 2026-04-10 archived in [DECISIONS-archive.md](DECISIONS-archive.md)
