---
name: eps-measure
description: Use when extracting room measurements from a floor plan for an EPS quote. Triggered when a floor plan image or PDF is provided and measurements are needed.
disable-model-invocation: true
---

# EPS Measure Skill

Extract room-by-room measurements from a floor plan using vision. Output `rooms.json` for use by eps-lineitems.

---

## Domain Knowledge

### Unit conventions
- Floor plans labeled in **mm**: divide by 1000 (e.g. `4200` → `4.2m`)
- Floor plans labeled in **m**: use directly
- Scale bar (e.g. "1:100"): measure relative distances and convert using scale
- No labels, no scale: estimate using reference objects (door = 0.9m wide, bedroom = 3.5–4.0m)

### Default assumptions
- Ceiling height: **2.4m** unless labeled otherwise
- Open-plan living/dining: treat as **one room** unless clearly separated by walls
- Stairs, hallways, laundries: **include** if they will be painted

### Job type → what to extract
| Job type | Surfaces to measure |
|---|---|
| `internal` | Walls + ceilings for every room |
| `ceilings` | Ceilings only |
| `external` | External walls + roof footprint |
| `full` | Internal walls + ceilings + external walls + roof |

### Area formulas
- Wall area per room: `2 × (length + width) × height`
- Ceiling area per room: `length × width`
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
─────────────────────────────────────────────────────────────
Master Bedroom         4.2   3.6   2.4   37.4       15.1
...
─────────────────────────────────────────────────────────────
TOTAL                                    XXX.X      XXX.X
```

Mark estimated rooms with `*`. List all flags below the table.

---

## Success Criteria

- `rooms.json` written with all rooms
- Total areas calculated
- Estimated rooms flagged
- No silent guesses — every uncertainty is surfaced to Allen

---

## Full workflow reference
`projects/eps/workflows/measure-floor-plan.md`
