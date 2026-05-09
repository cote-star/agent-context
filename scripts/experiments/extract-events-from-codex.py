#!/usr/bin/env python3
"""extract-events-from-codex.py — stamp the schema-v3 tool-call event stream onto codex result JSONs.

Codex counterpart to `extract-events-from-chorus.py`. The shape of a codex
session JSONL is different from a Claude Code session, so the JSONL walker is
codex-specific. Everything downstream (segmentation by Write boundaries,
derived stable fields, ground-truth handling, stamping) re-uses the chorus
extractor's helpers via importlib so the two scripts can never drift.

Codex session JSONL format (under ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl):
  - Each line is a JSON object with top-level `timestamp`, `type`, `payload`.
  - Types observed: `session_meta`, `event_msg`, `response_item`,
    `turn_context`.
  - Shell tool calls are `type: "response_item"`, `payload.type:
    "function_call"`, `payload.name: "exec_command"`, `payload.arguments`
    a stringified JSON containing keys `cmd` (the shell command), `workdir`,
    `yield_time_ms`, `max_output_tokens`. `cmd` is what the agent ran via zsh.
  - File patches are `type: "response_item"`, `payload.type:
    "custom_tool_call"`, `payload.name: "apply_patch"`, `payload.input` a
    string with the patch body (envelope markers `*** Add File: <path>`,
    `*** Update File: <path>`, `*** Delete File: <path>`).

Path-extraction strategy (codex runs everything via shell, so we parse `cmd`):
  - sed -n '<range>p' <path>          → tool=Read,  path=<path>
  - cat <path>  /  cat -- <path>      → tool=Read,  path=<path>
  - head <path>  /  tail <path>       → tool=Read,  path=<path>
  - nl -ba <path>                     → tool=Read,  path=<path>
  - grep <opts> <pattern> <path>      → tool=Grep,  path=<path>
  - rg   <opts> <pattern> <path>      → tool=Grep,  path=<path>
  - find <path> ...                   → tool=Glob,  path=<path>
  - ls   <path>                       → tool=LS,    path=<path>
  - cat > <p> <<EOF / tee <p> /
    echo … > <p> / printf … > <p>     → tool=Write, path=<p>
  - apply_patch (custom_tool_call)    → tool=Write, path=<file in patch body>
                                        when single-file; otherwise emitted as
                                        one Write event per file in the patch.
  - anything else                     → tool=Bash,  path=null

The path-extraction heuristics are pragmatic, not a full shell parser.
Compound commands (`a && b`, `a; b`, pipelines) are treated as a single Bash
event unless the leading verb matches a recognised pattern; this matches the
chorus extractor's "we don't try to parse shell" stance — codex is just noisier
because every read is a shell call.

Per-cell session resolution (no chorus dependency):
  - Walk recent files under ~/.codex/sessions/YYYY/MM/DD/.
  - Read each session's `session_meta.payload.cwd` and match against the
    cell's cwd (`<rerun>/<condition>`).
  - Prefer the latest session by mtime when multiple match.
  - Dedup by session id so the same session is never stamped onto more than
    one cell (mirrors the chorus extractor's seen_sessions dict).

Usage:
  scripts/experiments/extract-events-from-codex.py \\
    --rerun ~/agent-context-reruns/q2-2026-private/agent-chorus

  # Optional: feed ground-truth path arrays for one or more tasks.
  scripts/experiments/extract-events-from-codex.py \\
    --rerun <path> \\
    --ground-truth-paths L1=/path/to/ground-truth.json

  # Dry-run: print what would be stamped without writing
  scripts/experiments/extract-events-from-codex.py --rerun <path> --dry-run

Stdlib-only, Python 3.8+. No `chorus` dependency.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import shlex
import sys
from typing import Any, Dict, List, Optional, Tuple


# --- Reuse chorus helpers (single source of truth) --------------------------

_CHORUS_SCRIPT = pathlib.Path(__file__).resolve().parent / "extract-events-from-chorus.py"


def _load_chorus_module():
    spec = importlib.util.spec_from_file_location("extract_events_from_chorus", _CHORUS_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"could not spec-load {_CHORUS_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_CHORUS = _load_chorus_module()

# Re-export so callers/tests can use them off this module too.
derive_source_read_events = _CHORUS.derive_source_read_events
derive_unique_source_paths = _CHORUS.derive_unique_source_paths
derive_first_correct_file_ts = _CHORUS.derive_first_correct_file_ts
derive_dead_end_paths = _CHORUS.derive_dead_end_paths
derive_tool_calls_count = _CHORUS.derive_tool_calls_count
load_verification_shortcut_paths = _CHORUS.load_verification_shortcut_paths
load_ground_truth_paths = _CHORUS.load_ground_truth_paths
segment_events_by_task = _CHORUS.segment_events_by_task
stamp_result = _CHORUS.stamp_result
write_result = _CHORUS.write_result


# --- Codex session location ------------------------------------------------

DEFAULT_CODEX_SESSIONS_ROOT = pathlib.Path.home() / ".codex" / "sessions"


def iter_codex_session_files(root: pathlib.Path) -> List[pathlib.Path]:
    """Return all rollout-*.jsonl files under ~/.codex/sessions/YYYY/MM/DD/.

    Sorted newest-first by mtime so callers can short-circuit.
    """
    if not root.is_dir():
        return []
    out: List[pathlib.Path] = []
    for p in root.rglob("rollout-*.jsonl"):
        if p.is_file():
            out.append(p)
    out.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return out


def read_session_meta(jsonl_path: pathlib.Path) -> Optional[Dict[str, Any]]:
    """Read just the first non-blank line of a codex session JSONL — the
    session_meta entry — and return its payload dict (with `id`, `cwd`,
    `timestamp` etc).

    Returns None if the file is empty / unreadable / first line isn't
    session_meta. We don't crash on malformed sessions — agents in the wild
    sometimes write partial files.
    """
    try:
        with jsonl_path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line, strict=False)
                except json.JSONDecodeError:
                    return None
                if obj.get("type") != "session_meta":
                    return None
                pl = obj.get("payload")
                if isinstance(pl, dict):
                    return pl
                return None
    except OSError:
        return None
    return None


def find_codex_session_for_cell(
    cell_cwd: str,
    sessions_root: pathlib.Path = DEFAULT_CODEX_SESSIONS_ROOT,
    seen_session_ids: Optional[set] = None,
) -> Optional[Dict[str, Any]]:
    """Pick the most-recent codex session whose session_meta.cwd matches
    `cell_cwd` (resolved via realpath equivalence).

    Returns a dict shaped like {"file_path": str, "session_id": str,
    "timestamp": str, "cwd": str} so call-sites mirror the chorus extractor's
    session-entry contract. Returns None when no match is found.

    `seen_session_ids` is consulted (read-only) to skip sessions already used
    for another cell — the caller mutates the set after committing.
    """
    target = os.path.realpath(cell_cwd)
    files = iter_codex_session_files(sessions_root)
    for f in files:
        meta = read_session_meta(f)
        if not meta:
            continue
        cwd = meta.get("cwd")
        if not isinstance(cwd, str):
            continue
        try:
            if os.path.realpath(cwd) != target:
                continue
        except OSError:
            continue
        sid = meta.get("id") or meta.get("session_id")
        if seen_session_ids and sid in seen_session_ids:
            continue
        return {
            "file_path": str(f),
            "session_id": sid,
            "timestamp": meta.get("timestamp"),
            "cwd": cwd,
        }
    return None


# --- Path extraction from shell commands -----------------------------------

# Verbs whose first non-flag positional arg is a single readable path.
READ_VERBS = {"sed", "cat", "head", "tail", "nl", "less", "more", "bat"}
SEARCH_VERBS = {"grep", "rg", "ack", "ag"}
GLOB_VERBS = {"find", "fd"}
LS_VERBS = {"ls", "tree"}


def _split_argv(cmd: str) -> List[str]:
    """Best-effort shell-split. Falls back to whitespace split on shlex errors."""
    try:
        return shlex.split(cmd, posix=True)
    except ValueError:
        return cmd.split()


def _looks_like_path(tok: str) -> bool:
    """Crude positional-vs-flag check. We only care about distinguishing
    `--include`-style flags from real paths; the path can be relative or
    absolute, contain `/` or be a bare filename."""
    if not tok:
        return False
    if tok.startswith("-"):
        return False
    return True


def _last_positional(argv: List[str], skip_first: int = 1) -> Optional[str]:
    """Return the last positional argument in argv, skipping the verb and any
    flag/value pairs along the way. Heuristic: walk from the right and return
    the first token that isn't a flag (doesn't start with -)."""
    for tok in reversed(argv[skip_first:]):
        if _looks_like_path(tok):
            return tok
    return None


def _first_positional_after_pattern(argv: List[str], skip_first: int = 1) -> Optional[str]:
    """For grep/rg shape `<verb> <flags…> <pattern> <path?>`. We want the
    last positional (the path); pattern + path are both positional, so we
    return the second positional from the front. If only one positional
    exists, it's the pattern (search across cwd) → no path.
    """
    positionals: List[str] = []
    skip_value = False
    for tok in argv[skip_first:]:
        if skip_value:
            skip_value = False
            continue
        if tok.startswith("--") and "=" not in tok:
            # long flag without value — could take next token, but rg/grep
            # are mostly `--name=value`; assume no value.
            continue
        if tok.startswith("-") and not tok.startswith("--"):
            # short flag combo; assume no value (rg's flags-with-values
            # like -g use --glob= form usually). Imperfect but pragmatic.
            continue
        positionals.append(tok)
    if len(positionals) >= 2:
        return positionals[-1]
    return None


# `cat > path`, `cat >> path`, `tee path`, `echo … > path`, `printf … > path`.
# The trailing `<<EOF` / `<<'EOF'` is allowed but irrelevant.
_REDIRECT_RE = re.compile(r">>?\s*([^\s<>|;&]+)")


def _extract_redirect_target(cmd: str) -> Optional[str]:
    """Return the path to the right of the FIRST > or >> redirection, when
    the command starts with a verb that's commonly used for writes
    (`cat`, `tee`, `echo`, `printf`). Returns None otherwise so plain reads
    that happen to redirect output (e.g. `grep foo bar > /tmp/x`) aren't
    misclassified.
    """
    head = cmd.lstrip().split(None, 1)
    if not head:
        return None
    verb = head[0]
    if verb not in {"cat", "tee", "echo", "printf"}:
        return None
    m = _REDIRECT_RE.search(cmd)
    if not m:
        return None
    return m.group(1)


def classify_shell_command(cmd: str) -> Tuple[str, Optional[str]]:
    """Return (tool, path) for a single codex `cmd` string.

    `tool` is one of: "Read", "Grep", "Glob", "LS", "Write", "Bash".
    `path` is the extracted target path or None.
    """
    if not isinstance(cmd, str) or not cmd.strip():
        return ("Bash", None)

    # Write-via-redirect first: it overrides the verb classification because
    # `cat <path>` is a Read but `cat > <path>` is a Write.
    redir = _extract_redirect_target(cmd)
    if redir:
        return ("Write", redir)

    argv = _split_argv(cmd)
    if not argv:
        return ("Bash", None)
    verb = argv[0]
    # Strip command prefixes like `sudo`, `time`, `nice` so the verb is the
    # actual program. We keep this very conservative.
    while verb in {"sudo", "time", "nice", "env"} and len(argv) >= 2:
        argv = argv[1:]
        verb = argv[0]

    if verb in READ_VERBS:
        path = _last_positional(argv)
        if path:
            return ("Read", path)
        return ("Bash", None)
    if verb in SEARCH_VERBS:
        path = _first_positional_after_pattern(argv)
        return ("Grep", path)
    if verb in GLOB_VERBS:
        # `find <path> …` — first positional after verb (or "." default)
        for tok in argv[1:]:
            if _looks_like_path(tok):
                return ("Glob", tok)
            break
        return ("Glob", None)
    if verb in LS_VERBS:
        for tok in argv[1:]:
            if _looks_like_path(tok):
                return ("LS", tok)
        return ("LS", None)
    return ("Bash", None)


# --- apply_patch parsing ---------------------------------------------------

# Codex's apply_patch envelope uses `*** Add File: …`, `*** Update File: …`,
# `*** Delete File: …` markers. The standard unified-diff lines (`+++`,
# `---`) also appear inside Update sections. We accept either form.
_PATCH_FILE_RE = re.compile(
    r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s+(.+?)\s*$",
    re.MULTILINE,
)
_DIFF_PLUS_RE = re.compile(r"^\+\+\+\s+(?:b/)?(.+?)\s*$", re.MULTILINE)


def extract_apply_patch_paths(patch_body: str) -> List[str]:
    """Pull every patched file path out of a codex apply_patch input body.

    Returns paths in arrival order, deduped while preserving order. Empty
    list when nothing parses.
    """
    if not isinstance(patch_body, str) or not patch_body:
        return []
    out: List[str] = []
    seen: set = set()
    for m in _PATCH_FILE_RE.finditer(patch_body):
        p = m.group(1).strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    if out:
        return out
    # Fall back to unified-diff +++ markers.
    for m in _DIFF_PLUS_RE.finditer(patch_body):
        p = m.group(1).strip()
        if p == "/dev/null":
            continue
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


# --- JSONL walker -----------------------------------------------------------

def walk_codex_session_events(jsonl_path: pathlib.Path) -> List[Dict[str, Any]]:
    """Parse a codex session JSONL and emit tool-call events.

    Each event has keys: tool, path, ts, args. Events with no usable
    timestamp are skipped (with a stderr warning) — same policy as the
    chorus walker.

    apply_patch envelopes that touch multiple files emit one Write event per
    file (sharing the envelope's timestamp) so segmentation can attribute
    each task-write boundary correctly.
    """
    events: List[Dict[str, Any]] = []
    if not jsonl_path.is_file():
        print(f"WARN: codex session JSONL not found: {jsonl_path}", file=sys.stderr)
        return events

    with jsonl_path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line, strict=False)
            except json.JSONDecodeError:
                print(f"WARN: {jsonl_path.name}:{lineno} malformed JSON; skipping", file=sys.stderr)
                continue
            if obj.get("type") != "response_item":
                continue
            ts = obj.get("timestamp")
            payload = obj.get("payload") or {}
            if not isinstance(payload, dict):
                continue

            ptype = payload.get("type")
            if ptype == "function_call":
                name = payload.get("name")
                if name != "exec_command":
                    # write_stdin and other shapes don't carry a path; skip
                    # rather than mislabel.
                    continue
                if not isinstance(ts, str) or not ts:
                    print(
                        f"WARN: {jsonl_path.name}:{lineno} function_call missing timestamp; skipping",
                        file=sys.stderr,
                    )
                    continue
                args_raw = payload.get("arguments") or "{}"
                try:
                    args = json.loads(args_raw, strict=False) if isinstance(args_raw, str) else (args_raw or {})
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                cmd = args.get("cmd") or ""
                tool, path = classify_shell_command(cmd)
                events.append({
                    "tool": tool,
                    "path": path,
                    "ts": ts,
                    "args": args,
                })
                continue

            if ptype == "custom_tool_call" and payload.get("name") == "apply_patch":
                if not isinstance(ts, str) or not ts:
                    print(
                        f"WARN: {jsonl_path.name}:{lineno} apply_patch missing timestamp; skipping",
                        file=sys.stderr,
                    )
                    continue
                patch_body = payload.get("input") or ""
                paths = extract_apply_patch_paths(patch_body)
                if not paths:
                    # Couldn't parse a path — emit one Edit event so the
                    # caller still sees the operation in the event stream.
                    events.append({
                        "tool": "Edit",
                        "path": None,
                        "ts": ts,
                        "args": {"patch": patch_body[:200]},
                    })
                    continue
                for p in paths:
                    events.append({
                        "tool": "Write",
                        "path": p,
                        "ts": ts,
                        "args": {"patch_target": p},
                    })
                continue

            # Other response_item subtypes (message, reasoning,
            # function_call_output, custom_tool_call_output) carry no path
            # — ignore them.
    return events


# --- CLI --------------------------------------------------------------------

def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--rerun", required=True, help="Rerun directory containing _provenance.json + results/")
    parser.add_argument(
        "--ground-truth-paths",
        action="append",
        default=[],
        metavar="TASK=FILE",
        help="Ground-truth path arrays for a task. Repeat per task. "
             "FILE may be JSON (parse-ground-truth.py output) or GROUND_TRUTH.md.",
    )
    parser.add_argument(
        "--codex-sessions-root",
        default=str(DEFAULT_CODEX_SESSIONS_ROOT),
        help="Override the codex sessions root (default: ~/.codex/sessions)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print would-stamp values; do not modify result JSONs")
    args = parser.parse_args(argv)

    rerun = pathlib.Path(args.rerun).expanduser().resolve()
    if not rerun.is_dir():
        print(f"ERROR: rerun dir not found: {rerun}", file=sys.stderr)
        return 1

    prov_path = rerun / "_provenance.json"
    if not prov_path.exists():
        print(f"ERROR: _provenance.json not found at {prov_path}", file=sys.stderr)
        return 1
    # We don't require started_at to filter codex sessions — cwd matching is
    # already a strong filter. But we read provenance for parity / future use.
    json.loads(prov_path.read_text())

    sessions_root = pathlib.Path(args.codex_sessions_root).expanduser()

    # Parse ground-truth specs once (re-uses chorus loader).
    gt_by_task: Dict[str, Dict[str, List[str]]] = {}
    for spec in args.ground_truth_paths:
        try:
            tid, payload = load_ground_truth_paths(spec)
        except Exception as exc:  # noqa: BLE001 — same broad catch as chorus extractor
            print(f"WARN: skipping --ground-truth-paths {spec!r}: {exc}", file=sys.stderr)
            continue
        gt_by_task[tid] = payload

    stamped_tasks = 0
    seen_session_ids: set = set()

    agent = "codex"
    for condition in ("bare", "structured_fresh"):
        cell_dir = rerun / "results" / agent / condition
        if not cell_dir.is_dir():
            continue
        results = sorted(p for p in cell_dir.glob("*.json") if not p.name.endswith(".judge.json"))
        if not results:
            continue

        cell_cwd = str((rerun / condition).resolve())
        session = find_codex_session_for_cell(cell_cwd, sessions_root, seen_session_ids)
        if not session:
            print(f"  [{agent}/{condition}] no codex session found for cwd={cell_cwd}")
            continue
        session_id = session.get("session_id")
        if not session_id:
            print(f"  [{agent}/{condition}] session has no id")
            continue
        if session_id in seen_session_ids:
            print(
                f"  [{agent}/{condition}] WARN: session {session_id} already used for another cell; "
                "not stamping to avoid mixing condition-level event metrics",
                file=sys.stderr,
            )
            continue
        seen_session_ids.add(session_id)

        jsonl_path = pathlib.Path(session["file_path"])
        events = walk_codex_session_events(jsonl_path)
        segments = segment_events_by_task(events)

        print(
            f"  [{agent}/{condition}] cwd={cell_cwd} session={session_id} "
            f"events={len(events)} segments={sorted(segments.keys())} "
            f"jsonl={jsonl_path.name}"
        )

        if args.dry_run:
            continue

        shortcut_paths = load_verification_shortcut_paths(pathlib.Path(cell_cwd))

        for rp in results:
            tid = rp.stem  # "L1.json" → "L1"
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
