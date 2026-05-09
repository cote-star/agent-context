#!/usr/bin/env python3
"""scrub-aliases.py — replace real repo names with public aliases.

Reads a private aliases.json (single source of truth for real-name → alias
mapping) and rewrites real names to aliases in any file destined for public
docs (README, evidence/, viz, talk).

Word-boundary, case-sensitive substitution. Files matching skip_files in
aliases.json are skipped. Files marked expose_real_name_publicly=true keep
their real name unchanged.

Usage:
  scripts/experiments/scrub-aliases.py \\
    --aliases ~/agent-context-reruns/q2-2026-private/aliases.json \\
    --in <input-dir-or-file> \\
    --out <output-dir-or-file>

  scripts/experiments/scrub-aliases.py \\
    --aliases <path> \\
    --check <input-dir>     # exits non-zero if any real names found

Stdlib-only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
from typing import Iterable


def load_aliases(path: pathlib.Path) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Returns (replacements_map, applies_to_globs, skip_globs, retired_names).

    replacements_map: real_name -> alias for entries with expose_real_name_publicly=false.
    Real names where expose_real_name_publicly=true are excluded from the map (they
    pass through unchanged), but they are still tracked so --check doesn't flag them.

    retired_names: real names (and aliases) that were removed from the active slate
    but should still be flagged by --check, so stale references don't slip through.
    They are flagged but not auto-replaced (we don't know what they should become).
    """
    data = json.loads(path.read_text())
    aliases = data.get("aliases", {})
    replacements: dict[str, str] = {}
    for real, info in aliases.items():
        if not info.get("expose_real_name_publicly", False):
            replacements[real] = info["alias"]
    rules = data.get("scrub_rules", {})
    applies_to = rules.get("applies_to", ["**/*.md", "*.md", "**/*.html", "*.html", "**/*.json", "*.json", "**/*.txt", "*.txt"])
    skip = rules.get("skip_files", [])
    retired = data.get("retired_names", [])
    return replacements, applies_to, skip, retired


def matches_any_glob(path: pathlib.Path, root: pathlib.Path, globs: Iterable[str]) -> bool:
    rel = path.relative_to(root) if path.is_relative_to(root) else path
    rel_str = str(rel)
    name = path.name
    for g in globs:
        # Full relative-path match (handles "subdir/foo.md" etc.)
        if rel.match(g):
            return True
        # **/*.ext globs in pathlib.match() require at least one dir component,
        # so a top-level "foo.md" returns False against "**/*.md". Fall back to
        # matching just the filename against the pattern's tail.
        if g.startswith("**/"):
            tail = g[3:]
            if pathlib.PurePath(name).match(tail):
                return True
        # Prefix match for dir globs like "node_modules/**"
        if g.endswith("/**") and (rel_str.startswith(g[:-3]) or rel_str.startswith(g[:-3].rstrip("/"))):
            return True
    return False


def build_pattern(replacements: dict[str, str]) -> re.Pattern[str]:
    """Word-boundary, case-sensitive alternation of all real names, longest-first."""
    sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
    escaped = "|".join(re.escape(k) for k in sorted_keys)
    return re.compile(rf"(?<![A-Za-z0-9_-]){escaped}(?![A-Za-z0-9_-])")


def scrub_text(text: str, pattern: re.Pattern[str], replacements: dict[str, str]) -> tuple[str, int]:
    count = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return replacements[match.group(0)]

    return pattern.sub(_sub, text), count


def iter_target_files(
    root: pathlib.Path, applies_to: list[str], skip: list[str]
) -> Iterable[pathlib.Path]:
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in (".git", "node_modules", "__pycache__") for part in rel.parts):
            continue
        if not matches_any_glob(path, root, applies_to):
            continue
        if matches_any_glob(path, root, skip):
            continue
        yield path


def cmd_scrub(args: argparse.Namespace) -> int:
    aliases_path = pathlib.Path(args.aliases).expanduser()
    in_path = pathlib.Path(args.in_path).expanduser()
    out_path = pathlib.Path(args.out).expanduser()

    replacements, applies_to, skip, retired = load_aliases(aliases_path)
    if not replacements:
        print("WARN: no replacements configured (every alias has expose_real_name_publicly=true)", file=sys.stderr)
    pattern = build_pattern(replacements)

    if in_path.is_file():
        in_root = in_path.parent
        out_path.parent.mkdir(parents=True, exist_ok=True)
        text = in_path.read_text()
        new_text, count = scrub_text(text, pattern, replacements)
        out_path.write_text(new_text)
        print(f"scrubbed {count} occurrences -> {out_path}")
        return 0

    if not in_path.is_dir():
        print(f"ERROR: input path is neither file nor directory: {in_path}", file=sys.stderr)
        return 2

    out_path.mkdir(parents=True, exist_ok=True)
    total_files = 0
    total_subs = 0
    for src in iter_target_files(in_path, applies_to, skip):
        rel = src.relative_to(in_path)
        dst = out_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text()
        new_text, count = scrub_text(text, pattern, replacements)
        dst.write_text(new_text)
        total_files += 1
        total_subs += count
    # Copy non-target files verbatim so the output is a complete mirror
    for src in in_path.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(in_path)
        if any(part in (".git", "node_modules", "__pycache__") for part in rel.parts):
            continue
        dst = out_path / rel
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"scrubbed {total_subs} occurrences across {total_files} files -> {out_path}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    aliases_path = pathlib.Path(args.aliases).expanduser()
    in_path = pathlib.Path(args.check).expanduser()
    replacements, applies_to, skip, retired = load_aliases(aliases_path)
    # Build a pattern that matches active real names AND retired names (so stale
    # references to dropped slate entries still get flagged). Retired names are
    # not in the replacements map, so they are flagged but never auto-replaced.
    flag_terms: dict[str, str] = dict(replacements)
    for name in retired:
        flag_terms.setdefault(name, "(retired)")
    if not flag_terms:
        print("OK: no real names or retired names configured")
        return 0
    pattern = build_pattern(flag_terms)

    targets = [in_path] if in_path.is_file() else list(iter_target_files(in_path, applies_to, skip))
    hits: list[tuple[pathlib.Path, str, int, str]] = []
    for path in targets:
        text = path.read_text(errors="ignore")
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            kind = "retired" if match.group(0) in retired else "real-name"
            hits.append((path, match.group(0), line_no, kind))

    if not hits:
        print(f"OK: no real names found in {in_path}")
        return 0

    print(f"FAIL: {len(hits)} leak(s) found in {in_path}", file=sys.stderr)
    for path, name, line, kind in hits[:50]:
        print(f"  {path}:{line}  [{kind}] {name}", file=sys.stderr)
    if len(hits) > 50:
        print(f"  ... and {len(hits) - 50} more", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--aliases", required=True, help="Path to aliases.json")
    parser.add_argument("--in", dest="in_path", help="Input file or directory")
    parser.add_argument("--out", help="Output file or directory")
    parser.add_argument("--check", help="Directory or file to scan; exits non-zero if real names present")
    args = parser.parse_args(argv)

    if args.check:
        return cmd_check(args)
    if not args.in_path or not args.out:
        parser.error("--in and --out are required unless --check is used")
    return cmd_scrub(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
