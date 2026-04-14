# Client Intake SOP

Handle everything between "client said yes" and "project starts." Discovery, scope, proposal.

## Process

### Step 1 -- Gather Discovery Info

Ask Allen (or process a discovery form) for:
- What tools the client already uses
- What they want automated (pain points, manual tasks)
- Team size and who will use the automation
- Budget and timeline expectations
- Current monthly revenue/volume (to size the opportunity)

### Step 2 -- Create Scope Document

Define clearly:
- What will be built (deliverables)
- What's included
- What's NOT included (boundaries)
- Timeline with milestones
- Pricing (monthly retainer or project fee)
- Assumptions and dependencies

### Step 3 -- Draft Proposal

Short. Direct. One page max. No corporate speak.

"Here's your problem. Here's what we'll build. Here's what it'll cost. Here's when you'll have it."

Content:
- Problem (in their words)
- What we'll build to fix it
- Expected results
- Price and timeline
- What they need to provide
- Simple next steps

## Output Location

```
projects/personal/.tmp/clients/[client-slug]/
```

Save: `scope.md` + `proposal.md`. Create the directory if it doesn't exist.

**Client slug:** lowercase, hyphens, no special chars. "Bob's Plumbing" = `bobs-plumbing`.

## Scope Template

```markdown
# Scope: [Client Name]

## Overview
[One sentence: what we're building and why]

## Deliverables
1. [Specific thing]
2. [Specific thing]

## Included
- [What's in scope]

## Not Included
- [What's out of scope]

## Timeline
- Week 1: [milestone]
- Week 2: [milestone]
- Week 3: [milestone]
- Week 4: Handoff + training

## Pricing
[Monthly retainer or project fee]

## Assumptions
- [What we're assuming is true]

## Client Responsibilities
- [What they need to provide/do]
```

## Rules

- Never share one client's files with another
- Client-facing output: simple, clear, no jargon
- If info is missing, ask Allen. Don't guess.
- Flag if scope seems too big for the budget
- Flag if client expectations don't match what's realistic
- Default pricing: $1-5K/month depending on complexity
- Always confirm scope with Allen before generating the proposal
