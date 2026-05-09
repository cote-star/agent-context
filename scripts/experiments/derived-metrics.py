#!/usr/bin/env python3
"""derived-metrics.py — aggregate per-task v3 result JSONs into per-cell metrics.

Reads a directory of schema-v3 per-task experiment results and emits 28 derived
metrics per cell, where a cell is the tuple (agent, model_id, condition, repo).
Each cell is expected to contain ~6 task rows (the standard fresh-pack sweep).

Six metric families are computed:
  A. Outcome — correctness rates, risk-flag rate, citation precision.
  B. Speed — duration medians/means, seconds_per_correct, TTFCF.
  C. Navigation efficiency — hops, search/read ratio, tool-call counts,
     re-read rate, first-tool type, pack precedence, pack utilization,
     verification-shortcut hit rate, unique source files, dead ends.
  D. Output quality — citations count, ground-truth required-recall.
  E. Cost / efficiency — tokens_total_per_correct, cost_usd_per_correct,
     tokens_thinking_share. Honors token_metric_scope="cell_replicated"
     by dividing tokens_total by 6 before summing (the 6 rows in a
     cell_replicated cell are duplicates of one session total).
  F. Operator friction — permission_prompts_mean, interrupted_rate.

Design choices documented inline:
  - Path glob default mirrors the rerun layout used by extract-tokens-from-chorus.py
    and apply-provenance.py:
      <results-dir>/<repo>/results/<agent>/<condition>/<model-slug>/T*.json
    Files ending in `.judge.json` are excluded — those are LLM-judge sidecars,
    not result rows.
  - Per-correct denominators use yes_count + 0.5 * partial_count so partial
    correctness contributes proportionally; division by zero returns JSON null
    rather than Infinity (more useful in tables).
  - Median/mean ignore null values rather than treating them as 0.
  - For cell_replicated token rows, tokens_total is divided by task_count
    (typically 6) before summing so the sum recovers the session total exactly.
  - pack_utilization_rate is the simplified form noted in the spec: mean of
    distinct `.agent-context/current/*` paths read per task — computing the
    intersection with files actually present requires the source tree on disk
    and is left as a follow-on (see in-code comment).
  - verification_shortcut_hit_rate uses the v3 verification_shortcut_paths
    field (populated by the per-agent extractors from each cell's
    structured_fresh/.agent-context/current/search_scope.json). Null when
    the field isn't present (e.g., bare condition or pre-v3 results).

Usage:
  scripts/experiments/derived-metrics.py --results <dir>
  scripts/experiments/derived-metrics.py --results <dir> --out-json metrics.json
  scripts/experiments/derived-metrics.py --results <dir> --out-md metrics.md
  scripts/experiments/derived-metrics.py --results <dir> \\
      --cells claude/structured_fresh/agent-chorus,codex/bare/agent-chorus

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import statistics
import sys
from collections import Counter
from typing import Any


PACK_PREFIX = ".agent-context/"
PACK_CURRENT_PREFIX = ".agent-context/current/"


# ---------------------------------------------------------------------------
# Result discovery
# ---------------------------------------------------------------------------

def discover_results(results_dir: pathlib.Path) -> list[pathlib.Path]:
    """Glob result JSONs in the canonical rerun layout, skipping judge sidecars.

    Two layouts coexist:
      - With model slug:    <repo>/results/<agent>/<condition>/<model-slug>/T*.json
      - Without model slug: <repo>/results/<agent>/<condition>/T*.json

    The model-slug layout is used by lanes invoked with `--model` (cursor
    composer-2-fast, cursor opus). Default codex/claude lanes use the
    no-model layout. Grouping by (agent, model_id, condition, repo) handles
    both — model_id comes from the per-result JSON's `model_id` field, not
    the path.
    """
    paths: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    # Two distinct globs because pathlib's glob doesn't support
    # variable-depth wildcards within a single pattern.
    for pattern in ("*/results/*/*/*.json", "*/results/*/*/*/*.json"):
        for p in results_dir.glob(pattern):
            if p.name.endswith(".judge.json"):
                continue
            if p in seen:
                continue
            seen.add(p)
            paths.append(p)
    return sorted(paths)


def load_result(path: pathlib.Path) -> dict[str, Any] | None:
    """Read a result JSON; return None on parse error so one bad row doesn't poison the run."""
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARN: could not parse {path}: {exc}", file=sys.stderr)
        return None


