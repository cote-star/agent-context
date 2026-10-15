# Agent-Context Roadmap

`agent-context` is a repo-owned navigation layer and operating contract for
software repositories. It helps agents spend less context on orientation and
dead ends, so more of the window is available for reasoning, integration
analysis, and safe change work.

It is intentionally not a runtime platform, memory system, vector retriever,
graph database, orchestration framework, or replacement for source inspection.
The pack gives agents just-in-time access to repo structure, invariants,
negative guidance, proof expectations, and blast radius so they can navigate
with fewer unnecessary file opens and fewer compactions.

## Product Shape

Use `agent-context` when repo work depends on conventions, invariants,
cross-cutting surfaces, generated files, or recurring navigation paths that
agents should not rediscover from raw files every session.

The intended flow:

1. A repo adopts `.agent-context/current/`.
2. The `agent-context` skill creates the first structured context pack.
3. Agent entry files stay tiny. `AGENTS.md` carries the shared navigation
   contract, `CLAUDE.md` imports it literally, and optional adapters such as
   `GEMINI.md` and `.cursorrules` point at it. None of them carry the full
   context.
4. Agents read the shared entry contract, then progressively disclose the
   route-required pack files for the task.
5. The pack is merged and maintained like code.
6. Freshness policy and hooks flag context-relevant changes after merges.
7. Agents update only the relevant context sections when files, schemas,
   features, invariants, or public workflow rules change.
8. Agents do not edit application source merely to refresh context unless the
   user explicitly asks for source changes.

Human input is required when the repo gains outside knowledge that is not
encoded in code, tests, docs, or prior context: new principles, new ways of
working, unresolved product decisions, or behavior invariants that only a
maintainer can supply. Once that knowledge is captured, future agents can
maintain it through the normal context update path.

## Tenets

- **Navigation first:** most value comes from helping agents find the right
  authority, invariant, and blast-radius surfaces quickly.
- **Authority before exploration:** the pack names authority, contracts,
  invariants, risks, generated boundaries, and required proof before agents
  fall back to raw search.
- **Just-in-time context:** agents should not eagerly read the whole pack. They
  should start from the same entry contract and load follow-on files only as
  the task route requires.
- **Repo-owned and reviewable:** context lives beside the code and changes
  through normal review.
- **Navigation-cost bias:** optimize for repos where raw scanning creates dead
  ends, compactions, repeated orientation work, or missed integration
  surfaces.
- **Agent-agnostic:** Claude, Codex, Cursor, Gemini, OpenCode, and future
  agents should share the same navigation contract.
- **Invariants matter:** negative guidance, generated-file boundaries,
  required sibling surfaces, and silent-failure risks are first-class context.
- **Fresh but scoped:** context updates should target the changed area; do not
  rewrite the whole pack when a small section is stale.
- **Local-first:** no hosted control plane, no API key, no mandatory external
  index.
- **Evidence-backed:** claims should tie to verifier output, tests, reviewed
  evidence, or scrubbed experiment results.
- **Verification over vibes:** context quality should be mechanically checked
  through verifier rules, freshness checks, contracts, and tests wherever
  possible.
- **Honest incompleteness:** the pack should declare what it covers, what it
  does not cover, and when human help is needed.

## Current State

`agent-context` is public and installable as `agent-context-cli`.
The current release is v0.5.1:

- `uv tool install agent-context-cli` installs the CLI.
- `agent-context install-skill --agent claude` installs the bundled skill.
- The CLI remains Python stdlib-only with no runtime dependencies.
- New setups write one canonical `AGENTS.md` route and a literal `@AGENTS.md`
  import in `CLAUDE.md`; `agent-context routing` migrates an existing filled
  pack by rewriting only managed blocks, after fail-closed preflight checks.
- The full pack (tier 3) is the only generation target. `init --tier 1|2` is
  deprecated and warns; existing smaller packs keep working with `routing` and
  `verify`.
- Releases are gated on a Python 3.8/3.10/3.12 test matrix and an
  installed-wheel smoke test that covers a legacy filled pack.
- The public story is skill-first: the skill authors the pack, the CLI
  scaffolds, verifies, checks freshness, and installs hooks.
- `doctor` reports package-data health, verifier status, freshness summary,
  routing blocks, and hook status.
- Freshness diagnostics list the changed context-relevant paths and changed
  pack files that drove the result.
- CI adaptation guidance covers single apps, monorepos, generated/vendored
  paths, multiple roots, and hard-gate versus advisory freshness modes.
