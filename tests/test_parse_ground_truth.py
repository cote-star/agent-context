"""Tests for scripts/experiments/parse-ground-truth.py.

Covers happy path, multi-task shapes, line-suffix canonicalization, empty
sections, decoy backtick parsing, em-dash vs ASCII-hyphen headers, the
--task-id filter, and a skip-guarded round-trip against the real reviewer-only
GROUND_TRUTH.md when present on the local machine.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import pathlib
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "experiments" / "parse-ground-truth.py"

# Module name has a hyphen so we can't `import` it the normal way.
_spec = importlib.util.spec_from_file_location("parse_ground_truth", SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
parse_ground_truth_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parse_ground_truth_mod)  # type: ignore[union-attr]


SINGLE_TASK_FIXTURE = """\
# Ground Truth

Reviewer-only.

### L1 — Conformance check
Required answer: stuff happens.

Required citations:
- `scripts/conformance.sh` (file exists; canonical script)
- `.github/workflows/ci.yml:40-41` — `Run cross-implementation conformance` step
- `.github/workflows/release.yml:34-35` — `Verify conformance` step

Optional but expected:
- `docs/CLI_REFERENCE.md` — user-facing docs

Risk: citing only `cli/src/foo.rs` (Rust unit test) without `scripts/conformance.sh` means partial. Ignoring `Subcommand` identifier is fine.
"""

MULTI_TASK_FIXTURE = """\
# Ground Truth

### L1 — Easy
Required citations:
- `scripts/foo.sh` — exists

Risk: only citing `scripts/decoy.sh`.

### L2 - Easy with hyphen
Required citations:
- `cli/src/bar.rs:10-25` — gating function

Optional but expected:
- `docs/bar.md` — docs

Risk: nothing relevant here.

### M1 — Mid
Required files (must all appear):
- `cli/src/main.rs` — Rust dispatch
- `scripts/read_session.cjs` — Node dispatch

Risk: omitting `schemas/stats.json` breaks invariant.
"""

NO_BULLETS_FIXTURE = """\
### X1 — Empty body task
Required citations:

Optional but expected:

Risk: just prose, no decoys named.
"""

NO_RISK_BACKTICKS_FIXTURE = """\
### X2 — No backticks in risk
Required citations:
- `scripts/foo.sh` — file

Risk: a plan that fails for any reason without quoting concrete paths.
"""

NO_REQUIRED_FIXTURE = """\
### X3 — Numbered list shape
Required answer must include:

1. Some plan.
2. Other plan.

