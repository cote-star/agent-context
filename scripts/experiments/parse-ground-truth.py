#!/usr/bin/env python3
"""parse-ground-truth.py — extract per-task ground-truth path arrays from GROUND_TRUTH.md.

Reads a reviewer-only `GROUND_TRUTH.md` file (private rerun infra) and emits the
per-task path arrays that populate the schema v3 fields:

  - ground_truth_required_paths   ← `Required citations:` ∪ `Required files:`
  - ground_truth_optional_paths   ← `Optional but expected:`
  - ground_truth_decoy_paths      ← path-like backticks inside the `Risk:` paragraph

The downstream consumer is `apply-provenance.py` (or a sibling stamper) which
copies these arrays onto each task's result JSON so summarizers can compute
required-file recall, optional-file coverage, and dead-end-vs-decoy precision
without re-parsing markdown.

Format assumptions (best-effort, the input is markdown not a database):
  - Tasks are introduced by a level-3 header `### <task_id> — <title>` or
    `### <task_id> - <title>`. Both em-dash (U+2014) and ASCII hyphen-minus are
    accepted. The `<task_id>` is the whitespace-stripped token before the dash.
  - Each task may contain any of: `Required citations:`, `Required files:`,
    `Optional but expected:`, `Risk:`. Headers are matched case-insensitively
    and may carry any trailing text on the same line (e.g. parenthetical).
  - Path bullets are lines starting with `-` or `*`; the path is the first
    backtick-quoted segment on the line. A trailing `:line` or `:line-range`
    suffix on the path is stripped (so `cli/src/agent_context.rs:243-275`
    becomes `cli/src/agent_context.rs`). Bullets whose first backtick segment
    does not look like a path (no slash AND no extension, or has internal
    whitespace) are skipped.
  - Risk decoys are best-effort: every backticked path-like token in the Risk
    paragraph is collected, with the same line-suffix cleanup. No backticks
    in Risk → empty decoy list.
  - Per-task lists are de-duplicated, preserving order of first occurrence.
  - Subsections are scoped to the lines between their header and the next
    blank-line-followed-by-another-header — i.e., bullet collection stops at
    a Grep-verification fence, the next labeled subsection, or the next
    `###` task header, whichever comes first.

Usage:
  parse-ground-truth.py <GROUND_TRUTH.md> [--task-id L1] [--out-json <file>]

Default behavior parses every task in the file and writes the JSON map to
stdout:

  {
    "L1": {"required": [...], "optional": [...], "decoy": [...]},
    "L2": {...},
    ...
  }

`--task-id` filters to a single task. `--out-json` writes to a file instead of
stdout (the file is created or overwritten).

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Dict, List, Optional, Tuple

# Header lines that introduce a task: "### L1 — Conformance check"
# Group 1 captures everything before the first em-dash or hyphen separator.
# We accept em-dash (—, U+2014) or " - " (ASCII hyphen with surrounding space)
# so we don't accidentally split a task_id like "M1" on its own.
TASK_HEADER_RE = re.compile(r"^###\s+(.+?)\s+(?:—|-)\s+(.+)$")

# Subsection labels we care about. Match case-insensitively, allow trailing
# parenthetical (e.g. "Required files (must all appear):").
SUBSECTION_LABELS = {
    "required_citations": re.compile(r"^required\s+citations\b.*:\s*$", re.IGNORECASE),
    "required_files": re.compile(r"^required\s+files\b.*:\s*$", re.IGNORECASE),
    "optional": re.compile(r"^optional\s+but\s+expected\b.*:\s*$", re.IGNORECASE),
    "risk": re.compile(r"^risk\b.*?:", re.IGNORECASE),
}

# Match a `### ` task header (used to bound a section).
ANY_TASK_HEADER_RE = re.compile(r"^###\s+\S")

# Other labeled lines that should terminate a subsection (e.g. "Grep verification:",
# "Required answer:", "Required fix plan:"). Anything that looks like a
# `Word ...:` label at the start of a line and isn't itself a subsection we want.
OTHER_LABEL_RE = re.compile(r"^[A-Z][A-Za-z][A-Za-z /-]*:\s*$")

# Bullet line: leading "-" or "*" then space.
BULLET_RE = re.compile(r"^[-*]\s+(.*)$")

# Backtick segment finder.
BACKTICK_RE = re.compile(r"`([^`]+)`")

# Trailing `:line` or `:line-range` suffix on a path.
LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")


def looks_like_path(token: str) -> bool:
    """Best-effort path heuristic.

    Accept tokens that contain a slash OR a typical filename extension, and
    that don't have internal whitespace. The point is to skip backticked
    code/identifiers like `Subcommand` or `CURRENT_SCHEMA_VERSION`.
    """
    if not token or any(ch.isspace() for ch in token):
        return False
    if "/" in token:
        return True
    # No slash: only accept if it has a recognizable file extension at the end.
    if re.search(r"\.[A-Za-z0-9]{1,8}$", token):
        return True
    return False


def clean_path(token: str) -> str:
    """Strip a trailing `:line` or `:line-range` suffix."""
    return LINE_SUFFIX_RE.sub("", token).strip()


def split_into_task_blocks(text: str) -> List[Tuple[str, List[str]]]:
    """Return list of (task_id, lines) pairs in document order.

    Lines are the body lines of the task (excluding the `### ` header itself).
    Content that appears before any `### ` header is ignored.
    """
    blocks: List[Tuple[str, List[str]]] = []
    current_id: Optional[str] = None
    current_lines: List[str] = []
    for raw_line in text.splitlines():
        m = TASK_HEADER_RE.match(raw_line)
        if m:
            if current_id is not None:
                blocks.append((current_id, current_lines))
            current_id = m.group(1).strip()
            current_lines = []
            continue
        if current_id is not None:
            current_lines.append(raw_line)
    if current_id is not None:
        blocks.append((current_id, current_lines))
    return blocks


def extract_subsection_lines(lines: List[str], start_idx: int) -> List[str]:
    """Return the lines that belong to a labeled subsection.

    Begins after `start_idx` (the label line itself) and ends at the next
    blank line followed by another label, the next bullet-less labeled line,
    a fenced code block, or end of task. Conservative: we collect bullet
    lines until we hit something that is clearly the next region.
    """
    body: List[str] = []
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Stop on a fenced code block (Grep verification etc.)
        if stripped.startswith("```"):
            break
        # Stop on the next labeled subsection (any of our known labels).
        if any(rx.match(stripped) for rx in SUBSECTION_LABELS.values()):
            break
        # Stop on another `Capitalized Words:` label that isn't a bullet —
        # e.g. "Required answer:", "Required fix plan:", "Grep verification:".
        if OTHER_LABEL_RE.match(stripped) and not stripped.startswith(("-", "*")):
            break
        body.append(line)
        i += 1
    return body


def extract_paths_from_bullets(body_lines: List[str]) -> List[str]:
    """Pull the first backticked path token from each bullet line."""
    out: List[str] = []
    for line in body_lines:
        stripped = line.strip()
        # We allow nested bullet indentation too ("  - foo").
        bm = BULLET_RE.match(stripped)
        if not bm:
            continue
        bullet_body = bm.group(1)
        tick = BACKTICK_RE.search(bullet_body)
        if not tick:
            continue
        token = tick.group(1).strip()
        if not looks_like_path(token):
            continue
        out.append(clean_path(token))
    return out


def extract_paths_from_risk(body_lines: List[str]) -> List[str]:
    """Pull every path-like backticked token from the Risk paragraph."""
    out: List[str] = []
    for line in body_lines:
        for m in BACKTICK_RE.finditer(line):
            token = m.group(1).strip()
            if looks_like_path(token):
                out.append(clean_path(token))
    return out


def dedupe_preserve(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_task(task_id: str, lines: List[str]) -> Dict[str, List[str]]:
    """Parse a single task block into {required, optional, decoy} lists."""
    required: List[str] = []
    optional: List[str] = []
    decoy: List[str] = []

    saw_required_section = False

    for i, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if SUBSECTION_LABELS["required_citations"].match(stripped):
            saw_required_section = True
            body = extract_subsection_lines(lines, i)
            required.extend(extract_paths_from_bullets(body))
        elif SUBSECTION_LABELS["required_files"].match(stripped):
            saw_required_section = True
            body = extract_subsection_lines(lines, i)
            required.extend(extract_paths_from_bullets(body))
        elif SUBSECTION_LABELS["optional"].match(stripped):
            body = extract_subsection_lines(lines, i)
            optional.extend(extract_paths_from_bullets(body))
        elif SUBSECTION_LABELS["risk"].match(stripped):
            # The Risk: label often shares its line with the paragraph
            # (e.g. "Risk: citing only `cli/src/...`"). Collect the rest of
            # that line plus the continuation block.
            tail = stripped.split(":", 1)[1] if ":" in stripped else ""
            body = [tail] + extract_subsection_lines(lines, i)
            decoy.extend(extract_paths_from_risk(body))

    if not saw_required_section:
        print(
            f"WARN: task {task_id} has no Required citations: or Required files: section",
            file=sys.stderr,
        )

    return {
        "required": dedupe_preserve(required),
        "optional": dedupe_preserve(optional),
        "decoy": dedupe_preserve(decoy),
    }


def parse_ground_truth(text: str, task_id: Optional[str] = None) -> Dict[str, Dict[str, List[str]]]:
    """Parse the full GROUND_TRUTH.md text. Filter to one task_id if given."""
    out: Dict[str, Dict[str, List[str]]] = {}
    for tid, body in split_into_task_blocks(text):
        if task_id is not None and tid != task_id:
            continue
        out[tid] = parse_task(tid, body)
    return out


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0] if __doc__ else "parse GROUND_TRUTH.md"
    )
    parser.add_argument("path", help="Path to GROUND_TRUTH.md")
    parser.add_argument("--task-id", default=None, help="Parse only this task_id (e.g. L1)")
    parser.add_argument("--out-json", default=None, help="Write JSON to this file instead of stdout")
    args = parser.parse_args(argv)

    src = pathlib.Path(args.path).expanduser()
    if not src.is_file():
        print(f"ERROR: not a file: {src}", file=sys.stderr)
        return 1
    text = src.read_text(encoding="utf-8")

    parsed = parse_ground_truth(text, task_id=args.task_id)

    if args.task_id is not None and not parsed:
        print(f"ERROR: task_id {args.task_id!r} not found in {src}", file=sys.stderr)
        return 2

    payload = json.dumps(parsed, indent=2) + "\n"
    if args.out_json:
        pathlib.Path(args.out_json).expanduser().write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
