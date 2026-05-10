<!--
Cursor Meetup, May 2026
Talk: agent-context — Stop Re-Teaching Your Repo to Every Coding Agent

Format: Marp markdown. Renders to PDF / HTML / PPTX:
  npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.pdf
  npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.html
  npx @marp-team/marp-cli@latest cursor-meetup-may-2026.md -o cursor-meetup-may-2026.pptx

Slide breaks are `---` on its own line. SVG paths are relative to this file
(../docs/visuals/* and ../docs/demos/* and ../docs/evidence/figures/*).

Companion design reference: Portable_Agent_Context.pdf in this folder
(NotebookLM-generated visual deck). The markdown below is the source-of-truth
for narrative/evidence; visual figures may lag and will be refreshed.
-->
---
marp: true
theme: default
paginate: true
size: 16:9
backgroundColor: '#0B1220'
color: '#E2E8F0'
style: |
  /* NotebookLM-pattern dark theme: deep navy background, orange primary
     accent (#F97316), green secondary accent (#10B981) for success metrics
     and outcome labels. Mirrors the visual language of
     talk/Portable_Agent_Context.pdf (NotebookLM design reference). */
  section {
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0B1220 radial-gradient(ellipse at top, rgba(249,115,22,0.08), transparent 60%);
    color: #E2E8F0;
    padding: 60px;
  }
  section.lead {
    text-align: center;
    justify-content: center;
    background:
      radial-gradient(ellipse at center, rgba(249,115,22,0.18), transparent 65%),
      #0B1220;
  }
  h1 {
    color: #FFFFFF;
    font-weight: 800;
    font-size: 1.9em;
    letter-spacing: -0.01em;
    text-shadow: 0 2px 24px rgba(249,115,22,0.18);
  }
  h2 {
    color: #FFFFFF;
    font-weight: 800;
    border-bottom: 3px solid #F97316;
    padding-bottom: 0.25em;
    margin-bottom: 0.6em;
  }
  h3 {
    color: #94A3B8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.95em;
  }
  code {
    background-color: #1E293B;
    color: #FED7AA;
    padding: 0.1em 0.35em;
    border-radius: 4px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  pre {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-left: 3px solid #F97316;
    border-radius: 8px;
    padding: 1em;
    font-size: 0.85em;
    color: #E2E8F0;
  }
  pre code {
    background-color: transparent;
    padding: 0;
    color: #6EE7B7;
  }
  a {
    color: #FB923C;
    text-decoration: none;
    overflow-wrap: anywhere;
    border-bottom: 1px dotted rgba(251,146,60,0.4);
  }
  a:hover { border-bottom-style: solid; }
  strong { color: #F97316; font-weight: 700; }
  em { color: #94A3B8; }
  blockquote {
    border-left: 4px solid #F97316;
    background: rgba(249,115,22,0.06);
    padding: 0.6em 1em;
    color: #FED7AA;
    margin: 0.6em 0;
    font-style: normal;
    border-radius: 0 6px 6px 0;
  }
  ul li::marker { color: #F97316; }
  ol li::marker { color: #F97316; font-weight: 700; }
  table {
    border-collapse: collapse;
    width: 100%;
    background: rgba(15,23,42,0.6);
    border-radius: 8px;
    overflow: hidden;
  }
  th, td {
    padding: 0.5em 0.85em;
    border-bottom: 1px solid #1E293B;
    color: #E2E8F0;
  }
  th {
    background-color: #111827;
    text-align: left;
    color: #FFFFFF;
    border-bottom: 2px solid #F97316;
    text-transform: uppercase;
    font-size: 0.85em;
    letter-spacing: 0.04em;
  }
  /* Bold values inside tables (last cell typically) get the green
     "outcome/success" accent that NotebookLM uses for measured wins. */
  td strong { color: #34D399; }
  img {
    display: block;
    margin: 0 auto;
    max-height: 70vh;
    border-radius: 8px;
  }
  section::after {
    color: #64748B;
    font-size: 0.65em;
  }
---

<!-- _class: lead -->

# Stop Re-Teaching Your Repo to Every Coding Agent

### Make context portable, reviewable, fresh, and testable before the agent edits.

A concrete workflow for Cursor, Claude, Codex, Gemini, and OpenCode.

**Amit Prusty** · Cursor Meetup Amsterdam · May 2026
[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

---

## The agent is new here every time

Most coding agents enter a repo as a bright visitor with no durable map.

- They rediscover the tree.
- They infer ownership from whatever file they open first.
- They miss the invariant that decides whether an answer is safe.
- They repeat the same exploration in the next session, editor, or model.

A **cold session** — unknown files, unclear risks, expensive search — gets converted into **bounded work** — read order, named blast radius, verified output — only when the repo carries its own map.

![w:900](../docs/visuals/agent-context-loop.svg)

---

## The failure is often not intelligence. It is missing repo evidence.

We already check in tests, docs, schemas, CI, runbooks, and migration history.

**Agent context should be another checked-in repo artifact:** the map of what is true, risky, connected, and out-of-bounds.

| **Portable** | **Reviewable** | **Fresh** |
|:---|:---|:---|
| Markdown / JSON, not vendor memory. | Lives in git. Reviewed like code changes. | Drift is a failing preflight, not a quiet footnote. |

**The standard is simple: read the repo map before editing the repo.**

---

## Every serious corpus needs a navigation layer

The dual-routing architecture generalizes to any file system or stable corpus an agent must explore before acting:

1. Stable datasets
2. Design systems
3. Operations runbooks
4. **Code repositories** ← we focus here today

But today, we focus on where it hurts developers the most: code repositories.

---

## Explorable repo recall as a three-track system

agent-context works when **navigation**, **operating loop**, and **engineering** are treated as separate controls.

![w:1050](../docs/evidence/figures/three-tracks-importance-minimal.svg)

| Track | Question | Concretely |
|---|---|---|
| **Navigation** (control surface) | What should load, what should not, when should it stop? | read order / risky paths |
| **Operating Loop** (agent behavior) | How does this agent consume repo context during real work? | trust route / verify route |
| **Engineering** (systems layer) | What makes prior work durable, inspectable, and reusable? | manifest / tests / CI |

Outcomes when all three line up: bounded loading, provenance, faster evidence.

---

## Today's session: the Navigation track

The three tracks are companions, but each deserves its own focused conversation. **Today is the Navigation track** — the control surface that decides:

- **What to load** — completeness contracts that name every file family that must change together.
- **What not to load** — search scopes that bound where the agent grep-walks.
- **When to stop** — stop rules and verification shortcuts that say "you have enough to answer."

Operating Loop (how Claude vs Cursor vs Codex actually *consume* the same pack) and Engineering (manifest / tests / CI / freshness gates) are deliberately out of scope for this hour — covered through the methodology and tradeoff slides at a depth that supports the navigation story, not as standalone deep dives.

---

## The artifact: `.agent-context/`

A committed folder next to the code. No hosted service. No hidden memory. No editor lock-in.

![w:620](../docs/demos/cold-start-agent-context-hero.svg)

Four roles inside one pack:

- **Content** — markdown map: human-readable overview, code map, invariants, operations.
- **Authority** — required evidence: `routes.json`, `completeness_contract.json` — what MUST be in a complete answer.
- **Navigation** — bounded search: `search_scope.json` — scoped directories and verification shortcuts.
- **Quality** — machine checks: `manifest.json`, acceptance tests, CI-friendly verifier helpers.

Read by `[Cursor]` `[Claude]` `[Codex]` `[Gemini]` `[OpenCode]` through the same artifact.

---

## Same navigation design, opposite agent loops

The pack is one thing. The reading patterns it triggers are two:

| **Trust-and-Follow** (Claude / Gemini) | **Search-and-Verify** (Cursor / Codex) |
|:---|:---|
| Reads completeness contracts. Stops when the contract says done. | Bounds its grep to scoped directories and cross-checks verification shortcuts. |
| Compressed search → fewer files opened. | Expanded proof burden → more verification, fewer dead ends. |
| **14 → 4 files opened** (claude bare → structured). | **3 → 12 files opened** (cursor — but each carries a verified-against-shortcut signal). |

Model-agnostic by construction. The routing block (`CLAUDE.md` / `AGENTS.md` / `.cursorrules`) points tools at `.agent-context/` before source exploration.

---

## The engineering pipeline (a repeatable loop)

Not a library trick. An automated, checkable pipeline.

1. **Initialize** — scaffold the pack.
2. **Fill** — agent enumerates subsystems, fills templates (driven by `SKILL.md`).
3. **Verify** — structural checks, schema validation, grep-backed acceptance tests.
4. **Freshness** — fail the run when relevant code changed but context did not.
5. **Measure** — compare bare vs `structured_fresh` runs on hard tasks.

```bash
agent-context init . && agent-context verify . && agent-context freshness .
```

That is the meetup takeaway: **a repeatable operating loop, not a magic prompt.**

---

## What a reviewer actually checks

The review target is the context **diff**, not the model's private memory.

- **File families:** does the pack name every file family that must change together?
- **Negative guidance:** does it say which plausible files are deprecated, generated, or near-misses?
- **Silent failures:** does it call out the thing that can break without a compile error?

![w:1000](../docs/demos/demo-agent-context.svg)

The pack has a `# DO NOT TOUCH` line for a reason. Pull-request-style review of the context diff is the durable quality gate.

---

## How to test whether it works

The methodology is deliberately boring:

| Protocol piece | Why it matters |
|---|---|
| `bare` clone vs `structured_fresh` clone | Same repo, same task, only context changes. |
| Hard multi-hop tasks | Lookup tasks prove little; synthesis exposes wrong turns. |
| Grep-backed ground truth | Every expected file family is mechanically checkable. |
| Independent judge + audit | Self-scores are evidence, not verdicts. |

> **Freshness is a hard experiment gate. If the pack is stale, the run fails before agents start.**

---

## Quantified evidence — Q2 2026 multi-agent rerun

**252 graded answers · 48 cells · 6 repos · 4 model variants · bare vs structured_fresh.**
Fresh-pack isolated protocol; LLM-provisional grading via independent Claude Code subagents (one per cell, fresh context).

| Agent / Model | Bare yes-rate | Structured yes-rate | Δ |
|---|---:|---:|---:|
| **Claude Opus 4.7** (trust-and-follow) | 80% (4.80/6) | **100% (6.00/6)** | +20pp |
| **Cursor `claude-opus-4-7-medium`** | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| **Cursor `composer-2-fast`** | 61% (3.67/6) | **81% (4.83/6)** | +20pp |
| **Codex CLI 0.130.0** | 72% (4.33/6) | **78% (4.67/6)** | +6pp |

- **Claude Opus + structured pack: 6/6 perfect across all 6 repos.**
- **Cursor `composer-2-fast` (the default): biggest absolute correctness lift — +20pp.**
- **Production-risk → 0** with structured for Codex (0.33 → 0.00) and Cursor Opus medium (0.50 → 0.00).
- **Cursor Opus medium duration −65%** under structured (median 219s → 78s).

---

## What each agent's strongest signal looks like

Different agents expose different telemetry. Each lane is reported on its strongest measured signal — no blended scoreboard.

| Agent | Strongest measured signal | Bare | Structured |
|---|---|---:|---:|
| **Claude** (trust-and-follow) | Files opened / task (3-repo historical) | 6.3 | 1.9 |
| **Claude** (trust-and-follow) | Tokens / task (3-repo historical) | 38.6K | 13.1K |
| **Cursor `composer-2-fast`** (search-and-verify) | Yes-rate (Q2 rerun, 6 repos) | 61% | **81%** |
| **Cursor `claude-opus-4-7-medium`** | Median duration / task (Q2 rerun) | 219s | **78s** |
| **Codex CLI** | Risk flags / 6-task cell (Q2 rerun) | 0.33 avg | **0.00** |

Full breakdown: [docs/evidence/results.md](../docs/evidence/results.md) · [methodology + anomalies disclosure](../docs/evidence/metrics.md#methodology-and-disclosure).

---

## Tradeoffs, not magic

| Tradeoff | What it means |
|---|---|
| **Maintenance cost** | The pack must change when relevant code changes. |
| **Overfitting risk** | Packs should route and bound search, not quote every answer. |
| **Repo-size fit** | Small repos may only need tier 1. Full packs scale to complex/monorepo. |
| **Telemetry gaps** | Cursor stores sessions in opaque SQLite; tokens/cost stay null without reverse-engineering. |
| **Human review remains** | Context improves first drafts; it does not replace code review. |

> **The bargain:** spend a little repo-maintenance effort to stop every agent from rediscovering the same map.

---

## Try this on one repo tomorrow

That is enough to decide whether the repo needs the full tier 3 pack.

1. **Pick one painful workflow** — impact analysis, auth, cache, release, migration, or docs corpus.
2. **Create tier 1** — start with code map + search scope.
3. **Add one invariant** — name the silent failure and near-miss files.
4. **Run bare vs context** — same task, same repo, two clones.
5. **Review the diff** — files opened, dead ends, missing surfaces, risk.

```bash
agent-context init . && agent-context verify . && agent-context freshness .
```

---

## Make repo knowledge explicit

Install the skill into your agent of choice (one-time):

```bash
# Install for Claude Code:
git clone https://github.com/cote-star/agent-context.git \
  && cp -r agent-context/skills/agent-context ~/.claude/skills/

# Cursor reads .cursorrules natively. Open repo, no install needed.
```

Then in any repo, ask your agent:

> **Set up agent context for this repo.**

Start small with **tier 1**. Promote to **tier 3** when the repo has cross-cutting invariants or production-risk workflows. Context is a checked-in interface between repos and agents.

---

<!-- _class: lead -->

# Make context part of the repo

Not a prompt trick. Not a vendor feature. A checked-in standard teams can review.

`init` · `verify` · `freshness` · `bare vs structured_fresh`

Today: **Navigation track.** Operating Loop and Engineering tracks are companion conversations.

[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

— *Amit Prusty*