- The Cursor Meetup and Claude Community Meetup talks are complete. The live
  public talk surface is the tracked HTML pages under `talk/`; PDFs, speaker
  guides, demo orchestration, recordings, and audio work stay local.

## What We Optimize

Primary outcomes:

- fewer dead-end file opens
- fewer unnecessary raw source reads
- better required-file recall and precision
- better generated-file restraint
- better negative-guidance and invariant recall
- better full blast-radius analysis
- better stale-context detection
- better cross-agent consistency
- less confident partial work

Secondary outcomes:

- fewer tool calls
- faster first correct evidence
- lower token use
- fewer compactions

Efficiency only matters when quality and risk do not regress. A faster
incomplete answer is a failure.

## Now: Unified Progressive-Disclosure Entry Surface

Focus: make every supported agent enter through the same tiny navigation
contract while preserving just-in-time context.

Shipped in v0.5: one canonical `AGENTS.md` route, a literal `CLAUDE.md`
import, adapters that point rather than copy, a `routing` command that
migrates filled packs safely, and a verifier that resolves the import without
mistaking examples or prose for it. `00_START_HERE.md` is the mandatory first
read for every full pack.

Remaining:

- Keep `routes.json`, `completeness_contract.json`, `search_scope.json`, and
  `reporting_rules.json` as deterministic follow-on surfaces rather than
  replacement entry points.
- Verify that the generated route and the pack's own read order agree, and
  that every file a route names exists (today the verifier checks references,
  not ordering).
- Remove `--tier 1|2` generation in v0.6.0 and collapse the tier branches in
  routing, verify, and docs to one pack shape plus a compatibility path for
  existing packs.
- Prove real host loading, not just structure: a small per-host check that
  the imported contract is what the agent actually sees.
- Treat route divergence as an evaluation-validity risk. Do not compare agent
  performance until Claude and Codex share the same baseline context contract.

## Now: Maintenance Correctness

Focus: keep the public package, bundled skill, examples, and this repo's own
context pack coherent.

- Keep the self-pack current with the v0.5.x package layout
  (`agent_context/cli.py`, `pyproject.toml`, bundled package data, and
  local-only talk archives).
- Keep canonical templates, tools, and installable skill mirrors in sync.
- Continue improving verifier and doctor messages for common operator
  mistakes: leftover placeholders, empty globs, stale verification shortcuts,
  missing routing references, and package/version drift.
- Keep examples copyable without requiring readers to reconstruct context from
  design docs.

## Next: First-Setup Quality

Focus: make the initial skill-created pack strong enough that future updates
are mostly incremental.

- Improve the first-run skill flow: map major subsystems,
  authority files, generated outputs, silent-failure paths, required sibling
  surfaces, and existing ways of working.
- Create first-run acceptance checks and small ground-truth tasks that prove
  the pack helps agents navigate the repo.
- Use subagents or parallel passes during first setup when useful, but keep
  the resulting artifacts reviewable and checked in.
- Make human handoff explicit for knowledge the repo does not contain:
  principles, unresolved product decisions, external operating rules, and
  behavior invariants.

## Next: Scoped Freshness And Context Updates

Focus: keep context current without rewriting it wholesale.

- Detect changed context-relevant areas after merges to main.
- Guide agents to update only the relevant pack sections.
- Delete stale context when source reality changes.
- Keep branch-level sync possible, while treating main as the preferred
  freshness reference.
- Preserve the rule that context-refresh work touches context files unless the
  user explicitly asks for application source changes.

## Next: Identity, Status, And Coverage Contracts

Focus: make pack entries addressable and honest at the entry level, so routes
can point at the right thing after renames, skip what is historical, and say
what an answer did not cover. These items come from an unrelated design
exercise for an organisation-level knowledge layer whose failure modes are the
repo pack's failure modes at larger scale; the detailed notes and the ideas
deliberately left out are in `docs/future-directions.md`.

- **Stable IDs with aliases and supersession.** Give pack entries (code-map
  rows, invariants, contracts, routes) a stable ID, optional aliases, and an
  explicit `supersedes` link in `manifest.json`, so identity survives renames
  and a route can point at the superseding entry instead of a stale path.
- **Status vocabulary.** `accepted / proposed / historical` per file or
  section, with one code-defined meaning each. Default routes exclude
  `historical`; diagnosis routes can opt in.
- **Anchor-addressable routes.** Let `read_order` name a heading or entry ID
  (`file#heading`), so a route loads the paragraph it needs rather than the
  whole file.
- **Per-file verified-at revision.** Record the git revision each pack file
  was last verified against so `freshness` and `verify` can flag drift per
  file instead of per pack.
