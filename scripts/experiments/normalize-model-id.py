#!/usr/bin/env python3
"""normalize-model-id.py — backfill consistent `model_id` on result JSONs.

Why this exists:
  - Codex agent self-reports `model_id` inconsistently across runs ("gpt-5",
    "gpt-5-codex", or null) even though codex CLI records the actual model in
    each session's `session_meta.payload.model`. This fragments derived-metrics
    cells by what should be one model.
  - Cursor results in model-aware paths (results/cursor/<condition>/<model-slug>/)
    sometimes have null `model_id` even though the slug names the model. The
    path is authoritative.

Behavior:
  - Codex rows with null/inconsistent `model_id`: read the matching codex
    session JSONL (located via cwd → ~/.codex/sessions), pull its
    `session_meta.payload.model`, write back as `model_id`.
  - Cursor rows where the result is under a model-slug subdir: backfill
    `model_id` from the slug if missing.
  - Anything else: leave as-is.

Idempotent. Doesn't touch reviewer-confirmed rows.

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Optional


CODEX_SESSIONS_ROOT = pathlib.Path.home() / ".codex" / "sessions"
CLAUDE_SESSIONS_ROOT = pathlib.Path.home() / ".claude" / "projects"
TASK_ID_RE = re.compile(r"^(L1|L2|M1|M2|H1|H2)\.json$")


def _is_protected(data: dict) -> bool:
    return data.get("grading_method") == "reviewer-confirmed"


def _codex_session_meta_for_cwd(target_cwd: str) -> Optional[dict]:
    """Find a recent codex session whose session_meta cwd == target_cwd; return its full payload."""
    if not CODEX_SESSIONS_ROOT.is_dir():
        return None
    candidates: list[tuple[float, pathlib.Path]] = []
    for p in CODEX_SESSIONS_ROOT.rglob("rollout-*.jsonl"):
        try:
            candidates.append((p.stat().st_mtime, p))
        except OSError:
            continue
    candidates.sort(reverse=True)  # newest first
    for _, p in candidates:
        try:
            with p.open("r", encoding="utf-8") as fh:
                first = fh.readline()
        except OSError:
            continue
        try:
            obj = json.loads(first)
        except (json.JSONDecodeError, ValueError):
            continue
        if obj.get("type") != "session_meta":
            continue
        payload = obj.get("payload") or {}
        if payload.get("cwd") == target_cwd:
            return payload
    return None


def _codex_canonical_model_id(payload: Optional[dict]) -> str:
    """Build a stable model_id for codex from its session_meta.

    `session_meta.payload.model` is often null (codex CLI doesn't always
    record the underlying model), but `cli_version` is reliably present.
    Compose `codex-cli-<cli_version>` so all codex rows in a single rerun
    consolidate to one canonical, and the methodology section can note the
    underlying OpenAI model separately.
    """
    if not payload:
        return "codex-cli"
    model = payload.get("model")
    if isinstance(model, str) and model:
        return model
    cli_version = payload.get("cli_version")
    if isinstance(cli_version, str) and cli_version:
        return f"codex-cli-{cli_version}"
    return "codex-cli"


_CLAUDE_OPUS_PREFIX = "claude-opus-4-7"


def _canonicalize_claude_model(model: str) -> str:
    """Collapse Opus runtime-config variants (e.g., `claude-opus-4-7[1m]` for the
    1M-context variant) onto the base model id. Other claude models (haiku,
    sonnet, future opus revs) stay as-is so a real model swap is preserved.
    """
    if model.startswith(_CLAUDE_OPUS_PREFIX):
        return _CLAUDE_OPUS_PREFIX
    return model


def _claude_canonical_model_for_cwd(target_cwd: str) -> Optional[str]:
    """Walk recent claude session JSONLs; return the most-common assistant message.model
    for the session whose envelope cwd matches target_cwd. Claude Code's interactive
    runs sometimes report `claude-opus-4-7[1m]` (1M-context variant) in some messages
    and `claude-opus-4-7` in others; we pick the modal value per session, then
    canonicalize Opus variants together (haiku stays distinct).
    """
    if not CLAUDE_SESSIONS_ROOT.is_dir():
        return None
    candidates: list[tuple[float, pathlib.Path]] = []
    for p in CLAUDE_SESSIONS_ROOT.rglob("*.jsonl"):
        try:
            candidates.append((p.stat().st_mtime, p))
        except OSError:
            continue
    candidates.sort(reverse=True)
    for _, p in candidates:
        try:
            with p.open("r", encoding="utf-8") as fh:
                first = fh.readline()
            obj = json.loads(first)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if obj.get("cwd") != target_cwd:
            continue
        # Tally message.model across all assistant entries.
        counts: dict[str, int] = {}
        try:
            with p.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        ev = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if ev.get("type") != "assistant":
                        continue
                    msg = ev.get("message") or {}
                    model = msg.get("model")
                    if isinstance(model, str) and model:
                        counts[model] = counts.get(model, 0) + 1
        except OSError:
            continue
        if not counts:
            return None
        modal = max(counts.items(), key=lambda kv: kv[1])[0]
        return _canonicalize_claude_model(modal)
    return None


def _result_cwd_for_claude(result_path: pathlib.Path, repo_dir: pathlib.Path) -> str:
    """Same as codex: <repo>/<condition>/ is the claude lane cwd."""
    parts = result_path.relative_to(repo_dir / "results").parts
    condition = parts[1]
    return str((repo_dir / condition).resolve())


def _path_model_slug(result_path: pathlib.Path, results_root: pathlib.Path) -> Optional[str]:
    """If results_root/.../<agent>/<condition>/<slug>/<task>.json, return <slug>."""
    try:
        rel = result_path.relative_to(results_root)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) == 4:
        return parts[2]  # agent/condition/<slug>/task.json → slug at index 2
    return None


def _result_cwd_for_codex(result_path: pathlib.Path, repo_dir: pathlib.Path) -> str:
    """Codex sessions live in <repo>/<condition>/. Result is at <repo>/results/codex/<condition>/<task>.json."""
    parts = result_path.relative_to(repo_dir / "results").parts
    # parts: (agent, condition, [model_slug,] task.json)
    condition = parts[1]
    return str((repo_dir / condition).resolve())


def normalize_repo(repo_dir: pathlib.Path) -> dict[str, int]:
    """Walk one repo's results/ tree, normalize model_id where applicable."""
    counters = {
        "scanned": 0,
        "skipped_protected": 0,
        "codex_backfilled": 0,
        "claude_backfilled": 0,
        "cursor_backfilled_from_slug": 0,
        "unchanged": 0,
        "errors": 0,
    }
    results_root = repo_dir / "results"
    if not results_root.is_dir():
        return counters

    codex_model_cache: dict[str, Optional[dict]] = {}
    claude_model_cache: dict[str, Optional[str]] = {}

    for path in sorted(results_root.rglob("*.json")):
        if not TASK_ID_RE.match(path.name):
            continue
        if path.name.endswith(".judge.json"):
            continue
        counters["scanned"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            counters["errors"] += 1
            continue

        if _is_protected(data):
            counters["skipped_protected"] += 1
            continue

        agent = data.get("agent")
        current = data.get("model_id") or ""
        new_value: Optional[str] = None

        if agent == "codex":
            # Always re-anchor codex model_id — the agent's self-report drifts
            # ("gpt-5" vs "gpt-5-codex" vs null) even when codex CLI ran a
            # single model for the whole lane. Use codex-cli-<version> as the
            # canonical so all codex cells consolidate; methodology disclosure
            # names the underlying OpenAI model.
            cwd = _result_cwd_for_codex(path, repo_dir)
            if cwd not in codex_model_cache:
                codex_model_cache[cwd] = _codex_session_meta_for_cwd(cwd)
            canonical = _codex_canonical_model_id(codex_model_cache[cwd])
            if canonical != current:
                new_value = canonical

        elif agent == "claude":
            # Claude Code tags some messages as `claude-opus-4-7` and others
            # `claude-opus-4-7[1m]` within a single session, plus the prompt
            # asks the agent to populate model_id and it sometimes leaves it
            # null. First normalize whatever's already there (strip Opus
            # runtime-config suffixes); fall back to the session JSONL's
            # modal model when the field is empty.
            if current:
                canonical = _canonicalize_claude_model(current)
                if canonical != current:
                    new_value = canonical
            else:
                cwd = _result_cwd_for_claude(path, repo_dir)
                if cwd not in claude_model_cache:
                    claude_model_cache[cwd] = _claude_canonical_model_for_cwd(cwd)
                session_modal = claude_model_cache[cwd]
                if session_modal:
                    new_value = session_modal

        elif agent == "cursor":
            if not current:
                slug = _path_model_slug(path, results_root)
                if slug:
                    new_value = slug

        if new_value is None or new_value == current:
            counters["unchanged"] += 1
            continue

        data["model_id"] = new_value
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        if agent == "codex":
            counters["codex_backfilled"] += 1
        elif agent == "claude":
            counters["claude_backfilled"] += 1
        else:
            counters["cursor_backfilled_from_slug"] += 1

    return counters


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--rerun-root", default=os.environ.get("AGENT_CONTEXT_RERUN_ROOT", ""),
                        help="Matrix root containing per-repo subdirs")
    parser.add_argument("--repo", action="append", default=[],
                        help="Restrict to specific repo subdirs (repeatable)")
    args = parser.parse_args(argv)

    if not args.rerun_root:
        print("ERROR: rerun root required: pass --rerun-root or set AGENT_CONTEXT_RERUN_ROOT", file=sys.stderr)
        return 1

    root = pathlib.Path(args.rerun_root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: rerun root not found: {root}", file=sys.stderr)
        return 1

    if args.repo:
        repos = [root / r for r in args.repo]
    else:
        repos = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_") and "-before-" not in p.name)

    grand_total: dict[str, int] = {}
    for repo_dir in repos:
        if not repo_dir.is_dir():
            print(f"WARN: skipping missing repo: {repo_dir}", file=sys.stderr)
            continue
        c = normalize_repo(repo_dir)
        print(
            f"  {repo_dir.name}: scanned={c['scanned']} "
            f"codex={c['codex_backfilled']} "
            f"claude={c['claude_backfilled']} "
            f"cursor={c['cursor_backfilled_from_slug']} "
            f"unchanged={c['unchanged']} skipped_protected={c['skipped_protected']} "
            f"errors={c['errors']}"
        )
        for k, v in c.items():
            grand_total[k] = grand_total.get(k, 0) + v

    print(f"\nTotal: {grand_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