def cell_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """Per-cell key tuple: (agent, model_id, condition, repo). Missing model_id → ''."""
    return (
        row.get("agent") or "",
        row.get("model_id") or "",
        row.get("condition") or "",
        row.get("repo") or "",
    )


def filter_cells(
    rows_by_cell: dict[tuple[str, str, str, str], list[dict[str, Any]]],
    cell_filter: list[str] | None,
) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    """Restrict to cells matching `agent/condition/repo` triples (model_id wildcarded)."""
    if not cell_filter:
        return rows_by_cell
    wanted = {tuple(c.split("/")) for c in cell_filter}
    out: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for key, rows in rows_by_cell.items():
        agent, _model, condition, repo = key
        if (agent, condition, repo) in wanted:
            out[key] = rows
    return out


# ---------------------------------------------------------------------------
# Small helpers — null-aware numeric reductions
# ---------------------------------------------------------------------------

def _safe_median(values: list[float]) -> float | None:
    nums = [v for v in values if v is not None]
    return statistics.median(nums) if nums else None


def _safe_mean(values: list[float]) -> float | None:
    nums = [v for v in values if v is not None]
    return (sum(nums) / len(nums)) if nums else None


def _safe_div(numerator: float, denominator: float) -> float | None:
    """Return None for division by zero (so JSON serializes null, not Infinity)."""
    return (numerator / denominator) if denominator else None


def _parse_iso(ts: str | None) -> _dt.datetime | None:
    """Parse ISO-8601, tolerating trailing 'Z' (Python 3.8 fromisoformat doesn't)."""
    if not ts:
        return None
    try:
        return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _classify_tool(tool: str) -> str:
    """Classify a tool name into a coarse bucket. Lowercased substring match."""
    t = (tool or "").lower()
    if "grep" in t:
        return "grep"
    if "glob" in t:
        return "glob"
    if "find" in t:
        return "find"
    if "read" in t:
        return "read"
    if "shell" in t or "bash" in t or "exec" in t:
        return "shell"
    return "other"


# ---------------------------------------------------------------------------
# Per-task derivations
# ---------------------------------------------------------------------------

