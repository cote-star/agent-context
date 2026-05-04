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
  a { color: #F37021; text-decoration: none; overflow-wrap: anywhere; }
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

### A repo evidence standard for coding agents

Make context portable, reviewable, fresh, and testable before the agent edits.

A concrete workflow for Cursor, Claude, Codex, Gemini, and OpenCode.

Cursor Meetup · May 2026
[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

---

## The agent is new here every time

Most coding agents enter a repo as a bright visitor with no durable map.

- They rediscover the tree.
- They infer ownership from whatever file they open first.
- They miss the invariant that decides whether an answer is safe.
- They repeat the same exploration in the next session, editor, or model.

**The failure is often not intelligence. It is missing repo evidence.**

![w:900](../docs/visuals/agent-context-loop.svg)

---

## Thesis: every serious repo needs a navigation layer

We already check in tests, docs, schemas, CI, runbooks, and migration history.

**Agent context should be another checked-in repo artifact:** the map of what is true, risky, connected, and out-of-bounds.

- **Portable:** markdown and JSON, not vendor memory.
- **Reviewable:** context changes can be reviewed like code changes.
- **Fresh:** drift is a failing preflight, not a quiet footnote.

**The standard is simple: read the repo map before editing the repo.**

---

## Explorable recall has three tracks

The idea is bigger than a docs folder. A useful context layer has to coordinate **navigation**, **operating loop**, and **engineering**.

![w:1050](../docs/evidence/figures/three-tracks-importance-minimal.svg)

---

## The artifact: `.agent-context/`

A committed folder next to the code. No hosted service. No hidden memory. No editor lock-in.

![w:620](../docs/demos/cold-start-agent-context-hero.svg)

Three pack layers:

- **Content:** overview, code map, invariants, operations.
- **Authority:** routes, completeness contracts, reporting rules.
- **Navigation:** search scope, exclusions, verification shortcuts.

The idea is not “more docs.” It is **docs with contracts, scopes, and checks.**

---

## The workflow teams can copy

1. **Initialize** — create a tier 1 or tier 3 pack.
2. **Fill** — have an agent enumerate subsystems before writing.
3. **Verify** — run structural checks and grep-backed acceptance tests.
4. **Freshness** — fail the run when relevant code changed but context did not.
5. **Measure** — compare bare vs structured runs on hard tasks.

```bash
agent-context init --tier 1 .
agent-context verify .
agent-context freshness . --base-ref origin/main
```

That is the meetup takeaway: not a library trick, a repeatable operating loop.

---

## Demo: from empty repo to first-read contract

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

Then ask the agent:

> **Set up agent context for this repo.**

The agent fills the templates, writes acceptance tests, runs verify, and leaves a diff the team can review.

---

## What a reviewer actually checks

- **File families:** does the pack name every file family that must change together?
- **Negative guidance:** does it say which plausible files are deprecated, generated, or near-misses?
- **Silent failures:** does it call out the thing that can break without a compile error?

![w:1000](../docs/demos/demo-agent-context.svg)

The review target is the context diff, not the model's private memory.

---

## How to test whether it works

The methodology is deliberately boring:

| Protocol piece | Why it matters |
|---|---|
| Bare clone vs `structured_fresh` clone | Same repo, same task, only the context layer changes. |
| Hard multi-hop tasks | Lookup tasks prove little; synthesis tasks expose wrong turns. |
| Grep-backed ground truth | Every expected file family is mechanically checkable. |
| Independent judge + human audit | Self-scores are evidence, not verdicts. |

**If the pack is stale, the run fails before agents start.**

---

## Evidence dashboard

Different agents expose different telemetry. The clean read is agent-by-agent, not one blended scoreboard.

| Agent | Strongest available metric | Bare | With context |
|---|---|---:|---:|
| **Claude** | files opened / task | 6.3 | 1.9 |
| **Codex** | tokens / 6-task cell | 163K | 130K |
| **Cursor** | dead ends / task | 0.24 | 0.07 |

Each agent slide uses only the telemetry available for that agent. No unfinished lanes are included.

---

## Claude evidence

Claude showed the strongest navigation compression: it followed the context contract and opened far fewer files.

| Metric | Bare | With context | What changed |
|---|---:|---:|---:|
| Files opened / task | 6.3 | 1.9 | **~70% fewer files** |
| Tokens / task | 38.6K | 13.1K | **~65-70% fewer tokens** |

Best use case: impact analysis where the completeness contract names every file family and silent failure mode.

<small>Metric source: reviewer-graded Claude run set.</small>

---

## Codex evidence

Codex still verifies aggressively, but context reduced token load and cut self-reported risk flags.

| Metric | Bare | With context | What changed |
|---|---:|---:|---:|
| Tokens / 6-task cell | 163K | 130K | **20% fewer tokens** |
| Risk flags | 12 | 6 | **50% reduction** |
| Files opened / task | 7.7 | 7.1 | **7% fewer files** |

Codex is a search-and-verify agent: the pack mostly reduces search breadth and risk, not verification behavior.

---

## Cursor evidence

Cursor's strongest signal was operational: fewer dead ends and fewer files opened with the same task set.

| Metric | Bare | With context | What changed |
|---|---:|---:|---:|
| Dead ends / task | 0.24 | 0.07 | **71% fewer dead ends** |
| Files opened / task | 3.6 | 2.7 | **25% fewer files** |
| Risk flags | 14 | 10 | **29% reduction** |

Token telemetry is not available for Cursor in this harness, so the Cursor slide does not claim token savings.

---

## Lessons learned the hard way

| Lesson | Operational rule |
|---|---|
| Stale context can make a good agent worse. | Freshness is a hard experiment gate. |
| Easy tasks create fake confidence. | Use multi-hop tasks with near-misses and “do not touch” clauses. |
| Self-scores are unreliable. | Judge independently; audit before public claims. |
| Different agents read differently. | Design for trust-and-follow and search-and-verify paths. |

This is why the methodology matters as much as the folder.

---

## Tradeoffs, not magic

- **Maintenance cost:** the pack must change when relevant code changes.
- **Overfitting risk:** packs should route and bound search, not quote every answer.
- **Repo-size fit:** small repos may only need tier 1.
- **Telemetry gaps:** Cursor and local models expose different metrics than CLI agents.
- **Human review remains:** context improves first drafts; it does not replace code review.

**The bargain:** spend a little repo-maintenance effort to stop every agent from rediscovering the same map.

---

## Try this on one repo tomorrow

1. Pick one painful workflow: impact analysis, auth, cache, release, migration, or docs corpus.
2. Create tier 1: code map + search scope.
3. Add one invariant: the silent failure and near-miss files.
4. Run bare vs context: same task, same repo, two clones.
5. Review the diff: files opened, dead ends, missing surfaces, risk.

That is enough to decide whether the repo needs the full tier 3 pack.

---

## The first command

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 1 .
```

Or open the repo in your agent of choice and ask:

> **Set up agent context for this repo.**

Start small. Promote to tier 3 when the repo has cross-cutting invariants, duplicated architecture, or production-risk workflows.

**Make repo knowledge explicit before asking agents to change it.**

[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)

---

<!-- _class: lead -->

# Make context part of the repo

Not a prompt trick. Not a vendor feature. A checked-in standard teams can review.

`init` · `verify` · `freshness` · `bare vs structured_fresh`

[github.com/cote-star/agent-context](https://github.com/cote-star/agent-context)