Risk: citing only `cli/src/x.rs` is bad.
"""


class ParseGroundTruthCoreTest(unittest.TestCase):
    def test_single_task_happy_path(self) -> None:
        out = parse_ground_truth_mod.parse_ground_truth(SINGLE_TASK_FIXTURE)
        self.assertEqual(set(out.keys()), {"L1"})
        self.assertEqual(
            out["L1"]["required"],
            [
                "scripts/conformance.sh",
                ".github/workflows/ci.yml",
                ".github/workflows/release.yml",
            ],
        )
        self.assertEqual(out["L1"]["optional"], ["docs/CLI_REFERENCE.md"])
        # decoy: cli/src/foo.rs and scripts/conformance.sh; "Subcommand" is filtered
        # because it has no slash and no dotted extension.
        self.assertIn("cli/src/foo.rs", out["L1"]["decoy"])
        self.assertIn("scripts/conformance.sh", out["L1"]["decoy"])
        self.assertNotIn("Subcommand", out["L1"]["decoy"])

    def test_multi_task_file_with_different_shapes(self) -> None:
        out = parse_ground_truth_mod.parse_ground_truth(MULTI_TASK_FIXTURE)
        self.assertEqual(list(out.keys()), ["L1", "L2", "M1"])
        self.assertEqual(out["L1"]["required"], ["scripts/foo.sh"])
        self.assertEqual(out["L1"]["decoy"], ["scripts/decoy.sh"])
        self.assertEqual(out["L1"]["optional"], [])
        # L2 uses ASCII hyphen instead of em-dash, has line-range suffix
        self.assertEqual(out["L2"]["required"], ["cli/src/bar.rs"])
        self.assertEqual(out["L2"]["optional"], ["docs/bar.md"])
        self.assertEqual(out["L2"]["decoy"], [])
        # M1 uses Required files: instead of Required citations:
        self.assertEqual(
            out["M1"]["required"],
            ["cli/src/main.rs", "scripts/read_session.cjs"],
        )
        self.assertEqual(out["M1"]["decoy"], ["schemas/stats.json"])

    def test_line_range_suffix_canonicalized(self) -> None:
        out = parse_ground_truth_mod.parse_ground_truth(MULTI_TASK_FIXTURE)
        # `cli/src/bar.rs:10-25` should drop the suffix.
        self.assertEqual(out["L2"]["required"], ["cli/src/bar.rs"])
        # And the L1 fixture's ci.yml:40-41 should drop too.
        out2 = parse_ground_truth_mod.parse_ground_truth(SINGLE_TASK_FIXTURE)
        self.assertIn(".github/workflows/ci.yml", out2["L1"]["required"])
        self.assertNotIn(".github/workflows/ci.yml:40-41", out2["L1"]["required"])

    def test_section_with_no_bullets_returns_empty(self) -> None:
        with redirect_stderr(io.StringIO()):
            out = parse_ground_truth_mod.parse_ground_truth(NO_BULLETS_FIXTURE)
        self.assertEqual(out["X1"]["required"], [])
        self.assertEqual(out["X1"]["optional"], [])
        self.assertEqual(out["X1"]["decoy"], [])

    def test_risk_paragraph_with_backticks_extracts_decoys(self) -> None:
        out = parse_ground_truth_mod.parse_ground_truth(SINGLE_TASK_FIXTURE)
        self.assertIn("cli/src/foo.rs", out["L1"]["decoy"])

    def test_risk_paragraph_without_backticks_returns_empty(self) -> None:
        out = parse_ground_truth_mod.parse_ground_truth(NO_RISK_BACKTICKS_FIXTURE)
        self.assertEqual(out["X2"]["decoy"], [])

    def test_em_dash_header_parsed(self) -> None:
        text = "### EM1 — Title here\nRequired citations:\n- `scripts/x.sh` — note\n"
        out = parse_ground_truth_mod.parse_ground_truth(text)
        self.assertIn("EM1", out)
        self.assertEqual(out["EM1"]["required"], ["scripts/x.sh"])

    def test_ascii_hyphen_header_parsed(self) -> None:
        text = "### AH1 - Title here\nRequired citations:\n- `scripts/y.sh` - note\n"
        out = parse_ground_truth_mod.parse_ground_truth(text)
        self.assertIn("AH1", out)
        self.assertEqual(out["AH1"]["required"], ["scripts/y.sh"])

    def test_task_id_filter_returns_only_that_task(self) -> None:
        out = parse_ground_truth_mod.parse_ground_truth(MULTI_TASK_FIXTURE, task_id="L2")
        self.assertEqual(list(out.keys()), ["L2"])

    def test_warning_emitted_when_no_required_section(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            out = parse_ground_truth_mod.parse_ground_truth(NO_REQUIRED_FIXTURE)
        self.assertEqual(out["X3"]["required"], [])
        self.assertIn("X3", buf.getvalue())
        self.assertIn("no Required citations", buf.getvalue())

    def test_dedupe_preserves_first_occurrence(self) -> None:
        text = (
            "### D1 — dedupe\n"
            "Required citations:\n"
            "- `scripts/a.sh` — first\n"
            "- `scripts/b.sh` — second\n"
            "- `scripts/a.sh` — duplicate\n"
        )
        out = parse_ground_truth_mod.parse_ground_truth(text)
        self.assertEqual(out["D1"]["required"], ["scripts/a.sh", "scripts/b.sh"])


class ParseGroundTruthCliTest(unittest.TestCase):
    def _write_tmp(self, body: str) -> pathlib.Path:
        import tempfile

        d = tempfile.mkdtemp(prefix="pgt-test-")
        p = pathlib.Path(d) / "GROUND_TRUTH.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_cli_default_emits_json_to_stdout(self) -> None:
        p = self._write_tmp(SINGLE_TASK_FIXTURE)
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = parse_ground_truth_mod.main([str(p)])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("L1", parsed)
        self.assertEqual(
            parsed["L1"]["required"][0], "scripts/conformance.sh"
        )

    def test_cli_task_id_filter(self) -> None:
        p = self._write_tmp(MULTI_TASK_FIXTURE)
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = parse_ground_truth_mod.main([str(p), "--task-id", "M1"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(list(parsed.keys()), ["M1"])

    def test_cli_unknown_task_id_returns_nonzero(self) -> None:
        p = self._write_tmp(MULTI_TASK_FIXTURE)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = parse_ground_truth_mod.main([str(p), "--task-id", "ZZ"])
        self.assertNotEqual(rc, 0)


# Optional round-trip against a real GROUND_TRUTH.md from a private rerun
# directory. Only runs when the operator points at a real path via env var
# AGENT_CONTEXT_PRIVATE_RERUN_ROOT — keeps the public test suite portable
# (no machine-specific hardcoded paths) while preserving the round-trip
# check for maintainers.
_PRIVATE_RERUN_ROOT = os.environ.get("AGENT_CONTEXT_PRIVATE_RERUN_ROOT", "")
REAL_GT_PATH = (
    pathlib.Path(_PRIVATE_RERUN_ROOT).expanduser() / "agent-chorus" / "GROUND_TRUTH.md"
    if _PRIVATE_RERUN_ROOT
    else None
)


class ParseGroundTruthRoundTripTest(unittest.TestCase):
    @unittest.skipUnless(
        REAL_GT_PATH is not None and REAL_GT_PATH.exists(),
        "set AGENT_CONTEXT_PRIVATE_RERUN_ROOT=<path> to enable the real-file round-trip test",
    )
    def test_real_ground_truth_has_all_six_tasks(self) -> None:
        text = REAL_GT_PATH.read_text(encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            out = parse_ground_truth_mod.parse_ground_truth(text)
        self.assertEqual(
            sorted(out.keys()),
            sorted(["L1", "L2", "M1", "M2", "H1", "H2"]),
            f"unexpected task ids in real GROUND_TRUTH.md: {sorted(out.keys())}",
        )
        # L1 should at minimum surface scripts/conformance.sh as a required path.
        self.assertIn("scripts/conformance.sh", out["L1"]["required"])
        # M1 should surface its full required-files list including the new schema.
        self.assertIn("schemas/stats.json", out["M1"]["required"])


if __name__ == "__main__":
    unittest.main()
