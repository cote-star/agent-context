#!/usr/bin/env python3
"""Summarize Codex/Cursor fresh-pack experiment result JSON files.

Stdlib-only on purpose. This performs a tight validation pass for the result
shape used by docs/experiments/result.schema.json, then prints markdown tables.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from collections import defaultdict
from typing import Any


REQUIRED = {
    "task_id",
    "agent",
    "condition",
    "repo",
    "started_at",
    "finished_at",
    "files_opened_count",
    "dead_ends",
    "first_correct_file_hop",
    "files_opened_after_first_correct_hop",
    "post_hit_dead_ends",
    "tool_calls",
    "duration_seconds",
    "answer",
    "citations",
    "correct",
    "correctness_notes",
    "quality_self_score",
    "risk_flag",
    "risk_flag_explanation",
}

AGENTS = {"codex", "cursor"}
CONDITIONS = {"bare", "structured_fresh"}
CORRECT = {"yes", "partial", "no", "ungraded"}


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: result must be a JSON object")
    return data


def validate(path: pathlib.Path, data: dict[str, Any]) -> None:
    missing = sorted(REQUIRED - set(data))
    extra = sorted(set(data) - REQUIRED)
    if missing:
        raise ValueError(f"{path}: missing required fields: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{path}: unexpected fields: {', '.join(extra)}")
    if data["agent"] not in AGENTS:
        raise ValueError(f"{path}: agent must be one of {sorted(AGENTS)}")
    if data["condition"] not in CONDITIONS:
        raise ValueError(f"{path}: condition must be one of {sorted(CONDITIONS)}")
    if data["correct"] not in CORRECT:
        raise ValueError(f"{path}: correct must be one of {sorted(CORRECT)}")

    integer_fields = [
        "files_opened_count",
        "dead_ends",
        "first_correct_file_hop",
        "files_opened_after_first_correct_hop",
        "post_hit_dead_ends",
        "quality_self_score",
    ]
    for field in integer_fields:
        if not isinstance(data[field], int) or data[field] < 0:
            raise ValueError(f"{path}: {field} must be a non-negative integer")
    if not 1 <= data["quality_self_score"] <= 10:
        raise ValueError(f"{path}: quality_self_score must be between 1 and 10")
    if not isinstance(data["duration_seconds"], (int, float)) or data["duration_seconds"] < 0:
        raise ValueError(f"{path}: duration_seconds must be a non-negative number")
    if not isinstance(data["tool_calls"], dict):
        raise ValueError(f"{path}: tool_calls must be an object")
    if not isinstance(data["citations"], list):
        raise ValueError(f"{path}: citations must be an array")
    if not isinstance(data["risk_flag"], bool):
        raise ValueError(f"{path}: risk_flag must be boolean")


def fmt_avg(values: list[float]) -> str:
    if not values:
        return "-"
    return f"{statistics.mean(values):.1f}"


def summarize(results: list[dict[str, Any]]) -> str:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        groups[(item["agent"], item["condition"])].append(item)

    lines: list[str] = []
    lines.append("# Agent-Context Fresh-Pack Rerun Summary")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append("| Agent | Condition | Tasks | Yes | Partial | No | Ungraded | Avg files | Avg dead ends | Risk flags |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for agent in sorted(AGENTS):
        for condition in ("bare", "structured_fresh"):
            items = groups.get((agent, condition), [])
            counts = {name: sum(1 for x in items if x["correct"] == name) for name in CORRECT}
            lines.append(
                "| {agent} | {condition} | {tasks} | {yes} | {partial} | {no} | {ungraded} | {files} | {dead} | {risk} |".format(
                    agent=agent,
                    condition=condition,
                    tasks=len(items),
                    yes=counts["yes"],
                    partial=counts["partial"],
                    no=counts["no"],
                    ungraded=counts["ungraded"],
                    files=fmt_avg([x["files_opened_count"] for x in items]),
                    dead=fmt_avg([x["dead_ends"] for x in items]),
                    risk=sum(1 for x in items if x["risk_flag"]),
                )
            )

    lines.append("")
    lines.append("## Task Detail")
    lines.append("")
    lines.append("| Task | Agent | Condition | Correct | Files | Dead ends | First hit | Post-hit dead ends | Risk |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---|")
    for item in sorted(results, key=lambda x: (x["task_id"], x["agent"], x["condition"])):
        lines.append(
            "| {task} | {agent} | {condition} | {correct} | {files} | {dead} | {hop} | {post} | {risk} |".format(
                task=item["task_id"],
                agent=item["agent"],
                condition=item["condition"],
                correct=item["correct"],
                files=item["files_opened_count"],
                dead=item["dead_ends"],
                hop=item["first_correct_file_hop"],
                post=item["post_hit_dead_ends"],
                risk="yes" if item["risk_flag"] else "no",
            )
        )

    ungraded = [x for x in results if x["correct"] == "ungraded"]
    if ungraded:
        lines.append("")
        lines.append("> Warning: correctness claims are blocked until all results are reviewer-graded.")

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", help="Directory containing result JSON files")
    parser.add_argument("--schema", help="Accepted for workflow clarity; validation is built in")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.results_dir)
    if not root.is_dir():
        print(f"ERROR: results dir not found: {root}", file=sys.stderr)
        return 1

    paths = sorted(p for p in root.rglob("*.json") if p.name != "result.schema.json")
    if not paths:
        print(f"ERROR: no result JSON files found under {root}", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    try:
        for path in paths:
            data = load_json(path)
            validate(path, data)
            results.append(data)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(summarize(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
