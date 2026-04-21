---
name: excalidraw
description: Create Excalidraw diagrams — either editable JSON files (free, paste into excalidraw.com) or rendered PNG images (paid via kie.ai API). Use when someone asks to draw a diagram, make an Excalidraw visual, or build a hand-drawn visual.
---

# Excalidraw (Two Modes)

Two output types. Pick the right one based on the user's intent.

## Mode Selection

| User signal | Mode | Cost |
|---|---|---|
| "editable", "so I can edit", "excalidraw file", "paste into excalidraw.com" | **EDITABLE** → read `EDITABLE.md` | Free |
| "image", "PNG", "visual", "render", "picture", "slide", "for a post" | **PNG** → read `PNG.md` | ~$0.02–0.09 via kie.ai |
| Unclear | **Ask:** "Editable file (free, you edit it) or PNG image (rendered, ~$0.05)?" | — |

Do not load both mode files. Pick one after intent is clear.

## Shared principles (both modes)

- One color per logical zone. Blue = input, yellow = process, green = output, coral = warning, gray = neutral.
- Short labels (2–3 words max). Use icons over words when possible.
- Generous whitespace. 40px+ between major sections.
- Dark charcoal text (`#1e1e1e` or `#343a40`) on light backgrounds.

## Style guide

`style-guide.md` in this directory — PNG mode style reference (color palette, font spec, layout templates). Editable mode has its own color system documented in `EDITABLE.md`.

## After mode file loaded

Follow the workflow in the mode-specific file exactly. Do not mix editable JSON schema with PNG generation — they use entirely different tooling.
