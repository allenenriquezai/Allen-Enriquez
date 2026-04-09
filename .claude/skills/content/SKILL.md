---
name: content
description: Marketing content engine — plan, write, track, and QA content for Allen's personal brand. Triggers on "generate content", "write posts", "content calendar", "what to film", "30 day challenge", "marketing status", or /content.
---

Personal brand content engine. Do NOT read any other files — everything you need is here.

## Routing

Decide which agent to spawn based on what Allen is asking:

### Planning / tracking → `projects/personal/agents/personal-content-manager.md`
Triggers: "plan", "status", "what to film", "today", "report", "30 day", "campaign", "schedule", "tracker"

### Writing → `projects/personal/agents/personal-content-agent.md`
Triggers: "write", "generate", "script", "draft", "reel", "youtube", "post", "linkedin", "newsletter"

### Style research → `projects/personal/agents/personal-style-researcher.md`
Triggers: "research", "study", "analyze", "style guide", "hormozi"

### QA review → `projects/personal/agents/personal-marketing-qa.md`
Triggers: "QA", "review", "check", "before posting"

### Default → `projects/personal/agents/personal-content-manager.md`

For whichever agent is selected, spawn a general-purpose Agent with:

> Read your instructions from `{agent path}` and follow them. Task: {ALLEN'S REQUEST}

## Rules
- Do NOT read agent files, memory, or workflow docs — the agents handle that
- Do NOT post anything — only draft and show for approval
- If Allen asks to regenerate, re-run the same agent with the same request
