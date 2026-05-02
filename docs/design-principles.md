# Agent-Context Design Principles

16 principles derived from 6 experiment runs across 3 repo types (ML pipeline, CLI library, React frontend).

**Scope legend:**
- `[all repos]` — apply regardless of repo type, size, or stack
- `[pipeline/service]` — apply when there is runtime state, async execution, or shared infrastructure
- `[coexisting architectures]` — apply when a repo has multiple active patterns or is mid-migration
- `[complex repos]` — apply when the repo has >100 files or multiple distinct subsystems

## Universal (all repos)

| # | Scope | Principle |
|---|---|---|
| P1 | `[all repos]` | Index must declare its own incompleteness — CODE_MAP is navigation, not exhaustive impact list. For impact analysis, agents must cross-reference BEHAVIORAL_INVARIANTS and verify with grep. |
| P2 | `[all repos]` | Risk callouts belong inline in CODE_MAP, not only in a separate file. Highest-risk paths need a "Silent failure if missed" warning at the point of navigation. |
| P5 | `[all repos]` | Claude and Codex navigate differently — one format cannot optimize both. Claude follows structured prose; Codex does grep-first exploration. |
| P7 | `[all repos]` | Checklist rows in INVARIANTS prevent specific exclusion errors — name files explicitly by path, not by description. "All client files" is not enough — list them. |
| P8 | `[all repos]` | Zero dead ends is the strongest efficiency signal. Track files opened that turned out irrelevant as the primary metric, not just file count. |
| P9 | `[all repos]` | Model capability caps agent context effectiveness — test with best available model. Below a capability threshold, agents read the pack and explore anyway. |
| P10 | `[all repos]` | Agent self-scores are unreliable — reviewer grading against ground truth is mandatory for any experiment making quality claims. |
| P11 | `[all repos]` | Content is universal; routing is agent-specific. One pack, multiple bootstrap paths via CLAUDE.md / AGENTS.md / GEMINI.md. |
| P12 | `[all repos]` | Authority layer for trust-agents; navigation layer for verify-agents. Don't try to make one structured layer serve both agent architectures. |
| P13 | `[all repos]` | Bound the search space, don't prescribe the stop point. `search_directories` and `exclude_from_search` work; `stop_after` and `verify_budget` are ignored by search-and-verify agents. |
| P15 | `[all repos]` | Derived files are evidence, never edit targets. Exclude generated files at the search scope level, not just the reporting level — if an agent can see them, it will list them. |
| P16 | `[all repos]` | Routing must be imperative ("BEFORE starting, read these 3 files"), not suggestive ("follow the read order"). Agents interpret suggestive wording as optional. This is the difference between an agent using the pack vs skipping it. |

## Pipeline / Service repos

| # | Scope | Principle |
|---|---|---|
| P3 | `[pipeline/service]` | Runtime behavior matters as much as code structure — document silent failures. Any code path where failure produces no error (null return, silent drop, no log) must be called out explicitly. |
| P6 | `[coexisting architectures]` | Coexisting architectures need explicit boundary documentation. Tag CODE_MAP entries with their approach where relevant. |

## Complex repos

| # | Scope | Principle |
|---|---|---|
| P4 | `[complex repos]` | Change impact completeness > navigation speed. Agent context that makes agents faster but less complete on impact analysis is net-negative — it increases production risk while reducing tokens. |
| P14 | `[complex repos]` | Verification shortcuts must include line ranges, not just file paths. `"_base.py:131-135: _create_empty_result"` lets an agent check a specific location instead of reading the full file. Line ranges go stale faster but save the most exploration. |
