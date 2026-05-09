#!/usr/bin/env python3
"""extract-events-from-chorus.py — stamp the schema-v3 tool-call event stream onto result JSONs.

Companion to `extract-tokens-from-chorus.py`. Where that script summarises
per-cell token usage, this one walks each agent's native session log and
emits the schema-v3 event stream + the small set of derived stable fields
the schema specifies (so summarisers don't re-derive them every time):

  - tool_call_events          (raw ordered list of {tool, path, ts, args})
  - source_read_events        (filtered: path != null, not under .agent-context/)
  - unique_source_paths_read  (count of distinct source paths)
  - dead_end_paths            (read-but-not-cited / decoy paths)
  - first_correct_file_ts     (ISO-8601 ts of the first ground-truth hit)
  - tool_calls                (aggregate {tool: count} re-derived for consistency)

Coverage:
  - claude   ✅ (Claude Code session JSONL under ~/.claude/projects/.../<session>.jsonl)
  - codex    ⏳ separate extractor; codex session shape is different
  - cursor   ⏳ separate extractor; cursor IDE doesn't expose ordered tool events
  - opencode ⏳ separate extractor

Per-task processing:
  1. Locate the claude session JSONL for each (alias, condition, task) cell —
     same chorus-list strategy as extract-tokens-from-chorus.py.
  2. Walk the JSONL events. For each `tool_use` content block in an
     `assistant` envelope, capture:
       - tool = the tool name (Read, Bash, Grep, Glob, Edit, Write, ...)
       - path = the filesystem path the tool acted on, when applicable:
           Read / Edit / Write / NotebookEdit → input.file_path / input.notebook_path
           Bash → null (we don't try to parse `cat <path>` out of a shell command;
                  too noisy and the user's instructions for this script say null
                  unless trivially obvious — we keep it simple and emit null)
           Grep / Glob → null (search tools, no single path)
           other tools → null
       - ts = ISO-8601 timestamp from the message envelope
       - args = the raw input dict (preserved verbatim for debugging)
  3. Emit `tool_call_events` as the ordered list and derive stable fields.
  4. Stamp onto the result JSON for that task using json.dump.

Inputs (per task):
  - The session JSONL (resolved via chorus list, then read directly).
  - The result JSON to stamp onto.
  - The task's ground-truth path arrays (passed via --ground-truth-paths
    <task-id>=<path-to-json-or-md>). For tasks with no ground-truth
    available, first_correct_file_ts and dead_end_paths are left as null.

Edge cases:
  - A claude session with no tool_use events → tool_call_events = [],
    unique_source_paths_read = 0.
  - A path that's relative vs absolute → normalised relative-to-cwd before
    comparing to ground-truth paths. Symlinks are kept as-given.
  - A tool_use that's missing the timestamp → skipped with a warning;
    we don't crash the whole task on a single malformed event.
  - --ground-truth-paths file missing → skip those derivations, populate
    other fields.

Usage:
  scripts/experiments/extract-events-from-chorus.py \\
    --rerun ~/agent-context-reruns/q2-2026-private/agent-chorus

  # Optional: feed ground-truth path arrays for one or more tasks. The value
  # may be a JSON file (output of parse-ground-truth.py) or a GROUND_TRUTH.md
  # file (we'll detect by extension and parse on the fly).
  scripts/experiments/extract-events-from-chorus.py \\
    --rerun <path> \\
    --ground-truth-paths L1=/path/to/ground-truth.json \\
    --ground-truth-paths L2=/path/to/GROUND_TRUTH.md

  # Dry-run: print what would be stamped without writing
  scripts/experiments/extract-events-from-chorus.py --rerun <path> --dry-run

Stdlib-only, Python 3.8+. Requires `chorus` CLI on PATH (used only to
resolve the session JSONL path; actual event walking is direct JSONL parse).
"""

from __future__ import annotations

import argparse
import json
import re
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


SUPPORTED_AGENTS = {"claude"}  # codex/cursor/opencode get their own extractors after smoke

