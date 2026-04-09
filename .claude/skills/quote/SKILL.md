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

Spawn a general-purpose Agent with this prompt:

> Read your instructions from `projects/eps/agents/eps-quote-agent.md` and follow them. Task: Create a quote for {CLIENT/DEAL}. Service type: {TYPE}. {SCOPE DETAILS}. {RATE DETAILS}.

## After quote is created
The agent returns the Google Doc URL and total. Then spawn another Agent:

> Read your instructions from `projects/eps/agents/eps-email-agent.md` and follow them. Task: Draft the quote email for deal {DEAL_ID}. {EMAIL DETAILS}.

## Rules
- Do NOT read agent files, workflow files, or memory — the agent reads what it needs
- Ask ALL clarifying questions in one message upfront before spawning the agent
- Confirm rates before starting — this affects pricing
