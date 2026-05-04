#!/usr/bin/env python3
"""Summarize fresh-pack experiment result JSON files.

v2: 4-agent matrix (claude, codex, cursor, opencode), capture_method-aware
nullability for IDE captures, grading_method tracks LLM-judge vs reviewer-confirmed.

Stdlib-only on purpose. This performs a tight validation pass for the result
shape used by docs/experiments/result.schema.json, then prints markdown tables.

Use --public-only to restrict the output to reviewer-confirmed rows (the only
rows allowed to back public claims in README, viz, and talk).
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
    "capture_method",
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
    "grading_method",
    "quality_self_score",
    "risk_flag",
    "risk_flag_explanation",
}

# Optional reproducibility anchors stamped by apply-provenance.py post-run.
# Allowed but not required; if missing, summarize warns.
OPTIONAL = {
    "source_repo_sha",
    "pack_manifest_sha",
    "task_template_hash",
    "agent_context_cli_version",
}

AGENTS = {"claude", "codex", "cursor", "opencode"}
CAPTURE_METHODS = {"cli", "ide", "tunnel"}
CONDITIONS = {"bare", "structured_fresh"}
CORRECT = {"yes", "partial", "no", "ungraded"}
GRADING_METHODS = {"ungraded", "llm-provisional", "reviewer-confirmed"}

NULLABLE_WHEN_NON_CLI = {
    "tool_calls",
    "first_correct_file_hop",
    "files_opened_after_first_correct_hop",
    "post_hit_dead_ends",
}


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
    extra = sorted(set(data) - REQUIRED - OPTIONAL)
    if missing:
        raise ValueError(f"{path}: missing required fields: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{path}: unexpected fields: {', '.join(extra)}")
    for field in OPTIONAL:
        if field in data and data[field] is not None and not isinstance(data[field], str):
            raise ValueError(f"{path}: optional field {field} must be a string or null")
    if data["agent"] not in AGENTS:
        raise ValueError(f"{path}: agent must be one of {sorted(AGENTS)}")
    if data["capture_method"] not in CAPTURE_METHODS:
        raise ValueError(f"{path}: capture_method must be one of {sorted(CAPTURE_METHODS)}")
    if data["condition"] not in CONDITIONS:
        raise ValueError(f"{path}: condition must be one of {sorted(CONDITIONS)}")
    if data["correct"] not in CORRECT:
        raise ValueError(f"{path}: correct must be one of {sorted(CORRECT)}")
    if data["grading_method"] not in GRADING_METHODS:
        raise ValueError(f"{path}: grading_method must be one of {sorted(GRADING_METHODS)}")

    is_cli = data["capture_method"] == "cli"

    # Always-required non-negative integers
    for field in ("files_opened_count", "dead_ends", "quality_self_score"):
        v = data[field]
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"{path}: {field} must be a non-negative integer")
    if not 1 <= data["quality_self_score"] <= 10:
        raise ValueError(f"{path}: quality_self_score must be between 1 and 10")

    # CLI-only required (else null allowed)
    for field in ("first_correct_file_hop", "files_opened_after_first_correct_hop", "post_hit_dead_ends"):
        v = data[field]
        if is_cli:
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"{path}: {field} must be a non-negative integer when capture_method=cli")
        else:
            if v is not None and (not isinstance(v, int) or v < 0):
                raise ValueError(f"{path}: {field} must be null or non-negative integer when capture_method!=cli")

    # tool_calls: object when cli, object-or-null otherwise
    if is_cli:
        if not isinstance(data["tool_calls"], dict):
            raise ValueError(f"{path}: tool_calls must be an object when capture_method=cli")
    else:
        if data["tool_calls"] is not None and not isinstance(data["tool_calls"], dict):
            raise ValueError(f"{path}: tool_calls must be null or an object when capture_method!=cli")

    if not isinstance(data["duration_seconds"], (int, float)) or data["duration_seconds"] < 0:
        raise ValueError(f"{path}: duration_seconds must be a non-negative number")
    if not isinstance(data["citations"], list):
        raise ValueError(f"{path}: citations must be an array")
    if not isinstance(data["risk_flag"], bool):
        raise ValueError(f"{path}: risk_flag must be boolean")


def fmt_avg(values: list[float | int | None]) -> str:
    nums = [v for v in values if v is not None]
    if not nums:
        return "n/a"
    return f"{statistics.mean(nums):.1f}"


def fmt_int(value: int | None) -> str:
    return "n/a" if value is None else str(value)


def summarize(results: list[dict[str, Any]], public_only: bool = False) -> str:
    if public_only:
        results = [r for r in results if r["grading_method"] == "reviewer-confirmed"]

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        groups[(item["agent"], item["capture_method"], item["condition"])].append(item)

    lines: list[str] = []
    title = "Agent-Context Fresh-Pack Rerun Summary"
    if public_only:
        title += " (reviewer-confirmed only)"
    lines.append(f"# {title}")
    lines.append("")

    # Provenance summary
    grading_counts: dict[str, int] = defaultdict(int)
    for r in results:
        grading_counts[r["grading_method"]] += 1
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Total result rows: {len(results)}")
    for gm in ("reviewer-confirmed", "llm-provisional", "ungraded"):
        lines.append(f"- {gm}: {grading_counts.get(gm, 0)}")
    if not public_only and grading_counts.get("llm-provisional", 0) > 0:
        lines.append("")
        lines.append("> `llm-provisional` rows are LLM-judged but not yet reviewer-confirmed. They are NOT eligible for public claims. Run `audit-judge.py` and re-summarize with `--public-only` before quoting.")
    lines.append("")

    # Aggregate by (agent, capture_method, condition)
    lines.append("## Aggregate")
    lines.append("")
    lines.append("| Agent | Capture | Condition | Tasks | Yes | Partial | No | Ungraded | Avg files | Avg dead ends | Avg first hit | Risk flags |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for agent in sorted(AGENTS):
        for capture in sorted(CAPTURE_METHODS):
            for condition in ("bare", "structured_fresh"):
                items = groups.get((agent, capture, condition), [])
                if not items:
                    continue
                counts = {name: sum(1 for x in items if x["correct"] == name) for name in CORRECT}
                lines.append(
                    "| {agent} | {capture} | {condition} | {tasks} | {yes} | {partial} | {no} | {ungraded} | {files} | {dead} | {hop} | {risk} |".format(
                        agent=agent,
                        capture=capture,
                        condition=condition,
                        tasks=len(items),
                        yes=counts["yes"],
                        partial=counts["partial"],
                        no=counts["no"],
                        ungraded=counts["ungraded"],
                        files=fmt_avg([x["files_opened_count"] for x in items]),
                        dead=fmt_avg([x["dead_ends"] for x in items]),
                        hop=fmt_avg([x["first_correct_file_hop"] for x in items]),
                        risk=sum(1 for x in items if x["risk_flag"]),
                    )
                )

    lines.append("")
    lines.append("> `n/a` indicates the metric is not captured for that capture_method (typically IDE captures lack tool-level telemetry).")

    # Per-task detail
    lines.append("")
    lines.append("## Task Detail")
    lines.append("")
    lines.append("| Task | Agent | Capture | Condition | Correct | Grading | Files | Dead ends | First hit | Post-hit dead | Risk |")
    lines.append("|---|---|---|---|---|---|---:|---:|---:|---:|---|")
    for item in sorted(results, key=lambda x: (x["task_id"], x["agent"], x["capture_method"], x["condition"])):
        lines.append(
            "| {task} | {agent} | {capture} | {condition} | {correct} | {grading} | {files} | {dead} | {hop} | {post} | {risk} |".format(
                task=item["task_id"],
                agent=item["agent"],
                capture=item["capture_method"],
                condition=item["condition"],
                correct=item["correct"],
                grading=item["grading_method"],
                files=item["files_opened_count"],
                dead=item["dead_ends"],
                hop=fmt_int(item["first_correct_file_hop"]),
                post=fmt_int(item["post_hit_dead_ends"]),
                risk="yes" if item["risk_flag"] else "no",
            )
        )

    ungraded = [x for x in results if x["correct"] == "ungraded"]
    if ungraded:
        lines.append("")
        lines.append("> Warning: correctness claims are blocked until all results are reviewer-graded.")

    return "\n".join(lines)


def reproducibility_bundle(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing_anchor_rows = 0
    for r in results:
        anchors = {f: r.get(f) for f in OPTIONAL}
        # bare condition legitimately has null pack_manifest_sha; the other three anchors must be present.
        required_anchor_fields = [f for f in OPTIONAL if f != "pack_manifest_sha"]
        if any(anchors.get(f) in (None, "") for f in required_anchor_fields):
            missing_anchor_rows += 1
        if r["condition"] == "structured_fresh" and not anchors.get("pack_manifest_sha"):
            missing_anchor_rows += 1
        rows.append({
            "task_id": r["task_id"],
            "agent": r["agent"],
            "capture_method": r["capture_method"],
            "condition": r["condition"],
            "repo": r["repo"],
            "correct": r["correct"],
            "grading_method": r["grading_method"],
            "source_repo_sha": anchors["source_repo_sha"],
            "pack_manifest_sha": anchors["pack_manifest_sha"],
            "task_template_hash": anchors["task_template_hash"],
            "agent_context_cli_version": anchors["agent_context_cli_version"],
        })
    return {
        "rows": rows,
        "row_count": len(rows),
        "rows_missing_anchors": missing_anchor_rows,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", help="Directory containing result JSON files")
    parser.add_argument("--schema", help="Accepted for workflow clarity; validation is built in")
    parser.add_argument(
        "--public-only",
        action="store_true",
        help="Restrict output to reviewer-confirmed rows. Use this when generating numbers for README, evidence/, viz, or talk.",
    )
    parser.add_argument(
        "--reproducibility-bundle",
        metavar="OUT_PATH",
        help="Export a JSON bundle of per-row reproducibility anchors (source_repo_sha, pack_manifest_sha, task_template_hash, agent_context_cli_version). Run apply-provenance.py first to populate these fields.",
    )
    args = parser.parse_args(argv)

    root = pathlib.Path(args.results_dir)
    if not root.is_dir():
        print(f"ERROR: results dir not found: {root}", file=sys.stderr)
        return 1

    paths = sorted(
        p for p in root.rglob("*.json")
        if p.name != "result.schema.json" and not p.name.endswith(".judge.json")
    )
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

    if args.reproducibility_bundle:
        bundle = reproducibility_bundle(results)
        out_path = pathlib.Path(args.reproducibility_bundle).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, indent=2) + "\n")
        print(f"Wrote reproducibility bundle: {out_path}")
        if bundle["rows_missing_anchors"] > 0:
            print(f"WARN: {bundle['rows_missing_anchors']} row(s) missing one or more provenance anchors. Run apply-provenance.py.", file=sys.stderr)

    print(summarize(results, public_only=args.public_only))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
