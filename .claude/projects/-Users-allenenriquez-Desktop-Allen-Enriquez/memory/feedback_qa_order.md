---
name: EPS QA Order — Draft Email Before QA
description: Email must be drafted before QA runs, so QA checks quote doc and email together in one pass
type: feedback
---

Always draft the email first (draft_quote_email.py without --send), then run qa_quote.py so it checks both the quote doc and email draft together.

**Why:** Allen wants QA to evaluate the quote and email as a combined output, not sequentially. Running QA before drafting means QA can't check the actual email.

**How to apply:** In Stage 5 of the quote pipeline — Step 1 = draft email (no send), Step 2 = QA both together. If QA fails, fix issues, re-draft, then re-run QA. Never run qa_quote.py (pre-send) before draft_quote_email.py has run.
