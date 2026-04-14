---
name: EPS QA Workflow
description: QA sequence for client-facing output — draft email first, QA both together, never show Allen before QA passes
type: feedback
---

All client-facing output (quotes, emails, follow-ups) must pass QA before Allen sees it.

**Sequence:** Draft email (no --send) → QA checks doc + email together → Allen approval → send.

**Why:** Allen wants QA to evaluate combined output, not piecemeal. Running QA before drafting means QA can't check the actual email. And Allen never wants to see unvetted output.

**How to apply:** After any agent produces client-facing output, route to eps-qa-agent first. In quote pipeline Stage 5: draft_quote_email.py (no send) → qa_quote.py (checks both) → fix if needed → Allen sees it → send.
