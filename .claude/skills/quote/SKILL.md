---
name: quote
description: Create an EPS quote end-to-end. Triggers on "create a quote", "price up this job", "write a quote for", or /quote.
---

EPS quote creation. Do NOT read any other files — everything you need is here.

## Inputs needed (ask upfront if missing)
1. **Client name or deal ID**
2. **Service type** — residential painting, residential cleaning, commercial cleaning, builders cleaning, builders painting, builders painting + cleaning, bond clean
3. **Scope** — floor plan image OR text description of rooms/areas
4. **Rates** — default, multiplier, or custom (ask: "Default rates or custom?")

## How to run

Spawn the `eps-quote-agent` subagent with this prompt:

> Create a quote for {CLIENT/DEAL}. Service type: {TYPE}. {SCOPE DETAILS}. {RATE DETAILS}.

The agent follows `projects/eps/workflows/create-quote.md` through all stages:
1. Intake → job description → line items → QA → Google Doc → Pipedrive

## After quote is created
The agent returns the Google Doc URL and total. Then spawn `eps-email-agent` to draft the quote email (Stage 5).

## Rules
- Do NOT read agent files, workflow files, or memory — the agent reads what it needs
- Ask ALL clarifying questions in one message upfront before spawning the agent
- Confirm rates before starting — this affects pricing
