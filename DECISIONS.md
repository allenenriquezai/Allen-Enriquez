## 2026-04-20 — Reel-3 shipped + hook sticker locked + fast overlay SOP
**Problem:** Needed (1) a repeatable hook-sticker visual identity every reel uses on top of Allen's face, (2) a faster iteration path than re-rendering Hyperframes (~8 min) every time a text overlay changes, (3) a reliable way to composite face + animation + sticker when Hyperframes freezes the face mid-playback.
**Change:**
- Locked hook-sticker style in `memory/feedback_hook_sticker_style.md` — dark navy pill (#071020) + 5px cyan (#02B3E9) border + strong outer glow + Montserrat 900 uppercase white text with layered black stroke. Replaces earlier yellow sticky-note direction (rejected).
- Saved captions style in `memory/feedback_captions_style.md` — Montserrat 900 68px, layered text-shadow stroke (never `-webkit-text-stroke`), scale-1.16 active-word pop + cross-faded blue-word overlay, bottom:280px positioning, 6–7 word segments hard-cut on next segment.
- Saved Chrome-headless PNG pattern in `memory/feedback_overlay_png_chrome_headless.md` — `chrome --headless=new --virtual-time-budget=4000 --screenshot` produces transparent-bg PNGs in ~2s; ffmpeg `overlay=X:Y:enable='between(t,T1,T2)'` composites onto already-rendered reels in <30s.
- Added 3 new SOP sections to `.claude/skills/short-form-video/SKILL.md`: hook sticker spec, Chrome-headless fast iteration, and three-input ffmpeg composite (face base + overlay render + sticker PNG) that sidesteps Hyperframes' MOV-freeze and ambient-bg-DOM-bleed bugs.
- Created `projects/personal/videos/ready/` as symlink-only aggregator for upload-ready finals (avoids duplicate MP4s, keeps project folders self-contained).
- Shipped reel-3 ("5 Things AI Agents Do For Business Owners & Professionals") as proof-of-recipe using the new three-input composite + spy-avatar SVG in scene 4.
**Why:** Hyperframes' screenshot-capture mode is triggered by raw `requestAnimationFrame()` in our compositions — each full render is ~8 min. Chose Chrome-headless PNG + ffmpeg overlay for text iteration over switching the render mode (would require deep compositional refactor and lose the GSAP ergonomics). Chose three-input ffmpeg composite over fixing Hyperframes' face-freeze/DOM-bleed because root-cause fix is framework-level and this gives us a reliable, reproducible shipping path today. Symlinks over copies because Allen explicitly flagged duplicate storage as clutter.
**Criteria:** Speed: + (text-overlay changes now 30s instead of 8min; symlinks save 50MB per reel) | Cost: = | Accuracy: + (recipe is verifiable with frame-check; hook sticker standardized across reels) | Scale: + (SOPs documented in SKILL.md so next reel follows same path without re-discovery)
**Next:**
- Validate the SOP on reel-7 ("Are You Tired Of AI Emails") — if it flows smoothly, the recipe is production-grade.
- Consider promoting the hook-sticker HTML generator into `tools/` as a parameterized script (`tools/generate_hook_sticker.py <title> <subtitle> <out>.png`) so future reels don't re-copy the HTML scaffold.
- Investigate whether switching Hyperframes' render mode (remove raw `requestAnimationFrame` detection trigger) would cut the 8min floor — would enable full re-renders for animated overlays too.

---

## 2026-04-20 — Week 1 reel scripts v4 (Tue–Sun calendar, 6 options/day)
**Problem:** Week 1 v3 had 10 scripts but only 3 filmed + mixed "liked/rejected/rewrite" status. Allen wanted a logically ordered calendar where he can pick 2 reels/day from 6 options without decision friction. Two reels (1 + 2) shared the same CTA keyword (AGENT), risking DM flow collisions.
**Change:**
- New file `projects/personal/content/scripts/week1-reels-v4.md` — 34 scripts across Tue–Sun: 1 existing liked reel as Option A per day + 5 new (Sun = 2 As + 4 new). 30 new scripts total including Reel 10 rewrite
- Reused topic-backlog-v2.md as pre-validated source pool (Sabrina tutorials / Dan Martell lists / Kane Kallaway fundamentals / Angelica Automates proof / Nathan Hodgson objection-removal)
- Replaced Google Doc `1Y5mAR_Fjsj6Ap5OdgJ3Ziw6XB6WXDRTUO779tUHtt7w` content in-place via Docs API (deleteContentRange + insertText + per-line updateParagraphStyle for H1/H2/H3) — 1,166 lines, 50 headings
- Renamed doc from "Week 1 Reel Scripts v3 — 10 Reels" → "Week 1 Reel Scripts v4 — Tue–Sun Calendar"
- Moved doc to `My Drive > 1. Personal Brand > Contents` via Drive API (addParents + removeParents)
- Rewrote Reel 10 with Allen's "Build automation using Claude" angle. Dropped Reel 4 per Allen
- All 38 CTA keywords unique; Mon Reel 2 flagged to switch AGENT → AGENTS5 before posting
**Why:** Chose in-place doc replacement over new v4 doc + archive v3 — preserves Google Doc version history for rollback, keeps one link stable, no broken references elsewhere. Picked talking-head-only scripts (not screen recording) because v3 locked that constraint and current production is stable on it; Week 2 will loosen per content-calendar.md phase 2. 6 options/day (not 3) because Allen's decision time is the bottleneck — more options = faster pick.
**Criteria:** Speed: + (Allen scans one doc, picks 2, films — no re-prompting me for scripts) | Cost: = | Accuracy: + (all scripts filtered through H.E.I.T. + CCN + 3rd grade + viewer-first + unique CTA) | Scale: + (in-place doc replacement pattern reusable for future weeks)
**Next:**
- Track which Option letter wins each day → feed into Week 2 topic selection
- Build DM deliverables on-demand per memory rule (first real comment → build)
- Week 2 calendar can reuse push_reels_v4 script pattern — consider promoting `/tmp/push_reels_v4.py` logic into `tools/` as `update_gdoc_content.py`
- Add CTA-uniqueness check to content-creation workflow so collision like Mon Reel 1+2 doesn't repeat

---

## 2026-04-20 — First AE Hyperframes reel shipped + short-form recipe locked
**Problem:** Needed a repeatable, brand-consistent Hyperframes reel pipeline before shipping 2 more reels this week. First build (reel-2, What Is an AI Agent) required figuring out: face+animation composite, full-duration karaoke captions, brand hook sticker, and which GSAP props keep Hyperframes in fast render mode.
**Change:**
- Built `projects/personal/videos/reel-2/` — 7 scene compositions + karaoke captions + ambient bg + transparent-bg root, composite via ffmpeg chroma-key + brand sticker overlay
- Shipped `renders/final-v4.mp4` (55.56s, 1080×1920, 23MB) through iterations v2 → v3 (sticker added) → v4 (fast-mode refactor)
- Generated brand hook sticker via Pillow: dark panel + blue glow + white Montserrat 900, 2-line layout (`assets/hook-sticker.png`)
- Locked the full recipe into `projects/personal/workflows/content/video-editing.md` — project scaffold, sticker spec, karaoke caption rules, scene composition rules, composite ffmpeg command, fast-mode render rules
- Refactored all 10 compositions to fast-mode-preferred props (removed: blur filter tweens, onUpdate typewriters, color/boxShadow/className tweens). Replaced with: scale+fade entries, per-char opacity stagger, sibling .glow divs, layered word spans for karaoke, opacity on .step-active-bg
**Why:** Committed to Hyperframes after yesterday's consolidation — first real output validated the stack and surfaced the speed/quality trade-offs. Chose chroma-key composite (face visible through transparent bg zones) over alpha-channel render because Hyperframes webm output was yuv420p not yuva420p. Kept GSAP despite screenshot-mode trigger — full native-timing refactor deferred; visual quality stays identical with ~40% speedup (4m25s vs 7m).
**Criteria:** Speed: + (40% faster render, locked recipe = no re-discovery next reel) | Cost: = | Accuracy: + (verified frames, karaoke synced to source-time whisper transcript) | Scale: + (SOP doc enables reel 3-4 without re-figuring)
**Next:** Build 2 more reels on this recipe. Future upgrades when needed: (1) true 5x speedup via full GSAP→native data-* timing rewrite, (2) Nate Herk heavy motion (whip transitions, chrome gradient text, camera dollies, visual callbacks) for brand hype reels, (3) 4-6s CTA hold for classic outro land.

---

## 2026-04-19 — Hyperframes becomes primary video stack
**Problem:** Video skills split across global (`~/.claude/skills/` — Nate Herk's Hyperframes suite) and project (`.claude/skills/video-edit` — old Pillow/FFmpeg). Two incompatible engines. Allen wanted ownership + one unified system.
**Change:**
- Moved 7 Hyperframes skills to `.claude/skills/`: hyperframes, hyperframes-cli, hyperframes-registry, gsap, make-a-video, short-form-video, website-to-hyperframes
- Deleted `.claude/skills/video-edit/` + empty `.claude/skills/edit-video/`
- Rewired `.claude/skills/content/SKILL.md` router + `projects/personal/workflows/content/content-formats.md` to point at Hyperframes skills
- Updated memory `project_hyperframes_video_stack.md` → PRIMARY; deleted `project_video_pipeline.md` + `project_reel_pipeline.md`
**Why:** Absorb (Option A) beats route (Option B) because Allen wants to layer brand customization on the skills. Route would leave customization awkward across global/project boundary. Trade-off: lose auto-updates from Nate's repo. Acceptable — manual pull when new features ship.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Delete `tools/edit_video.py` + `personal-video-editor.md` agent (pending). Build `enriquez-hyperframes` brand overlay (#02B3E9, Roboto Mono + Montserrat, 90pt captions, AE logo). Test first real reel.

---

## 2026-04-19 — Reel script rewrite (Week 1 trim + Week 2 pool)
**Problem:** Week 1's 14 reels were generated in bulk before angle was locked. Every fix-pass on Reel 1 exposed a new misalignment (hook too soft, distancing voice, overlapping EXPLAIN/ILLUSTRATE, false Allen-specific claim in Reel 2). 5 reels contradicted the main teach or duplicated proof. No fresh topic pool for Week 2+. Allen wants to read variations + pick winners, not iterate line-by-line.
**Change:**
- Killed reels 6, 8, 9, 11, 13 from source doc `1DZ2gI5nUIdMVYSgOZo__rq8gyEXHYEIsRKHjqXev-xU`. Remaining: 1, 2, 3, 4, 5, 7, 10, 12, 14.
- Reel 1 rewritten end-to-end (hook / explain / illustrate / takeaway / CTA — all passes applied iteratively)
- Reel 2 truth fix: "I bought every AI tool" → "I started with n8n. Connected ChatGPT, Zapier, the works." (per memory rule — only claim what Allen has lived)
- Voice sweep across reels 2–13: 8 distancing phrases replaced (most people / everyone / they → you)
- Source doc formatting upgrade: yellow highlight on all spoken script lines + one-sentence-per-line teleprompter layout
- Competitor research: `projects/personal/reference/intel/competitor-scripts.md` — 27 pieces from Justyn the AI Guy (TikTok) + Sabrina Ramonov (YouTube/TikTok/Substack)
- Fresh Week 2 pool: 30 reel scripts in new doc `19vYDtUWhPWhcRYD2uFx97JU3Lh5HqaXKakUXqacUk9E` across 5 categories (Proof / Tutorials / Mindset / News-hook / PAS), ghostwriter-grade rewrite applied after first pass
- 2 new memory rules: `feedback_reels_one_to_one.md` (1:1 voice), `feedback_cta_deliverables_on_demand.md` (don't pre-build DM lead magnets)
**Why:** Line-by-line patching exposed root cause: scripts generated before angle locked. Better to trash weak ones + mass-generate fresh pool than patch forever. Justyn/Sabrina research surfaced useful FORMAT patterns (caption SEO, news-hook templates, comment-for-DM funnel) but their topics didn't match Allen's niche — noted to research topic-matched creators (Nick Saraev / Liam Ottley / Brand Nat / Kane Kallaway) in future pass. Agent delegation used for bulk generation (50 then 30 variations) — kept main context clean, parallelised quality pass. Sabrina's "AI chatbot for lead gen, follow up FAST and FIRST" = Allen's EPS story exactly → direct template for his first proof-lane reel. Gap flagged: neither Allen nor I have a "mine 1 long-form → 10 clips" loop yet — top strategic finding from research.
**Criteria:** Speed: + (30 fresh scripts in one agent pass, beats line-by-line patching) | Cost: = ($0 — web search + agent delegation only) | Accuracy: + (truth rules enforced via memory, $40K fabricated claim removed) | Scale: + (variation doc structure + memory rules apply to future script batches)
**Next:** Allen reads 30 fresh scripts, picks winners to film. Decide if Speed to Lead reel copies from variations doc into Week 1 source doc. Research pass 2 on topic-matched creators. Once first long-form asset ships (YouTube or Substack), build the clip-farm loop.

## 2026-04-19 — Hyperframes video stack installed + Week 1 reel pipeline
**Problem:** Allen saw Nate Herk-style motion-graphic reels (AE-branded overlays, karaoke captions, animated diagrams) and wanted that look for Week 1 content. Existing Python pipeline (`tools/edit_video.py`) handles talking-head cuts/captions/zoom but can't do branded motion graphics or generated animation scenes. Shooting all 6 Week 1 reels tonight — needs a fast path to final production-ready shorts in 6 hours.
**Change:**
- Installed HeyGen Hyperframes (HTML+GSAP+Puppeteer → MP4). 7 skills global (`~/.claude/skills/`: hyperframes, hyperframes-cli, gsap, hyperframes-registry, website-to-hyperframes, make-a-video, short-form-video).
- Cloned Nate Herk's `hyperframes-student-kit` (12 reference projects) to `projects/personal/reference/hyperframes-student-kit/`.
- Created `projects/personal/videos/reel-1` through `reel-6/` workspace.
- Scaffolded + built first composition: `projects/personal/videos/reel-1/index.html` — 42s EXPLAIN + ILLUSTRATE animation (13 scenes, AE brand: #02B3E9 blue, dark navy, Roboto Mono + Montserrat, blue glow) — Allen approved the look.
- Rendered draft MP4 (2.9 MB, clean lint).
- Added Hyperframes section + two-pipeline table to `projects/personal/workflows/content/video-editing.md`.
- New memory: `project_hyperframes_video_stack.md`, indexed in MEMORY.md.
- Brand asset folder: `projects/personal/reference/brand/` for `brand-guidelines.png` (Allen to drop).
- Logged DM magnet backlog: `projects/personal/TODO.md` — build only on comment trigger.
**Why:** Two pipelines beats one. Python stays for plain talking-head (fast, proven). Hyperframes takes motion-graphic reels + brand polish + from-scratch animation scenes (replaces need for screen recordings on teaching beats). `npx skills add heygen-com/hyperframes` chosen over manual clone — installs skills that teach Claude framework-specific patterns (data-* attrs, window.__timelines, composition scaffold) not in generic web docs. Student kit cloned separately as reference so Allen's own videos don't live inside someone else's repo. DM magnets deferred to trigger event — no proof of demand, don't build speculatively.
**Criteria:** Speed: + (animations generated from code, no stock footage hunt) | Cost: = ($0 — Hyperframes free/open source) | Accuracy: + (deterministic renders, brand-system compliant by design) | Scale: + (template one reel, clone for N reels)
**Next:** Allen shoots 6 face-cam reels tonight → drops raw.mp4 per slot → build compositions using Reel 1 as template + karaoke captions + AE intro/outro → render finals → upload to Blotato. Second pass once volume built: evaluate if Python pipeline still needed or if Hyperframes absorbs all formats.

## 2026-04-18 — US painter sales asset stack + Enriquez OS app reorg
**Problem:** (1) Cold-calling US painting companies produced warm interest but lost every lead at email stage — no lead magnet, landing page, calendar, or follow-up. (2) Allen couldn't see which automations were running or rotting — PH outreach, cold calls, content all in different files/sheets/apps. Wanted "one app to operate everything."
**Change:**
- US painter sales stack: `projects/personal/sales-assets/` (lead magnet PDF, one-pager PDF, follow-up sequence, invoice template, demo video script, two `build_*.py` PDF generators) + `projects/personal/landing-page/` (static HTML + CSS, GitHub Pages-ready) + `tools/cold_call_followup.py` (4-email Day 0/2/5/10 automation, attaches PDF, tracks JSON state).
- Campaigns scaffolded: `projects/personal/campaigns/{us-painters,ph-outbound}/{offer.md, icp.md, assets.md, pipeline.md}`.
- Library scaffolded: `projects/personal/library/{notes,projects,links}/`.
- Dashboard reorg: 5 tabs (Personal/Learn/Work/Content/Outreach) with sub-pills, replacing Home/Habits/Learn/Brief/Spend. New blueprints `routes_ops.py` (4 endpoints aggregating PH outreach + cold call + content state) and `routes_notes.py` (CRUD on library markdown). New JS `static/{ops.js, library.js}`. `app.py` registers both. Gunicorn restarted, all endpoints live.
- Memory: `project_personal_brand_strategy.md` rewritten (US painters cold-call primary, supersedes "PH content-led" framing). `reference_jordan_platten.md` added (deferred Q3+).
**Why:** Cold calls already produced warm interest — gap was conversion infrastructure, not lead volume. Quote builder ($297-$497 entry) chosen because Allen runs it daily at EPS for $114K/mo — provable from day one. Lead-gen-as-a-service rejected (Allen can't deliver leads today). Free Google Calendar over paid Calendly per Allen preference. Dashboard reorg done as render-only over markdown/JSON files — single source of truth in repo, AI keeps reading same files. Cloud migration considered, deferred — local solid first. CRM Kanban merge deferred — link from Outreach tab for now. 4 parallel sub-agents used for the build wave (campaigns + 2 blueprints + UI refactor) — cut wall time ~4x vs serial.
**Criteria:** Speed: + (5-min PDF build, 72hr offer, one-glance ops view) | Cost: = ($0 — no paid tools added) | Accuracy: + (single source of truth preserved, no data duplication) | Scale: + (campaigns folder template fits N campaigns, library accepts N notes/projects)
**Next:** Replace calendar + demo video placeholders. Lock PH offer pricing. Build PH lead magnets per niche. Make actual cold calls / send actual DMs (assets exist, no leads through them yet). Future: chat-as-action-bus, CRM Kanban merge into Outreach tab, cloud migration.

## 2026-04-18 — PH outbound outreach system
**Problem:** No PH market outbound for personal brand consultancy. Allen refuses daily manual prospecting/writing. Cold FB/IG DM automation = ban risk. Pure $0 rules out paid tools.
**Change:** `tools/outreach.py` (main CLI: discover, enrich, queue, log-sent, followups, replies, stats). 4 modules: `outreach_sources.py` (Places + BusinessList + JobStreet + Kalibrr + FB inbox), `outreach_enrich.py` (website + Snov + Hunter + FB Graph + Haiku hook), `outreach_messages.py` (12 templates + Haiku generator + queue markdown), `outreach_lifecycle.py` (log-sent parser + followup detector + reply drafter). `projects/personal/templates/outreach/` 12 template files. `outreach_config.yaml` limits + segments + guardrails. 2 launchd plists (daily 6am + Sunday 3am). `workflows/sales/ph-outreach-system.md` SOP. `/personal-ph-outreach` skill. 2 new sheets (PH Outreach CRM, PH FB Groups curated).
**Why:** Automate everything up to send, keep send manual (platform ban protection). Haiku 4.5 (~$3-5/mo) chosen over pure $0 templates because personalisation = 3-5x reply rate. Recruitment/VA + real estate brokerages locked as segments (Tier 1 ICP from research: budget + daily pain + tech-literate). Skipped ManyChat (engagement too low), WhatsApp outbound (opt-in funnel barrier), LinkedIn paid tools (budget), dental/small biz (phase 2). 4 parallel sub-agents built Phases 2-5 simultaneously, cut build time ~4x.
**Criteria:** Speed: + | Cost: - (Haiku $3-5/mo) | Accuracy: + | Scale: +
**Next:** Allen adds API keys (Places required, Snov/Hunter/FB Graph optional). Launchctl load. Join 5 Priority-1 FB groups. First real queue fires Apr 19 6am — validate voice quality on first 5 messages. Verify BusinessList/JobStreet/Kalibrr selectors live.

## 2026-04-18 — Feedback loop — outcome tracking + pattern detection
**Problem:** Outbound actions (emails, quotes, content, outreach) had no closed feedback loop. Outcomes vanished — no tracking of replies, win rates, or content performance. Intel docs updated manually. Workflow SOPs never improved from data.
**Change:** `tools/log_outcome.py` (outcome logger CLI, 7 action types). `tools/check_outcomes.py` (EOD checker: Pipedrive deal stage, Gmail reply search, outreach log cross-ref, manual content queue; pattern detection across template/tag/domain; intel doc auto-append; workflow_flags.json generation). `automation/com.enriquezOS.eod-ops.plist` chained after crm_sync. `.claude/skills/start/SKILL.md` added Outcome + Workflow Flags sections.
**Why:** Deterministic rules (5+ data points, 1.5x+ ratio) over LLM — zero cost, catches 80% of signal. Single JSONL log for append speed + grep. Intel docs append-only preserves history. Blotato/paid tools deferred until content volume justifies. Social APIs (Meta Graph, YouTube Data) deferred pending account setup decisions.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Build Meta Graph + YouTube Data checkers once Allen confirms channel/page/IG account setup. First real data from weekend content batch.

## 2026-04-17 — Quote workflow: hyperlinks + deal value
**Problem:** Pipedrive notes showed raw URLs instead of clickable hyperlinks. Deal value was never set after quoting — pipeline reports showed $0 for quoted deals.
**Change:** `qa_quote.py` — added `_urls_to_links()` to convert email body URLs to `<a href>` in Pipedrive notes. `update_pipedrive_deal.py` — added `--field value --value` support. `create-quote.md` — added deal value step to Stage 4d.
**Why:** Allen sends quotes via Pipedrive (copy from note). Raw URLs look unprofessional and require manual linking. Deal value needed for pipeline reporting accuracy.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: =
**Next:** Verify hyperlinks render correctly in next quote sent via Pipedrive.

## 2026-04-17 — Context diet — personal brand token reduction
**Problem:** Personal brand tasks loaded CONTEXT.md + 8 mandatory blocking files (~11,500 tokens). Voice rules, hook patterns, quality checklist, audience notes, and script structures were duplicated 2-3x across files.
**Change:** Deduplicated 6 sections across 4 files. Inlined unique memory bits (team, timeline, self-quote) into CONTEXT.md. Replaced "load all 8" blocking loader with task-type tiered loading. Updated content skill and feedback memory. Total: CONTEXT.md, hormozi-style-guide.md, content-creation.md, icp-language.md, content/SKILL.md, feedback_content_load_context.md.
**Why:** Graphify plugin (code graph) was considered but only indexes code via Tree-sitter — can't touch markdown context files. Deduplication + conservative tiers chosen over strict tiers to preserve output quality. Content writing tier always includes ICP language to prevent generic scripts.
**Criteria:** Speed: = | Cost: + | Accuracy: = | Scale: =
**Next:** Test with `/content` skill. Consider similar diet for EPS context.

## 2026-04-17 — CRM sync baseline fix + quote template restructure
**Problem:** CRM sync missed SM8 Work Order status for deals that were never cached or already Work Order on first sync (Jeevan Paila case). Job description templates mixed deal-specific exclusions into GENERAL EXCLUSIONS section.
**Change:** `crm_sync.py` — added baseline mismatch check after transition detection; expanded `advance_from` to include SITE VISIT + QUOTE IN PROGRESS stages. 16 job description templates — renamed GENERAL EXCLUSIONS/QUOTE EXCLUSIONS → EXCLUSIONS. `internal_painting.md` — restructured SCOPE OF WORK with A/B/C subsections + C. NOTES for deal-specific items. Updated `create-quote.md` and `qa.md` section references.
**Why:** Baseline check needed because transition-only logic silently missed deals where SM8 was already ahead. Exclusion rename because GENERAL implies another type exists; deal-specific items belong in SCOPE OF WORK → C. NOTES where they're contextual.
**Criteria:** Speed: = | Cost: = | Accuracy: + | Scale: =
**Next:** Run sync live to apply 5 pending DEPOSIT moves. Consider adding A/B/C structure to other painting templates.

## 2026-04-17 — SM8 → Pipedrive full sync + automation health
**Problem:** SM8 job status (Work Order, Completed), site visits, and activities weren't reflected in Pipedrive. Allen had to check two systems. launchd automations had stale exit codes and no monitoring.
**Change:** `crm_sync.py` — restructured to sync ALL SM8 activities to Pipedrive (not just diff deals), auto-advance to DEPOSIT on Work Order, UUID-based dedup via `posted_to_pd` column. `eps-dashboard/app.js` — removed SM8 note filter, added color-coded note borders. New: `com.enriquezOS.crm-sync.plist` (10-min polling), `automation_status.py` + plist (daily WhatsApp report at 3 PM). Fixed 4 shell scripts with 3x retry logic. Symlinked all plists.
**Why:** Allen works in Pipedrive, ops team works in SM8. Polling chosen over n8n/webhooks because Allen wants zero external tool setup. 10-min interval balances freshness vs SM8 rate limits.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Add SM8 SMS/email/call sync. Monitor 429 rate limits at 10-min polling frequency.

## 2026-04-17 — Split CRM skills: /personal-crm + /eps-crm
**Problem:** Single `/crm` skill only covered personal brand Google Sheets CRM. EPS Pipedrive CRM had 5 CLI tools but no skill wrapper — required manual tool invocation or workflow doc navigation.
**Change:** Renamed `.claude/skills/crm/` → `.claude/skills/personal-crm/`. Created `.claude/skills/eps-crm/SKILL.md` wrapping `crm_monitor.py`, `crm_sync.py`, `pipedrive_activities.py`, `pipedrive_create.py`, `update_pipedrive_deal.py`.
**Why:** Allen needs quick invoke for both CRM systems. Naming was ambiguous — "CRM" could mean either. Skill wrapper removes need to remember tool names and CLI flags.
**Criteria:** Speed: + | Cost: = | Accuracy: = | Scale: +
**Next:** Test both skills live. Consider adding single-deal deep lookup action.

## 2026-04-16 — Carousel generator: profile header + no-profile flag
**Problem:** Carousel slides needed optional profile header (circular photo, name, handle) like Hormozi/Dan Martell style. Also needed ability to generate without it for Canva workflows.
**Change:** `tools/generate_carousel.py` — added `draw_profile_header()`, `--no-profile` CLI flag, `show_profile` param on title/CTA renderers. `projects/personal/assets/profile.png` — saved profile photo. Updated default handle to @allenenriquezz.
**Why:** Allen uses Canva for final styling, so needs clean slides without baked-in branding. Profile header stays available for standalone PNG output.
**Criteria:** Speed: + | Cost: = | Accuracy: = | Scale: +
**Next:** Canva Connect MCP integration for direct text push into Canva templates

## 2026-04-16 — Quote template section spacing fix
**Problem:** Job description sections in Google Docs ran together with no visual separation. Allen flagged it looked cramped.
**Change:** `tools/fill_quote_template.py` line 177 — changed `"\n".join()` to `"\n\n".join()` for job_description array. Adds blank line between sections, keeps bullets within sections compact.
**Why:** `\n` only separates array items by one line break (no visual gap). `\n\n` adds a blank line between sections without affecting intra-section bullet spacing.
**Criteria:** Speed: = | Cost: = | Accuracy: + | Scale: +
**Next:** Monitor if spacing is sufficient or needs `\n\n\n` for bigger gaps

## 2026-04-16 — Email format rules + liquid nail add-on saved to SOP
**Problem:** Email format preferences (bullet points, bold concerns, discount phrasing) and liquid nail service add-on not documented. Next session would lose context.
**Change:** `projects/eps/workflows/sales/create-quote.md` — added email format rules section. `projects/eps/job_descriptions/misc_painting_repairs.md` — added liquid nail add-on with one-bullet-per-section pattern.
**Why:** Allen corrected email draft from paragraphs to bullet points. Liquid nail is a recurring add-on that should be templated.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Add more add-ons to misc template as they come up

## 2026-04-16 — QA tool fix: accept painting method section
**Problem:** qa_quote.py hardcoded "CLEANING METHOD" as required section for all quotes. Painting jobs always failed QA.
**Change:** `tools/qa_quote.py` — now accepts either CLEANING METHOD or PAINTING METHOD. Removed GUARANTEES from hard requirement.
**Why:** Painting job descriptions use "PAINTING METHOD" per their templates. QA was blocking valid painting quotes.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: =
**Next:** Consider service-type-aware section validation (paint vs clean templates have different required sections)

## 2026-04-16 — SOP update: Pipedrive address is custom field
**Problem:** Quote workflow assumed address was a standard Pipedrive field. It's always a custom field — caused missed address lookup.
**Change:** `projects/eps/workflows/sales/create-quote.md` — updated Stage 1 intake to specify address lives in custom deal field.
**Why:** Allen corrected after address was missed on Ronda Jones quote (Deal #1299).
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: =
**Next:** None

## 2026-04-16 — CRM dropdown cleanup + sticky save button
**Problem:** "Not Interested - No Convo" redundant with "Hung Up - No Convo". Dropdown order didn't follow natural call escalation. Save button in kanban modal required scrolling — bad for accessibility.
**Change:** Removed "Not Interested - No Convo" from DROPDOWN_VALUES + DEAD_OUTCOMES (personal_crm.py), OUTCOME_TO_STAGE (crm_kanban/app.py). Reordered dropdown to escalation flow. Migrated 4 sheet rows. Updated validation on 10 tabs. Made modal footer sticky (flex col + overflow-y on body).
**Why:** Allen uses "Hung Up - No Convo" for same purpose. Fewer options = faster calling flow. Sticky save = less friction during high-volume calling sessions.
**Criteria:** Speed: + | Cost: = | Accuracy: = | Scale: =
**Next:** Monitor if any other dropdown options are redundant after more calling sessions.

## 2026-04-16 — Jake-style CLAUDE.md trim
**Problem:** CLAUDE.md was 131 lines (~1,500+ tokens), loaded every conversation. Half was behavior rules, design principles, correction loops that only matter once inside a workspace. Wasted tokens on every message.
**Change:** Trimmed CLAUDE.md to 73 lines — pure map + routing + tools access. Moved Design Principles, Behavior, Change Tracking into both workspace CONTEXT.md files. Added Token Management table (explicit load/don't-load per task type). Removed sections already duplicated in CONTEXT.md files (Correction Loop, Quality).
**Why:** Following Jake Van Clief's (RinDig) pattern more closely. His rule: "right context, not all context." CLAUDE.md should be a map (~800 tokens). Workspace-specific rules load on demand when that workspace is active. Tools & Access table stays in CLAUDE.md so sessions always know their capabilities.
**Criteria:** Speed: + | Cost: + | Accuracy: = | Scale: =
**Next:** Test in fresh sessions. Verify EPS and personal tasks still route correctly and load the right context.

## 2026-04-15 — Workspace restructure: kill agents, merge into workflows
**Problem:** Preferences scattered across 5+ locations (agent files, workflow files, memory files, multiple CLAUDE.md files). Corrections saved to memory but missed during execution because subagents didn't read memory, and even main session missed preferences when info was in the wrong file. Same corrections needed repeatedly.
**Change:** Deleted 23 agent files, merged into 28 department-organized workflow SOPs. Killed workspace CLAUDE.md files, replaced with CONTEXT.md. Rewrote root CLAUDE.md as lean routing table. Updated 6 skills to read workflows directly instead of spawning agents. Baked 7 memory-stored quoting preferences into create-quote.md. Added correction loop to CLAUDE.md (corrections → update workflow file, not just memory).
**Why:** Inspired by Jake Van Clief's three-layer architecture (CLAUDE.md → CONTEXT.md → workflows). His simpler pattern gives more deterministic results because: one source of truth per task, main session keeps all context, corrections actually stick. Agent spawning was an optimization that cost accuracy — principle #1 (less Allen input) and #2 (accuracy) both suffered.
**Criteria:** Speed: = | Cost: + | Accuracy: + | Scale: +
**Next:** Test `/quote` and `/content` in fresh sessions. Fine-tune workflow files based on real-world use. Trim verbose workflows after testing.

## 2026-04-14 — Quoting process hard rules + fill_quote_template fix
**Problem:** Quote creation had multiple process failures: mob fees added without asking, job descriptions rewritten instead of copied from templates, line items lumped together instead of per component/apartment/level, docs left unfilled, wrong pipeline used, totals changed during reformatting.
**Change:** Updated `eps-quote-agent.md` (added General hard rules + Job Description hard rule), `create-quote.md` workflow (added Hard Rules section + job description rule), `fill_quote_template.py` (changed `\n\n` join to `\n` for compact spacing), `feedback_quoting_process.md` memory (consolidated 7 rules). Added doc naming convention rule.
**Why:** Allen corrected the quoting process 5+ times in one session. Rules needed to be enforced in the actual agent/workflow files, not just memory. Templates exist for job descriptions — never invent. Rates exist in pricing.json — never make up prices.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Consider automating doc naming in `create_quote_folder.py` to match the convention instead of using deal ID format.

## 2026-04-14 — Reel video pipeline: doodle illustrations + Hormozi captions
**Problem:** "4 Levels of AI" reel had no visual illustrations during teaching sections. Previous version used detailed UI mockups that were too small for phone screens. Needed animated visuals synced to voiceover, Hormozi-style captions, and Allen's face preserved on hook/CTA.
**Change:** `projects/personal/.tmp/video_test/full_video_v4.py` — complete renderer with doodle illustration primitives (person, arrows, sparkles, boxes, check/error icons), 4 level drawing functions synced to real transcription timestamps, real Make/Zapier/n8n logos, Hormozi caption system. `full_video_v5.py` — compositor that loads Allen's face from MOV for hook/CTA, doodle frames for L1-L4, 90pt bold captions with yellow highlight box, MEDVi screenshot overlay with blurred face. Whisper transcription for word-level timing.
**Why:** Pillow + FFmpeg over Remotion — zero cost, Python-native, no rewrite needed. Doodle style over UI mockups — bolder on phone. Yellow marker box over colored text — Hormozi standard. Face on hook/CTA — personal connection. Compressed center layout — where eyes go on phone.
**Criteria:** Speed: + | Cost: + (zero) | Accuracy: + | Scale: = (manual per reel, template potential later)
**Next:** Build reusable reel template. Auto-editing pipeline (auto-editor + faster-whisper). First content batch recording.

## 2026-04-14 — E1 tender pipeline: vision analysis + smart filtering + Pipedrive attachment
**Problem:** E1 scraper downloaded entire project packages (131 files) but couldn't analyze image-based floor plans. Large specs (1.1M chars) truncated blindly, losing all painting-relevant sections. No way to attach docs or measurements to Pipedrive deals.
**Change:** `tools/analyze_tender_docs.py` — full rewrite with smart file filtering (RELEVANT/SKIP keywords), Claude Vision via pdf2image+Haiku for floor plans, keyword section extraction for specs, finishes schedule classification. `tools/attach_plans_and_notes.py` — new tool for Pipedrive file attachment (curl multipart), measurement notes (painting: ceilings/walls/skirting/doors; cleaning: ceiling area), builder contact/org creation and linking.
**Why:** Noticeboard tenders have 100+ files per project — need automated filtering. Image-based architectural PDFs can't be text-parsed. Keyword extraction beats truncation for massive specs. Builder contacts need to exist in CRM for follow-up workflow.
**Criteria:** Speed: + | Cost: + | Accuracy: + | Scale: +
**Next:** Reformat deal notes (hard to read). Create quotes from measurement data. Build Noticeboard Open download flow.

## 2026-04-14 — SM8 ↔ Pipedrive auto-linking + dashboard SM8 intelligence
**Problem:** Dashboard showed "no SM8 job linked" for deals like Ronda Jones even though SM8 had the job (EPSP1937) with site visit data and photos. Root cause: Pipedrive custom field was empty, crm_sync only looked at that field, data_loader silently filtered out empty sm8_status, and EOD flagged it. Dashboard had no SM8 activity history — someone looking at a deal card had no idea what happened.
**Change:** `tools/crm_sync.py` — address-based fallback SM8 matching (with street-level specificity guard), auto-link job # back to Pipedrive, flag SITE VISIT same as DEPOSIT, cache SM8 activities/staff/files to SQLite with enriched notes (Job Check Out, Booking labels + travel/time). `tools/eps-dashboard/data_loader.py` — removed WHERE filter, added logging. `tools/eps-dashboard/app.py` — extended deal detail API, added project detail API. `tools/eps-dashboard/static/app.js` — light mode, bigger text, SM8 activity timeline, project detail modal, note dedup. `style.css` + `base.html` + `index.html` — light mode.
**Why:** Allen needs dashboard to give complete picture without checking SM8. Address fallback chosen over manual linking — catches all unlinked deals automatically. Generic address guard (must have street number or street word) prevents false positives. Light mode + bigger text per Allen's request.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** SM8 v2 API for Room Scan/SMS/photos. Verify cron order (crm_sync before eod_ops). Could add SM8 job description to deal modal.

## 2026-04-14 — Carousel tool rewrite (Dan Martell style)
**Problem:** Carousel generator produced dark background slides with Impact font — didn't match Allen's preference (white bg, Hormozi/Dan Martell style, large clean text). Tool had no auto-scaling, text overflowed on longer copy.
**Change:** Full rewrite of `tools/generate_carousel.py` — white bg, Helvetica Bold, brand blue (#02B3E9) accents, 4:5 ratio (1080x1350), auto-scale font when text overflows, vertically centered layout. Created `projects/personal/reference/carousel-references/style-reference.md`. Saved `feedback_carousel_style.md` to memory.
**Why:** Allen wants automated carousels matching Dan Martell's clean style — no Canva. Helvetica Bold chosen over Impact (too condensed). Auto-scaling prevents manual font tweaking. 4:5 ratio is optimal feed format.
**Criteria:** Speed: + | Cost: + | Accuracy: + | Scale: +
**Next:** Could add profile photo/avatar support for quote-style carousels. Content agent should enforce 15-word max per slide body.

## 2026-04-14 — Caveman token-efficiency plugin installed
**Problem:** Output tokens expensive and slow. No compression on Claude Code responses.
**Change:** `~/.claude/settings.json` — added SessionStart hook (caveman-activate.js) and UserPromptSubmit hook (caveman-mode-tracker.js). Downloaded 4 hook files to `~/.claude/hooks/`. Installed Node.js via Homebrew.
**Why:** Caveman reduces output tokens ~65-75% while keeping technical accuracy. Fits cost + speed principles. Manual install chosen because Node wasn't available — install script requires it. Existing GSD statusline preserved to avoid conflict.
**Criteria:** Speed: + | Cost: + | Accuracy: = | Scale: =
**Next:** Merge caveman badge into GSD statusline. Test all 3 intensity levels.

## 2026-04-14 — Dashboard stage accuracy + Pipedrive notes in deal modal
**Problem:** Dashboard stage columns didn't match Pipedrive pipelines — tender stages (FOLLOW UP, CONTACT MADE) mixed into deal view, and tenders showed deal-only stages (NEW, SITE VISIT). Deal detail modal had no notes — team couldn't see call notes or deal history without opening Pipedrive.
**Change:** `tools/eps-dashboard/static/app.js` — split stage orders per pipeline type (DEAL_STAGE_ORDER, TENDER_STAGE_ORDER), route tender pipelines correctly, show all columns even when empty, render last 3 Pipedrive notes in deal modal. `tools/eps-dashboard/pipedrive_client.py` — added `fetch_deal_notes()`. `tools/eps-dashboard/app.py` — notes in `/api/deal/<id>` response.
**Why:** Team needs accurate pipeline view without Pipedrive access. Notes give deal context at a glance — limited to 3 to avoid clutter (Allen's call).
**Criteria:** Speed: = | Cost: = | Accuracy: + | Scale: =
**Next:** Named Cloudflare tunnel for permanent URL. Consider caching notes in SQLite to reduce API calls.

## 2026-04-14 — CRM Sync hardening + SQLite cache + recurring visits + dashboard detail
**Problem:** CRM Sync crashed on transient API errors. Wrong address field key. SM8 job lookup failed due to `#` prefix. No persistent state. No recurring client visit history. Dashboard had no detail view or SM8 status. Team couldn't access dashboard remotely.
**Change:** `tools/crm_sync.py` — retry logic, correct field keys, `#` strip, SQLite cache (deals + sync_log + recurring_visits tables), SM8 status change → Pipedrive notes, recurring client sync (7 clients mapped by company_uuid, 41 visits stored). `tools/eps-dashboard/` — deal detail modal, SM8 badges, `/api/deal/<id>` endpoint. Cloudflared quick tunnel for remote access.
**Why:** System needs to already know deal state — no live lookups. Recurring clients need visit history (last visit, notes, issues) without searching SM8 every time. Team is distributed across countries.
**Criteria:** Speed: + | Cost: + | Accuracy: + | Scale: +
**Next:** Wire recurring visits into dashboard project detail. Fix Studio Pilates UUID. Proper domain for dashboard. Populate Win-Back pipeline.

## 2026-04-13 — Google Docs tool + content strategy lock
**Problem:** No way to create Google Docs programmatically on personal account. Content scripts were too long, too generic, and not automation-focused.
**Change:** Built `tools/create_gdoc.py` (create + move to Drive folder). Reworked video scripts to v2.4 — short reels (45-60s hooks) + long reels (2-4 min walkthroughs). Show Claude Code by name. 1 reel/day schedule.
**Why:** Allen needs to edit scripts collaboratively in Google Docs, not in local .md files. Short/long reel split mirrors Sabrina Ramonov's proven format. Claude Code as filter attracts buyers, not hobbyists.
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Film first 4 shorts Wednesday. Screen record systems Sunday. Long reels week 2.

# Enriquez OS — Decision Log

System design decisions, why they were made, and how they score on design criteria.

**Rules:**
- Log architectural/design decisions only — not routine tasks or data updates
- Keep "Change" to 2-3 conceptual bullets — `git log` has the file-by-file detail
- Archive entries older than 2 weeks to `DECISIONS-archive.md`

---

## 2026-04-13 — EPS department restructure + 4 new operations tools
**Problem:** No cross-system sync (Pipedrive ↔ SM8), no automated re-engagement, no EOD ops scan, no tender campaign automation. Agents had duplicate pipeline ID tables and inconsistent patterns. No department structure — flat list of 9 agents.
**Change:**
- Built 4 tools: `eod_ops_manager.py` (deal/project context files + questions queue), `crm_sync.py` (Pipedrive ↔ SM8 reconciliation), `reengage_campaign.py` (client + lost deal re-engagement), `tender_batch.py` (daily E1 → CRM pipeline)
- Merged E1 agent into tender agent (9 → 8 agents), cleaned all agents (dedup, frontmatter, model fixes)
- Reorganized into 4 lifecycle departments: Lead Gen → Sales → Operations → Retention
**Why:** Tools over agents for automated work — zero context burn, zero token cost. Agents reserved for interactive work only. Single source of truth for pipeline IDs (crm-ops.md) eliminates 3-way duplication. Tender agent switched from Sonnet → Haiku (4x cheaper, only orchestrates tools).
**Criteria:** Speed: + | Cost: + (all tools $0, tender agent 4x cheaper) | Accuracy: + (SM8 source of truth, EOD scan catches mismatches) | Scale: + (per-deal context files, batch processing)
**Next:** Set up launchd plists for daily/weekly automation. Build EPS Ops Dashboard for team visibility.

---

## 2026-04-13 — Re-engagement campaign system
**Problem:** 58 previous clients with "REENGAGE" activities sitting untouched. No system to process them — all manual. Re-engagement project boards (Board 3 Clean, Board 5 Paint) existed but nobody was moving through stages. No connection between Pipedrive activities, SM8 service history, and outreach.
**Change:**
- Built cross-referenced client list (Pipedrive activities × Projects boards × SM8 jobs) → Google Sheet tracker with 44 qualified clients
- Sent batch 1 (7 personalized emails) with SM8-verified service details, created follow-up call activities, moved projects to "Added to Sequence"
- Planned `tools/reengage_campaign.py` — automated batch tool that replaces manual process at $0 token cost
**Why:** Manual approach cost ~$3-5/batch in Claude tokens. Automated script does same thing for $0. Chose tool + morning briefing integration (Option C) over new agent — complexity doesn't justify an agent yet. Will also cover lost deals win-back in same tool.
**Criteria:** Speed: + | Cost: + | Accuracy: + (SM8 as source of truth) | Scale: + (batch processing)
**Next:** Build reengage_campaign.py, add lost deals mode, create reengagement workflow doc, hook into morning briefing

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

## 2026-04-13 — Carousel tool upgrade + change tracking rule
**Problem:** Carousel generator had no header/body separation (all text same size). Scripts were only embedded in Python code, lost between sessions. Allen's decisions weren't being tracked across systems.
**Change:** Added `||` separator to `generate_carousel.py` for header/body split. Added "Tracking Changes" section to main `CLAUDE.md` — all decisions logged in relevant files with change logs. Saved scripts as standalone files.
**Why:** Allen needs every session to pick up exactly where the last one left off. Embedding scripts in code meant they got lost. The carousel needed visual hierarchy to match Hormozi style (bold header, lighter body).
**Criteria:** Speed: + | Cost: = | Accuracy: + | Scale: +
**Next:** Consider adding profile picture + name to carousel title slides. PDF generator could become a reusable tool.

---

## 2026-04-13 — Level 4 definition locked + video script structure
**Problem:** Level 4 (Agentic) was described as "reads your pipeline, writes your emails" — too basic, sounds like Level 3 with a chatbot. Video script was missing INTRO and WHAT THIS IS ABOUT sections.
**Change:** Level 4 now = "AI agents handle marketing, lead gen, sales, and delivery end to end. They learn from unlimited data and do the actual work." Updated carousel, script, and brand agent. Added INTRO + WHAT THIS IS ABOUT to Video 1 script. Timeline corrected: Level 1→4 in less than a month.
**Why:** Allen's vision for Level 4 is the Medvi model — full departments running on AI, not just task automation. The script needed the full flow (Hook → Intro → What this is about → Content → Stats → CTA) to match what Allen actually recorded.
**Criteria:** Speed: = | Cost: = | Accuracy: + | Scale: =
**Next:** Allen films voiceover, then re-sync visuals + captions to final audio.

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

## 2026-04-11 — Brand direction locked: audience vs customer split, ICP, positioning

**Problem:** Brand agent and intel docs had placeholder ICP data. No clear distinction between who Allen serves with content vs who pays. Channel identity undefined. Service offering vague.

**Change:**
- Rewrote ICP sections in `personal-brand-agent.md` — audience (VAs, broad PH) vs customers (service businesses, creators with budget, professionals)
- Populated `reference/intel/icp-language.md` and `market-validation.md` with research-backed competitor data, pricing benchmarks, delivery models
- Defined channel identity: personal brand (not build-in-public, not tutorial channel)

**Why:** Allen was unclear on who to target and what to sell. Ran two parallel research agents (ICP validation + competitive landscape). Research showed VAs can't pay ($0-20/mo budget) but are the biggest audience. Service businesses (trades, AU/US/UK) are the real revenue. Content creators are secondary. Competitors (Nate Herk, Nick Saraev, Sabrina Ramonov) are all developers — Allen's edge is being a non-technical operator.

**Criteria:** Speed: + (intel docs now pre-populated, agents read them automatically) | Cost: = | Accuracy: + (research-backed, not guesses) | Scale: + (all content/outreach agents now aligned to same direction)

**Next:** Create content scripts aligned with new direction. Reach out to first 3 free-build clients. Solve delivery model (whose Claude account?).

---

## 2026-04-13 — Video generation pipeline (Pillow + FFmpeg)
**Problem:** Allen needed animated visuals for his "4 Levels of AI" video — UI mockups of ChatGPT, Gmail, n8n, Claude Code with transitions and captions. No budget for video editing tools.

**Change:** Built frame-by-frame video generation using Pillow (image rendering) + FFmpeg (video encoding) + Whisper (audio transcription). Created animated scenes for all 4 levels, Hormozi-style word-by-word captions, and used real Claude Code screenshots as Level 4 base. All scripts in `projects/personal/.tmp/video_test/`.

**Why:** CapCut/DaVinci/Fiverr all cost money or time. Pillow + FFmpeg were already installed on Allen's Mac. Gives full programmatic control — can re-render with different timing when Allen provides final voiceover. AI video generators (Kling, Pika) can't do precise UI mockups. Trade-off: lower visual polish than After Effects, but zero cost and instant iteration.

**Criteria:** Speed: + (renders in seconds, instant iteration) | Cost: + (zero — all local, free tools) | Accuracy: = (UI mockups decent but not pixel-perfect) | Scale: + (reusable pipeline for future videos)

**Next:** Allen edits voiceover, drops final audio. Re-sync visuals to final timestamps. Improve Claude Code UI fidelity.

---

## 2026-04-14 — EPS launchd automation + Sales & Operations Dashboard

**Problem:** 5 EPS tools (tender_batch, eod_ops_manager, crm_sync, reengage_campaign) built but required manual execution. No shared visibility into deal/tender/project status for the team.

**Change:** Created 4 launchd plists (tender-batch 6AM, eod-ops 5PM chained, reengage Mon 7AM, eps-dashboard persistent). Built full EPS Dashboard as separate Flask app (`tools/eps-dashboard/`) with 6 tabs: Overview, Deals, Projects, Re-engagement, Sent Tenders, E1 Inbox. Kanban views per pipeline/board with all stages always visible. Live Pipedrive data + EOD intelligence overlay.

**Why:** Team needs shared visibility without logging into Pipedrive. Separate app from personal dashboard because team will use it. Kanban over table view because it mirrors Pipedrive's mental model. Live API + EOD overlay because Pipedrive API is free but EOD analysis adds intelligence (flags, next actions, questions).

**Criteria:** Speed: + (auto-runs, instant page loads) | Cost: = (zero — local Flask, free Pipedrive API, no Claude tokens) | Accuracy: + (live data, fixed pipeline_id filter bug) | Scale: + (team access, auto-start via launchd)

**Next:** Populate Win-Back pipeline with lost deals. Update reengage_campaign.py to target new pipelines. Polish dashboard UI.

---

## 2026-04-14 — Re-engagement + Win-Back Pipedrive pipelines

**Problem:** Re-engagement was on Pipedrive Projects boards — wrong structure for sales follow-up. Won clients and lost deals mixed together with no qualifying step.

**Change:** Created two new Pipedrive pipelines: Re-engagement (ID: 9, 7 stages for won clients: referral → repeat → Google review) and Win-Back (ID: 10, 5 stages for lost deals with qualifying gate). Migrated 28 projects to Re-engagement deals. Removed old project boards.

**Why:** Deals pipeline is the right structure for re-engagement (stages, activity tracking, values). Separate pipelines for won vs lost because different workflows — won clients are warm (skip qualifying), lost deals need qualifying first. Win-Back INTERESTED moves to main pipeline — no duplication. One re-engagement pipeline (not split Clean/Paint) because service type doesn't matter at outreach stage.

**Criteria:** Speed: + (clear workflow, no confusion) | Cost: = (no API cost) | Accuracy: + (right entities in right pipelines) | Scale: + (auto-population planned via reengage tool)

**Next:** Auto-populate Win-Back from reengage_campaign.py. Add value + recency tags for quick qualifying.

---

> Entries before 2026-04-10 archived in [DECISIONS-archive.md](DECISIONS-archive.md)
