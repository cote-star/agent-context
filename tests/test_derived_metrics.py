"""Per-cell aggregation tests for scripts/experiments/derived-metrics.py.

Synthesizes schema-v3 result JSONs in a tmpdir, runs derived-metrics.py
against the layout it expects in the wild
(`<dir>/<repo>/results/<agent>/<condition>/<model-slug>/T*.json`), and
verifies that each of the 28 derived metrics matches a hand-computed
expected value.

Stdlib-only `unittest`, matching the rest of the suite.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "experiments" / "derived-metrics.py"


def _load_module():
    """Import derived-metrics.py despite its hyphenated filename."""
    spec = importlib.util.spec_from_file_location("derived_metrics", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dm = _load_module()


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------

def _base_row(idx: int, **overrides):
    """Minimal v3-shaped result row, easy to override per test."""
    row = {
        "task_id": f"T{idx}",
        "agent": "claude",
        "capture_method": "cli",
        "condition": "structured_fresh",
        "repo": "agent-chorus",
        "started_at": "2026-05-08T10:00:00Z",
        "finished_at": "2026-05-08T10:00:30Z",
        "files_opened_count": 5,
        "dead_ends": 1,
        "first_correct_file_hop": 2,
        "files_opened_after_first_correct_hop": 3,
        "post_hit_dead_ends": 0,
        "tool_calls": {"read_file": 4, "grep": 1, "glob_file_search": 0},
        "tool_call_events": [
            {"tool": "read_file", "path": ".agent-context/current/INDEX.md",
             "ts": "2026-05-08T10:00:01Z"},
            {"tool": "read_file", "path": "src/foo.py",
             "ts": "2026-05-08T10:00:05Z"},
        ],
        "source_read_events": [
            {"tool": "read_file", "path": "src/foo.py",
             "ts": "2026-05-08T10:00:05Z"},
        ],
        "unique_source_paths_read": 1,
        "dead_end_paths": ["src/decoy.py"],
        "first_correct_file_ts": "2026-05-08T10:00:05Z",
        "ground_truth_required_paths": ["src/foo.py"],
        "ground_truth_optional_paths": ["src/bar.py"],
        "ground_truth_decoy_paths": ["src/decoy.py"],
        "duration_seconds": 30.0,
        "answer": "the answer",
        "citations": [{"path": "src/foo.py", "line": 1, "note": ""}],
        "correct": "yes",
        "correctness_notes": "",
        "grading_method": "reviewer-confirmed",
        "quality_self_score": 8,
        "risk_flag": False,
        "risk_flag_explanation": "",
        "model_id": "claude-opus-4-7",
        "permission_prompts_count": 0,
        "interrupted": False,
    }
    row.update(overrides)
    return row


def _write_cell(
    root: pathlib.Path,
    rows,
    repo: str = "agent-chorus",
    agent: str = "claude",
    condition: str = "structured_fresh",
    model_slug: str = "claude-opus-4-7",
):
    """Lay out a cell directory in the canonical rerun shape and write rows."""
    cell_dir = root / repo / "results" / agent / condition / model_slug
    cell_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(rows, start=1):
        (cell_dir / f"T{i}.json").write_text(json.dumps(row) + "\n")
    return cell_dir


def _make_six(**common) -> list[dict]:
    """Six rows pre-shaped to a baseline cell. `common` overrides on every row."""
    return [_base_row(i, **common) for i in range(1, 7)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class DiscoveryTests(unittest.TestCase):
    def test_discover_skips_judge_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cell = _write_cell(root, _make_six())
            (cell / "T1.judge.json").write_text("{}")
            paths = dm.discover_results(root)
            names = sorted(p.name for p in paths)
            self.assertEqual(names, [f"T{i}.json" for i in range(1, 7)])

    def test_discover_returns_empty_when_layout_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dm.discover_results(pathlib.Path(tmp)), [])


class CorrectnessAndOutcomeTests(unittest.TestCase):
    def test_correctness_rates_and_risk_flag_rate(self):
        rows = _make_six()
        # Force outcomes: 4 yes, 1 partial, 1 no; 2 risk-flagged.
        rows[0]["correct"] = "yes"
        rows[1]["correct"] = "yes"
        rows[2]["correct"] = "yes"
        rows[3]["correct"] = "yes"
        rows[4]["correct"] = "partial"
        rows[5]["correct"] = "no"
        rows[0]["risk_flag"] = True
        rows[1]["risk_flag"] = True
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["correctness_yes_rate"], 4 / 6)
        self.assertAlmostEqual(m["correctness_partial_rate"], 1 / 6)
        self.assertAlmostEqual(m["correctness_no_rate"], 1 / 6)
        self.assertAlmostEqual(m["risk_flag_rate"], 2 / 6)

    def test_citation_precision_handles_null_ground_truth(self):
        rows = _make_six()
        # First row: 1/2 cites are valid. Other rows: ground-truth-null → skipped.
        rows[0]["citations"] = [
            {"path": "src/foo.py"},   # required → valid
            {"path": "src/bogus.py"}, # not in required ∪ optional
        ]
        for r in rows[1:]:
            r["ground_truth_required_paths"] = None
            r["ground_truth_optional_paths"] = None
        m = dm.compute_cell_metrics(rows)
        # Only row 0 contributes, with precision 0.5.
        self.assertAlmostEqual(m["citation_precision"], 0.5)


class SpeedTests(unittest.TestCase):
    def test_duration_and_seconds_per_correct(self):
        rows = _make_six()
        for i, dur in enumerate([10.0, 20.0, 30.0, 40.0, 50.0, 60.0]):
            rows[i]["duration_seconds"] = dur
        # 3 yes + 1 partial + 2 no → denom = 3 + 0.5 = 3.5
        rows[0]["correct"] = "yes"
        rows[1]["correct"] = "yes"
        rows[2]["correct"] = "yes"
        rows[3]["correct"] = "partial"
        rows[4]["correct"] = "no"
        rows[5]["correct"] = "no"
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["duration_seconds_median"], 35.0)
        self.assertAlmostEqual(m["duration_seconds_mean"], 210.0 / 6)
        self.assertAlmostEqual(m["seconds_per_correct"], 210.0 / 3.5)

    def test_seconds_per_correct_division_by_zero_is_null(self):
        rows = _make_six(correct="no")
        m = dm.compute_cell_metrics(rows)
        self.assertIsNone(m["seconds_per_correct"])
        # tokens_total_per_correct uses the same denominator semantics.
        self.assertIsNone(m["tokens_total_per_correct"])

    def test_ttfcf_seconds_median_skips_nulls(self):
        rows = _make_six()
        # Row 0: 5s. Row 1: 15s. Row 2: null first_correct_file_ts → skipped.
        rows[0]["started_at"] = "2026-05-08T10:00:00Z"
        rows[0]["first_correct_file_ts"] = "2026-05-08T10:00:05Z"
        rows[1]["started_at"] = "2026-05-08T10:00:00Z"
        rows[1]["first_correct_file_ts"] = "2026-05-08T10:00:15Z"
        rows[2]["first_correct_file_ts"] = None
        for r in rows[3:]:
            r["first_correct_file_ts"] = None
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["ttfcf_seconds_median"], 10.0)


class NavigationTests(unittest.TestCase):
    def test_search_vs_read_ratio_and_tool_call_aggregates(self):
        rows = _make_six()
        # Each row: 4 reads, 2 grep, 1 glob, 1 find → searches=4, reads=4 → ratio=1.0
        for r in rows:
            r["tool_calls"] = {
                "read_file": 4, "grep": 2, "glob_file_search": 1, "find": 1,
            }
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["search_vs_read_ratio"], 1.0)
        self.assertAlmostEqual(m["tool_calls_total_mean"], 8.0)
        # 6 yes → denom 6, sum=48, per_correct=8.
        self.assertAlmostEqual(m["tool_calls_per_correct"], 8.0)

    def test_re_read_rate_and_pack_precedence(self):
        rows = _make_six()
        # Row 0 reads foo.py twice and bar.py once → 1 repeated of 3 paths = 1/3.
        rows[0]["source_read_events"] = [
            {"path": "src/foo.py"},
            {"path": "src/foo.py"},
            {"path": "src/bar.py"},
        ]
        # Row 0 first event is a pack-current read → True.
        rows[0]["tool_call_events"] = [
            {"tool": "read_file", "path": ".agent-context/current/INDEX.md",
             "ts": "2026-05-08T10:00:01Z"},
            {"tool": "read_file", "path": "src/foo.py",
             "ts": "2026-05-08T10:00:05Z"},
        ]
        # Row 1 first event is a source read → False; null source_read_events
        # so it's excluded from the re-read mean (only row 0 contributes).
        rows[1]["tool_call_events"] = [
            {"tool": "read_file", "path": "src/baz.py",
             "ts": "2026-05-08T10:00:01Z"},
        ]
        rows[1]["source_read_events"] = None
        # Other rows null events → skipped from rates.
        for r in rows[2:]:
            r["tool_call_events"] = None
            r["source_read_events"] = None

        m = dm.compute_cell_metrics(rows)
        # Only row 0 contributes (3 reads, foo.py repeats once) → 1/3.
        self.assertAlmostEqual(m["re_read_rate"], 1 / 3)
        # 1 of 2 tasks has pack precedence → 0.5.
        self.assertAlmostEqual(m["pack_read_precedence_rate"], 0.5)
        self.assertEqual(m["first_tool_call_type"]["dominant"], "read")

    def test_pack_utilization_mean_distinct_paths(self):
        rows = _make_six()
        rows[0]["tool_call_events"] = [
            {"tool": "read_file", "path": ".agent-context/current/INDEX.md", "ts": "x"},
            {"tool": "read_file", "path": ".agent-context/current/HOTSPOTS.md", "ts": "x"},
            {"tool": "read_file", "path": ".agent-context/current/INDEX.md", "ts": "x"},
            {"tool": "read_file", "path": "src/foo.py", "ts": "x"},
        ]
        # Distinct pack-current paths in row 0 = 2; rows 1..5 baseline has 1.
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["pack_utilization_rate"], (2 + 1 * 5) / 6)

    def test_unique_dead_ends_means(self):
        rows = _make_six()
        for i, val in enumerate([1, 2, 3, 4, 5, 6]):
            rows[i]["unique_source_paths_read"] = val
            rows[i]["dead_ends"] = val
            rows[i]["post_hit_dead_ends"] = val - 1
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["unique_source_files_opened_mean"], 21 / 6)
        self.assertAlmostEqual(m["dead_ends_mean"], 21 / 6)
        self.assertAlmostEqual(m["post_hit_dead_ends_mean"], 15 / 6)

    def test_verification_shortcut_hit_rate_null_when_field_absent(self):
        m = dm.compute_cell_metrics(_make_six())
        self.assertIsNone(m["verification_shortcut_hit_rate"])

    def test_verification_shortcut_hit_rate_computed_from_field(self):
        rows = _make_six()
        shortcuts = ["src/server.py", "src/config.py", "src/handler.py"]
        # Row 0: read 3/3 shortcuts (hit-rate 1.0).
        rows[0]["verification_shortcut_paths"] = shortcuts
        rows[0]["source_read_events"] = [{"path": p} for p in shortcuts]
        # Row 1: read 1/3 (hit-rate 0.333).
        rows[1]["verification_shortcut_paths"] = shortcuts
        rows[1]["source_read_events"] = [{"path": "src/server.py"}]
        # Row 2: read 0/3 (hit-rate 0.0).
        rows[2]["verification_shortcut_paths"] = shortcuts
        rows[2]["source_read_events"] = [{"path": "unrelated.py"}]
        # Rows 3-5: shortcuts field absent (null) — excluded from mean.

        m = dm.compute_cell_metrics(rows)
        # Mean of (1.0, 1/3, 0.0) = ~0.444
        self.assertAlmostEqual(m["verification_shortcut_hit_rate"], (1.0 + 1/3 + 0.0) / 3)

    def test_verification_shortcut_hit_rate_falls_back_to_citations(self):
        """Cursor doesn't emit source_read_events. A cited shortcut still counts."""
        rows = _make_six()
        shortcuts = ["src/server.py", "src/config.py", "src/handler.py"]
        # Row 0: no reads, but cites 2/3 shortcut paths → hit-rate 2/3.
        rows[0]["verification_shortcut_paths"] = shortcuts
        rows[0]["source_read_events"] = None
        rows[0]["citations"] = [{"path": "src/server.py"}, {"path": "src/config.py"}]
        # Row 1: cites a non-shortcut path → hit-rate 0.
        rows[1]["verification_shortcut_paths"] = shortcuts
        rows[1]["source_read_events"] = None
        rows[1]["citations"] = [{"path": "unrelated.py"}]
        # Row 2: read AND cite, dedup → still 1/3.
        rows[2]["verification_shortcut_paths"] = shortcuts
        rows[2]["source_read_events"] = [{"path": "src/server.py"}]
        rows[2]["citations"] = [{"path": "src/server.py"}]
        # Rows 3-5: no shortcuts.

        m = dm.compute_cell_metrics(rows)
        # Mean of (2/3, 0.0, 1/3) ≈ 0.333
        self.assertAlmostEqual(m["verification_shortcut_hit_rate"], (2/3 + 0.0 + 1/3) / 3)


