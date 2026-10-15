# Future directions: lessons from an org-level knowledge-layer pilot

Status: notes for future direction, not commitments. Nothing here is scheduled,
and none of it changes the current pack format or CLI. Recorded October 2026.

These notes distil an unrelated, proposal-stage design exercise for an
organisation-level product knowledge layer (decisions, questions, evidence and
specs across many initiatives, served to agents and people). The problems it hit
are the same problems a repo pack hits at larger scale, so the transferable ideas
are worth keeping next to the roadmap. Where that design needs a hosted service,
it is listed as a non-goal, not a plan.

## What transfers, mapped to the pack

| Idea | Where it would land | Why it fits the tenets |
|---|---|---|
| **Stable identity plus aliases.** Identity lives in a stable ID with aliases and an explicit `supersedes` link, never in a title or filename. Renames keep identity; superseded content stays reachable but is not current. | `manifest.json` (per-file `id`, `aliases`, `supersedes`), `reporting_rules.json` | Authority before exploration: routes can point at the superseding entry instead of a stale path. |
| **Titles aid discovery, metadata carries state.** A structured title (`<scope> — <artifact type> — <subject>`) is a cheap discovery signal, generated from metadata rather than typed by hand. Mutable fields (status, owner, version) never go in the title. | Section headings in pack files; `20_CODE_MAP.md` rows; a future `agent-context` lint | Verification over vibes: a convention held by construction, not discipline. |
| **Anchor-addressable sections.** Routes can name a heading or entry ID, not just a file, so a bounded read is possible without semantic chunking. | `routes.json` `read_order` entries of the form `file#heading` | Just-in-time context: load the paragraph the route needs, not the file. |
| **Status vocabulary per file or section:** `accepted / proposed / historical`. Default routes exclude `historical` unless the task asks for it. One code-defined meaning of each status word. | `manifest.json`, `routes.json` filters, verifier rule | Honest incompleteness: the pack says what is current and what is kept for the record. |
| **Verified-at source revision per file.** Each pack file records the git revision it was last verified against, not only the pack-level `git_revision`. `verify` and `freshness` can then flag per-file drift. | `manifest.json`, `tools/check_freshness.sh` | Fresh but scoped: refresh only the stale section. |
| **Result-coverage contract.** An answer must declare `complete`, `more available`, `stale source`, `source failed` or `no match`, and "no match" is never evidence of absence. Checks that could not run report `skipped`, and skipped is not clean. | `reporting_rules.json` global rules; `completeness_contract.json` | Verification over vibes; honest incompleteness. |
| **Per-route context budget.** A route declares a token or byte budget; `verify` measures the `read_order` size against it. Budget is an acceptance criterion measured per *successful* task: a smaller read that loses evidence is a failure, not a win. | `routes.json` (`budget`), verifier | Navigation-cost bias. |
| **Deterministic, logged route selection.** A `route <task-type>` command prints which files were chosen and why, from rules, with no model in the loop. A model classifies only ambiguous intent, and its choice is measured against the rules baseline. | New CLI subcommand | Repo-owned and reviewable: relevance decisions are inspectable. |
| **Frozen question set as the acceptance test.** Beyond lookup, impact, cross-cutting and diagnosis, cover: exact-ID hit, alias hit, buried evidence, superseded content, retained exception, duplicate local ID, inaccessible content, partial-result disclosure. | `templates/acceptance_tests.md` | Evidence-backed. |
| **Contradiction and dangling-reference lint.** The pilot found rules that contradicted each other, dozens of dangling references, and four definitions of one status word. A grep-level linter with exit codes, run in CI, caught these; convert mechanical prose rules into validators before retiring the prose. | `tools/verify_agent_context.py` | Verification over vibes. |
| **Deterministic material-change classification.** Decide "this change needs a pack update" from which fields or paths changed, owner-defined, rather than asking a model whether a diff is minor. | `tools/check_freshness.sh`, `CONTEXT_RELEVANT_PATHS` | Fresh but scoped. |
| **Red/green audit format for pack reviews.** Each red finding carries an evidence pointer, who found it, and confidence (`verified in source / reproduced in fixture / inferred`); each green asset names its target home; a "red-team the replacement" table lists how each fix could fail and its condition for green. | `docs/` review template; skill update flow | Evidence-backed. |
| **One fact, one home.** Three copies of a process definition drifted. Either generate copies from one source or retire them. This repo already enforces that for the bundled skill mirror. | `30_BEHAVIORAL_INVARIANTS.md` (invariant 1) | Repo-owned and reviewable. |

## Scaling from one repo to many

Recorded as an option, not a direction. Everything stays local-first and the
index stays derived and non-authoritative.

- **Namespaced IDs.** Any ID that leaves its repo carries the repo as a
  namespace. The pilot saw one bare local ID mean three things in three scopes.
- **Derived portfolio index.** A rebuildable index over many packs (ID, type,
  title, aliases, owner role, status, source revision) that answers "which repo
  owns X" without loading any pack. It is a query result, not a file anyone
  edits, and it is never the source of truth.
- **One declared writable authority per object.** External systems of record
  are referenced by identity, not copied into the pack.
- **Per-machine copies drift.** The pilot accumulated well over a hundred
  unreviewed rule files on individual machines. Thin clients generated from one
  reviewed, versioned source beat local corpora; record which version each
  consumer actually runs and test rollback. For this project that is the case
  for keeping entry files tiny and the bundled skill a byte-identical mirror.
- **Pinned process version per work item.** Changing a gate on in-flight work
  needs an explicit migration decision; it must not change silently.

## Lessons the pilot paid for

- Markdown used as a database fails; prose used as enforcement fails.
- Compulsory startup loads scale with the knowledge base, not the task.
  Splitting files changes nothing if the instruction still says "load every
  file". This is why the canonical route loads start-here and invariants,
  then only the selected route.
- A derived "pending" view treated as a source rotted: a large share of it was
  its own regeneration log. Derived views are queries, not files.
- A summary is not recovery state. A continuation record (task, source
  versions, pending operations) is.
- Retrieved instructions are content, not policy. A flag that says "approved"
  inside retrieved text is not authorisation. The canonical `AGENTS.md`
  block already states this for pack consumers.
- Storage format and retrieval behaviour are separate choices. "The model can
  read the whole store" is the forced-context pattern in a new container.

## Non-goals confirmed by the comparison

The organisation-level design needs things a repo pack should not grow:

- a hosted service exposed over MCP or HTTP, with per-user permissions,
  delegated writes and permission-filtered results;
- durable operation records and reconciliation for uncertain external writes;
- sandboxed execution over retrieval handles with server-enforced limits;
- wiki and ticket systems as sources of record;
- vector search, an LLM router that picks references, a graph database, a
  multi-agent fleet or a custom UI, each deferred there too until a measured
  miss justifies it.

agent-context stays a checked-in, repo-owned, stdlib-only pack. If any of the
above is ever needed, it belongs in a separate tool that reads packs, not in
the pack format.

## Open questions carried over

- Who decides relevance: rules only, or rules with a measured model fallback?
- What is a material change, defined by diff fields rather than judgement?
- How should a pack express "this section is historical" so that routes skip
  it by default but diagnosis tasks can still reach it?
