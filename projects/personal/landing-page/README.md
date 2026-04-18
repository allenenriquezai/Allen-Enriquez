# Landing Page

Static site. No build step. Drop into GitHub Pages or any static host.

## Files
- `index.html` — single page
- `style.css` — all styles
- `lead-magnet.pdf` — downloaded by the hero/CTA buttons

## Local preview
```
cd projects/personal/landing-page
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy to GitHub Pages
1. Create new repo (e.g. `allen-enriquez/landing`)
2. Push contents of this folder to `main` branch
3. Repo → Settings → Pages → Source: `main` branch, `/` (root)
4. Wait ~60 sec. Site goes live at `https://allen-enriquez.github.io/landing/`
5. Add custom domain later via Settings → Pages → Custom domain

## Before going live — replace
- `calendar.app.google/your-link-here` (in index.html) with real Google Calendar booking link
- Update email if needed (`allenenriquez006@gmail.com`)
