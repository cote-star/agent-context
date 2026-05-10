# Cursor Meetup talk · May 2026

## Live deck (read this first)

| File | Purpose |
|---|---|
| [`index.html`](index.html) | Self-contained HTML deck — 21 slides, deep-navy theme. Byte-identical copy of `cursor-meetup-may-2026.html`; this filename is the GitHub Pages target. |
| [`cursor-meetup-may-2026.html`](cursor-meetup-may-2026.html) | The deck source-of-truth. Hand-authored HTML + CSS (deep-navy `#0A0E1A` background; green `#10B981` = lift/structured wins; orange `#F97316` = bare/routing/`.agent-context/` artifact). 21 slides, strict 720px-per-slide budget, Rule-of-Three on per-agent panels. |
| [`cursor-meetup-may-2026.pdf`](cursor-meetup-may-2026.pdf) | PDF render of the HTML deck — portable handout / projection backup. Rendered via `render-pdf.sh` (Chrome/Chromium/Edge headless). |
| [`render-pdf.sh`](render-pdf.sh) | Re-renders `cursor-meetup-may-2026.pdf` from the HTML source. Picks the first available headless browser (Chrome / Chromium / Edge). Run from inside `talk/`. |

## Stage support

| File | Purpose |
|---|---|
| [`demo-script.md`](demo-script.md) | Live-demo commands for slide 9 (Engineering pipeline), on-stage flow, backup plan, reset commands for rehearsal. |
| [`pre-recorded-fill.md`](pre-recorded-fill.md) | Recording instructions for the fill MP4 (plays during slide 9). |

## Audit + companion docs

| File | Purpose |
|---|---|
| [`deck-audit-2026-05-10.md`](deck-audit-2026-05-10.md) | End-to-end audit (story arc, audience comprehension, evidence credibility, gaps) that drove the 21-slide structure. |
| [`notebooklm-update-brief-2026-05-10.md`](notebooklm-update-brief-2026-05-10.md) | Single-source brief to drop into NotebookLM as a "source" so it can refresh `Portable_Agent_Context.pdf`. Inlines every metric tracked. The NotebookLM-generated visual deck and the live HTML deck share a deep-navy + green/orange palette family. |

## Design references (NotebookLM-generated, not the live deck)

| File | Purpose |
|---|---|
| [`Portable_Agent_Context.pdf`](Portable_Agent_Context.pdf) | NotebookLM-generated visual deck — design reference, not rendered to the live deck. |
| [`notebooklm-hero-reference.png`](notebooklm-hero-reference.png) | NotebookLM hero infographic — design reference. |

## Archive

| File | Purpose |
|---|---|
| [`archive/audience-presenter-devrel-review.md`](archive/audience-presenter-devrel-review.md) | Earlier audience/presenter/DevRel review — superseded by `deck-audit-2026-05-10.md`. Kept for back-reference. |
| [`archive/cursor-meetup-may-2026-marp-source.md`](archive/cursor-meetup-may-2026-marp-source.md) | Earlier Marp markdown source for the deck (light cream theme, content auto-rendered to HTML/PDF). Superseded by the hand-authored `cursor-meetup-may-2026.html`; kept for content recovery. |
| [`archive/cursor-meetup-may-2026-marp-cream.html`](archive/cursor-meetup-may-2026-marp-cream.html) | Marp render of the previous deck (cream theme). Reference only. |
| [`archive/cursor-meetup-may-2026-marp-cream.pdf`](archive/cursor-meetup-may-2026-marp-cream.pdf) | PDF of the same. Reference only. |

Fresh Codex/Cursor evidence is produced with the private isolated rerun
harness. The public deck is `talk/index.html`; local research harnesses
stay untracked and ignored.

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

PowerPoint export is no longer auto-generated (the old Marp `.pptx`
flow is in `archive/`). To produce a `.pptx`, open the PDF in
PowerPoint or Keynote and export, or hand-port slides from the HTML
source.
