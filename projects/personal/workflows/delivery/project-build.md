# Project Build SOP

Build the actual automation for clients. Code, agents, workflows, integrations -- whatever the scope says.

## Process

### Step 1 -- Read the Scope
```
projects/personal/.tmp/clients/[client-slug]/scope.md
```

### Step 2 -- Plan the Build
From the scope, determine:
- Tools/platforms to use
- Integrations needed
- Agents or prompts to write
- Build order
- Credentials/access needed from client

### Step 3 -- Build It
- Write code, prompts, workflows, configs
- Clean and documented
- Built for client's skill level (not developers)
- Test as you go

### Step 4 -- Document Everything
- What was built
- How it works (simple for client)
- How to use it (step-by-step)
- How to maintain it (what might break, how to fix)
- Credentials/config client needs to know

## Output Location

```
projects/personal/.tmp/clients/[client-slug]/deliverables/
```

Save: code/configs in subfolders + `README.md` + `setup-guide.md` + `maintenance.md`.

## What You Can Build

- Claude Code agents -- prompts, skills, workflows
- n8n workflows -- JSON exports with docs
- Zapier automations -- step-by-step setup guides
- Python scripts -- tools, scrapers, processors
- CRM automations -- Pipedrive, HubSpot, etc.
- Email automations -- sequences, templates, triggers
- Dashboards -- Flask apps, Google Sheets
- API integrations -- webhooks, middleware, connectors

## Build Standards

**Code:** Python 3.10+. Requirements documented. Env vars for secrets (never hardcode). Error handling with clear messages. Logging for debugging.

**Agents/Prompts:** Clear role. Specific instructions. Examples where helpful. Guardrails (what NOT to do).

**Workflows (n8n/Zapier):** Document each node. Include error paths. Note rate limits. Export configs for backup.

**Documentation:** README for every deliverable. Screenshots where helpful. "If this breaks" section. Contact info for support.

## When Done

Update project status:
```
projects/personal/.tmp/clients/[client-slug]/status.md
```
Mark deliverables as complete and ready for QA.

## Rules

- Never share one client's deliverables with another
- All code must be clean, commented, and working
- Client-facing docs: simple language, no jargon
- Technical docs: clear enough for a junior dev to maintain
- If outside scope -- stop and flag it
- If you need credentials -- ask Allen, don't guess
- Reliability over cleverness
- Include error handling -- things will break
- Simple solutions over complex ones
- Test before marking as done
