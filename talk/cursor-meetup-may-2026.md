---
marp: true
theme: default
paginate: true
size: 16:9
backgroundColor: '#0B1220'
color: '#E2E8F0'
style: |
  /* NotebookLM-pattern dark theme: deep navy background, orange primary
     accent (#F97316), green outcome accent (#10B981 / #34D399) for success
     metrics and outcome labels. Mirrors talk/Portable_Agent_Context.pdf. */
  section {
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0B1220 radial-gradient(ellipse at top, rgba(249,115,22,0.08), transparent 60%);
    color: #E2E8F0;
    padding: 50px 60px;
    font-size: 0.95em;
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
    margin-bottom: 0.5em;
    font-size: 1.55em;
  }
  h3 {
    color: #94A3B8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.92em;
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
    padding: 0.8em;
    font-size: 0.78em;
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
    padding: 0.5em 1em;
    color: #FED7AA;
    margin: 0.5em 0;
    font-style: normal;
    border-radius: 0 6px 6px 0;
    font-size: 0.95em;
  }
  ul li::marker { color: #F97316; }
  ol li::marker { color: #F97316; font-weight: 700; }
  table {
    border-collapse: collapse;
    width: 100%;
    background: rgba(15,23,42,0.6);
    border-radius: 8px;
    overflow: hidden;
    font-size: 0.85em;
  }
  th, td {
    padding: 0.4em 0.7em;
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
  td strong { color: #34D399; }
  img {
    display: block;
    margin: 0 auto;
    max-height: 65vh;
    border-radius: 8px;
  }
  section::after {
    color: #64748B;
    font-size: 0.65em;
  }
  small { color: #94A3B8; font-size: 0.8em; }
---

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

Structure: 21 slides per talk/notebooklm-update-brief-2026-05-10.md, with
the per-agent deep-dive series (slides 13–16) and methodology slide (17)
landing between the headline grid and the comparison-to-prior-art slide.
Audit log: talk/deck-audit-2026-05-10.md.
-->

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

| Track | Question | Concretely |
|---|---|---|
| **Navigation** *(control surface)* | What should load, what should not, when should it stop? | read order / risky paths |
| **Operating Loop** *(agent behavior)* | How does this agent consume repo context during real work? | trust route / verify route |
| **Engineering** *(systems layer)* | What makes prior work durable, inspectable, and reusable? | manifest / tests / CI |

> Outcomes when all three line up: **bounded loading · provenance · faster evidence.**

<small>*Explorable recall = an agent can re-discover the same map any time, on its own, from checked-in repo artifacts.*</small>

---

## Today's session: the Navigation track

**Navigation = the control surface.** What the agent loads, doesn't load, and when it stops.

- **What to load** — completeness contracts that name every file family that must change together.
- **What not to load** — search scopes that bound where the agent grep-walks.
- **When to stop** — stop rules and verification shortcuts that say "you have enough to answer."

<small>Operating Loop (how Claude vs Cursor vs Codex consume the same pack) and Engineering (manifest / tests / CI / freshness gates) are companion conversations — out of scope for this hour.</small>

---

## The artifact: `.agent-context/`

A committed folder next to the code. No hosted service. No hidden memory. No editor lock-in.

![w:520](../docs/demos/cold-start-agent-context-hero.svg)

Four roles inside one pack:

- **Content** — markdown map: overview, code map, invariants, operations.
- **Authority** — required evidence: `routes.json`, `completeness_contract.json`.
- **Navigation** — bounded search: `search_scope.json` + verification shortcuts.
- **Quality** — machine checks: manifest, acceptance tests, CI helpers.

<small>**Tier 1** = code map + search scope, 2 files. **Tier 3** = full pack with authority + completeness contracts, ~10 files. Start tier 1; promote when the repo has cross-cutting invariants or production-risk workflows.</small>

Read by `[Cursor]` `[Claude]` `[Codex]` `[Gemini]` `[OpenCode]` through the same artifact.

---

## Same navigation design, opposite agent loops

> **Trust-and-Follow:** reads the pack as authoritative.
> **Search-and-Verify:** uses the pack as a starting hint, then greps to confirm.

| **Trust-and-Follow** (Claude / Gemini) | **Search-and-Verify** (Cursor / Codex) |
|:---|:---|
| Reads completeness contracts. Stops when the contract says done. | Bounds its grep to scoped directories and cross-checks verification shortcuts. |
| Compressed search → fewer files opened. | Expanded proof burden → more verification, fewer dead ends. |
| **14 → 4 files opened** *(claude bare → structured)*. | **3 → 12 files opened** *(cursor — but each carries a verified-against-shortcut signal)*. |

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

- **File families** — does the pack name every file family that must change together?
- **Negative guidance** — does it say which plausible files are deprecated, generated, or near-misses?
- **Silent failures** — does it call out the thing that can break without a compile error?

![w:900](../docs/demos/demo-agent-context.svg)

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

| Agent / Model | Bare yes-rate | Structured yes-rate | Δ |
|---|---:|---:|---:|
| **Claude Opus 4.7** *(Trust-and-Follow)* | 80% (4.80/6) | **100% (6.00/6)** | +20pp |
| **Cursor `claude-opus-4-7-medium`** | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| **Cursor `composer-2-fast`** *(default)* | 61% (3.67/6) | **81% (4.83/6)** | +20pp |
| **Codex CLI 0.130.0** | 72% (4.33/6) | **78% (4.67/6)** | +6pp |

- **Claude Opus + structured pack: 6/6 perfect across all 6 repos.**
- **Cursor `composer-2-fast`: biggest absolute correctness lift — +20pp.**
- **Production-risk → 0** for Codex (0.33 → 0.00) and Cursor Opus medium (0.50 → 0.00).
- **Cursor Opus medium duration −65%** under structured (median 219s → 78s).

<small>*Risk-flag = the agent confidently cites the wrong file or misses an invariant; acting on the answer would break production.* · LLM-provisional grading — see methodology slide.</small>

---

## Per-agent: Claude Opus 4.7 *(Trust-and-Follow)*

> **Perfect 6/6 across all 6 repos under structured. The pack carries the answer; Claude trusts the contract.**

| Metric | Bare | Structured | Δ |
|---|---:|---:|---|
| Correctness yes-rate | 80% (4.80/6) | **100% (6.00/6)** | **+20pp** |
| Risk-flag rate / 6 tasks | 0.20 | 0.17 | small |
| Median duration / task | 65s | **56s** | −14% |
| Tool calls per correct | 14.2 | **8.8** | **−38%** |
| Files opened / task | 4.5 | **2.7** | **−40%** |
| Re-read rate *(same file twice = wasted attention)* | 0.015 | 0.004 | −73% |
| Citations / task | 8.9 | 9.3 | flat |
| Quality self-score | 8.8 | 9.0 | up |
| Dead ends / post-hit | 0 / 0 | 0 / 0 | already perfect |

<small>**Narrative:** Claude consumes the pack as authoritative — opens fewer files, top-level Grep tool not invoked. Tool-call efficiency gain (−38%) is the strongest of any lane. One residual risk-flag indicates contract refinement headroom. · 6 cells / 36 graded tasks · agent-chorus/bare ran on Haiku (5h-session fallback) — reported separately.</small>

---

## Per-agent: Cursor `claude-opus-4-7-medium` *(Search-and-Verify)*

> **219s → 78s under structured (−65%). Search-and-verify collapses when the pack guides navigation.**

| Metric | Bare | Structured | Δ |
|---|---:|---:|---|
| Correctness yes-rate | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| Risk-flag rate / 6 tasks | 0.50 | **0.00** | **eliminated** |
| Median duration / task | 219s | **78s** | **−65%** |
| Tool calls per correct | 8.3 | 7.9 | small |
| Files opened / task | 4.8 | 3.9 | −19% |
| Hops to first correct file *(verification depth)* | 0.83 | 1.42 | up — reads MORE files near the answer to verify pack vs source |
| Search-vs-read ratio | 0.89 | 0.57 | dropped |
| Verification-shortcut hit rate | n/a | 0.15 | new in structured |
| Dead ends / post-hit | 0.1 / 0 | **0 / 0** | eliminated |

<small>**Narrative:** Bare Opus medium is the slowest lane in the rerun — heavy `glob` + `grep` recon before reads. Structured cuts duration nearly two-thirds. Hop-count up = a feature: structured Opus reads MORE files near the answer to verify the pack's claim against source. · 6 cells / 36 graded tasks · daemon-reference/bare hallucinated writes on first attempt; recovered on retry, 6/6 final.</small>

---

## Per-agent: Cursor `composer-2-fast` *(default model)*

> **Biggest absolute correctness lift — 61% → 81% (+20pp). The pack rescues a weaker model.**

| Metric | Bare | Structured | Δ |
|---|---:|---:|---|
| Correctness yes-rate | 61% (3.67/6) | **81% (4.83/6)** | **+20pp** |
| Risk-flag rate / 6 tasks | 0.67 | 0.50 | down — still riskiest |
| Median duration / task | 111s | 112s | flat |
| Tool calls per correct | 5.6 | **4.6** | −18% |
| Files opened / task | 2.9 | 2.6 | small |
| Search-vs-read ratio | 0.52 | 0.44 | down |
| Verification-shortcut hit rate | n/a | 0.17 | new in structured |
| Citations / task | 5.3 | 5.6 | flat |
| Dead ends / post-hit | 0.2 / 0 | 0.1 / 0 | down |

<small>**Narrative:** composer-2-fast shows the smallest duration lift (none) but the largest correctness lift — the pack rescues a weaker model. Still the riskiest lane in both conditions; structured doesn't eliminate composer risk flags entirely (0.67 → 0.50). Lower citation count throughout — composer cites less by design. · 6 cells / 36 graded tasks · polyglot-monorepo/structured hit a transient provider error on first attempt; recovered on retry, 6/6 final.</small>

---

## Per-agent: Codex CLI 0.130.0 *(Search-and-Verify)*

> **Risk flags eliminated under structured (0.33 → 0.00). 97% of the pack's files actually read.**

| Metric | Bare | Structured | Δ |
|---|---:|---:|---|
| Correctness yes-rate | 72% (4.33/6) | 78% (4.67/6) | +6pp |
| Risk-flag rate / 6 tasks | 0.33 | **0.00** | **eliminated** |
| Median duration / task | 55s | 126s | **slower** *(trades wall-clock for correctness)* |
| Tool calls per correct | 11.4 | 9.2 | −19% |
| Files opened / task | 6.2 | 5.1 | −18% |
| Pack utilization rate *(fraction of pack files actually read)* | 0.14 | **0.97** | **+83pp · 97% read** |
| Verification-shortcut hit rate | n/a | **0.19** | highest in rerun |
| Hops to first correct file *(verification depth)* | 1.0 | 1.33 | up — verifies more deeply |
| Quality self-score | 8.9 | 9.3 | up |

<small>**Narrative:** Codex is *slower* under structured — trades wall-clock for correctness. Pack utilization 97% means codex reads almost every file in `.agent-context/current/` for structured tasks. No skimming. Search-shortcut hit rate is the highest of any agent (19%) — codex actively cross-checks `search_scope.json` shortcuts. · 6 cells / 36 graded tasks · all codex tokens are `cell_replicated` (per-cell session totals).</small>

---

## How we measured. What it covers. What it doesn't.

- **Scope.** 252 graded tasks · 48 cells · 6 repos × 4 model variants × 2 conditions × 6 tasks. Same general-purpose template across all repos.
- **Grading.** Each cell graded by an independent Claude Code subagent — fresh context, fixed judge prompt. **No human spot-audit.** Treat numbers as directional, not certified.
- **Protocol.** Fresh-pack isolated. Every `structured_fresh` clone passed `agent-context verify` + strict `check_freshness.sh` before the agent started. Pack content authored at v0.2.0; validated at v0.3.1.
- **Telemetry caveats.** Cursor sessions in opaque SQLite — tokens/cost null in this rerun. Codex tokens are `cell_replicated` (per-cell session totals, not per-task).

**Anomalies preserved (not masked):** composer/structured/polyglot transient retry · opus-medium/bare/daemon hallucination retry · claude/bare/agent-chorus ran on Haiku via 5h-session fallback · `org-second-brain` skipped (pack/EXPERIMENT setup needs review). **Working slate is 6 repos.**

<small>Public claims may only quote reviewer-confirmed rows. This rerun's grading is provisional; cell numbers may shift after spot-audit.</small>

---

## How this relates to what you already do

| You already have... | agent-context |
|---|---|
| **`.cursorrules` / `AGENTS.md` / `CLAUDE.md`** — single-file routing | Uses these as routing blocks pointing into the structured pack. Not a replacement. |
| **MCP servers** — runtime tool access (web, DB, internal APIs) | Different layer. agent-context is the *navigation map*; MCP is *access*. |
| **Vector RAG** — semantic recall over chunks | Pack is *structural recall*: deterministic file lists, contracts, verification shortcuts. **Pair them; don't pick.** |
| **Cursor project memory / "rules for AI"** | Pack supplements, doesn't replace. Pack lives in git; IDE memory may not. |

> **For Cursor users specifically:** `.cursorrules` already exists in your repo. agent-context adds the rest of the contract — completeness, search scope, verification shortcuts — and Cursor reads it natively.

---

## Tradeoffs, not magic

| Tradeoff | What it means |
|---|---|
| **Maintenance cost** | The pack must change when relevant code changes. |
| **Overfitting risk** | Packs should route and bound search, not quote every answer. |
| **Repo-size fit** | Small repos may only need tier 1. Full packs scale to complex/monorepos. |
| **Telemetry gaps** | Cursor stores sessions in opaque SQLite; tokens/cost stay null without reverse-engineering. |
| **Human review remains** | Context improves first drafts; it does not replace code review. |
| **Runtime cost** | Structured runs are similar or cheaper *per correct answer*. The cost is human-time to author the pack. |

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

<!-- _class: lead -->

# Make context part of the repo

Not a prompt trick. Not a vendor feature. A checked-in standard teams can review.

`init` · `verify` · `freshness` · `bare vs structured_fresh`

Today: **Navigation track.** Operating Loop and Engineering tracks are companion conversations.

> **Pick one repo. Run `agent-context init`. Open a PR for the diff.**

[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

— *Amit Prusty*
