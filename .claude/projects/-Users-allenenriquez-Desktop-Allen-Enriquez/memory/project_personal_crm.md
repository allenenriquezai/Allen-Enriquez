---
name: Personal Brand CRM Manager
description: personal_crm.py tool for managing Google Sheets CRM, evening briefings, post-calling cleanup, and email drafting
type: project
---

Built 2026-04-08. Tool: tools/personal_crm.py with 5 subcommands:
- clean — one-time sheet cleanup (reorder cols, format, sort called leads to top)
- evening-brief — sends prioritised call list + personal Gmail/Calendar to allenenriquez.ai@gmail.com
- cleanup — post-calling normalisation (automated at 12:30 AM via launchd)
- review — terminal summary
- draft --row N --tab "Tab" — drafts outreach email with swappable opener

Why: Allen cold-calls painting companies in Charlotte NC for his AI consultancy. Sheet CRM at Google Sheets ID 1G5ATV3g22TVXdaBHfRTkbXthuvnRQuDbx-eI7bUNNz8.

How to apply: Morning briefing is EPS-only. Evening briefing is personal-only. Clean separation. The EA orchestrates by running scheduled tools — no actual EA agent prompt exists yet.

Status: Clean + evening-brief + cleanup + draft all working. launchd cleanup plist installed (12:30 AM daily).

Next: Build a real EA subagent that can delegate to tools on Allen's behalf.
