#!/usr/bin/env python3
"""Extract EXPERIMENT.md and GROUND_TRUTH.md blocks from a per-repo task template.

Usage:
    scripts/experiments/scaffold-tasks.py \\
        docs/experiments/tasks/agent-chorus.md \\
        ~/agent-context-reruns/agent-chorus

The task-template markdown contains two fenced ```markdown ...``` blocks under
the headings "## EXPERIMENT.md — Tasks block" and "## GROUND_TRUTH.md — Reviewer
block". This script extracts those blocks and writes them to EXPERIMENT.md and
GROUND_TRUTH.md inside the target rerun directory, replacing whatever scaffold
prepare-codex-cursor-rerun.sh produced.

Stdlib-only. Refuses to overwrite if either output file is missing the
prepare-codex-cursor-rerun.sh scaffold header (`# Agent-Context Fresh-Pack
Rerun` for EXPERIMENT.md, `# Ground Truth` for GROUND_TRUTH.md). This guards
against silently destroying hand-edited rerun content if someone points the
script at the wrong directory. Pass --force to override.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


EXPERIMENT_HEADER_RE = re.compile(r"^##\s+EXPERIMENT\.md\b", re.IGNORECASE)
GROUND_TRUTH_HEADER_RE = re.compile(r"^##\s+GROUND_TRUTH\.md\b", re.IGNORECASE)
FENCE_RE = re.compile(r"^```(?:markdown|md)?\s*$")
END_FENCE_RE = re.compile(r"^```\s*$")


def extract_block(text: str, header_re: re.Pattern[str]) -> str:
    """Extract the first fenced ```markdown block following a matching header.

    Inside a template's outer ```markdown fence, nested ```bash (or other
    language) fences are written as ``\\```bash`` to keep them from prematurely
    closing the outer block. The extracted output is a standalone markdown
    file, so those backslash-escapes must be un-escaped on extraction —
    otherwise downstream tools (preflight grep-block detection, agent
    rendering) will not see the inner fences as real code blocks.

    Raises ValueError if the header or the block is missing.
    """
    lines = text.splitlines()
    in_section = False
    in_block = False
    block: list[str] = []

    for line in lines:
        if not in_section:
            if header_re.match(line):
                in_section = True
            continue
        if in_section and not in_block:
            if FENCE_RE.match(line):
                in_block = True
                continue
            # Header for some other section before fence -> abort
            if line.startswith("## ") and not header_re.match(line):
                in_section = False
                continue
            continue
        if in_block:
            if END_FENCE_RE.match(line):
                # Un-escape inner fences that were backslash-escaped in the
                # template to survive the outer markdown fence. After this
                # the extracted block is standalone-valid markdown.
                content = "\n".join(block) + "\n"
                content = content.replace("\\```", "```")
                return content
            block.append(line)

    if not in_section:
        raise ValueError(f"header {header_re.pattern!r} not found in template")
    if not in_block:
        raise ValueError(f"no fenced block found after header {header_re.pattern!r}")
    raise ValueError(f"unclosed fenced block after header {header_re.pattern!r}")


EXPERIMENT_SCAFFOLD_HEADER = "# Agent-Context Fresh-Pack Rerun"
GROUND_TRUTH_SCAFFOLD_HEADER = "# Ground Truth"


def _looks_like_scaffold(path: pathlib.Path, expected_header: str) -> bool:
    """Quick guard: does this file look like a fresh scaffold or a re-scaffold target?

    A file is safe to overwrite only when it begins with the scaffold header.
    Hand-edited rerun content (or content already populated by a previous
    scaffold-tasks run) keeps the same header on top, so re-scaffolding the
    same rerun dir is fine. But if the file has been heavily rewritten or
    points at the wrong dir entirely, refuse.
    """
    try:
        head = path.read_text(errors="ignore").lstrip().splitlines()
    except Exception:
        return False
    return bool(head) and head[0].strip() == expected_header


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("template", help="Path to docs/experiments/tasks/<repo>.md")
    parser.add_argument("rerun_root", help="Path to the prepared rerun directory (created by prepare-codex-cursor-rerun.sh)")
    parser.add_argument("--allow-todo", action="store_true", help="Permit TODO markers in the extracted blocks (skeleton mode)")
    parser.add_argument("--force", action="store_true", help="Overwrite EXPERIMENT.md / GROUND_TRUTH.md even if their scaffold headers are missing (use only when you know the target dir is correct)")
    args = parser.parse_args(argv)

    template_path = pathlib.Path(args.template).resolve()
    rerun_root = pathlib.Path(args.rerun_root).resolve()

    if not template_path.is_file():
        print(f"ERROR: template not found: {template_path}", file=sys.stderr)
        return 1
    if not rerun_root.is_dir():
        print(f"ERROR: rerun root not a directory: {rerun_root}", file=sys.stderr)
        return 1

    experiment_path = rerun_root / "EXPERIMENT.md"
    ground_truth_path = rerun_root / "GROUND_TRUTH.md"

    for p in (experiment_path, ground_truth_path):
        if not p.is_file():
            print(f"ERROR: expected scaffold not present: {p}\n"
                  f"  Did you run scripts/experiments/prepare-codex-cursor-rerun.sh first?",
                  file=sys.stderr)
            return 1

    # Scaffold-header safety guard: refuse to overwrite content that doesn't
    # look like a fresh prepare-codex-cursor-rerun.sh scaffold (or a previous
    # scaffold-tasks run). Override with --force.
    if not args.force:
        for p, expected in (
            (experiment_path, EXPERIMENT_SCAFFOLD_HEADER),
            (ground_truth_path, GROUND_TRUTH_SCAFFOLD_HEADER),
        ):
            if not _looks_like_scaffold(p, expected):
                print(
                    f"ERROR: {p} does not start with the scaffold header "
                    f"{expected!r}.\n"
                    f"  Refusing to overwrite — this looks like hand-edited content,\n"
                    f"  or you may be pointed at the wrong rerun dir.\n"
                    f"  If you really want to replace it, re-run with --force.",
                    file=sys.stderr,
                )
                return 1

    template_text = template_path.read_text()

    try:
        experiment_block = extract_block(template_text, EXPERIMENT_HEADER_RE)
    except ValueError as exc:
        print(f"ERROR: extracting EXPERIMENT.md block from {template_path}: {exc}", file=sys.stderr)
        return 1

    try:
        ground_truth_block = extract_block(template_text, GROUND_TRUTH_HEADER_RE)
    except ValueError as exc:
        print(f"ERROR: extracting GROUND_TRUTH.md block from {template_path}: {exc}", file=sys.stderr)
        return 1

    todo_warnings: list[str] = []
    if "TODO" in experiment_block:
        todo_warnings.append("EXPERIMENT.md still contains TODO markers")
    if "TODO" in ground_truth_block:
        todo_warnings.append("GROUND_TRUTH.md still contains TODO markers")

    if todo_warnings and not args.allow_todo:
        print("ERROR: extracted blocks contain TODO markers — adapt the template before running:", file=sys.stderr)
        for w in todo_warnings:
            print(f"  - {w}", file=sys.stderr)
        print("  Re-run with --allow-todo to proceed anyway (the rerun will be flagged REQUIRES-EDIT).", file=sys.stderr)
        return 2

    experiment_path.write_text(_experiment_preamble() + experiment_block)
    ground_truth_path.write_text(_ground_truth_preamble() + ground_truth_block)

    print(f"OK: wrote {experiment_path}")
    print(f"OK: wrote {ground_truth_path}")
    if todo_warnings:
        print("WARN: extracted content has TODO markers (--allow-todo set); rerun is REQUIRES-EDIT.")
    return 0


def _experiment_preamble() -> str:
    return (
        "# Agent-Context Fresh-Pack Rerun\n"
        "\n"
        "Read this entire file before starting.\n"
        "\n"
        "## Rules\n"
        "\n"
        "1. Run tasks in order.\n"
        "2. Do not read `GROUND_TRUTH.md`.\n"
        "3. Write one JSON result file per task under the path provided in your launch prompt.\n"
        "4. Result JSON must match `../result.schema.json`.\n"
        "5. Set `correct` to `ungraded`; the human reviewer will grade later.\n"
        "6. Cite exact files and line numbers for factual claims.\n"
        "7. Track task-local files opened, dead ends, first correct file hop, post-hit dead ends, tool calls, and duration honestly.\n"
        "\n"
    )


def _ground_truth_preamble() -> str:
    return (
        "# Ground Truth\n"
        "\n"
        "Reviewer-only. Agents must not read this file.\n"
        "\n"
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