class DiscoveryGlobLayoutTests(unittest.TestCase):
    """discover_results must find both the model-aware and legacy result layouts."""

    def test_discover_finds_model_aware_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # 5-level: <repo>/results/<agent>/<condition>/<model-slug>/T*.json
            cell = root / "agent-chorus" / "results" / "cursor" / "bare" / "claude-opus-4-7-medium"
            cell.mkdir(parents=True)
            (cell / "L1.json").write_text("{}")
            paths = dm.discover_results(root)
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].name, "L1.json")

    def test_discover_finds_legacy_no_model_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # 4-level: <repo>/results/<agent>/<condition>/T*.json
            cell = root / "agent-chorus" / "results" / "claude" / "bare"
            cell.mkdir(parents=True)
            (cell / "L1.json").write_text("{}")
            paths = dm.discover_results(root)
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].name, "L1.json")

    def test_discover_handles_both_layouts_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "r1" / "results" / "claude" / "bare").mkdir(parents=True)
            (root / "r1" / "results" / "claude" / "bare" / "L1.json").write_text("{}")
            (root / "r2" / "results" / "cursor" / "bare" / "composer-2-fast").mkdir(parents=True)
            (root / "r2" / "results" / "cursor" / "bare" / "composer-2-fast" / "M1.json").write_text("{}")
            paths = dm.discover_results(root)
            self.assertEqual(len(paths), 2)
            names = sorted(p.name for p in paths)
            self.assertEqual(names, ["L1.json", "M1.json"])

    def test_discover_honours_skipped_marker(self):
        """A repo with .skipped is excluded from discovery so metrics ignore it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "good" / "results" / "claude" / "bare").mkdir(parents=True)
            (root / "good" / "results" / "claude" / "bare" / "L1.json").write_text("{}")
            (root / "broken" / "results" / "claude" / "bare").mkdir(parents=True)
            (root / "broken" / "results" / "claude" / "bare" / "L1.json").write_text("{}")
            (root / "broken" / ".skipped").write_text("setup needs review\n")

            paths = dm.discover_results(root)
            self.assertEqual(len(paths), 1)
            self.assertIn("good", str(paths[0]))
            self.assertNotIn("broken", str(paths[0]))


class OutputQualityTests(unittest.TestCase):
    def test_citations_count_and_required_recall(self):
        rows = _make_six()
        # Row 0: required=[a,b], cites a (hit), reads b (hit) → recall=1.
        rows[0]["ground_truth_required_paths"] = ["src/a.py", "src/b.py"]
        rows[0]["citations"] = [{"path": "src/a.py"}, {"path": "src/c.py"}]
        rows[0]["source_read_events"] = [{"path": "src/b.py"}]
        # Row 1: required=[a], hit nothing → recall=0.
        rows[1]["ground_truth_required_paths"] = ["src/a.py"]
        rows[1]["citations"] = [{"path": "src/c.py"}]
        rows[1]["source_read_events"] = [{"path": "src/d.py"}]
        # Other rows: null required → skipped.
        for r in rows[2:]:
            r["ground_truth_required_paths"] = None
        m = dm.compute_cell_metrics(rows)
        # citations_count_mean: row0=2, row1=1, rows2..5 baseline=1 each → 7/6.
        self.assertAlmostEqual(m["citations_count_mean"], 7 / 6)
        self.assertAlmostEqual(m["ground_truth_required_recall"], 0.5)


class CostTests(unittest.TestCase):
    def test_cell_replicated_token_dedup(self):
        rows = _make_six()
        # cell_replicated: every row stamped with the SAME session total.
        for r in rows:
            r["tokens_total"] = 60_000
            r["token_metric_scope"] = "cell_replicated"
        # All 6 yes → denom 6. Expected per-correct after dedup:
        #   each row contributes 60000/6 = 10000, sum = 60000, /6 = 10000.
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["tokens_total_per_correct"], 60_000 / 6)

    def test_cost_and_thinking_share(self):
        rows = _make_six()
        for i, c in enumerate([0.10, 0.20, 0.30, 0.40, 0.50, 0.60]):
            rows[i]["cost_usd"] = c
        # tokens_thinking_share: 2 rows with valid splits → mean of shares.
        rows[0]["tokens_total"] = 1000
        rows[0]["tokens_thinking"] = 250
        rows[1]["tokens_total"] = 2000
        rows[1]["tokens_thinking"] = 1000
        # 6 yes → denom 6.
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["cost_usd_per_correct"], 2.10 / 6)
        self.assertAlmostEqual(m["tokens_thinking_share"], (0.25 + 0.5) / 2)

    def test_token_metrics_null_when_absent(self):
        m = dm.compute_cell_metrics(_make_six())
        self.assertIsNone(m["tokens_total_per_correct"])
        self.assertIsNone(m["cost_usd_per_correct"])
        self.assertIsNone(m["tokens_thinking_share"])


class FrictionTests(unittest.TestCase):
    def test_permission_prompts_and_interrupted(self):
        rows = _make_six()
        for i, p in enumerate([0, 1, 2, 3, 4, 5]):
            rows[i]["permission_prompts_count"] = p
        rows[0]["interrupted"] = True
        rows[1]["interrupted"] = True
        m = dm.compute_cell_metrics(rows)
        self.assertAlmostEqual(m["permission_prompts_mean"], 15 / 6)
        self.assertAlmostEqual(m["interrupted_rate"], 2 / 6)


class CliTests(unittest.TestCase):
    def test_cli_emits_expected_cell_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _write_cell(root, _make_six())
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--results", str(root),
                    "--out-json", str(out_json),
                    "--out-md", str(out_md),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0,
                             msg=f"stderr={result.stderr}")
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())
            payload = json.loads(out_json.read_text())
            self.assertIn("generated_at", payload)
            self.assertEqual(len(payload["cells"]), 1)
            cell = payload["cells"][0]
            self.assertEqual(cell["agent"], "claude")
            self.assertEqual(cell["condition"], "structured_fresh")
            self.assertEqual(cell["repo"], "agent-chorus")
            self.assertEqual(cell["task_count"], 6)
            # All baseline rows are correct=yes → yes_rate = 1.0.
            self.assertAlmostEqual(cell["metrics"]["correctness_yes_rate"], 1.0)
            md = out_md.read_text()
            self.assertIn("A. Outcome", md)
            self.assertIn("F. Operator friction", md)

    def test_cli_omits_empty_cells_via_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _write_cell(root, _make_six())
            out_json = root / "out.json"
            # Filter to a cell that doesn't exist → expect zero cells, no crash.
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--results", str(root),
                    "--out-json", str(out_json),
                    "--cells", "codex/bare/some-other-repo",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0,
                             msg=f"stderr={result.stderr}")
            payload = json.loads(out_json.read_text())
            self.assertEqual(payload["cells"], [])

    def test_cli_errors_on_missing_results_dir(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT_PATH),
                "--results", "/no/such/path/should/exist/here",
            ],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
