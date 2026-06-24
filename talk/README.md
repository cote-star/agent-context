# agent-context talk pages

## Live deck (read this first)

| File | Purpose |
|---|---|
| [`index.html`](index.html) | The GitHub Pages target. Currently a byte-identical copy of `claude-dev-day-jun-2026.html` (Claude Community Meetup Amsterdam, June 2026 — warm-dark/terracotta edition, 20 slides). |
| [`claude-dev-day-jun-2026.html`](claude-dev-day-jun-2026.html) | The Claude Meetup edition source-of-truth — fork of the Cursor deck: Claude-first evidence ordering, merged per-agent slides, CLAUDE.md/Skills framing, hiring banner. |
| [`cursor-meetup-may-2026.html`](cursor-meetup-may-2026.html) | The completed Cursor Meetup edition — hand-authored HTML + CSS (deep-navy `#0A0E1A` background; green `#10B981` = lift/structured wins; orange `#F97316` = bare/routing/`.agent-context/` artifact). |
| [`LinkedIN_QR.JPG`](LinkedIN_QR.JPG), [`amit_passport.jpeg`](amit_passport.jpeg) | Public image assets referenced by both deck pages. Keep these paths stable; the HTML loads them directly. |

Both talks are complete. The public surface is the live HTML pages above
plus their referenced image assets. PDFs, speaker guides, render scripts,
demo orchestration notes, recordings, and audio-mastering work are local
archive material under ignored `talk/_archive-local/`.

## Rendering

The HTML pages are already committed. No build step is required to view
or deploy them. Open locally:

```bash
# from the repo root
open talk/index.html
# or, to serve over http (recommended — relative asset paths)
python3 -m http.server 8000
# then visit http://localhost:8000/talk/
```

Local serving is recommended over `file://` because the pages load assets
via relative paths (`../docs/visuals/`, `../docs/demos/`, and local talk
images).

## GitHub Pages URL

Once Pages is enabled on the repo (one-time, ~30s manual step described
below), the live deck will be at:

> `https://cote-star.github.io/agent-context/talk/`

The pages link to SVG assets under `../docs/{visuals,demos}/...`, which
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

## Updating Live Pages

The talks are archived as complete, so prefer typo/link fixes only. If the
current public page changes, edit `claude-dev-day-jun-2026.html` and refresh
the Pages target:

```bash
# from the repo root
cp talk/claude-dev-day-jun-2026.html talk/index.html
```

The completed Cursor edition remains available at
`talk/cursor-meetup-may-2026.html`. Edit it only if fixing the archived
public page directly.

## Local Archive

Completed-talk support files live locally under `talk/_archive-local/`
and are intentionally ignored by git. Use that directory for PDFs,
speaker guides, runbooks, recordings, audio work, and one-off scripts.
