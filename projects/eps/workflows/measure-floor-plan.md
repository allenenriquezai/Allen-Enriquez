# Measure Floor Plan

Extract room-by-room measurements from a floor plan image or PDF.

---

## Input Required

Before starting, confirm you have:
- **Floor plan file** — local path or Google Drive link (image: JPG/PNG, or PDF)
- **Job type** — what surfaces are in scope:
  - `internal` → walls + ceilings
  - `ceilings` → ceilings only
  - `external` → external walls + roof
  - `full` → internal walls + ceilings + external

If file is missing, ask for it before proceeding.

---

## How to Read the Floor Plan

Open and read the file directly using vision.

**Extract for each room:**
- Room name (e.g. Master Bedroom, Living Room, Bathroom 1)
- Length (m) and Width (m)
- Ceiling height (m) — use labeled height if shown; otherwise assume **2.4m**
- Whether it has a ceiling in scope
- Whether it is external-facing

**Reading tips:**
- Dimensions are usually labeled along walls (e.g. `4200` = 4.2m, `3600` = 3.6m)
- If the plan uses mm, convert: divide by 1000 (e.g. `4200mm → 4.2m`)
- If the plan uses a scale bar (e.g. 1:100), note the scale and estimate from relative sizes
- For open-plan areas (living/dining combined), treat as one room unless clearly separated by walls
- Stairs, hallways, and laundries: include if they would be painted

**If dimensions are not labeled:**
- Look for a scale bar or noted scale (e.g. "Scale 1:100")
- Estimate relative to a known reference (standard door = 0.9m wide, standard bedroom = ~3.5–4.0m wide)
- Note estimated rooms with `"estimated": true` in the output
- Do NOT guess silently — flag uncertain rooms

---

## Output

Save to `projects/eps/.tmp/rooms.json`:

```json
{
  "source_file": "path/to/floor_plan.pdf",
  "job_type": "internal",
  "assumed_ceiling_height_m": 2.4,
  "rooms": [
    {
      "name": "Master Bedroom",
      "length_m": 4.2,
      "width_m": 3.6,
      "height_m": 2.4,
      "surfaces": ["walls", "ceiling"],
      "estimated": false,
      "notes": ""
    },
    {
      "name": "Bathroom 1",
      "length_m": 2.1,
      "width_m": 1.8,
      "height_m": 2.4,
      "surfaces": ["walls", "ceiling"],
      "estimated": false,
      "notes": "Includes shower recess walls"
    }
  ],
  "flags": [
    "Stairwell detected — may require high-level access (EXT-02 rate)"
  ],
  "total_wall_area_sqm": 0,
  "total_ceiling_area_sqm": 0
}
```

After writing the file, also calculate and fill in:
- `total_wall_area_sqm` = sum of all rooms: `2 × (length + width) × height`
- `total_ceiling_area_sqm` = sum of all rooms: `length × width`

---

## After Output

Print a summary table to the screen:

```
Room                   L(m)  W(m)  H(m)  Wall(sqm)  Ceil(sqm)
─────────────────────────────────────────────────────────────
Master Bedroom         4.2   3.6   2.4   37.4       15.1
Living Room            6.0   4.5   2.4   50.4       27.0
...
─────────────────────────────────────────────────────────────
TOTAL                                    XXX.X      XXX.X
```

Flag any rooms marked `"estimated": true` with an asterisk (*).

---

## Togal.ai (Future Enhancement)

When Togal.ai API access is available:
- Run `tools/togal_measure.py --file "path"` BEFORE the vision step
- If it returns data, use that instead of vision extraction
- Fall back to vision if Togal.ai fails or returns low confidence

For now: vision only.
