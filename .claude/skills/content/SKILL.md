---
name: content
description: Marketing content engine — plan, write, track, and QA content for Allen's personal brand. Triggers on "generate content", "write posts", "content calendar", "what to film", "30 day challenge", "marketing status", or /content.
---

Personal brand content engine. Do NOT read any other files — everything you need is here.

## Routing

Decide which agent to spawn based on what Allen is asking:

### Planning / tracking requests → spawn `personal-content-manager`
Trigger words: "plan", "status", "what to film", "today", "report", "30 day", "campaign", "behind", "schedule", "mark", "tracker"

Examples:
- "What do I need to film today?" → content-manager
- "Marketing status" → content-manager
- "How's the campaign going?" → content-manager
- "Mark day 3 reel 1 as filmed" → content-manager

### Writing requests → spawn `personal-content-agent`
Trigger words: "write", "generate", "script", "draft", "reel", "youtube", "post", "linkedin", "newsletter"

Examples:
- "Write me 2 reel scripts about AI" → content-agent
- "Generate this week's LinkedIn posts" → content-agent
- "Draft a YouTube script about automation" → content-agent

### Style research → spawn `personal-style-researcher`
Trigger words: "research", "study", "analyze", "style guide", "hormozi"

Examples:
- "Research Hormozi's style" → style-researcher
- "Analyze these scripts" → style-researcher
- "Update the style guide" → style-researcher

### QA review → spawn `personal-marketing-qa`
Trigger words: "QA", "review", "check", "before posting"

Examples:
- "QA this reel script" → marketing-qa
- "Check this before I post" → marketing-qa

### Default (no clear signal)
Spawn `personal-content-manager` — it will assess what's needed and delegate.

## Rules
- Do NOT read agent files, memory, or workflow docs — the agents handle that
- Do NOT post anything — only draft and show for approval
- If Allen asks to regenerate, re-run the same agent with the same request
