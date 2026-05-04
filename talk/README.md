# Cursor Meetup talk · May 2026

Files in this folder:

| File | Purpose |
|---|---|
| [`index.html`](index.html) | Self-contained HTML deck. Open locally in any browser, or visit the GitHub Pages URL once Pages is enabled (see below). |
| [`cursor-meetup-may-2026.md`](cursor-meetup-may-2026.md) | Marp markdown source (single source of truth for the talk content). The HTML deck is hand-rendered to match. |
| [`demo-script.md`](demo-script.md) | Live-demo commands, on-stage flow, backup plan if anything fails, reset commands for rehearsal. |
| [`pre-recorded-fill.md`](pre-recorded-fill.md) | Recording instructions for the slide-7 MP4 (the agent-fills-the-pack clip). |
| [`audience-presenter-devrel-review.md`](audience-presenter-devrel-review.md) | Narrative review across audience, presenter, and DevRel perspectives. |

For fresh Codex/Cursor evidence before the meetup, use
[`docs/experiments/codex-cursor-fresh-pack-rerun.md`](../docs/experiments/codex-cursor-fresh-pack-rerun.md).

## Rendering

The HTML deck is **already rendered and committed** at `index.html` — no build step required. Open it locally with any browser:

```bash
open ~/sandbox/play/agent-context/talk/index.html
# or
python3 -m http.server -d ~/sandbox/play/agent-context 8000
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

Edit `cursor-meetup-may-2026.md` (the Marp source) **and** `index.html` (the rendered HTML) so they stay in sync. They're hand-mirrored — there is no auto-build step. After edits, push to `main`; Pages re-deploys automatically.

## Format / format conversion

If you ever want a PDF or PPTX export of the deck (for organizer review or backup), the Marp source can be rendered with marp-cli:

```bash
npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.pdf
npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.pptx
```

(One-time `npx` install of `@marp-team/marp-cli`.)