- **Result-coverage contract.** Extend `reporting_rules.json` so an answer
  must declare `complete`, `more available`, `stale source`, `source failed`
  or `no match`; "no match" is never evidence of absence, and a check that
  could not run reports `skipped`, which is not clean.
- **Per-route budget.** A route may declare a read budget; `verify` measures
  the `read_order` size against it. Budget is judged per successful task: a
  smaller read that loses evidence is a failure, not a win.
- **Deterministic, explainable routing.** An `agent-context route <task>`
  command that prints which files were chosen and why, from rules only. If a
  model ever classifies ambiguous intent, measure it against the rules
  baseline rather than replacing the rules.
- **Wider acceptance set.** Beyond lookup, impact, cross-cutting and
  diagnosis, add cases for alias hits, buried evidence, superseded content,
  retained exceptions, duplicate local IDs, and partial-result disclosure.
- **Contradiction and dangling-reference lint.** Verifier rules for pack
  statements that contradict each other, references to files or headings that
  no longer exist, and status words used with more than one meaning.
- **Deterministic material-change classification.** Decide that a diff needs
  a pack update from which paths and fields changed, owner-defined in
  `CONTEXT_RELEVANT_PATHS`, rather than asking a model whether it was minor.
- **Red/green review format.** A review template where each finding carries
  an evidence pointer, who found it, and a confidence label (`verified in
  source / reproduced in fixture / inferred`), plus a table of how each fix
  could fail and what makes it green.

## Next: Evidence Confidence

Focus: keep public claims honest.

- Run reviewer spot-audit on the LLM-provisional Q2 grades before
  strengthening claims.
- Preserve anomalies in the public methodology instead of normalizing them
  away.
- Fix or rerun the skipped `org-second-brain` setup before making claims
  about non-code corpora.
- Keep README, evidence docs, and talk pages aligned on what is measured:
  code repositories are validated; non-code corpora are not yet validated.

## Later: Measurement Evidence

Focus: help teams evaluate whether `agent-context` improves their own repo
without over-claiming from unreviewed local runs.

- Keep private working harnesses and raw run artifacts local until results are
  scrubbed, reviewed, and worth publishing.
- Measure navigation quality before feature cleverness: dead ends, required
  surfaces, negative guidance, blast-radius completeness, generated-file
  restraint, stale-context handling, and cross-agent consistency.
- Publish compact maintainer review guidance for `.agent-context/` changes
  only after the local methodology is proven.
- Add reference artifact sets only when they are maintained and verifiable,
  not as static showcase snapshots.

## Later: Many Repos

Recorded as an option, not a direction. Everything stays local-first; any
index is derived and never the source of truth.

- Namespaced IDs: any ID that leaves its repo carries the repo as a namespace.
- A rebuildable, derived index over many packs (ID, type, title, aliases,
  owner role, status, source revision) that answers "which repo owns X"
  without loading any pack. It is a query result, not a file anyone edits.
- One declared writable authority per object; external systems of record are
  referenced by identity, not copied into packs.
- A pinned contract version per repo, so a change to shared route rules is an
  explicit migration rather than a silent change to in-flight work.

## Non-Goals

- No chat-history memory system.
- No hosted control plane, no service exposed over MCP or HTTP, no per-user
  permission-filtered index, no delegated writes, no operation receipts.
- No vector search, no model that picks references, no graph database, no
  multi-agent fleet, no custom UI. Each is deferred until a measured miss
  justifies it, and even then it belongs in a separate tool that reads packs.
- No automatic codebase crawler that edits context without review.
- No replacement for tests, CI, or human ownership.
- No eager "read the whole repo" or "read the whole pack" workflow.
- No benchmark machinery as product surface; measurement exists to improve the
  navigation contract, not to become the user workflow.
- No claim that non-code corpora are validated until the skipped
  knowledge-base setup is fixed and rerun.

## Open Questions

- What repo signals show that a pack is worth maintaining?
- What is the smallest shared entry contract that works across Claude, Codex,
  Cursor, Gemini, and OpenCode?
- How should the skill decide which pack sections to update after a merge?
- Which verifier checks catch stale or contradictory navigation without
  becoming noisy?
- Which first-run acceptance tasks best prove the pack prevents dead ends and
  missed blast-radius surfaces?
- Who decides relevance: rules only, or rules with a measured model fallback?
- What is a material change, defined by diff fields rather than judgement?
- How should a pack mark a section as historical so default routes skip it
  while diagnosis tasks can still reach it?