def _correctness_counts(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    yes = sum(1 for r in rows if r.get("correct") == "yes")
    partial = sum(1 for r in rows if r.get("correct") == "partial")
    no = sum(1 for r in rows if r.get("correct") == "no")
    return yes, partial, no


def _correct_denom(yes: int, partial: int) -> float:
    return yes + 0.5 * partial


def _citation_precision(row: dict[str, Any]) -> float | None:
    req = row.get("ground_truth_required_paths")
    opt = row.get("ground_truth_optional_paths")
    if req is None and opt is None:
        return None
    valid = set(req or []) | set(opt or [])
    cites = row.get("citations") or []
    if not cites:
        return 0.0
    hits = sum(1 for c in cites if c.get("path") in valid)
    return hits / len(cites)


def _ttfcf_seconds(row: dict[str, Any]) -> float | None:
    started = _parse_iso(row.get("started_at"))
    hit = _parse_iso(row.get("first_correct_file_ts"))
    if started is None or hit is None:
        return None
    return (hit - started).total_seconds()


def _tool_calls_total(row: dict[str, Any]) -> int | None:
    tc = row.get("tool_calls")
    if not isinstance(tc, dict):
        return None
    return sum(v for v in tc.values() if isinstance(v, int))


def _tool_calls_by_bucket(row: dict[str, Any]) -> dict[str, int]:
    """Bucket the row's tool_calls aggregate into {grep, glob, find, read, ...}."""
    tc = row.get("tool_calls") or {}
    buckets: Counter = Counter()
    if isinstance(tc, dict):
        for name, count in tc.items():
            if not isinstance(count, int):
                continue
            buckets[_classify_tool(name)] += count
    return dict(buckets)


def _re_read_rate(row: dict[str, Any]) -> float | None:
    events = row.get("source_read_events")
    if events is None:
        return None
    paths = [e.get("path") for e in events if isinstance(e, dict) and e.get("path")]
    if not paths:
        return None
    counts = Counter(paths)
    repeated = sum(1 for path, n in counts.items() if n >= 2)
    return repeated / len(paths)


def _first_tool_bucket(row: dict[str, Any]) -> str | None:
    events = row.get("tool_call_events")
    if not events:
        return None
    first = events[0]
    if not isinstance(first, dict):
        return None
    return _classify_tool(first.get("tool", ""))


def _pack_read_precedence(row: dict[str, Any]) -> bool | None:
    """First event with non-null path begins with `.agent-context/`."""
    events = row.get("tool_call_events")
    if not events:
        return None
    for ev in events:
        if not isinstance(ev, dict):
            continue
        path = ev.get("path")
        if path:
            return path.startswith(PACK_PREFIX)
    return None


def _pack_current_paths_read(row: dict[str, Any]) -> int | None:
    """Distinct `.agent-context/current/*` paths the agent touched in tool_call_events.

    Simplified pack_utilization_rate: counts distinct pack-current paths read
    per task. The full intersection with files actually present in
    `.agent-context/current/` requires the source tree on disk, which the
    metrics tool deliberately does not load (keeps it stdlib + pure-data).
    """
    events = row.get("tool_call_events")
    if events is None:
        return None
    paths = {
        ev.get("path") for ev in events
        if isinstance(ev, dict) and isinstance(ev.get("path"), str)
        and ev["path"].startswith(PACK_CURRENT_PREFIX)
    }
    return len(paths)


def _ground_truth_required_recall(row: dict[str, Any]) -> float | None:
    required = row.get("ground_truth_required_paths")
    if not required:
        return None
    seen: set[str] = set()
    for c in row.get("citations") or []:
        p = c.get("path")
        if isinstance(p, str):
            seen.add(p)
    for ev in row.get("source_read_events") or []:
        if isinstance(ev, dict):
            p = ev.get("path")
            if isinstance(p, str):
                seen.add(p)
    hits = sum(1 for p in required if p in seen)
    return hits / len(required)


def _verification_shortcut_hit_rate(row: dict[str, Any]) -> float | None:
    """Fraction of the cell's verification-shortcut paths the agent actually read.

    The pack's `search_scope.json` lists path-targeted verification shortcuts
    per task family (e.g., "look at src/server.py for HelloHandler"). The
    extractor stamps that list onto each result as `verification_shortcut_paths`.
    Hit rate = how many of those the agent's source-read events actually
    touched. Null when the field is missing/empty (bare condition, or pre-v3).
    """
    shortcuts = row.get("verification_shortcut_paths")
    if not shortcuts:
        return None
    read_paths: set[str] = set()
    for ev in row.get("source_read_events") or []:
        if isinstance(ev, dict):
            p = ev.get("path")
            if isinstance(p, str):
                read_paths.add(p)
    hits = sum(1 for p in shortcuts if p in read_paths)
    return hits / len(shortcuts)


def _tokens_total_normalized(row: dict[str, Any], task_count: int) -> float | None:
    """Token total normalized for cell_replicated rows.

    cell_replicated means the same session total has been stamped on every
    one of the N task rows in the cell. To recover the session total when
    summing across rows, divide each row's tokens_total by N.
    """
    t = row.get("tokens_total")
    if not isinstance(t, int):
        return None
    if row.get("token_metric_scope") == "cell_replicated" and task_count:
        return t / task_count
    return float(t)


def _tokens_thinking_share(row: dict[str, Any]) -> float | None:
    thinking = row.get("tokens_thinking")
    total = row.get("tokens_total")
    if not isinstance(thinking, int) or not isinstance(total, int) or total <= 0:
        return None
    return thinking / total


# ---------------------------------------------------------------------------
# Cell aggregator — produces all 28 metrics
# ---------------------------------------------------------------------------

def compute_cell_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    yes, partial, no = _correctness_counts(rows)
    correct_denom = _correct_denom(yes, partial)

    # A. Outcome
    correctness_yes_rate = yes / n if n else None
    correctness_partial_rate = partial / n if n else None
    correctness_no_rate = no / n if n else None
    risk_flag_rate = (sum(1 for r in rows if r.get("risk_flag") is True) / n) if n else None
    citation_precision = _safe_mean([_citation_precision(r) for r in rows])

    # B. Speed
    durations = [r.get("duration_seconds") for r in rows if isinstance(r.get("duration_seconds"), (int, float))]
    duration_median = statistics.median(durations) if durations else None
    duration_mean = (sum(durations) / len(durations)) if durations else None
    seconds_per_correct = _safe_div(sum(durations), correct_denom) if durations else None
    ttfcf_median = _safe_median([_ttfcf_seconds(r) for r in rows])

    # C. Navigation efficiency
    hops_to_first_correct_file_median = _safe_median([
        r.get("first_correct_file_hop") for r in rows
    ])

    per_task_search_read_ratio: list[float | None] = []
    tool_call_totals: list[int] = []
    for r in rows:
        buckets = _tool_calls_by_bucket(r)
        searches = buckets.get("grep", 0) + buckets.get("glob", 0) + buckets.get("find", 0)
        reads = buckets.get("read", 0)
        per_task_search_read_ratio.append(_safe_div(searches, reads))
        total = _tool_calls_total(r)
        if total is not None:
            tool_call_totals.append(total)

    search_vs_read_ratio = _safe_mean(per_task_search_read_ratio)
    tool_calls_total_mean = (sum(tool_call_totals) / len(tool_call_totals)) if tool_call_totals else None
    tool_calls_per_correct = _safe_div(sum(tool_call_totals), correct_denom) if tool_call_totals else None

    re_read_rate = _safe_mean([_re_read_rate(r) for r in rows])

    first_tool_buckets = [b for b in (_first_tool_bucket(r) for r in rows) if b is not None]
    if first_tool_buckets:
        counter = Counter(first_tool_buckets)
        dominant, dominant_count = counter.most_common(1)[0]
        first_tool_call_type = {
            "dominant": dominant,
            "rate": dominant_count / len(first_tool_buckets),
            "distribution": dict(counter),
        }
    else:
        first_tool_call_type = None

    pack_read_flags = [v for v in (_pack_read_precedence(r) for r in rows) if v is not None]
    pack_read_precedence_rate = (
        sum(1 for v in pack_read_flags if v) / len(pack_read_flags)
        if pack_read_flags else None
    )

    pack_utilization_rate = _safe_mean([_pack_current_paths_read(r) for r in rows])

    verification_shortcut_hit_rate = _safe_mean([
        _verification_shortcut_hit_rate(r) for r in rows
    ])

    unique_source_files_opened_mean = _safe_mean([
        r.get("unique_source_paths_read") for r in rows
    ])
    dead_ends_mean = _safe_mean([r.get("dead_ends") for r in rows])
    post_hit_dead_ends_mean = _safe_mean([r.get("post_hit_dead_ends") for r in rows])

    # D. Output quality
    citations_count_mean = _safe_mean([
        len(r.get("citations") or []) for r in rows
    ])
    ground_truth_required_recall = _safe_mean([
        _ground_truth_required_recall(r) for r in rows
    ])

    # E. Cost / efficiency
    tokens_norm = [_tokens_total_normalized(r, n) for r in rows]
    tokens_norm_present = [t for t in tokens_norm if t is not None]
    if tokens_norm_present:
        tokens_total_per_correct = _safe_div(sum(tokens_norm_present), correct_denom)
    else:
        tokens_total_per_correct = None

    costs = [r.get("cost_usd") for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    cost_usd_per_correct = _safe_div(sum(costs), correct_denom) if costs else None

    tokens_thinking_share = _safe_mean([_tokens_thinking_share(r) for r in rows])

    # F. Operator friction
    permission_prompts_mean = _safe_mean([r.get("permission_prompts_count") for r in rows])
    interrupted_count = sum(1 for r in rows if r.get("interrupted") is True)
    interrupted_rate = interrupted_count / n if n else None

    return {
        # A
        "correctness_yes_rate": correctness_yes_rate,
        "correctness_partial_rate": correctness_partial_rate,
        "correctness_no_rate": correctness_no_rate,
        "risk_flag_rate": risk_flag_rate,
        "citation_precision": citation_precision,
        # B
        "duration_seconds_median": duration_median,
        "duration_seconds_mean": duration_mean,
        "seconds_per_correct": seconds_per_correct,
        "ttfcf_seconds_median": ttfcf_median,
        # C
        "hops_to_first_correct_file_median": hops_to_first_correct_file_median,
        "search_vs_read_ratio": search_vs_read_ratio,
        "tool_calls_total_mean": tool_calls_total_mean,
        "tool_calls_per_correct": tool_calls_per_correct,
        "re_read_rate": re_read_rate,
        "first_tool_call_type": first_tool_call_type,
        "pack_read_precedence_rate": pack_read_precedence_rate,
        "pack_utilization_rate": pack_utilization_rate,
        "verification_shortcut_hit_rate": verification_shortcut_hit_rate,
        "unique_source_files_opened_mean": unique_source_files_opened_mean,
        "dead_ends_mean": dead_ends_mean,
        "post_hit_dead_ends_mean": post_hit_dead_ends_mean,
        # D
        "citations_count_mean": citations_count_mean,
        "ground_truth_required_recall": ground_truth_required_recall,
        # E
        "tokens_total_per_correct": tokens_total_per_correct,
        "cost_usd_per_correct": cost_usd_per_correct,
        "tokens_thinking_share": tokens_thinking_share,
        # F
        "permission_prompts_mean": permission_prompts_mean,
        "interrupted_rate": interrupted_rate,
    }


# Metric-family layout for Markdown output.
METRIC_FAMILIES: list[tuple[str, list[str]]] = [
    ("A. Outcome", [
        "correctness_yes_rate",
        "correctness_partial_rate",
        "correctness_no_rate",
        "risk_flag_rate",
        "citation_precision",
    ]),
    ("B. Speed", [
        "duration_seconds_median",
        "duration_seconds_mean",
        "seconds_per_correct",
        "ttfcf_seconds_median",
    ]),
    ("C. Navigation efficiency", [
        "hops_to_first_correct_file_median",
        "search_vs_read_ratio",
        "tool_calls_total_mean",
        "tool_calls_per_correct",
        "re_read_rate",
        "first_tool_call_type",
        "pack_read_precedence_rate",
        "pack_utilization_rate",
        "verification_shortcut_hit_rate",
        "unique_source_files_opened_mean",
        "dead_ends_mean",
        "post_hit_dead_ends_mean",
    ]),
    ("D. Output quality", [
        "citations_count_mean",
        "ground_truth_required_recall",
    ]),
    ("E. Cost / efficiency", [
        "tokens_total_per_correct",
        "cost_usd_per_correct",
        "tokens_thinking_share",
    ]),
    ("F. Operator friction", [
        "permission_prompts_mean",
        "interrupted_rate",
    ]),
]


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def build_cell_records(
    rows_by_cell: dict[tuple[str, str, str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    # Sort: (agent, condition, repo, model_id) per spec.
    sorted_keys = sorted(rows_by_cell.keys(), key=lambda k: (k[0], k[2], k[3], k[1]))
    for key in sorted_keys:
        rows = rows_by_cell[key]
        agent, model_id, condition, repo = key
        cells.append({
            "agent": agent,
            "model_id": model_id,
            "condition": condition,
            "repo": repo,
            "task_count": len(rows),
            "metrics": compute_cell_metrics(rows),
        })
    return cells


def render_json(cells: list[dict[str, Any]]) -> str:
    payload = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cells": cells,
    }
    return json.dumps(payload, indent=2) + "\n"


def _fmt(v: Any) -> str:
    """Compact, readable cell value for Markdown tables."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        # Keep small floats readable; large ones round to 2 decimals.
        if abs(v) >= 100:
            return f"{v:.1f}"
        if abs(v) >= 1:
            return f"{v:.3f}"
        return f"{v:.4f}"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, dict):
        # first_tool_call_type → "read (0.83)"
        if "dominant" in v and "rate" in v:
            return f"{v['dominant']} ({v['rate']:.2f})"
        return json.dumps(v, sort_keys=True)
    return str(v)


def render_markdown(cells: list[dict[str, Any]]) -> str:
    lines: list[str] = ["# Derived Metrics", ""]
    if not cells:
        lines.append("_No cells found._")
        lines.append("")
        return "\n".join(lines)

    label_for = lambda c: f"{c['agent']}/{c['condition']}/{c['repo']} ({c['model_id'] or '—'})"

    for family_title, metric_names in METRIC_FAMILIES:
        lines.append(f"## {family_title}")
        lines.append("")
        header = ["cell"] + metric_names
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for c in cells:
            row = [label_for(c)] + [_fmt(c["metrics"].get(m)) for m in metric_names]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def aggregate(
    results_dir: pathlib.Path,
    cell_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    paths = discover_results(results_dir)
    rows_by_cell: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for p in paths:
        row = load_result(p)
        if row is None:
            continue
        rows_by_cell.setdefault(cell_key(row), []).append(row)

    rows_by_cell = filter_cells(rows_by_cell, cell_filter)

    # Drop empty cells and warn (covers the directory-existed-but-no-rows case).
    nonempty: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for key, rows in rows_by_cell.items():
        if not rows:
            print(f"WARN: empty cell skipped: {key}", file=sys.stderr)
            continue
        nonempty[key] = rows

    return build_cell_records(nonempty)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--results", required=True,
                        help="Directory containing per-rerun results (globbed: <dir>/*/results/*/*/*/*.json)")
    parser.add_argument("--out-json", help="Write aggregated metrics to this JSON file")
    parser.add_argument("--out-md", help="Write a Markdown table per metric family to this file")
    parser.add_argument("--cells", default="",
                        help="Comma-separated list of agent/condition/repo cells to include")
    args = parser.parse_args(argv)

    results_dir = pathlib.Path(args.results).expanduser().resolve()
    if not results_dir.is_dir():
        print(f"ERROR: results dir not found: {results_dir}", file=sys.stderr)
        return 1

    cell_filter = [c.strip() for c in args.cells.split(",") if c.strip()] or None
    cells = aggregate(results_dir, cell_filter)

    json_text = render_json(cells)
    if args.out_json:
        pathlib.Path(args.out_json).write_text(json_text)
        print(f"Wrote {args.out_json} ({len(cells)} cells)")
    else:
        sys.stdout.write(json_text)

    if args.out_md:
        pathlib.Path(args.out_md).write_text(render_markdown(cells))
        print(f"Wrote {args.out_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
