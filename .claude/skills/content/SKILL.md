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
| "research", "hooks", "trending", "competitors" | `projects/personal/workflows/content/content-research.md` |

## How to run

1. Read `projects/personal/CONTEXT.md` for brand rules, voice, and quality gate
2. Read the matching workflow from the table above
3. Follow it

## Rules
- Do NOT post anything — only draft and show for approval
- Always check `projects/personal/CONTEXT.md` voice rules before writing any content
- If Allen asks to regenerate, re-run the same workflow
