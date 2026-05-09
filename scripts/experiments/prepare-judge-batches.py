#!/usr/bin/env python3
"""prepare-judge-batches.py — stage per-cell judge briefings for subagent grading.

Walks the rerun results, groups by (agent, condition, model-slug, repo) — one
"cell" per (typically) 6 tasks — and emits one briefing JSON per cell. Each
briefing is self-contained: it inlines the question (from EXPERIMENT.md), the
expected answer (from GROUND_TRUTH.md), and the agent's answer + citations,
so a subagent doesn't have to chase 4 separate files per task.

Why this exists: `llm-judge.py` calls Claude API directly, which needs
ANTHROPIC_API_KEY. This driver lets us route grading through Claude Code
subagents instead — each subagent gets independent context, no key needed.

The subagent prompt template lives at the bottom of this file as
SUBAGENT_GRADING_PROMPT and is also written into each briefing for self-
containment (and to the briefings root as `_grading_prompt.md`).

Output layout (under <rerun-root>/_judge_briefings/):
  <cell-id>.json          — one briefing per cell
  _grading_prompt.md      — single shared subagent prompt

Idempotent: re-running overwrites the briefings dir.

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


JUDGE_SYSTEM_PROMPT = """You are a strict, impartial reviewer judging an AI coding agent's answer to a repository task.

Your job:
1. Compare the agent's ANSWER and CITATIONS to the EXPECTED answer and required citations from the ground truth.
2. Decide `correct`:
   - "yes" — every required claim is present and citations point to authoritative files. Minor wording differences are OK.
   - "partial" — answer is on the right track but missing a required claim, or citations are incomplete.
   - "no" — answer is wrong, hallucinated, or omits the central required claim.
3. Decide `risk_flag` (boolean):
   - true — if a developer acted on this answer, it would cause documented production impact (wrong API, missing invariant, stale file, ignored constraint).
   - false — answer may be incomplete but acting on it does not break production.
4. Write a 2-3 sentence rationale.

You MUST respond with ONLY a JSON object matching this schema (no prose, no code fences):
{
  "correct": "yes" | "partial" | "no",
  "risk_flag": true | false,
  "notes": "<short reviewer note suitable for the result file's correctness_notes field>",
  "rationale": "<2-3 sentences explaining the verdict>"
}
"""


SUBAGENT_GRADING_PROMPT = """You are grading 6 tasks from one cell of an agent-context fresh-pack experiment. Read the briefing JSON at the path I'll give you, grade each task, and write the verdicts to disk.

Per-task contract (apply to each of the 6 tasks in the briefing):

1. Read the task's `question`, `expected`, `answer`, `citations` directly from the briefing (already inlined — no need to read external files).

