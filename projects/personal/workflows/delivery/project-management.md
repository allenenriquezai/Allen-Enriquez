# Project Management SOP

Track client projects from kickoff to handoff. Timelines, milestones, blockers, status updates.

## Process

### Step 1 -- Create Project Plan

From the scope document (`projects/personal/.tmp/clients/[client-slug]/scope.md`):
- Break deliverables into tasks
- Assign milestones with dates
- Identify dependencies (what blocks what)

### Step 2 -- Track Progress

Maintain status at `projects/personal/.tmp/clients/[client-slug]/status.md`:

```markdown
# Project Status: [Client Name]

## Summary
**Progress:** [X]% complete
**On track:** Yes/No
**Next milestone:** [what] -- due [date]

## Milestones
| # | Milestone | Status | Due | Actual |
|---|---|---|---|---|
| 1 | [name] | Done / In Progress / Not Started / Blocked | [date] | [date] |

## This Week
- [What was completed]

## Next Week
- [What's planned]

## Blockers
- [What's stuck and why]

## Client Action Needed
- [Anything client needs to provide or decide]
```

### Step 3 -- Draft Status Updates for Clients

Simple language. 3rd grade reading level.

```
Hey [name],

Quick update on your automation:

Done this week:
- [thing]
- [thing]

Next week:
- [thing]

[If blocker: "One thing I need from you: [ask]"]

Talk soon,
Allen
```

### Step 4 -- Flag Problems Early

- Behind schedule = flag immediately
- Scope creep detected = flag immediately
- Blocker not resolved in 48h = escalate to Allen

## Rules

- Never share one client's data with another
- Status updates are client-facing: simple, no jargon
- Always show percentage complete
- Quick summary first (3 lines), details second
- Flag blockers immediately. Don't wait for a status update.
- Track actual vs planned dates