# Tools whose input dict carries a single source-file path we can attribute to.
# Order matters here only insofar as we look these keys up in order; the first
# hit wins.
PATH_INPUT_KEYS_BY_TOOL: Dict[str, Tuple[str, ...]] = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "MultiEdit": ("file_path",),
    "NotebookEdit": ("notebook_path",),
}


# --- chorus helpers (mirror style of extract-tokens-from-chorus.py) ----------

def chorus_list(agent: str, cwd: str) -> List[Dict[str, Any]]:
    """Run `chorus list --agent <agent> --cwd <cwd> --json` and return parsed list."""
    try:
        out = subprocess.check_output(
            ["chorus", "list", "--agent", agent, "--cwd", cwd, "--json"],
            text=True, stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        print(f"WARN: chorus list failed for agent={agent}: {exc.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        print(f"WARN: chorus list returned non-JSON for agent={agent}: {exc}", file=sys.stderr)
        return []


def find_session_jsonl_for_cell(
    agent: str,
    cwd: str,
    started_window: Optional[Tuple[str, str]],
) -> Optional[Dict[str, Any]]:
    """Find the chorus session that covers the experiment window for this cell.

    Returns the chorus list entry (which includes `file_path` for claude sessions),
    or None if nothing matches.
    """
    sessions = chorus_list(agent, cwd)
    if not sessions:
        return None
    sessions.sort(
        key=lambda s: s.get("modified_at") or s.get("started_at") or s.get("created_at") or "",
        reverse=True,
    )
    if started_window:
        start, _end = started_window
        for s in sessions:
            ts = s.get("started_at") or s.get("modified_at") or s.get("created_at") or ""
            if ts >= start:
                return s
    return sessions[0]


# --- JSONL walking ----------------------------------------------------------

def extract_path_from_tool_input(tool: str, tool_input: Dict[str, Any]) -> Optional[str]:
    """Pull the single source-file path out of a tool input dict, if applicable.

    Returns None for tools we don't attribute a single path to (Bash, Grep,
    Glob, Task, WebFetch, MCP tools, …). The caller treats those as path=null
    in the event stream.
    """
    if not isinstance(tool_input, dict):
        return None
    for key in PATH_INPUT_KEYS_BY_TOOL.get(tool, ()):
        v = tool_input.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def walk_claude_session_events(jsonl_path: pathlib.Path) -> List[Dict[str, Any]]:
    """Parse a Claude Code session JSONL and return tool-call events.

    Each returned event has keys: tool, path, ts, args. Events with no
    timestamp are skipped (with a warning to stderr).
    """
    events: List[Dict[str, Any]] = []
    if not jsonl_path.is_file():
        print(f"WARN: session JSONL not found: {jsonl_path}", file=sys.stderr)
        return events

    with jsonl_path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Malformed line — keep going; chorus does the same.
                print(f"WARN: {jsonl_path.name}:{lineno} malformed JSON; skipping", file=sys.stderr)
                continue
            if obj.get("type") != "assistant":
                continue
            ts = obj.get("timestamp")
            msg = obj.get("message") or {}
            content = msg.get("content") or []
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                tool = block.get("name")
                if not isinstance(tool, str):
                    continue
                if not isinstance(ts, str) or not ts:
                    print(
                        f"WARN: {jsonl_path.name}:{lineno} tool_use missing timestamp; skipping",
                        file=sys.stderr,
                    )
                    continue
                tool_input = block.get("input") or {}
                path = extract_path_from_tool_input(tool, tool_input if isinstance(tool_input, dict) else {})
                events.append({
                    "tool": tool,
                    "path": path,
                    "ts": ts,
                    "args": tool_input if isinstance(tool_input, dict) else {},
                })
    return events


# --- Derivations ------------------------------------------------------------

def normalise_path(path: str, cwd: Optional[str]) -> str:
    """Best-effort: turn an absolute path under cwd into a cwd-relative path.

    No symlink resolution (per spec). Returns the input unchanged if it's
    already relative or doesn't share the cwd prefix.
    """
    if not cwd or not path or not os.path.isabs(path):
        return path
    try:
        rel = os.path.relpath(path, cwd)
    except ValueError:
        return path
    # Don't escape upward into absolute-y territory; if the relpath starts
    # with .. it's outside the cwd and we leave it alone.
    if rel.startswith(".."):
        return path
    return rel


def is_under_agent_context(path: str) -> bool:
    """True when the path is inside `.agent-context/` (relative or absolute form)."""
    if not path:
        return False
    # Relative form.
    if path.startswith(".agent-context/") or path == ".agent-context":
        return True
    # Absolute form: anywhere in the path components.
    parts = pathlib.PurePath(path).parts
    return ".agent-context" in parts


def derive_source_read_events(
    events: List[Dict[str, Any]],
    cwd: Optional[str],
) -> List[Dict[str, Any]]:
    """Filter to events with path != null AND path NOT under .agent-context/."""
    out: List[Dict[str, Any]] = []
    for ev in events:
        p = ev.get("path")
        if not p:
            continue
        rel = normalise_path(p, cwd)
        if is_under_agent_context(rel):
            continue
        # Keep the event as-is but normalise the path field for downstream
        # comparisons. We preserve raw `args` for debugging.
        out.append({
            "tool": ev["tool"],
            "path": rel,
            "ts": ev["ts"],
            "args": ev.get("args", {}),
        })
    return out


def derive_unique_source_paths(source_read_events: List[Dict[str, Any]]) -> int:
    return len({ev["path"] for ev in source_read_events if ev.get("path")})


def derive_first_correct_file_ts(
    source_read_events: List[Dict[str, Any]],
    required_paths: Optional[List[str]],
) -> Optional[str]:
    """Earliest ts of an event whose path is in required_paths.

    Returns None when required_paths is None/empty or no event matched.
    """
    if not required_paths:
        return None
    required = set(required_paths)
    for ev in source_read_events:  # already in arrival order
        if ev.get("path") in required:
            return ev.get("ts")
    return None


def derive_dead_end_paths(
    source_read_events: List[Dict[str, Any]],
    required_paths: Optional[List[str]],
    optional_paths: Optional[List[str]],
    citations: Optional[List[Dict[str, Any]]],
) -> Optional[List[str]]:
    """Heuristic: a dead-end path is one the agent read but didn't credit.

    Concretely: paths in source_read_events that are NOT in
    (ground_truth_required_paths ∪ ground_truth_optional_paths ∪ cited paths).
    Decoy paths are intentionally NOT in the allow-list — reading a decoy
    counts as a dead end (matches the schema description).

    Returns None when we have neither ground-truth paths nor citations to
    compare against — there's no signal to compute against.
    """
    if not required_paths and not optional_paths and not citations:
        return None
    allow: set = set()
    if required_paths:
        allow.update(required_paths)
    if optional_paths:
        allow.update(optional_paths)
    if citations:
        for c in citations:
            if isinstance(c, dict):
                p = c.get("path")
                if isinstance(p, str) and p:
                    allow.add(p)
    seen: set = set()
    out: List[str] = []
    for ev in source_read_events:
        p = ev.get("path")
        if not p or p in seen:
            continue
        seen.add(p)
        if p not in allow:
            out.append(p)
    return out


def derive_tool_calls_count(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Aggregate {tool: count} from the event stream."""
    counts: Dict[str, int] = {}
    for ev in events:
        tool = ev.get("tool")
        if not isinstance(tool, str):
            continue
        counts[tool] = counts.get(tool, 0) + 1
    return counts


# --- Per-task segmentation -------------------------------------------------

# Schema task_ids: {L1, L2, M1, M2, H1, H2}. The lane prompt asks the agent
# to write one result JSON per task at `../results/<agent>/<condition>/[<model>/]<task>.json`.
# Each Write to a `<task>.json` path marks the END of that task's events.
TASK_RESULT_FILE_RE = re.compile(r"(?:^|/)(L1|L2|M1|M2|H1|H2)\.json$")
TASK_WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}


def load_verification_shortcut_paths(cell_cwd: pathlib.Path) -> Optional[List[str]]:
    """Pull the cell's verification shortcut paths from search_scope.json.

    Each task family in `<cwd>/.agent-context/current/search_scope.json` carries
    a `verification_shortcuts` array; each entry's `file` is a path the agent
    is expected to consult to verify a hypothesis. The union of those paths
    (deduped, in first-seen order) becomes `verification_shortcut_paths`.

    Returns None when the pack isn't present (bare condition or pre-init repo).
    Returns [] when the pack is present but defines no shortcuts.
    """
    scope_path = cell_cwd / ".agent-context" / "current" / "search_scope.json"
    if not scope_path.is_file():
        return None
    try:
        data = json.loads(scope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    families = data.get("task_families")
    if not isinstance(families, dict):
        return []
    seen: set = set()
    out: List[str] = []
    for fam in families.values():
        if not isinstance(fam, dict):
            continue
        for sc in fam.get("verification_shortcuts") or []:
            if not isinstance(sc, dict):
                continue
            p = sc.get("file")
            if not isinstance(p, str) or not p or p in seen:
                continue
            seen.add(p)
            out.append(p)
    return out


def segment_events_by_task(events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Split a cell-level event stream into per-task chunks.

    The lane runs all 6 tasks in ONE agent session, so events captured by
    `walk_claude_session_events` are cell-level. Per-task derived metrics
    (TTFCF, first-tool-type, re-read rate, pack-read precedence) require
    per-task event slices.

    Strategy: each Write/Edit to `<task_id>.json` marks the boundary for
    that task. All events accumulated since the last boundary (including
    the boundary write itself) belong to the task being written.

    Tasks that are rewritten across the session accumulate events from
    every write — extend (not overwrite) so we don't lose work that
    happened between rewrites. Trailing events with no boundary are
    dropped (they belong to no task — e.g., the agent stopped early).
    """
    segments: Dict[str, List[Dict[str, Any]]] = {}
    pending: List[Dict[str, Any]] = []
    for ev in events:
        pending.append(ev)
        if ev.get("tool") not in TASK_WRITE_TOOLS:
            continue
        path = ev.get("path")
        if not isinstance(path, str):
            continue
        m = TASK_RESULT_FILE_RE.search(path)
        if not m:
            continue
        tid = m.group(1)
        # Multiple writes to the same task → accumulate, don't overwrite.
        segments.setdefault(tid, []).extend(pending)
        pending = []
    return segments


# --- Ground-truth path loading ---------------------------------------------

def load_ground_truth_paths(spec: str) -> Tuple[str, Dict[str, List[str]]]:
    """Parse a `--ground-truth-paths <task-id>=<file>` spec.

    Accepts:
      - JSON file (output of parse-ground-truth.py) — either the full
        per-task map or a single-task dict already.
      - .md file — invoked through parse-ground-truth.py via Python import
        (kept simple: we shell out to the script if it's adjacent).

    Returns (task_id, {"required":[...], "optional":[...], "decoy":[...]}).
    Raises on parse failure.
    """
    if "=" not in spec:
        raise ValueError(f"--ground-truth-paths expects task-id=path, got: {spec!r}")
    task_id, path_str = spec.split("=", 1)
    task_id = task_id.strip()
    src = pathlib.Path(path_str).expanduser()
    if not src.is_file():
        raise FileNotFoundError(f"ground-truth path not found: {src}")
    if src.suffix.lower() == ".json":
        data = json.loads(src.read_text(encoding="utf-8"))
        # If it's a per-task map, pull this task's entry.
        if isinstance(data, dict) and task_id in data and isinstance(data[task_id], dict):
            entry = data[task_id]
        elif isinstance(data, dict) and ("required" in data or "optional" in data or "decoy" in data):
            entry = data
        else:
            raise ValueError(
                f"ground-truth JSON for task {task_id!r} doesn't match expected shape"
            )
        return task_id, {
            "required": list(entry.get("required") or []),
            "optional": list(entry.get("optional") or []),
            "decoy": list(entry.get("decoy") or []),
        }
    # .md → fall back to parse-ground-truth.py (keeps single source of truth).
    parser_path = pathlib.Path(__file__).parent / "parse-ground-truth.py"
    if not parser_path.is_file():
        raise FileNotFoundError(
            f"can't parse {src.name}: parse-ground-truth.py not next to this script"
        )
    out = subprocess.check_output(
        [sys.executable, str(parser_path), str(src), "--task-id", task_id],
        text=True,
    )
    data = json.loads(out)
    if task_id not in data:
        raise ValueError(f"task {task_id!r} not found in {src}")
    entry = data[task_id]
    return task_id, {
        "required": list(entry.get("required") or []),
        "optional": list(entry.get("optional") or []),
        "decoy": list(entry.get("decoy") or []),
    }


# --- Stamping ---------------------------------------------------------------

def stamp_result(
    result_path: pathlib.Path,
    events: List[Dict[str, Any]],
    cwd: Optional[str],
    ground_truth: Optional[Dict[str, List[str]]],
    verification_shortcut_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute derivations and write them onto `result_path`.

    Returns the final dict (post-stamp) for inspection. Idempotent — running
    twice with the same inputs yields byte-identical output.
    """
    data = json.loads(result_path.read_text(encoding="utf-8"))
    citations = data.get("citations") if isinstance(data.get("citations"), list) else None

    source_reads = derive_source_read_events(events, cwd)
    unique_count = derive_unique_source_paths(source_reads)

    required = ground_truth["required"] if ground_truth else None
    optional = ground_truth["optional"] if ground_truth else None
    decoy = ground_truth["decoy"] if ground_truth else None

    first_correct_ts = derive_first_correct_file_ts(source_reads, required)
    dead_ends = derive_dead_end_paths(source_reads, required, optional, citations)

    data["tool_call_events"] = events
    data["source_read_events"] = source_reads
    data["unique_source_paths_read"] = unique_count
    data["first_correct_file_ts"] = first_correct_ts
    data["dead_end_paths"] = dead_ends
    # Re-derive the aggregate count dict for consistency with the event stream.
    data["tool_calls"] = derive_tool_calls_count(events)
    if ground_truth is not None:
        data["ground_truth_required_paths"] = required
        data["ground_truth_optional_paths"] = optional
        data["ground_truth_decoy_paths"] = decoy
    # verification_shortcut_paths is per-cell; pass-through whatever the caller
    # resolved (None for bare condition, list otherwise).
    if verification_shortcut_paths is not None:
        data["verification_shortcut_paths"] = verification_shortcut_paths
    return data


def write_result(result_path: pathlib.Path, data: Dict[str, Any]) -> None:
    result_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# --- CLI --------------------------------------------------------------------

def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--rerun", required=True, help="Rerun directory containing _provenance.json + results/")
    parser.add_argument("--agents", default="claude", help="Comma-separated agent names to process (default: claude)")
    parser.add_argument(
        "--ground-truth-paths",
        action="append",
        default=[],
        metavar="TASK=FILE",
        help="Ground-truth path arrays for a task. Repeat per task. "
             "FILE may be JSON (parse-ground-truth.py output) or GROUND_TRUTH.md.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print would-stamp values; do not modify result JSONs")
    args = parser.parse_args(argv)

    if not shutil.which("chorus"):
        print("ERROR: chorus CLI not on PATH", file=sys.stderr)
        return 1

    rerun = pathlib.Path(args.rerun).expanduser().resolve()
    if not rerun.is_dir():
        print(f"ERROR: rerun dir not found: {rerun}", file=sys.stderr)
        return 1

    prov_path = rerun / "_provenance.json"
    if not prov_path.exists():
        print(f"ERROR: _provenance.json not found at {prov_path}", file=sys.stderr)
        return 1
    prov = json.loads(prov_path.read_text())
    started = prov.get("prepared_at", "")

    # Parse ground-truth specs once.
    gt_by_task: Dict[str, Dict[str, List[str]]] = {}
    for spec in args.ground_truth_paths:
        try:
            tid, payload = load_ground_truth_paths(spec)
        except (ValueError, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
            print(f"WARN: skipping --ground-truth-paths {spec!r}: {exc}", file=sys.stderr)
            continue
        gt_by_task[tid] = payload

    requested_agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    skipped_agents: List[str] = []
    stamped_tasks = 0
    seen_sessions: Dict[Tuple[str, str], str] = {}

    for agent in requested_agents:
        if agent not in SUPPORTED_AGENTS:
            skipped_agents.append(agent)
            continue
        for condition in ("bare", "structured_fresh"):
            cell_dir = rerun / "results" / agent / condition
            if not cell_dir.is_dir():
                continue
            results = sorted(p for p in cell_dir.glob("*.json") if not p.name.endswith(".judge.json"))
            if not results:
                continue

            cell_cwd = str((rerun / condition).resolve())
            session = find_session_jsonl_for_cell(agent, cell_cwd, (started, ""))
            if not session:
                print(f"  [{agent}/{condition}] no chorus session found for cwd={cell_cwd}")
                continue
            session_id = session.get("session_id") or session.get("id")
            if not session_id:
                print(f"  [{agent}/{condition}] session has no id")
                continue
            duplicate = [cond for (seen_agent, cond), sid in seen_sessions.items() if seen_agent == agent and sid == session_id]
            if duplicate:
                print(
                    f"  [{agent}/{condition}] WARN: session {session_id} already used for {agent}/{duplicate[0]}; "
                    "not stamping to avoid mixing condition-level event metrics",
                    file=sys.stderr,
                )
                continue
            seen_sessions[(agent, condition)] = session_id

            jsonl_path_str = session.get("file_path")
            if not jsonl_path_str:
                print(f"  [{agent}/{condition}] chorus list entry missing file_path; cannot read events", file=sys.stderr)
                continue
            jsonl_path = pathlib.Path(jsonl_path_str)
            events = walk_claude_session_events(jsonl_path)

            # Segment the cell-level event stream into per-task slices using
            # Write-to-result-json boundaries. Without this, every task in the
            # cell would be stamped with the full session's events and per-task
            # metrics (TTFCF, first-tool-type, re-read rate, pack-read precedence)
            # would be cell-level data masquerading as per-task data.
            segments = segment_events_by_task(events)

            print(
                f"  [{agent}/{condition}] cwd={cell_cwd} session={session_id} "
                f"events={len(events)} segments={sorted(segments.keys())} "
                f"jsonl={jsonl_path.name}"
            )

            if args.dry_run:
                continue

            # Per-cell verification shortcut paths come from the pack's
            # search_scope.json — same value stamped on every task in the cell.
            shortcut_paths = load_verification_shortcut_paths(pathlib.Path(cell_cwd))

            for rp in results:
                tid = rp.stem  # e.g. "L1.json" → "L1"
                task_events = segments.get(tid)
                if task_events is None:
                    print(
                        f"  [{agent}/{condition}/{tid}] WARN: no segment found "
                        f"(agent never wrote {tid}.json in this session); skipping",
                        file=sys.stderr,
                    )
                    continue
                gt = gt_by_task.get(tid)
                stamped = stamp_result(
                    rp, task_events, cwd=cell_cwd, ground_truth=gt,
                    verification_shortcut_paths=shortcut_paths,
                )
                write_result(rp, stamped)
                stamped_tasks += 1

    print(f"\nStamped: {stamped_tasks} tasks")
    if skipped_agents:
        print(
            f"Skipped (not in SUPPORTED_AGENTS): {', '.join(skipped_agents)}  — "
            "claude-only for now; codex/cursor extractors come after smoke runs"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
