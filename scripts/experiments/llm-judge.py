#!/usr/bin/env python3
"""llm-judge.py — Claude-as-judge first pass for fresh-pack experiment results.

Reads each result JSON in a rerun directory, looks up the task in EXPERIMENT.md
and the expected answer/citations in GROUND_TRUTH.md, then asks Claude to
grade `correct` (yes/partial/no) and `risk_flag` (true/false). Writes a
sidecar `<result>.judge.json` and updates the original result JSON to
`grading_method: "llm-provisional"`.

Idempotent: results already marked `reviewer-confirmed` are skipped (human
work is never overwritten).

Inputs:
  rerun directory layout
    <rerun>/EXPERIMENT.md
    <rerun>/GROUND_TRUTH.md
    <rerun>/results/<agent>/<condition>/<task>.json

Backend: Claude API. Set ANTHROPIC_API_KEY in env.
Model: claude-opus-4-7 by default (override with --model).

Privacy: Anthropic Enterprise plan keeps content private. See
docs/experiments/q2-2026-rerun/METHODOLOGY.md for the disclosure.

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request
import urllib.error
from typing import Any


API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 1500


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


JUDGE_USER_TEMPLATE = """## Task

Task ID: {task_id}
Agent: {agent}
Capture method: {capture_method}
Condition: {condition}

## Question (from EXPERIMENT.md)

{question}

## Expected (from GROUND_TRUTH.md)

{expected}

## Agent's answer

{answer}

## Agent's citations

{citations}

Grade the agent's answer per the rules in the system prompt."""


def parse_experiment_tasks(path: pathlib.Path) -> dict[str, str]:
    """Extract task_id -> question text from EXPERIMENT.md.

    Tasks are headed by `### <ID> -- <kind>` (or similar). We capture the body
    until the next `### ` heading.
    """
    text = path.read_text()
    tasks: dict[str, str] = {}
    pattern = re.compile(r"^###\s+([A-Z]\d+)\s*[-–—]+\s*(.+?)\n(.*?)(?=^###\s|\Z)", re.S | re.M)
    for match in pattern.finditer(text):
        task_id = match.group(1).strip()
        body = match.group(3).strip()
        tasks[task_id] = body
    return tasks


def parse_ground_truth_tasks(path: pathlib.Path) -> dict[str, str]:
    """Extract task_id -> ground truth body from GROUND_TRUTH.md, same shape as EXPERIMENT.md."""
    if not path.exists():
        return {}
    return parse_experiment_tasks(path)


def hash_input(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()[:16]


def call_claude(api_key: str, model: str, system: str, user: str, max_tokens: int) -> dict[str, Any]:
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_verdict(api_response: dict[str, Any]) -> dict[str, Any]:
    content = api_response.get("content", [])
    if not content:
        raise RuntimeError(f"empty content in API response: {api_response}")
    text = "".join(block.get("text", "") for block in content if block.get("type") == "text").strip()
    # Strip code fences if present (defensive)
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"judge did not return valid JSON: {exc}\nraw: {text[:500]}") from exc
    for field in ("correct", "risk_flag", "notes", "rationale"):
        if field not in verdict:
            raise RuntimeError(f"judge response missing field {field}: {verdict}")
    if verdict["correct"] not in ("yes", "partial", "no"):
        raise RuntimeError(f"judge returned invalid correct value: {verdict['correct']!r}")
    if not isinstance(verdict["risk_flag"], bool):
        raise RuntimeError(f"judge returned non-bool risk_flag: {verdict['risk_flag']!r}")
    return verdict


