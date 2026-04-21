# Short-Form Video — Hook Sticker Spec

**Load this file when:** designing or editing the hook sticker for a new reel.

Every short-form reel for Allen's brand gets a **hook sticker** — a dark-navy rounded pill with bright cyan border + outer glow + bold white uppercase text — layered over the talking head during the hook window (0 → ~8s) and optionally the CTA window. Same sticker, same style, every reel. This is how viewers see the topic headline while Allen's face is on screen.

## Exact spec (baked into `feedback_hook_sticker_style.md`)

- Container: `background: #071020`, `border: 5px solid #02B3E9`, `border-radius: 36px`
- Glow: `box-shadow: 0 0 28px rgba(2,179,233,0.85), 0 0 64px rgba(2,179,233,0.50), 0 10px 26px rgba(0,0,0,0.55)`
- Text: Montserrat 900, UPPERCASE, white, layered black text-shadow stroke (`-3/3/3/3` offsets + `0 6px 18px rgba(0,0,0,0.7)` drop)
- Text wrap: `white-space: nowrap` on each line + tune font-size so each line fits (54–64px for 800px wide sticker)
- Position: upper-center of 1080×1920 frame (roughly y=200, x=70 when sticker PNG is 940×460)
- Shows during face-visible windows, covered by scene overlays during middle
- **Reference working file:** `projects/personal/videos/reel-3/assets/pin-note.html` (filename is misleading — it IS the hook sticker)

## What NOT to do

**Do NOT use** a yellow Post-it style, a pin-note tack, or any "sticky paper" skeuomorphism. Allen rejected that direction — the dark pill matches his brand system.

## Workflow

Build as standalone HTML → screenshot with headless Chrome → composite via ffmpeg (see `FFMPEG-RECIPES.md` Recipe 1). Do NOT re-render the full Hyperframes composition for sticker copy changes.
