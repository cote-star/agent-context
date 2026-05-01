# Agent-Context Roadmap

This roadmap is intentionally practical. The goal is not to make `agent-context` a runtime platform; it is to make checked-in repo context easier to create, trust, measure, and maintain.

## Product Direction

`agent-context` should remain:

- **Local-first**: no server, no API key, no hosted dependency.
- **Repo-native**: the pack lives beside the code it describes.
- **Agent-agnostic**: useful to Claude, Codex, Cursor, Gemini, and humans.
- **Evidence-backed**: claims should be tied to verifier output, experiment results, or before/after measurements.

## Near Term: v0.3

Focus: make first-pack creation less ambiguous.

- Improve `agent-context doctor` so it reports pack tier, missing files, routing block status, and likely next command.
- Add clearer verifier messages for common failures: leftover `REPLACE`, glob patterns that match nothing, stale verification shortcuts, and missing routing references.
- Add a small set of pack-quality examples: "good invariant", "bad invariant", "good search scope", "bad search scope".
- Tighten the examples so a new user can copy patterns without reading every design doc.

## Mid Term: v0.4

Focus: make freshness enforcement easier to adopt in real repos.

- Expand CI adaptation guidance for monorepos, generated files, vendored code, and multiple app roots.
- Add ready-to-copy GitHub Actions variants for common layouts.
- Improve `check_freshness.sh` diagnostics so teams can see exactly which changed paths triggered the warning.
- Document when freshness should be blocking versus advisory.

## Later: v0.5

Focus: measure whether a pack is actually helping.

- Add lightweight before/after evaluation scripts for file opens, token estimates, dead ends, and missed required files.
- Provide a repeatable task prompt format for teams to grade their own repos.
- Add more reference packs: backend service, React app, CLI, data pipeline, and monorepo.
- Publish a compact "pack review checklist" for maintainers reviewing agent-context changes in PRs.

## Non-Goals

- No chat-history memory system.
- No hosted control plane.
- No automatic codebase crawler that edits context without review.
- No replacement for tests, CI, or human ownership.

## Open Questions

- How much can verifier heuristics catch before they become noisy?
- Should tier 3 contracts support optional file families, or does that weaken their value?
- What is the smallest useful measurement harness that teams will actually run?
- Which routing conventions should differ between Claude/Gemini and Codex/Cursor as their behaviors change?
