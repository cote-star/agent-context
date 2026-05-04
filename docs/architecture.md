# Three-Layer Agent-Context Architecture

## Layer 1 — Content (Markdown)

5 files read by humans and all agents:

| File | Purpose |
|---|---|
| `00_START_HERE.md` | Entrypoint, fast facts, task routing, stop rules |
| `10_SYSTEM_OVERVIEW.md` | Architecture, runtime flow, silent failure modes |
| `20_CODE_MAP.md` | Navigation index (risk + authority columns), lookup shortcuts, tracing flows |
| `30_BEHAVIORAL_INVARIANTS.md` | Testable invariants, change checklists, file families, negative guidance |
| `40_OPERATIONS_AND_RELEASE.md` | Validation commands, CI checks, deploy, release |

## Layer 2 — Authority (JSON)

3 files for trust-and-follow agents (Claude, Gemini):

| File | Purpose |
|---|---|
| `routes.json` | Task-type → pack read order mapping with named patterns |
| `completeness_contract.json` | Required files per change pattern — "what MUST be in the answer" |
| `reporting_rules.json` | Grouped reporting, stop conditions, verify budgets |

Claude trusts these as authoritative. Result: answers from pure context, zero files opened.

> **v0.2.0 note.** The public `agent-context` repo now ships the authority layer as part of tier 3. Earlier public builds documented this layer but left it to `agent-chorus`; tier 3 now includes it directly so a repo can carry the full contract without depending on the chorus CLI.

## Layer 3 — Navigation (JSON)

1 file for search-and-verify agents (Codex, Cursor):

| File | Purpose |
|---|---|
| `search_scope.json` | `search_directories`, `exclude_from_search`, `verification_shortcuts` per task type |

Codex uses these to focus exploration. Does NOT stop Codex from reading — bounds WHERE it searches.

## Helper Tools

The repo ships two helper tools that should be copied into `.agent-context/tools/` when a pack is created:

| File | Purpose |
|---|---|
| `verify_agent_context.py` | Machine-checkable integrity validation for the pack |
| `check_freshness.sh` | Freshness check for "code changed but pack not updated" |

These scripts are the canonical implementation behind the reference CI and pre-push examples. Teams should adapt how they are invoked, not rewrite their logic from scratch. The Python CLI (`bin/agent-context`) wraps both for a friendlier surface: `bin/agent-context verify` and `bin/agent-context freshness`.

## Two Agent Architectures

### Trust-and-follow (Claude, likely Gemini)

1. Reads the index or instruction
2. Follows the prescribed read order
3. Trusts the completeness contract
4. Stops when the contract says sufficient
5. Opens repo files only to extract specific values

**What helps:** Authoritative completeness lists. Stop conditions. Grouped reporting rules. The more precise the contract, the fewer files Claude opens.

**What hurts:** Vague or incomplete contracts — Claude will trust a wrong contract and produce a wrong answer confidently. This is why tier 3 validates authority-layer paths and requires example entries to be removed before the pack passes.

### Search-and-verify (Codex, Cursor)

1. Reads the index as one signal among many
2. Greps the repo to build its own understanding
3. Cross-references structured artifacts against code
4. Continues reading until its internal confidence threshold is met
5. Overrides the contract when code suggests otherwise

**What helps:** Scoped search boundaries. Relevance filters that prevent enumeration of derived files. Completeness contracts that prevent dropping pass-through files.

**What hurts:** Stop rules (Codex doesn't stop). Read-order prescriptions (Codex reads in grep-result order). Verify budgets (Codex's budget is "until I'm satisfied").

**Freshness gate.** Any current claim about Codex or Cursor against this pattern requires a fresh-pack rerun under the protocol in [`docs/experiments/codex-cursor-fresh-pack-rerun.md`](experiments/codex-cursor-fresh-pack-rerun.md). Stale-pack runs (e.g., the May 2 2026 one-shot) are treated as maintenance failures, not product evidence — `agent-context verify` and `agent-context freshness` must pass on the structured condition before the agent starts.

## Agent Routing Blocks

Minimal blocks prepended to repo root files (~90 tokens each):

**CLAUDE.md** (trust-and-follow):
```
BEFORE starting any task, read these 3 files in order:
1. .agent-context/current/00_START_HERE.md
2. .agent-context/current/30_BEHAVIORAL_INVARIANTS.md
3. .agent-context/current/20_CODE_MAP.md
Do NOT open repo source files until steps 1-3 are complete.
Then open only files the pack identifies as relevant to your task.
```

**AGENTS.md** (search-and-verify):
```
1. Read .agent-context/current/search_scope.json → identify task type
2. Search ONLY within scoped directories defined in search_scope.json
3. Use verification_shortcuts to confirm specific facts quickly
4. Do not open repo source files outside the scoped directories
```

## Enforcement

The target enforcement model for `agent-context` CI verification combines integrity and freshness checking for PR gates:

- **Integrity**: all pack file references resolve, no template variables in JSON, glob patterns match real files
- **Freshness**: if context-relevant code changed, the pack was also updated
- **Exit code 1** if integrity fails or code changed without pack update

Teams should set up a verification check in their CI pipeline to run on PRs against main. At minimum, the check should run the machine-checkable structural and semantic validation by invoking the copied helper tools in `.agent-context/tools/`.

A reference CI job is provided in [`references/ci-example.yml`](references/ci-example.yml), repo adaptation guidance in [`ci-adaptation.md`](ci-adaptation.md), and an advisory pre-push hook in [`../tools/pre-push-hook.sh`](../tools/pre-push-hook.sh). Teams should adapt these to their existing CI pipeline. Manifest checksum sealing is a future enhancement — the current manifest is informational.

## Maintenance

| Trigger | What happens | Guard |
|---|---|---|
| Agent opens PR | Patch .agent-context (separate commit) | Human reviews in PR + CI verify |
| Human opens PR | No auto-update | Agent lacks context |
| "Update agent context" | Diff + propose patches | Human approves each section |
| CI check fails | Code changed but pack not updated | Must update pack before merge |
| Pre-push hook | Freshness warning | Advisory only, never blocks |