def judge_one(
    result_path: pathlib.Path,
    experiment_tasks: dict[str, str],
    ground_truth_tasks: dict[str, str],
    api_key: str,
    model: str,
    max_tokens: int,
    dry_run: bool,
    only_ungraded: bool = False,
) -> tuple[str, dict[str, Any] | None]:
    result = json.loads(result_path.read_text())

    if result.get("grading_method") == "reviewer-confirmed":
        return ("skip-reviewer-confirmed", None)
    if only_ungraded and result.get("grading_method") == "llm-provisional":
        return ("skip-already-llm-provisional", None)

    task_id = result["task_id"]
    question = experiment_tasks.get(task_id, f"(no EXPERIMENT.md entry for {task_id})")
    expected = ground_truth_tasks.get(task_id, f"(no GROUND_TRUTH.md entry for {task_id})")

    citations = "\n".join(
        f"- {c.get('path')}{':' + str(c['line']) if c.get('line') else ''}  {c.get('note','')}".rstrip()
        for c in result.get("citations", [])
    ) or "(no citations)"

    user = JUDGE_USER_TEMPLATE.format(
        task_id=task_id,
        agent=result["agent"],
        capture_method=result["capture_method"],
        condition=result["condition"],
        question=question,
        expected=expected,
        answer=result.get("answer", "(no answer)"),
        citations=citations,
    )

    input_hash = hash_input({"system": JUDGE_SYSTEM_PROMPT, "user": user, "model": model})

    if dry_run:
        return ("dry-run", {
            "task_id": task_id,
            "result_path": str(result_path),
            "judge_model": model,
            "judged_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "input_hash": input_hash,
            "would_call": True,
        })

    api_response = call_claude(api_key, model, JUDGE_SYSTEM_PROMPT, user, max_tokens)
    verdict = extract_verdict(api_response)

    judge_record = {
        "task_id": task_id,
        "result_path": str(result_path.resolve()),
        "judge_model": model,
        "judged_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "tokens_used": api_response.get("usage", {}),
        "input_hash": input_hash,
    }

    judge_path = result_path.with_suffix(".judge.json")
    judge_path.write_text(json.dumps(judge_record, indent=2) + "\n")

    # Update original result with provisional grade
    result["correct"] = verdict["correct"]
    result["correctness_notes"] = verdict["notes"]
    result["risk_flag"] = verdict["risk_flag"]
    result["risk_flag_explanation"] = verdict["rationale"]
    result["grading_method"] = "llm-provisional"
    result_path.write_text(json.dumps(result, indent=2) + "\n")

    return ("judged", judge_record)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", required=True, help="Rerun directory containing EXPERIMENT.md, GROUND_TRUTH.md, results/")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true", help="Build prompts but don't call API")
    parser.add_argument("--only-task", help="Judge only this task_id (for debugging)")
    parser.add_argument("--only-ungraded", action="store_true", help="Skip rows already marked llm-provisional or reviewer-confirmed; useful for follow-on runs that should only judge new results")
    args = parser.parse_args(argv)

    rerun = pathlib.Path(args.rerun).expanduser()
    if not rerun.is_dir():
        print(f"ERROR: rerun dir not found: {rerun}", file=sys.stderr)
        return 1

    experiment_tasks = parse_experiment_tasks(rerun / "EXPERIMENT.md")
    ground_truth_tasks = parse_ground_truth_tasks(rerun / "GROUND_TRUTH.md")
    if not experiment_tasks:
        print(f"ERROR: no tasks parsed from {rerun}/EXPERIMENT.md", file=sys.stderr)
        return 1

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not args.dry_run and not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Use --dry-run to test prompt building.", file=sys.stderr)
        return 1

    result_paths = sorted(
        p for p in (rerun / "results").rglob("*.json")
        if not p.name.endswith(".judge.json")
    )
    if args.only_task:
        result_paths = [p for p in result_paths if json.loads(p.read_text()).get("task_id") == args.only_task]

    if not result_paths:
        print(f"ERROR: no result files found under {rerun / 'results'}", file=sys.stderr)
        return 1

    counts = {
        "judged": 0,
        "skip-reviewer-confirmed": 0,
        "skip-already-llm-provisional": 0,
        "dry-run": 0,
        "error": 0,
    }
    for path in result_paths:
        try:
            status, _ = judge_one(
                path, experiment_tasks, ground_truth_tasks,
                api_key, args.model, args.max_tokens, args.dry_run,
                only_ungraded=args.only_ungraded,
            )
            counts[status] = counts.get(status, 0) + 1
            print(f"  [{status:24}] {path}")
        except Exception as exc:  # noqa: BLE001
            counts["error"] += 1
            print(f"  [ERROR                   ] {path}: {exc}", file=sys.stderr)

    print()
    for k, v in counts.items():
        print(f"{k}: {v}")
    return 0 if counts["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
