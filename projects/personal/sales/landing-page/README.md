# Landing Page — Brand / Content Audience

Brief personal brand page for YouTube/IG/TikTok comment CTAs.

## Files
- `index.html` — single page
- `style.css` — all styles
- `profile.png` — hero photo

## Local preview
```
cd projects/personal/sales/landing-page
python3 -m http.server 8000
# open http://localhost:8000
```

## Before going live — fix these

**1. Form backend (Formspree)**
- Sign up free at https://formspree.io (50 submissions/month free)
- Create new form → copy the endpoint ID
- In `index.html`, replace `YOUR_FORMSPREE_ID` with the ID
- Test submit. Responses land in email.

Alternative if Formspree limit is tight: Tally.so embed or Google Forms.

**2. Verify social handles**
Current assumptions in `index.html`:
- YouTube: `@allenenriquezz` (confirmed from reel screenshot)
- Instagram: `@allenenriquezz` (verify — may differ)
- TikTok: `@allenenriquezz` (verify — may differ)
- Facebook: `profile.php?id=61574343211417` (confirmed from memory)

Fix any wrong handles before deploying.

## Deploy to GitHub Pages
1. New repo: `allen-enriquez/connect` (or similar)
2. Push this folder contents to `main`
3. Repo → Settings → Pages → Source: `main`, `/` root
4. Live at `https://allen-enriquez.github.io/connect/`
5. Add custom domain later (e.g. `allenenriquez.com`)

## Use case
Reply to YouTube comments with this URL. Form submissions → Allen reaches out 1:1 within 48 hours.
