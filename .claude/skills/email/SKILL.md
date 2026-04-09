---
name: email
description: Draft or send an EPS client email. Triggers on "draft the email", "send the quote email", "follow up with", "write an email to", or /email.
---

EPS email drafting and sending. Do NOT read any other files — everything you need is here.

## Email types

### Quote email
Inputs needed:
- Client email, first name, deal ID
- Template key (see table below)
- Opener (1-line personal detail from the call)
- Situation (1 sentence: who they are + what they need)
- Concerns (residential only): concern 1, concern 2
- Bonus line (optional)
- Doc URL (from quote creation)

### Follow-up email
Inputs needed:
- Deal ID, client email, first name
- Template key
- Opener

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

Spawn a general-purpose Agent with this prompt:

> Read your instructions from `projects/eps/agents/eps-email-agent.md` and follow them. Task: Draft a {quote/follow-up} email for deal {DEAL_ID}. Template: {KEY}. First name: {NAME}. Email: {EMAIL}. Opener: "{OPENER}". Situation: "{SITUATION}". {Concerns if residential}. {Bonus if any}. Doc URL: {URL if quote email}.

The agent:
1. Drafts email (no send)
2. Runs QA on quote doc + email together
3. Shows draft to Allen after QA passes
4. Sends only after Allen approves

## Rules
- Do NOT read agent files, templates, or memory
- Ask for missing inputs upfront — especially template key and opener
- Never send without Allen's explicit approval
