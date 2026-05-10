# Cursor Meetup talk · May 2026

Files in this folder:

| File | Purpose |
|---|---|
| [`index.html`](index.html) | Self-contained HTML deck (current — 21-slide structure). Open locally in any browser, or visit the GitHub Pages URL once Pages is enabled (see below). |
| [`cursor-meetup-may-2026.md`](cursor-meetup-may-2026.md) | Marp markdown source (single source of truth for the talk content). HTML deck is auto-rendered via marp-cli. |
| [`cursor-meetup-may-2026.html`](cursor-meetup-may-2026.html) | Standalone HTML render (same content as `index.html`). |
| [`cursor-meetup-may-2026.pdf`](cursor-meetup-may-2026.pdf) | PDF render — portable handout / projection backup. |
| [`Portable_Agent_Context.pdf`](Portable_Agent_Context.pdf) | NotebookLM-generated visual deck — design reference for the dark + orange/green palette. Not the live deck. |
| [`unnamed.png`](unnamed.png) | NotebookLM hero infographic — design reference. |
| [`demo-script.md`](demo-script.md) | Live-demo commands for slide 9 (Engineering pipeline), on-stage flow, backup plan, reset commands for rehearsal. |
| [`pre-recorded-fill.md`](pre-recorded-fill.md) | Recording instructions for the fill MP4 (plays during slide 9). |
| [`notebooklm-update-brief-2026-05-10.md`](notebooklm-update-brief-2026-05-10.md) | Single-source brief to drop into NotebookLM as a "source" so it can refresh `Portable_Agent_Context.pdf` to match the current deck. Inlines every metric tracked. |
| [`deck-audit-2026-05-10.md`](deck-audit-2026-05-10.md) | End-to-end audit (story arc, audience comprehension, evidence credibility, gaps) that drove the current 21-slide structure. |
| [`audience-presenter-devrel-review.md`](audience-presenter-devrel-review.md) | Earlier audience/presenter/DevRel review (historical — superseded by the 2026-05-10 audit, kept for back-reference). |

Fresh Codex/Cursor evidence is produced with the private isolated rerun harness.
The public deck is `talk/index.html`; local research harnesses stay untracked
and ignored.

## Rendering

The HTML deck is **already rendered and committed** at `index.html` — no build step required. Open it locally with any browser:

```bash
# from the repo root
open talk/index.html
# or, to serve over http (recommended — relative SVG asset paths)
python3 -m http.server 8000
# then visit http://localhost:8000/talk/
```

Local serving is recommended over `file://` because the deck loads SVG assets via relative paths.

## GitHub Pages URL

Once Pages is enabled on the repo (one-time, ~30s manual step described below), the live deck will be at:

> `https://cote-star.github.io/agent-context/talk/`

The deck links to the SVG assets at `../docs/visuals/...`, which resolve to `/agent-context/docs/visuals/...` — both are served by Pages since the workflow uploads the whole repo.

## One-time Pages setup

The deploy workflow at `.github/workflows/deploy-pages.yml` runs on every push to `main`, but the repo settings need to be enabled once:

1. Go to **Settings → Pages** on the GitHub repo
2. Under **Build and deployment → Source**, choose **GitHub Actions**
3. Push any commit to `main` (or run the workflow manually via Actions tab → "Deploy GitHub Pages" → "Run workflow")

After the first successful run, the live URL will appear in the Pages settings panel and on the workflow run summary.

## Updating the deck

Edit `cursor-meetup-may-2026.md` (the Marp source), then re-render via marp-cli. The HTML and PDF are committed alongside the source so the GitHub Pages deck always reflects the latest content.

```bash
# from the repo root
npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.html
npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.pdf --allow-local-files
cp talk/cursor-meetup-may-2026.html talk/index.html   # GitHub Pages target
```

After edits, push to `main`; Pages re-deploys automatically.

## Format conversion

The Marp source can also export to PowerPoint:

```bash
npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.pptx
```