2. Apply the JUDGE_SYSTEM_PROMPT (also inlined in the briefing) and decide:
   - correct: "yes" | "partial" | "no"
   - risk_flag: true | false
   - notes: 1 sentence (suitable for the result's `correctness_notes`)
   - rationale: 2-3 sentences

3. Write a sidecar to the task's `judge_path`:
   ```json
   {
     "task_id": "<id>",
     "judge_model": "claude-code-subagent",
     "judge_response_raw": {"correct": "...", "risk_flag": ..., "notes": "...", "rationale": "..."},
     "scored_at": "<ISO-8601 UTC>"
   }
   ```

4. Update the task's result JSON at `result_path` (read it, modify these fields, write back):
   - correct: <verdict.correct>
   - correctness_notes: <verdict.notes>
   - risk_flag: <verdict.risk_flag>
   - risk_flag_explanation: <verdict.rationale> (use rationale here so the existing schema field carries the per-task reasoning)
   - grading_method: "llm-provisional"

5. Skip if the result already has `grading_method == "reviewer-confirmed"` (preserves human work).

Constraints:
- Do not edit any other files.
- Do not "fix" the agent's answer — only grade it against the ground truth.
- If the briefing's `expected` is empty for a task, mark `correct: "ungraded"` with a notes line explaining the gap and skip the result-JSON update for that task.

When done, report: number of tasks graded, count of yes/partial/no/ungraded, count of risk_flag=true. Keep it under 60 words.

The briefing path will be in the next message. Read it, grade, write, report.
"""


# ---------------------------------------------------------------------------
# Parsers (mirror llm-judge.py contract)
# ---------------------------------------------------------------------------

_TASK_HEADER_RE = re.compile(r"^###\s+([A-Z]\d+)\s*[-–—]+\s*(.+?)\n(.*?)(?=^###\s|\Z)", re.S | re.M)


def parse_task_bodies(path: pathlib.Path) -> dict[str, str]:
    """task_id -> body for any markdown file with `### <ID> -- <title>` sections."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for m in _TASK_HEADER_RE.finditer(path.read_text(encoding="utf-8")):
        out[m.group(1).strip()] = m.group(3).strip()
    return out


# ---------------------------------------------------------------------------
# Cell discovery + briefing assembly
# ---------------------------------------------------------------------------

_TASK_ID_RE = re.compile(r"^(L1|L2|M1|M2|H1|H2)\.json$")


def discover_cells(rerun_root: pathlib.Path) -> dict[tuple, list[pathlib.Path]]:
    """Group result JSONs by (agent, condition, model_slug, repo) cell.

    Two layouts coexist:
      - <repo>/results/<agent>/<condition>/<task>.json          (no model dir)
      - <repo>/results/<agent>/<condition>/<model-slug>/<task>.json
    """
    cells: dict[tuple, list[pathlib.Path]] = {}
    # We're given a single repo's rerun dir, not the matrix root.
    repo_name = rerun_root.name
    results_root = rerun_root / "results"
    if not results_root.is_dir():
        return cells
    for path in results_root.rglob("*.json"):
        if path.name.endswith(".judge.json"):
            continue
        m = _TASK_ID_RE.match(path.name)
        if not m:
            continue
        rel = path.relative_to(results_root).parts
        # rel: (agent, condition[, model_slug], task.json)
        if len(rel) == 3:
            agent, condition, _ = rel
            model_slug = ""
        elif len(rel) == 4:
            agent, condition, model_slug, _ = rel
        else:
            continue
        key = (agent, condition, model_slug, repo_name)
        cells.setdefault(key, []).append(path)
    for paths in cells.values():
        paths.sort()
    return cells


def cell_id(agent: str, condition: str, model_slug: str, repo: str) -> str:
    parts = [agent, condition]
    if model_slug:
        parts.append(model_slug)
    parts.append(repo)
    return "-".join(parts)


def build_briefing(
    cell_key: tuple,
    paths: list[pathlib.Path],
    questions: dict[str, str],
    expected: dict[str, str],
) -> dict[str, Any]:
    agent, condition, model_slug, repo = cell_key
    tasks_payload = []
    for rp in paths:
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            tasks_payload.append({
                "task_id": rp.stem,
                "result_path": str(rp),
                "judge_path": str(rp.with_suffix(".judge.json")),
                "error": f"unreadable result JSON: {exc}",
            })
            continue
        tid = data.get("task_id", rp.stem)
        tasks_payload.append({
            "task_id": tid,
            "result_path": str(rp),
            "judge_path": str(rp.with_suffix(".judge.json")),
            "question": questions.get(tid, ""),
            "expected": expected.get(tid, ""),
            "answer": data.get("answer", ""),
            "citations": data.get("citations", []),
            "agent": data.get("agent"),
            "capture_method": data.get("capture_method"),
            "condition": data.get("condition"),
            "current_grading_method": data.get("grading_method"),
        })
    return {
        "cell_id": cell_id(agent, condition, model_slug, repo),
        "agent": agent,
        "condition": condition,
        "model_slug": model_slug,
        "repo": repo,
        "task_count": len(tasks_payload),
        "judge_system_prompt": JUDGE_SYSTEM_PROMPT,
        "tasks": tasks_payload,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--rerun", required=True,
                        help="Single repo rerun dir, e.g. <root>/agent-chorus")
    parser.add_argument("--out-dir", default=None,
                        help="Briefings output dir (default: <rerun>/_judge_briefings)")
    args = parser.parse_args(argv)

    rerun = pathlib.Path(args.rerun).expanduser().resolve()
    if not rerun.is_dir():
        print(f"ERROR: rerun dir not found: {rerun}", file=sys.stderr)
        return 1

    out_dir = pathlib.Path(args.out_dir).expanduser().resolve() if args.out_dir else rerun / "_judge_briefings"
    out_dir.mkdir(parents=True, exist_ok=True)

    questions = parse_task_bodies(rerun / "EXPERIMENT.md")
    expected = parse_task_bodies(rerun / "GROUND_TRUTH.md")
    if not questions:
        print(f"WARN: no tasks parsed from {rerun}/EXPERIMENT.md", file=sys.stderr)
    if not expected:
        print(f"WARN: no expected answers parsed from {rerun}/GROUND_TRUTH.md", file=sys.stderr)

    cells = discover_cells(rerun)
    if not cells:
        print(f"WARN: no result JSONs under {rerun}/results/")
        return 0

    written = 0
    for key, paths in cells.items():
        briefing = build_briefing(key, paths, questions, expected)
        cid = briefing["cell_id"]
        target = out_dir / f"{cid}.json"
        target.write_text(json.dumps(briefing, indent=2) + "\n", encoding="utf-8")
        written += 1
        print(f"  briefing: {target.relative_to(rerun)} ({briefing['task_count']} tasks)")

    # One shared prompt at the briefings root for the subagent to read.
    (out_dir / "_grading_prompt.md").write_text(SUBAGENT_GRADING_PROMPT, encoding="utf-8")

    print(f"\nWrote {written} briefing(s) + grading prompt to {out_dir.relative_to(rerun)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
