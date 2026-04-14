---
name: email
description: Draft or send an EPS client email. Triggers on "draft the email", "send the quote email", "follow up with", "write an email to", or /email.
---

EPS email drafting and sending. The main session handles this directly.

## Email types

### Quote email
Inputs: client email, first name, deal ID, template key, opener, situation, concerns (residential only), bonus (optional), doc URL

### Follow-up email
Inputs: deal ID, client email, first name, template key, opener

### Template keys
| Service | Key |
|---|---|
| Residential painting | `residential_painting` |
| Residential cleaning | `residential_cleaning` |
| Commercial cleaning | `commercial_cleaning` |
| Builders cleaning | `builders_cleaning` |
| Builders painting | `builders_painting` |
| Builders painting + cleaning | `builders_painting_cleaning` |
| Bond clean | `bond_clean` |

## How to run

**Quote email:**
1. Read `projects/eps/CONTEXT.md`
2. Follow Stage 5 + 6 of `projects/eps/workflows/sales/create-quote.md`

**Follow-up email:**
1. Read `projects/eps/CONTEXT.md`
2. Read `projects/eps/workflows/sales/follow-up-email.md` and follow it

## Rules
- Ask for missing inputs upfront — especially template key and opener
- Draft first → QA → Allen approves → send
- Never send without Allen's explicit approval
