#!/usr/bin/env python3
"""apply-provenance.py — stamp reproducibility anchors into result JSONs.

Walks `<rerun>/results/` and writes four anchor fields into every result JSON:

  source_repo_sha           git HEAD of source repo at experiment start
  pack_manifest_sha         sha256 of structured_fresh's manifest.json (null when bare)
  task_template_hash        sha256(EXPERIMENT.md + GROUND_TRUTH.md)
  agent_context_cli_version version string of bin/agent-context

Inputs:
  - `<rerun>/_provenance.json` written by `prepare-codex-cursor-rerun.sh`
  - `<rerun>/EXPERIMENT.md` and `<rerun>/GROUND_TRUTH.md` (for task_template_hash)

Idempotent. Run after agents finish writing results, before llm-judge.py.
Existing values are preserved if `--no-overwrite` is set; otherwise they are
overwritten (so re-running picks up corrected provenance).

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


def sha256_of_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def task_template_hash(rerun: pathlib.Path) -> str:
    h = hashlib.sha256()
    for name in ("EXPERIMENT.md", "GROUND_TRUTH.md"):
        path = rerun / name
        if path.exists():
            h.update(path.read_bytes())
        h.update(b"\n--FILE_BOUNDARY--\n")
    return h.hexdigest()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rerun", required=True, help="Rerun directory containing _provenance.json and results/")
    parser.add_argument("--no-overwrite", action="store_true", help="Preserve any existing anchor values; only fill missing/null fields")
    args = parser.parse_args(argv)

    rerun = pathlib.Path(args.rerun).expanduser()
    if not rerun.is_dir():
        print(f"ERROR: rerun dir not found: {rerun}", file=sys.stderr)
        return 1

    prov_path = rerun / "_provenance.json"
    if not prov_path.exists():
        print(f"ERROR: _provenance.json not found at {prov_path}", file=sys.stderr)
        print("       Run prepare-codex-cursor-rerun.sh first; it emits this file.", file=sys.stderr)
        return 1
    prov = json.loads(prov_path.read_text())

    template_hash = task_template_hash(rerun)

    # v3 schema split: pack_content_origin_version is the agent-context version
    # that filled the pack content; validator_cli_version is the version that
    # ran verify/freshness for THIS rerun's preflight. agent_context_cli_version
    # stays for backward-compat with v2 readers.
    base = {
        "source_repo_sha": prov.get("source_repo_sha"),
        "task_template_hash": template_hash,
        "agent_context_cli_version": prov.get("agent_context_cli_version"),
        "pack_content_origin_version": prov.get(
            "pack_content_origin_version", prov.get("agent_context_cli_version")
        ),
        "validator_cli_version": prov.get("validator_cli_version"),
    }
    anchors_for_condition = {
        "bare": {**base, "pack_manifest_sha": None},  # bare has no pack
        "structured_fresh": {**base, "pack_manifest_sha": prov.get("pack_manifest_sha")},
    }

    results_root = rerun / "results"
    if not results_root.is_dir():
        print(f"ERROR: results dir not found: {results_root}", file=sys.stderr)
        return 1

    paths = sorted(
        p for p in results_root.rglob("*.json")
        if p.name != "result.schema.json" and not p.name.endswith(".judge.json")
    )
    if not paths:
        print(f"ERROR: no result files under {results_root}", file=sys.stderr)
        return 1

    stamped = 0
    skipped = 0
    for path in paths:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            print(f"WARN: skipping unreadable {path}: {exc}", file=sys.stderr)
            continue
        condition = data.get("condition")
        if condition not in anchors_for_condition:
            print(f"WARN: skipping {path}: unknown condition {condition!r}", file=sys.stderr)
            continue
        target = anchors_for_condition[condition]

        changed = False
        for field, value in target.items():
            current = data.get(field)
            if args.no_overwrite and current not in (None, ""):
                continue
            if current != value:
                data[field] = value
                changed = True

        if changed:
            path.write_text(json.dumps(data, indent=2) + "\n")
            stamped += 1
        else:
            skipped += 1

    print(f"stamped: {stamped}")
    print(f"unchanged: {skipped}")
    print(f"task_template_hash: {template_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
