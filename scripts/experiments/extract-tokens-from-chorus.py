#!/usr/bin/env python3
"""extract-tokens-from-chorus.py — stamp post-hoc token usage onto result JSONs.

Reads each agent's native session log via the `chorus` CLI, sums input + output
tokens across the experiment session, and stamps the totals onto result JSON
files for that (agent, condition) cell. Run this AFTER agents finish writing
result JSONs and AFTER apply-provenance.py.

Coverage:
  - claude   ✅ (chorus reads ~/.claude/projects/<...>/<session-id>.jsonl with usage data)
  - codex    ✅ (chorus reads ~/.codex/sessions/.../session.json with usage data)
  - cursor   ⚠️ chorus's cursor adapter does NOT read ~/.cursor/chats/ where
              cursor-agent v3.2.16 stores sessions. Tokens left null until the
              chorus adapter is extended (logged as follow-on work in PLAN.md).
  - opencode ⚠️ ollama backend doesn't expose per-task usage in a chorus-readable
              form. Tokens left null.

Methodology note: each (agent, condition) cell ran 6 tasks inside ONE
agent-CLI session, so the chorus-reported total is a per-CELL number, not a
per-task number. This script stamps the per-cell total onto every task in
that cell — `summarize-results.py`'s `mean(tokens_total)` over the 6 tasks
then returns the per-cell total (matching the historical viz's "Avg tokens"
field, which is also per-cell). Per-task token attribution requires parsing
message boundaries inside the session and is left for a future revision.

Usage:
  scripts/experiments/extract-tokens-from-chorus.py \\
    --rerun ~/agent-context-reruns/q2-2026-private/agent-chorus

  # Override which agents to process (default: claude + codex)
  scripts/experiments/extract-tokens-from-chorus.py \\
    --rerun <path> --agents claude,codex

  # Dry-run: print what would be stamped without writing
  scripts/experiments/extract-tokens-from-chorus.py --rerun <path> --dry-run

Stdlib-only, Python 3.8+. Requires `chorus` CLI on PATH.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any


SUPPORTED_AGENTS = {"claude", "codex"}  # cursor + opencode are gaps; see docstring


def chorus_list(agent: str, cwd: str) -> list[dict[str, Any]]:
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


def chorus_read(agent: str, session_id: str, cwd: str) -> dict[str, Any] | None:
    """Run `chorus read --agent <agent> --id <id> --cwd <cwd> --json`."""
    try:
        out = subprocess.check_output(
            ["chorus", "read", "--agent", agent, "--id", session_id, "--cwd", cwd, "--json"],
            text=True, stderr=subprocess.PIPE,
        )
        return json.loads(out)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"WARN: chorus read failed for agent={agent} id={session_id}: {exc}", file=sys.stderr)
        return None


def sum_tokens(session: dict[str, Any]) -> tuple[int | None, int | None, int | None, str | None]:
    """Sum input/output/cached tokens and detect model_id.

    chorus's session shape varies per agent; we look for common keys
    ('usage', 'token_usage', 'input_tokens', etc.) across messages.
    Returns (input, output, cached, model_id) — any can be None if the
    session doesn't expose that field.
    """
    total_input = 0
    total_output = 0
    total_cached = 0
    model_id: str | None = None
    saw_any = False

    messages = session.get("messages") or session.get("turns") or []
    for msg in messages:
        usage = msg.get("usage") or msg.get("token_usage") or {}
        if not isinstance(usage, dict):
            continue
        for key in ("input_tokens", "prompt_tokens", "input"):
            v = usage.get(key)
            if isinstance(v, int):
                total_input += v
                saw_any = True
                break
        for key in ("output_tokens", "completion_tokens", "output"):
            v = usage.get(key)
            if isinstance(v, int):
                total_output += v
                saw_any = True
                break
        for key in ("cache_read_input_tokens", "cached_tokens", "cache_read"):
            v = usage.get(key)
            if isinstance(v, int):
                total_cached += v
                break
        if model_id is None:
            mid = msg.get("model") or msg.get("model_id") or session.get("model")
            if isinstance(mid, str):
                model_id = mid

    if not saw_any:
        return (None, None, None, model_id)
    return (total_input, total_output, total_cached if total_cached > 0 else None, model_id)


def find_session_for_cell(
    agent: str,
    cwd: str,
    started_window: tuple[str, str] | None,
) -> dict[str, Any] | None:
    """Find the chorus session that covers the experiment window for this cell.

    Strategy:
      1. List all sessions for this agent in this repo.
      2. Pick the most recent one that started within the experiment window
         (provenance.prepared_at .. now). If no window provided, take the
         most recent session.
    """
    sessions = chorus_list(agent, cwd)
    if not sessions:
        return None
    # chorus list typically sorts most-recent first; sort defensively by
    # session timestamp if available.
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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--rerun", required=True, help="Rerun directory containing _provenance.json + results/")
    parser.add_argument("--agents", default="claude,codex", help="Comma-separated agent names to process (default: claude,codex)")
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
    source_repo = prov.get("source_repo_path")
    if not source_repo:
        print("ERROR: _provenance.json missing source_repo_path", file=sys.stderr)
        return 1
    started = prov.get("prepared_at", "")

    requested_agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    skipped: list[str] = []
    stamped_cells = 0

    for agent in requested_agents:
        if agent not in SUPPORTED_AGENTS:
            skipped.append(agent)
            continue
        for condition in ("bare", "structured_fresh"):
            cell_dir = rerun / "results" / agent / condition
            results = sorted(p for p in cell_dir.glob("*.json") if not p.name.endswith(".judge.json"))
            if not results:
                continue

            session = find_session_for_cell(agent, source_repo, (started, ""))
            if not session:
                print(f"  [{agent}/{condition}] no chorus session found")
                continue
            session_id = session.get("session_id") or session.get("id")
            if not session_id:
                print(f"  [{agent}/{condition}] session has no id")
                continue
            data = chorus_read(agent, session_id, source_repo)
            if not data:
                continue

            tin, tout, tcached, mid = sum_tokens(data)
            if tin is None and tout is None:
                print(f"  [{agent}/{condition}] session {session_id} has no token usage data")
                continue
            ttot = (tin or 0) + (tout or 0)

            print(f"  [{agent}/{condition}] session={session_id} tokens_in={tin} tokens_out={tout} cached={tcached} model={mid}")

            if args.dry_run:
                continue

            for rp in results:
                d = json.loads(rp.read_text())
                d["tokens_input"] = tin
                d["tokens_output"] = tout
                d["tokens_total"] = ttot
                if tcached is not None:
                    d["tokens_cached"] = tcached
                if mid:
                    d["model_id"] = mid
                rp.write_text(json.dumps(d, indent=2) + "\n")
            stamped_cells += 1

    print(f"\nStamped: {stamped_cells} cells")
    if skipped:
        print(f"Skipped (not in SUPPORTED_AGENTS): {', '.join(skipped)}  — see docstring for chorus adapter gaps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
