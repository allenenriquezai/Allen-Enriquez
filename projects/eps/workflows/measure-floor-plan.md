
# EPS Measure Skill

Extract room-by-room measurements from a floor plan using vision. Output `rooms.json` for use by eps-lineitems.

---

## Domain Knowledge

### Unit conventions
- Floor plans labeled in **mm**: divide by 1000 (e.g. `4200` -> `4.2m`)
- Floor plans labeled in **m**: use directly
- Scale bar (e.g. "1:100"): measure relative distances and convert using scale
- No labels, no scale: estimate using reference objects (door = 0.9m wide, bedroom = 3.5-4.0m)

### Default assumptions
- Ceiling height: **2.4m** unless labeled otherwise
- Open-plan living/dining: treat as **one room** unless clearly separated by walls
- Stairs, hallways, laundries: **include** if they will be painted

### Job type -> what to extract
| Job type | Surfaces to measure |
|---|---|
| `internal` | Walls + ceilings for every room |
| `ceilings` | Ceilings only |
| `external` | External walls + roof footprint |
| `full` | Internal walls + ceilings + external walls + roof |

### Area formulas
- Wall area per room: `2 x (length + width) x height`
- Ceiling area per room: `length x width`
- External wall (high, >3m): use EXT-02 rate — flag this room

---

## Decision Logic

| Situation | Action |
|---|---|
| Dimensions clearly labeled | Read directly — no estimation needed |
| Scale bar present, no labels | Apply scale to estimate dimensions — mark `"estimated": false` if confident |
| No labels, no scale bar | Estimate from reference objects — mark `"estimated": true` |
| Stairwell detected | Include in rooms list + add to `flags`: "Stairwell — may need high-level access (EXT-02 rate)" |
| Vaulted / raked ceiling | Flag it: "Vaulted ceiling in [room] — may affect area calculation" |
| File on Google Drive | Read file path from context — use vision directly on the downloaded image |
| Dimensions are ambiguous | Flag the room — do NOT guess silently |

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
- If the plan uses mm, convert: divide by 1000 (e.g. `4200mm -> 4.2m`)
- If the plan uses a scale bar (e.g. 1:100), note the scale and estimate from relative sizes
- For open-plan areas (living/dining combined), treat as one room unless clearly separated by walls
- Stairs, hallways, and laundries: include if they would be painted

**If dimensions are not labeled:**
- Look for a scale bar or noted scale (e.g. "Scale 1:100")
- Estimate relative to a known reference (standard door = 0.9m wide, standard bedroom = ~3.5-4.0m wide)
- Note estimated rooms with `"estimated": true` in the output
- Do NOT guess silently — flag uncertain rooms

---

## Output

Write to `projects/eps/.tmp/rooms.json`:

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
    }
  ],
  "flags": [],
  "total_wall_area_sqm": 0,
  "total_ceiling_area_sqm": 0
}
```

After writing: calculate and fill `total_wall_area_sqm` and `total_ceiling_area_sqm`.

---

## After Output

Print a summary table:

```
Room                   L(m)  W(m)  H(m)  Wall(sqm)  Ceil(sqm)
-------------------------------------------------------------
Master Bedroom         4.2   3.6   2.4   37.4       15.1
Living Room            6.0   4.5   2.4   50.4       27.0
...
-------------------------------------------------------------
TOTAL                                    XXX.X      XXX.X
```

Mark estimated rooms with `*`. List all flags below the table.

---

## Togal.ai (Future — Not Yet Built)

When Togal.ai API access is available, a measurement tool will be added here.
For now: vision only.

---

## Success Criteria

- `rooms.json` written with all rooms
- Total areas calculated
- Estimated rooms flagged
- No silent guesses — every uncertainty is surfaced to Allen
