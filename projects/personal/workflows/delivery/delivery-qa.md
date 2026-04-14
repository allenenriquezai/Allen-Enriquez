# Delivery QA SOP

Last gate before anything ships to a client. No PASS = no ship.

## Process

### Step 1 -- Read Scope + Deliverables
- Scope: `projects/personal/.tmp/clients/[client-slug]/scope.md`
- Deliverables: `projects/personal/.tmp/clients/[client-slug]/deliverables/`

### Step 2 -- Check Scope Match
For each deliverable in the scope:
- Was it built? Yes/No
- Does it match what was promised?
- Any gaps between scope and delivery?

### Step 3 -- Test Functionality
- Does the code run without errors?
- Do integrations connect properly?
- Do agents follow their instructions?
- Are edge cases handled?
- Does error handling work?

### Step 4 -- Check Documentation
- README exists and is clear?
- Client would understand how to use it?
- Setup steps complete and accurate?
- Maintenance docs included?

### Step 5 -- Check Quality
- Code is clean and commented
- No hardcoded secrets or credentials
- No placeholder/TODO items left
- Client-facing text is simple and jargon-free
- Technical docs clear for a junior dev

### Step 6 -- Generate QA Report

Write to `projects/personal/.tmp/clients/[client-slug]/qa-report.md`:

```markdown
# QA Report: [Client Name]

**Date:** [date]
**Verdict:** PASS / FAIL

## Scope Coverage
| # | Deliverable | Built | Matches Scope | Notes |
|---|---|---|---|---|
| 1 | [name] | Y/N | Y/N | [notes] |

## Functionality Tests
| Test | Result | Notes |
|---|---|---|
| [what tested] | PASS/FAIL | [details] |

## Documentation Check
| Item | Present | Quality | Notes |
|---|---|---|---|
| README | Y/N | Good/Needs Work | [notes] |
| Setup guide | Y/N | Good/Needs Work | [notes] |
| Maintenance | Y/N | Good/Needs Work | [notes] |

## Issues Found

### Critical (must fix before shipping)
- [issue + location + how to fix]

### Minor (should fix, not blocking)
- [issue + suggestion]

### Recommendations
- [improvement ideas]
```

## Verdict Rules

**PASS:** All scope items built. All deliverables work. Docs complete. No critical issues.

**FAIL:** Any scope item missing. Critical bugs. Docs incomplete. Security issues (hardcoded keys, no auth, exposed data).

## Rules

- Never pass something that doesn't match scope
- Never pass code with obvious bugs
- Never pass incomplete documentation
- Be specific: "line 45 of scraper.py has an unhandled exception" not "code has issues"
- Re-test after fixes
- Flag security issues as CRITICAL
- Client data isolation -- never reference other clients
