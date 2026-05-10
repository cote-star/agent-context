# Cursor Meetup talk · May 2026

## Live deck (read this first)

| File | Purpose |
|---|---|
| [`index.html`](index.html) | Self-contained HTML deck — 21 slides, deep-navy theme. Byte-identical copy of `cursor-meetup-may-2026.html`; this filename is the GitHub Pages target. |
| [`cursor-meetup-may-2026.html`](cursor-meetup-may-2026.html) | The deck source-of-truth. Hand-authored HTML + CSS (deep-navy `#0A0E1A` background; green `#10B981` = lift/structured wins; orange `#F97316` = bare/routing/`.agent-context/` artifact). 21 slides, strict 720px-per-slide budget, Rule-of-Three on per-agent panels. |
| [`cursor-meetup-may-2026.pdf`](cursor-meetup-may-2026.pdf) | PDF render of the HTML deck — portable handout / projection backup. Rendered via `render-pdf.sh` (Chrome/Chromium/Edge headless). |
| [`render-pdf.sh`](render-pdf.sh) | Re-renders `cursor-meetup-may-2026.pdf` from the HTML source. Picks the first available headless browser (Chrome / Chromium / Edge). Run from inside `talk/`. |

Fresh Codex/Cursor evidence is produced with the isolated rerun harness.
The public deck is `talk/index.html`; local research notes and generated
working artifacts stay untracked and ignored.

## Rendering

The HTML deck is **already rendered and committed** at `index.html` and
`cursor-meetup-may-2026.html` — no build step required to view. Open
locally:

```bash
# from the repo root
open talk/index.html
# or, to serve over http (recommended — relative SVG asset paths)
python3 -m http.server 8000
# then visit http://localhost:8000/talk/
```

Local serving is recommended over `file://` because the deck loads SVG
assets via relative paths (`../docs/visuals/`, `../docs/demos/`).

## GitHub Pages URL

Once Pages is enabled on the repo (one-time, ~30s manual step described
below), the live deck will be at:

> `https://cote-star.github.io/agent-context/talk/`

The deck links to SVG assets under `../docs/{visuals,demos}/...`, which
resolve to `/agent-context/docs/...` — Pages serves the whole repo, so
the relative paths work.

## One-time Pages setup

The deploy workflow at `.github/workflows/deploy-pages.yml` runs on
every push to `main`, but the repo settings need to be enabled once:

1. Go to **Settings → Pages** on the GitHub repo
2. Under **Build and deployment → Source**, choose **GitHub Actions**
3. Push any commit to `main` (or run the workflow manually via Actions
   tab → "Deploy GitHub Pages" → "Run workflow")

After the first successful run, the live URL appears in the Pages
settings panel and on the workflow run summary.

## Updating the deck

Edit `cursor-meetup-may-2026.html` directly. Then refresh both
derivative artifacts in one pass:

```bash
# from the repo root
cp talk/cursor-meetup-may-2026.html talk/index.html
(cd talk && ./render-pdf.sh)
```

After edits, commit `cursor-meetup-may-2026.html`, `index.html`, and
`cursor-meetup-may-2026.pdf` together; push to `main`; Pages re-deploys
automatically.

## Format conversion

PowerPoint export is not auto-generated. To produce a `.pptx`, open the
PDF in PowerPoint or Keynote and export, or hand-port slides from the
HTML source.
