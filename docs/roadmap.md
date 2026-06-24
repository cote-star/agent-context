# Agent-Context Roadmap

This roadmap is intentionally practical. The goal is not to make
`agent-context` a runtime platform; it is to make checked-in system
evidence easier to create, trust, measure, and maintain.

## Current State

`agent-context` is public and installable as `agent-context-cli`.
The current release is v0.4.2:

- `uv tool install agent-context-cli` installs the CLI.
- `agent-context install-skill --agent claude` installs the bundled skill.
- The CLI remains Python stdlib-only with no runtime dependencies.
- The public story is skill-first: the skill authors the pack, the CLI
  scaffolds, verifies, checks freshness, and installs hooks.
- `doctor` reports package-data health, verifier status, freshness summary,
  routing blocks, and hook status.
- Freshness diagnostics list the changed context-relevant paths and changed
  pack files that drove the result.
- CI adaptation guidance covers single apps, monorepos, generated/vendored
  paths, multiple roots, and hard-gate versus advisory freshness modes.
- The Cursor Meetup and Claude Community Meetup talks are complete. The
  live public talk surface is the tracked HTML pages under `talk/`; PDFs,
  speaker guides, demo orchestration, recordings, and audio work stay local.

## Product Direction

`agent-context` should remain:

- **Local-first**: no server, no API key, no hosted dependency.
- **Repo-native**: artifacts live beside the code they describe.
- **Agent-agnostic**: useful to Claude, Codex, Cursor, Gemini, OpenCode,
  and humans.
- **Evidence-backed**: claims should be tied to verifier output,
  experiment results, reviewer audit, or before/after measurements.
- **Reviewable**: agents can draft packs, but humans merge the artifact
  through the same path as code.

## Now: Maintenance Correctness

Focus: keep the public package, bundled skill, examples, and this repo's
own context pack coherent.

- Keep the self-pack current with the v0.4.x package layout
  (`agent_context/cli.py`, `pyproject.toml`, bundled package data, and
  local-only talk archives).
- Keep canonical templates, tools, and installable skill mirrors in sync.
- Continue improving verifier and doctor messages for common operator
  mistakes: leftover placeholders, empty globs, stale verification shortcuts,
  missing routing references, and package/version drift.
- Keep examples copyable without requiring readers to reconstruct context
  from the design docs.

## Next: Evidence Confidence

Focus: turn the Q2 2026 rerun from useful directional evidence into a
cleaner public proof set.

- Run reviewer spot-audit on the LLM-provisional Q2 grades before
  strengthening claims.
- Preserve anomalies in the public methodology instead of normalizing them
  away.
- Fix or rerun the skipped `org-second-brain` setup before making claims
  about non-code corpora.
- Keep README, evidence docs, and talk pages aligned on what is measured:
  code repositories are validated; non-code corpora are not yet validated.

## Next: Adoption Ergonomics

Focus: make it easier for real repos to adopt freshness and CI without
copying this repo's exact layout.

- Validate the expanded CI guidance against more real repo layouts.
- Add more ready-to-copy workflow snippets only when a layout pattern is
  proven useful enough to maintain.
- Keep freshness diagnostics actionable as teams report noisy path sets.
- Collect examples of when teams choose blocking versus advisory freshness.

## Later: Measurement Evidence

Focus: help teams evaluate whether `agent-context` improves their own repo
without over-claiming from unreviewed local runs.

- Keep private working harnesses and raw run artifacts local until results are
  scrubbed, reviewed, and worth publishing.
- Exercise repeatable task-prompt formats against more repos and refine the
  reviewer checklist from observed misses.
- Publish a compact review checklist for maintainers reviewing
  `.agent-context/` changes in PRs, separate from experiment grading.
- Add more reference artifact sets only when they are maintained and
  verifiable, not as static showcase snapshots.

## Non-Goals

- No chat-history memory system.
- No hosted control plane.
- No automatic codebase crawler that edits context without review.
- No replacement for tests, CI, or human ownership.
- No claim that non-code corpora are validated until the skipped
  knowledge-base setup is fixed and rerun.

## Open Questions

- How much can verifier heuristics catch before they become noisy?
- Should tier-3 contracts support optional file families, or does that
  weaken their value?
- What is the smallest useful measurement harness that teams will actually
  run?
- Which routing conventions should differ between trust-and-follow agents
  and search-and-verify agents as their behaviors change?
