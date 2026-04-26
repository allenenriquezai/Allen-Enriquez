# Coach ICP Ad Landing Page

Landing page for the ₱5K/mo PH Meta ad campaign targeting coach ICP. Single-page funnel with Tally form embed for ad-lead intake.

## Files

- `index.html` — single page with all sections
- `style.css` — responsive dark theme with brand blue styling
- README.md — this file

## Sections

1. **Hero** — headline + subheadline + primary CTA
2. **Video embed** — placeholder for YouTube unlisted or Loom embed
3. **Pain** — 5-card grid of coach problems
4. **Pillars** — 5-pillar system summary table
5. **Proof** — drink-own-champagne + EPS case study + client notes
6. **How we engage** — 3-step process with diagnostic → pilot → retainer
7. **Form section** — Tally embed for intake (Name, IG handle, pain multi-select, free text)
8. **Final CTA** — reinforce problem + CTA to book call
9. **Footer** — branding + contact info + IG handle

## Setup Steps

### 1. Create Tally form

1. Go to https://tally.so/r/new
2. Create a new form with these fields:
   - **Name** (text, required)
   - **Instagram handle** (text, required)
   - **What's eating your time?** (multiple-choice checkboxes):
     - DMs and questions
     - Client onboarding
     - No-show follow-ups
     - No content posted
   - **Anything else I should know?** (long text, optional)

3. Under **Integrations** → **Webhooks**, add:
   - **URL:** `https://<crm-host>/api/ad-leads/intake`
   - **Method:** POST
   - **Trigger:** Form submission
   - **Payload:** Send full submission JSON

4. Copy the Tally form URL/ID from the top of the form

### 2. Insert Tally form ID into HTML

In `index.html`, find this line:

```html
<iframe data-tally-src="https://tally.so/r/YOUR_FORM_ID" loading="lazy" style="border:none;"></iframe>
```

Replace `YOUR_FORM_ID` with the actual ID from your Tally form URL (e.g., `w47D8L` from `https://tally.so/r/w47D8L`).

### 3. Add video embed

When Allen films the diagnostic/positioning video (YouTube unlisted or Loom), update this line in `index.html`:

```html
<!-- Allen drops in YouTube unlisted or Loom embed URL here later -->
```

Replace with an embed code:

**YouTube:**
```html
<iframe width="100%" height="100%" src="https://www.youtube.com/embed/VIDEO_ID" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style="border-radius:16px;"></iframe>
```

**Loom:**
```html
<iframe src="https://www.loom.com/embed/LOOM_ID" frameborder="0" allowfullscreen style="border-radius:16px; width:100%; height:100%;"></iframe>
```

### 4. Local preview

```bash
cd projects/personal/sales/ad-landing-coaches
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy to GitHub Pages

1. Create a new repo: `allen-enriquez/ad-landing-coaches` (or preferred name)
2. Push contents of this folder to `main` branch
3. In repo Settings → Pages → Source: set to `main` / `/` root
4. Live at: `https://allen-enriquez.github.io/ad-landing-coaches/`
5. (Optional) Add custom domain later in Pages settings

## Ad Campaign Flow

1. Meta ad → landing page URL
2. Form submission → Tally webhook → POST to `https://<crm-host>/api/ad-leads/intake`
3. CRM endpoint receives JSON (name, ig_handle, pain_tags, notes) → stores as `outreach_prospects` row with `status='ad-lead'`
4. Manual outreach from .csv export or CRM dashboard

## Tally Webhook Payload Format

Tally sends POST body like:

```json
{
  "eventId": "...",
  "createdAt": "2026-04-26T12:00:00Z",
  "respondent": {
    "email": "...",
    "name": "..."
  },
  "response": {
    "Field-1 (Name)": "John Doe",
    "Field-2 (IG handle)": "@johncoach",
    "Field-3 (Pain)": ["DMs and questions", "No content posted"],
    "Field-4 (Anything else)": "Also struggling with..."
  }
}
```

CRM endpoint normalizes this to `outreach_prospects` table format.

## Voice & Copy Notes

- 3rd-grade reading level
- <10 words per sentence in headlines
- "Free 30-min diagnostic" (no "first 5 case-study trades" in public copy)
- "Stop doing all the work. Start running a system." = core positioning
- Pain cards use coach language, not tech language ("ghosted again" not "conversion optimization")
- Proof section = drink-own-champagne + verifiable internal case study + live client mentions (data/testimonials "on request")

## Next Steps

- Allen films diagnostic video (or records Loom)
- Create Tally form and insert ID into HTML
- Test form submission locally
- Push to GitHub
- Share landing page URL in Meta ad campaign
