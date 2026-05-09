#!/usr/bin/env python3
"""audit-judge.py — human spot-audit of LLM-provisional judge verdicts.

Samples a configurable fraction of `<result>.judge.json` files (default 30%)
and presents each to a human reviewer for confirm/override. On confirm,
the corresponding result JSON's `grading_method` is set to
`"reviewer-confirmed"`. On override, the reviewer's `correct`/`risk_flag`
/notes replace the LLM's, and `grading_method` becomes
`"reviewer-confirmed"`.

Public-claims gate: only `reviewer-confirmed` rows are eligible for public
artifacts (README, viz, talk). See METHODOLOGY.md.

Audit log: `~/agent-context-reruns/q2-2026-private/audit-log/<timestamp>.jsonl`

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import random
import sys


VALID_CORRECT = ("yes", "partial", "no")


def find_judge_pairs(results_root: pathlib.Path) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Return list of (result_path, judge_path) tuples for llm-provisional rows."""
    pairs: list[tuple[pathlib.Path, pathlib.Path]] = []
    for judge_path in sorted(results_root.rglob("*.judge.json")):
        result_path = judge_path.with_suffix("")  # strips .json
        result_path = result_path.with_suffix(".json")  # adds .json back without .judge
        # judge_path = "L1.judge.json" -> we need "L1.json"
        result_name = judge_path.name.replace(".judge.json", ".json")
        result_path = judge_path.parent / result_name
        if not result_path.exists():
            print(f"WARN: judge file without result: {judge_path}", file=sys.stderr)
            continue
        try:
            data = json.loads(result_path.read_text())
        except json.JSONDecodeError:
            continue
        if data.get("grading_method") == "llm-provisional":
            pairs.append((result_path, judge_path))
    return pairs


def render_for_review(result: dict, judge: dict) -> str:
    cit = "\n".join(
        f"  - {c.get('path')}{':' + str(c['line']) if c.get('line') else ''}  {c.get('note','')}".rstrip()
        for c in result.get("citations", [])
    ) or "  (none)"
    return f"""
==================================================================
Task: {result['task_id']}   Agent: {result['agent']}   Capture: {result['capture_method']}   Condition: {result['condition']}
Repo: {result['repo']}
Result file: {judge['result_path']}

--- Agent's answer ---
{result.get('answer', '(no answer)')}

--- Agent's citations ---
{cit}

--- LLM judge verdict ({judge['judge_model']}, {judge['judged_at']}) ---
correct: {judge['verdict']['correct']}
risk_flag: {judge['verdict']['risk_flag']}
notes: {judge['verdict']['notes']}
rationale: {judge['verdict']['rationale']}
==================================================================
"""


def prompt_reviewer(result: dict, judge: dict) -> tuple[str, dict]:
    """Returns (action, fields_to_apply).

    action ∈ {"confirm", "override", "skip"}.
    fields_to_apply: dict of fields to write into the result JSON.
    """
    print(render_for_review(result, judge))
    while True:
        ans = input("Action — [c]onfirm  [o]verride  [s]kip  [q]uit: ").strip().lower()
        if ans in ("c", "confirm", ""):
            return "confirm", {
                "correct": judge["verdict"]["correct"],
                "correctness_notes": judge["verdict"]["notes"],
                "risk_flag": judge["verdict"]["risk_flag"],
                "risk_flag_explanation": judge["verdict"]["rationale"],
                "grading_method": "reviewer-confirmed",
            }
        if ans in ("o", "override"):
            new_correct = ""
            while new_correct not in VALID_CORRECT:
                new_correct = input(f"  correct {VALID_CORRECT}: ").strip().lower()
            risk_in = ""
            while risk_in not in ("y", "n", "yes", "no", "true", "false"):
                risk_in = input("  risk_flag [y/n]: ").strip().lower()
            risk = risk_in in ("y", "yes", "true")
            notes = input("  reviewer notes (one line): ").strip()
            return "override", {
                "correct": new_correct,
                "correctness_notes": notes,
                "risk_flag": risk,
                "risk_flag_explanation": notes,
                "grading_method": "reviewer-confirmed",
            }
        if ans in ("s", "skip"):
            return "skip", {}
        if ans in ("q", "quit"):
            return "quit", {}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", required=True, help="Rerun directory (contains results/)")
    parser.add_argument("--sample", type=float, default=0.30, help="Fraction of llm-provisional rows to audit (default 0.30)")
    parser.add_argument("--seed", type=int, default=20260504, help="Random seed for deterministic sampling")
    parser.add_argument("--all", action="store_true", help="Audit every llm-provisional row instead of sampling")
    parser.add_argument(
        "--audit-log-dir",
        default=str(pathlib.Path.home() / "agent-context-reruns" / "q2-2026-private" / "audit-log"),
        help="Directory to write audit JSONL log",
    )
    args = parser.parse_args(argv)

    rerun = pathlib.Path(args.rerun).expanduser()
    results_root = rerun / "results"
    if not results_root.is_dir():
        print(f"ERROR: results dir not found: {results_root}", file=sys.stderr)
        return 1

    pairs = find_judge_pairs(results_root)
    if not pairs:
        print("ERROR: no llm-provisional rows found. Run llm-judge.py first.", file=sys.stderr)
        return 1

    if args.all:
        sample = pairs
    else:
        rng = random.Random(args.seed)
        n = max(1, int(round(len(pairs) * args.sample)))
        sample = rng.sample(pairs, n)

    print(f"Found {len(pairs)} llm-provisional rows; auditing {len(sample)} (sample={args.sample if not args.all else 1.0:.0%}).")

    audit_log_dir = pathlib.Path(args.audit_log_dir).expanduser()
    audit_log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    log_path = audit_log_dir / f"audit-{timestamp}.jsonl"

    counts = {"confirm": 0, "override": 0, "skip": 0, "quit": 0}
    with log_path.open("w") as logf:
        for result_path, judge_path in sample:
            result = json.loads(result_path.read_text())
            judge = json.loads(judge_path.read_text())
            action, fields = prompt_reviewer(result, judge)
            counts[action] = counts.get(action, 0) + 1
            log_entry = {
                "result_path": str(result_path),
                "judge_path": str(judge_path),
                "task_id": result["task_id"],
                "agent": result["agent"],
                "action": action,
                "applied": fields,
                "audited_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            logf.write(json.dumps(log_entry) + "\n")
            if action == "quit":
                print("Quitting audit early. Already-applied confirmations stay; un-audited rows remain llm-provisional.")
                break
            if fields:
                result.update(fields)
                result_path.write_text(json.dumps(result, indent=2) + "\n")

    print()
    for k, v in counts.items():
        print(f"{k}: {v}")
    print(f"Audit log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
