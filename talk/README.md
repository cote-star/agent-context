# Cursor Meetup talk · May 2026

## Live deck (read this first)

| File | Purpose |
|---|---|
| [`index.html`](index.html) | Self-contained HTML deck (current — 21-slide structure, light cream theme). Open locally in any browser, or visit the GitHub Pages URL once Pages is enabled (see below). |
| [`cursor-meetup-may-2026.md`](cursor-meetup-may-2026.md) | Marp markdown source — single source of truth for the talk content. HTML and PDF are rendered from this file. |
| [`cursor-meetup-may-2026.html`](cursor-meetup-may-2026.html) | Standalone HTML render (byte-identical to `index.html`). |
| [`cursor-meetup-may-2026.pdf`](cursor-meetup-may-2026.pdf) | PDF render — portable handout / projection backup. |

## Stage support

| File | Purpose |
|---|---|
| [`demo-script.md`](demo-script.md) | Live-demo commands for slide 9 (Engineering pipeline), on-stage flow, backup plan, reset commands for rehearsal. |
| [`pre-recorded-fill.md`](pre-recorded-fill.md) | Recording instructions for the fill MP4 (plays during slide 9). |

## Audit + companion docs

| File | Purpose |
|---|---|
| [`deck-audit-2026-05-10.md`](deck-audit-2026-05-10.md) | End-to-end audit (story arc, audience comprehension, evidence credibility, gaps) that drove the current 21-slide structure. |
| [`notebooklm-update-brief-2026-05-10.md`](notebooklm-update-brief-2026-05-10.md) | Single-source brief to drop into NotebookLM as a "source" so it can refresh `Portable_Agent_Context.pdf`. Inlines every metric tracked. NotebookLM owns the dark + orange/green palette; the live deck does not. |

## Design references (NotebookLM-generated, not the live deck)

| File | Purpose |
|---|---|
| [`Portable_Agent_Context.pdf`](Portable_Agent_Context.pdf) | NotebookLM-generated visual deck — dark + orange/green palette, kept as a design reference for the brief. Not rendered to the live deck. |
| [`notebooklm-hero-reference.png`](notebooklm-hero-reference.png) | NotebookLM hero infographic — design reference. |

## Archive

| File | Purpose |
|---|---|
| [`archive/audience-presenter-devrel-review.md`](archive/audience-presenter-devrel-review.md) | Earlier audience/presenter/DevRel review — superseded by `deck-audit-2026-05-10.md`. Kept for back-reference. |

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
