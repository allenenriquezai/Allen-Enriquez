---
name: quote
description: Create an EPS quote end-to-end. Triggers on "create a quote", "price up this job", "write a quote for", or /quote.
---

EPS quote creation. The main session handles this directly.

## Inputs needed (ask upfront if missing)
1. **Client name or deal ID**
2. **Service type** — residential painting, residential cleaning, commercial cleaning, builders cleaning, builders painting, builders painting + cleaning, bond clean
3. **Scope** — floor plan image OR text description of rooms/areas
4. **Rates** — default, multiplier, or custom (ask: "Default rates or custom?")

## How to run

1. Read `projects/eps/CONTEXT.md` for workspace rules
2. Read `projects/eps/workflows/sales/create-quote.md` and follow it exactly
3. The workflow covers the full pipeline: intake → measure → line items → doc → email → QA → send

## Rules
- Ask ALL clarifying questions in one message upfront before starting
- Confirm rates before starting — this affects pricing
- Follow the workflow step by step — every rule, every stage
