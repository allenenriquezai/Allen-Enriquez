---
name: content
description: Marketing content engine — plan, write, track, and QA content for Allen's personal brand. Triggers on "generate content", "write posts", "content calendar", "what to film", "30 day challenge", "marketing status", or /content.
---

Personal brand content engine. The main session handles this directly.

## Routing

Pick the right workflow based on Allen's request:

| Allen says | Read |
|---|---|
| "plan", "status", "what to film", "today", "report", "campaign", "schedule" | `projects/personal/workflows/content/content-calendar.md` |
| "write", "generate", "script", "draft", "reel", "youtube", "post", "linkedin" | `projects/personal/workflows/content/content-creation.md` |
| "research", "hooks", "trending", "competitors" | **→ Use `/content-research` skill instead** |
| "edit video", "cut footage", "edit reel", "video editing" | **→ Use `/video-edit` skill instead** |

## How to run

1. **Immediately on invoke** — before asking Allen what task — load all 5 brand context files:
   - `projects/personal/CONTEXT.md` (brand foundation, voice, quality gate)
   - `projects/personal/reference/content-strategy-v2.md` (current strategy + frameworks)
   - `projects/personal/reference/hormozi-style-guide.md`
   - `projects/personal/workflows/content/content-creation.md`
   - `projects/personal/intel/icp-language.md`
2. Ask Allen which mode (plan / write) if not already clear
3. Read the matching workflow from the routing table
4. Follow the workflow

## Rules
- Do NOT post anything — only draft and show for approval
- Always check `projects/personal/CONTEXT.md` voice rules before writing any content
- For content writing: also load `hormozi-style-guide.md` + `content-creation.md` + `icp-language.md`
- If Allen asks to regenerate, re-run the same workflow
