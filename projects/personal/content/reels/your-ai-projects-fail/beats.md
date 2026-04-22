# Beats — YOUR AI PROJECTS FAIL

Source: `~/Desktop/Personal Brand - Contents/Animation Ready From Capcut/YOUR AI PROJECTS FAIL.mov` — 4320×7680 @ 60fps, 46.53s
Black overlay window (animation canvas): **5.47s → 40.23s** (34.77s)

## Segment map

| # | Segment | Start | End | Duration | Face/Overlay |
|---|---------|-------|-----|----------|--------------|
| — | Hook (face) | 0.00 | 5.47 | 5.47 | face |
| — | **Middle (animation)** | **5.47** | **40.23** | **34.77** | **overlay** |
| — | CTA (face) | 40.23 | 46.53 | 6.30 | face |

Boundaries derived from `ffmpeg blackdetect` (pix_th=0.10, d=0.3).

## Full VO transcript (middle-local seconds, whisper small.en, word-level)

| Start | End | Phrase |
|---|---|---|
| 0.14 | 1.66 | People buy tools. |
| 1.66 | 4.25 | ChatGPT, Zapier, Make. |
| 4.25 | 5.39 | They connect things. |
| 5.39 | 6.64 | When it breaks, they quit. |
| 6.64 | 8.45 | The problem isn't the tool. |
| 8.45 | 10.88 | It's that they don't have a system. |
| 10.88 | 12.96 | A tool is a hammer. |
| 12.96 | 15.40 | A system is the blueprint for the house. |
| 15.40 | 17.11 | I stopped chasing tools. |
| 17.11 | 19.16 | I mapped out my processes first, |
| 19.16 | 21.02 | told AI to follow it, |
| 21.02 | 23.40 | and then everything changed. |
| 23.40 | 25.05 | Before you touch any AI tool, |
| 25.05 | 27.00 | write down your process, |
| 27.00 | 28.16 | step by step, |
| 28.16 | 29.82 | as detailed as you can. |
| 29.82 | 31.28 | That's the system. |
| 31.28 | 32.90 | AI follows systems, |
| 32.90 | 34.77 | but it can't follow chaos. |

19 beats, avg 1.83s each. All times are middle-local (subtract 5.47 already applied; this is what the composition uses).

## Proposed beat → drawing map (GATE 1 — approve before I build)

Style: hand-drawn Rough.js sketches, cyan `#02B3E9` primary stroke on navy `#05080F`, accent red `#ff4757` for wrong/fail, green `#22c55e` for right/win.
No drawing repeats. Each beat = one new subject.

| # | Phrase | Drawing subject | Motion |
|---|---|---|---|
| 1 | People buy tools. | Shopping cart with a price tag reading "BUY" | cart stroke-draws L→R, tag flips in |
| 2 | ChatGPT, Zapier, Make. | 3 labelled badges stacked — "CHATGPT" "ZAPIER" "MAKE" | each pops on its word, slight wobble on land |
| 3 | They connect things. | Loose spaghetti lines linking the 3 badges | lines draw word-by-word |
| 4 | When it breaks, they quit. | Cracked chain link + big red ✗ | shatter FX on "breaks", ✗ stamp on "quit" |
| 5 | The problem isn't the tool. | A single hammer with red slash through it | hammer draws, red slash sweeps across |
| 6 | It's that they don't have a system. | Chaotic scribble-cloud with arrows going nowhere | wild scribble auto-draws, arrows shoot random dirs |
| 7 | **A tool is a hammer.** | **HAMMER** — large, clean, centered, cyan | payoff: stroke-draws bold, scale pulse, 1.2s hold |
| 8 | **A system is the blueprint for the house.** | **BLUEPRINT** scroll unfurls → **HOUSE** builds on grid lines | blueprint unrolls, grid appears, house constructs on beat |
| 9 | I stopped chasing tools. | Stick figure running after floating icons, then palm-up halt | chase → freeze → halt stamp |
| 10 | I mapped out my processes first, | 3 flowchart boxes + connecting arrows | boxes pop sequentially, arrows trace between |
| 11 | told AI to follow it, | Small robot head tracing the flowchart path | bot slides along path from box to box |
| 12 | and then everything changed. | Big green ✓ check with radial glow burst | slam-stamp on "changed", glow rays fan out |
| 13 | Before you touch any AI tool, | Raised open palm / STOP gesture | palm draws, pulse on "before" |
| 14 | write down your process, | Pencil drawing a wavy line on notepad | pencil traces live with the word |
| 15 | step by step, | Numbered staircase — 1, 2, 3 risers | each step draws on each word |
| 16 | as detailed as you can. | Magnifying glass zooming into the notepad | mag glass draws, zoom-scale on "detailed" |
| 17 | That's the system. | Gear with "SYSTEM" stamp | gear rotates in, stamp lands on "system" |
| 18 | AI follows systems, | Robot walking along a straight blueprint line | bot trundles L→R |
| 19 | but it can't follow chaos. | Tornado/scribble storm — bot stumbles off-line | tornado draws, bot topples, end on chaos |

## Style locks

- Canvas: `#05080F` navy
- Primary stroke: `#02B3E9` cyan (Rough.js, roughness 1.5–2.5 for hand-drawn wobble)
- Alert: `#ff4757` red (fail beats: 4, 5, 19)
- Confirm: `#22c55e` green (win beats: 12)
- Labels: Montserrat 900 uppercase, 90–140pt depending on emphasis
- Chrome/numerals: Roboto Mono 500
- Payoff holds: ≥1s on beats 7, 8, 12, 17
- Secondary motion during holds (pulse, drift, glow oscillation) — no dead frames
- Each drawing generated ONCE at module init with fixed Rough.js `seed` (determinism)

## Out of scope (handed to `/short-form-video` next)

- Karaoke captions over the full reel
- Hook sticker on face hook (0–5.47s)
- CTA sticker on face CTA (40.23–46.53s)
- Full MP4 render
