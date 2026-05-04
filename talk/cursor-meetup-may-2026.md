<!--
Cursor Meetup, May 2026
Talk: agent-context — checked-in repo evidence for coding agents

Format: Marp markdown. Renders to PDF / HTML / PPTX:
  npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.pdf
  npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.html
  npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.pptx

Slide breaks are `---` on its own line. SVGs paths are relative to this file
(../docs/visuals/* and ../docs/demos/* and ../docs/evidence/figures/*).
-->
---
marp: true
theme: default
paginate: true
size: 16:9
backgroundColor: '#FDFCF8'
color: '#111827'
style: |
  section {
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #FDFCF8;
    color: #111827;
    padding: 60px;
  }
  section.lead {
    text-align: center;
    justify-content: center;
  }
  h1 { color: #111827; font-weight: 800; font-size: 1.7em; }
  h2 { color: #111827; font-weight: 800; border-bottom: 3px solid #F37021; padding-bottom: 0.2em; }
  h3 { color: #475569; font-weight: 600; }
  code {
    background-color: #FFF7E8;
    color: #111827;
    padding: 0.1em 0.3em;
    border-radius: 4px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  pre {
    background-color: #FFF7E8;
    border: 1px solid #E8D9BE;
    border-radius: 8px;
    padding: 1em;
    font-size: 0.85em;
  }
  pre code { background-color: transparent; padding: 0; }
  a { color: #F37021; text-decoration: none; }
  a:hover { text-decoration: underline; }
  strong { color: #111827; font-weight: 700; }
  em { color: #475569; }
  blockquote {
    border-left: 4px solid #F37021;
    padding-left: 1em;
    color: #475569;
    margin-left: 0;
    font-style: italic;
  }
  ul li::marker { color: #F37021; }
  ol li::marker { color: #F37021; }
  table { border-collapse: collapse; width: 100%; }
  th, td { padding: 0.4em 0.8em; border-bottom: 1px solid #E8D9BE; }
  th { background-color: #FFF7E8; text-align: left; }
  img { display: block; margin: 0 auto; max-height: 75vh; }
  section::after {
    color: #64748B;
    font-size: 0.65em;
  }
---

<!-- _class: lead -->

# agent-context

### Checked-in repo evidence for coding agents

What we built · what we measured · what we narrowed

Cursor Meetup · May 2026
[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

---

## The cold-start tax

Every coding-agent session starts cold:

- re-reads the directory tree
- guesses ownership boundaries
- misses the one invariant that should have shaped the answer

Same shape in **Claude, Codex, Cursor, Gemini, OpenCode**. Compounds across every question, every reviewer, every agent.

![w:900](../docs/visuals/agent-context-loop.svg)

---

## One folder, every agent

Commit `.agent-context/` to your repo. `init` writes the same routing block into four standard project-rule files. Modern agents read several of these **together** — not 1:1 — so any one is enough to route any agent.

| Routing file | Common pick-ups |
|---|---|
| `.cursorrules` | Cursor |
| `CLAUDE.md` | Claude · Claude Code · Cursor |
| `AGENTS.md` | Codex · OpenCode · Cursor |
| `GEMINI.md` | Gemini |

**One pack. Four routing files. Redundant by design — any one routes any agent.**

---

## What's in the pack

![w:680](../docs/demos/cold-start-agent-context-hero.svg)

Three layers + quality. Tier 3 = 11 files committed alongside your code.

---

## Two reading patterns, one pack

```text
Search-and-verify  (Codex, Cursor, OpenCode w/ local model)
  search_scope   →  scoped grep   →  verification shortcut  →  answer

Trust-and-follow   (Claude, Gemini, OpenCode w/ Anthropic backend)
  routing block  →  required files  →  completeness contract  →  answer
```

Same content. Two reading paths. Most authoring projects pick one mode and break for the other; agent-context provides scaffolding for both.

---

## Live demo · init

```bash
$ cd examples/hello-service
$ ~/agent-context/bin/agent-context init --tier 3 .
Initialized .agent-context/current/ with 11 files (tier 3)
Copied helper tools to .agent-context/tools/
Wrote routing block in CLAUDE.md
Wrote routing block in AGENTS.md
Wrote routing block in GEMINI.md
Wrote routing block in .cursorrules
```

Open `.cursorrules` → routing block lives there. Same in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`.

---

## Live demo · agent fills the pack

> **"Set up agent context for this repo."**

[Embed pre-recorded MP4 — ~30s real, sped up to ~15s]

[`SKILL.md`](../SKILL.md) drives the agent:

1. enumerate every subsystem first (so nothing silently gets skipped)
2. fill all 11 templates
3. write acceptance tests with grep verification
4. run the machine checks

---

## Live demo · verify

```bash
$ ~/agent-context/bin/agent-context verify .
OK: agent-context passed machine-checkable validation (tier 3)
```

Checks: structure · JSON schema · real glob matches · template-marker elimination.

CI-friendly. Pair with `freshness` (drift detection) and `doctor` (env diagnostics).

---

## What we measured · March/April 2026

![w:1100](../docs/visuals/hero-stat-ribbon.svg)

78+ reviewer-graded answers across three repos with grep-backed verification:

- ML pipeline · 501 files · Python
- Dual CLI · 155 files · Rust + Node.js
- React frontend · 1,982 files · TypeScript

Same template, zero modifications.

---

## What the May 2026 rerun showed

![w:1100](../docs/visuals/may-2026-rerun-ribbon.svg)

**Honest read-out:**

- ✓ Navigation efficiency confirmed for Codex and Cursor
- ✗ Correctness lift not reproduced in this one-repo focused rerun
- ⚠ Stale-pack guidance caused 3 dead ends in the Codex structured run

Cursor evidence is provisional · aggregate measurement on the v0.5 roadmap.

---

## Model-agnostic by construction

![w:1100](../docs/visuals/opencode-tunnel-deployment.svg)

The pack is markdown and JSON; routing blocks are plain text.

Operator-verified with **OpenCode + OSS model** (Devstral Small 2 / Qwen 4B) over an SSH tunnel. **No commercial-frontier dependency.**

---

## Lessons from the rerun

**Freshness is part of the claim.** Stale pack guidance caused 3 dead ends in the Codex structured run. A pack that drifts from code is worse than no pack — agents trust it.

**Reviewer grading > self-scoring.** Self-reported file counts can mislead. Reviewer-graded yes-rate against ground truth is the only metric we trust for correctness.

**Tier system as adoption ladder.** Start at tier 1 (2 files). Scale when the team is ready. Each tier is a valid stopping point — no hidden dependency on the full pack.

**Repo-agnostic design ≠ universal evidence.** We have evidence on three code-repo types. Non-code corpora (datasets, design systems, runbooks) — designed to generalize, not yet measured.

---

## Try it tonight

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 3 .
```

Or open the repo in your agent of choice and ask:

> **Set up agent context for this repo.**

**One folder. Every coding agent. Read before any edit.**

[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

---

<!-- _class: lead -->

## Questions

[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

`agent-context init` · `verify` · `freshness` · `doctor`

Thank you.
