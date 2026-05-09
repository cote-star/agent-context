"""Unit tests for scripts/experiments/extract-events-from-chorus.py.

We don't run chorus here. Instead we exercise the script's pure helpers
directly against a synthesized claude-session-shaped JSONL to keep the
tests hermetic and fast. The chorus-orchestration layer in `main()` is a
thin wrapper around `extract-tokens-from-chorus.py`'s already-tested
pattern; what's new (and worth covering) is the JSONL walker plus the
per-task derivations.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "experiments" / "extract-events-from-chorus.py"


def _load_module():
    """Load the script as a module — its filename has dashes so we can't `import` directly."""
    spec = importlib.util.spec_from_file_location("extract_events_from_chorus", SCRIPT_PATH)
    assert spec and spec.loader, f"could not spec-load {SCRIPT_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


EE = _load_module()


# A fixed cwd we'll synthesise events under, to test relative/absolute path
# normalisation deterministically.
FAKE_CWD = "/tmp/agent-rerun/structured_fresh"


def _envelope(ts: str, blocks: list, *, cwd: str = FAKE_CWD, kind: str = "assistant") -> dict:
    return {
        "type": kind,
        "timestamp": ts,
        "cwd": cwd,
        "sessionId": "fake-session",
        "message": {
            "model": "claude-opus-test",
            "id": f"msg_{ts}",
            "type": "message",
            "role": "assistant",
            "content": blocks,
        },
    }


def _tool_use(name: str, tool_input: dict) -> dict:
    return {
        "type": "tool_use",
        "id": f"toolu_{name}_{abs(hash(json.dumps(tool_input, sort_keys=True))) % 100000}",
        "name": name,
        "input": tool_input,
    }


def _write_jsonl(tmp: pathlib.Path, lines: list) -> pathlib.Path:
    p = tmp / "session.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for obj in lines:
            fh.write(json.dumps(obj) + "\n")
    return p


class WalkClaudeSessionEventsTest(unittest.TestCase):
    """Exercise the JSONL walker directly."""

    def test_mixed_events_yield_expected_count_and_paths(self) -> None:
        # 4 events: Read with file_path, Grep (no path), Bash (no path), Read again.
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp, [
                _envelope("2026-05-04T10:00:00.000Z", [
                    _tool_use("Read", {"file_path": f"{FAKE_CWD}/src/index.tsx"}),
                ]),
                _envelope("2026-05-04T10:00:01.000Z", [
                    _tool_use("Grep", {"pattern": "TODO", "path": f"{FAKE_CWD}/src"}),
                ]),
                _envelope("2026-05-04T10:00:02.000Z", [
                    _tool_use("Bash", {"command": "ls -la"}),
                ]),
                _envelope("2026-05-04T10:00:03.000Z", [
                    _tool_use("Read", {"file_path": f"{FAKE_CWD}/src/api.ts"}),
                ]),
            ])
            events = EE.walk_claude_session_events(jsonl)

        self.assertEqual(len(events), 4)
        self.assertEqual([e["tool"] for e in events], ["Read", "Grep", "Bash", "Read"])
        # Read events keep the absolute path; Grep/Bash have path=None.
        self.assertEqual(events[0]["path"], f"{FAKE_CWD}/src/index.tsx")
        self.assertIsNone(events[1]["path"])
        self.assertIsNone(events[2]["path"])
        self.assertEqual(events[3]["path"], f"{FAKE_CWD}/src/api.ts")
        # Each event preserves the raw args dict.
        self.assertEqual(events[0]["args"], {"file_path": f"{FAKE_CWD}/src/index.tsx"})
        self.assertEqual(events[2]["args"], {"command": "ls -la"})

    def test_session_with_no_tool_use_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp, [
                # Just a permission-mode line + a user prompt + an assistant text reply.
                {"type": "permission-mode", "permissionMode": "auto"},
                {
                    "type": "user", "timestamp": "2026-05-04T10:00:00.000Z",
                    "message": {"role": "user", "content": "hi"},
                },
                _envelope("2026-05-04T10:00:01.000Z", [
                    {"type": "text", "text": "Sure, here's an answer."},
                ]),
            ])
            events = EE.walk_claude_session_events(jsonl)
        self.assertEqual(events, [])

    def test_tool_use_missing_timestamp_is_skipped_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            # Build envelope manually so we can drop the timestamp.
            bad_env = _envelope("2026-05-04T10:00:00.000Z", [
                _tool_use("Read", {"file_path": f"{FAKE_CWD}/x.txt"}),
            ])
            del bad_env["timestamp"]
            good_env = _envelope("2026-05-04T10:00:01.000Z", [
                _tool_use("Read", {"file_path": f"{FAKE_CWD}/y.txt"}),
            ])
            jsonl = _write_jsonl(tmp, [bad_env, good_env])
            events = EE.walk_claude_session_events(jsonl)
        # Only the well-formed event survives; the missing-ts one is skipped.
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["path"], f"{FAKE_CWD}/y.txt")


class DerivationTests(unittest.TestCase):
    """Cover the derived-stable-fields helpers."""

    def _make_events(self) -> list:
        # Mix of source reads, an .agent-context read, a Grep, a Bash.
        return [
            {"tool": "Read", "path": f"{FAKE_CWD}/src/index.tsx", "ts": "2026-05-04T10:00:00.000Z", "args": {}},
            {"tool": "Read", "path": f"{FAKE_CWD}/.agent-context/current/manifest.json", "ts": "2026-05-04T10:00:01.000Z", "args": {}},
            {"tool": "Grep", "path": None, "ts": "2026-05-04T10:00:02.000Z", "args": {}},
            {"tool": "Read", "path": f"{FAKE_CWD}/src/api.ts", "ts": "2026-05-04T10:00:03.000Z", "args": {}},
            {"tool": "Read", "path": f"{FAKE_CWD}/src/index.tsx", "ts": "2026-05-04T10:00:04.000Z", "args": {}},
            {"tool": "Bash", "path": None, "ts": "2026-05-04T10:00:05.000Z", "args": {}},
        ]

    def test_source_read_filter_excludes_agent_context_paths(self) -> None:
        evs = self._make_events()
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        # 3 Reads under src/ remain; the .agent-context one is filtered;
        # Grep/Bash are filtered (path=None).
        self.assertEqual(len(srcs), 3)
        self.assertTrue(all(not e["path"].startswith(".agent-context/") for e in srcs))
        self.assertEqual(
            [e["path"] for e in srcs],
            ["src/index.tsx", "src/api.ts", "src/index.tsx"],
        )

    def test_unique_source_paths_count_dedupes_repeated_reads(self) -> None:
        evs = self._make_events()
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        # src/index.tsx appears twice, src/api.ts once → 2 unique.
        self.assertEqual(EE.derive_unique_source_paths(srcs), 2)
        # And the source_read_events list has both occurrences (re-read tracking).
        self.assertEqual(len(srcs), 3)

    def test_first_correct_file_ts_picks_earliest_match(self) -> None:
        evs = self._make_events()
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        ts = EE.derive_first_correct_file_ts(srcs, ["src/api.ts"])
        # src/api.ts is the third source-read event; its ts is 10:00:03.
        self.assertEqual(ts, "2026-05-04T10:00:03.000Z")

    def test_first_correct_file_ts_is_null_without_match(self) -> None:
        evs = self._make_events()
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        self.assertIsNone(EE.derive_first_correct_file_ts(srcs, ["unrelated/path.ts"]))
        self.assertIsNone(EE.derive_first_correct_file_ts(srcs, []))
        self.assertIsNone(EE.derive_first_correct_file_ts(srcs, None))

    def test_dead_end_paths_excludes_required_optional_and_cited(self) -> None:
        evs = self._make_events()
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        dead = EE.derive_dead_end_paths(
            srcs,
            required_paths=["src/index.tsx"],
            optional_paths=[],
            citations=[{"path": "src/api.ts"}],
        )
        # Both source paths are accounted for → no dead ends.
        self.assertEqual(dead, [])

    def test_dead_end_paths_returns_unaccounted_paths(self) -> None:
        evs = self._make_events() + [
            {"tool": "Read", "path": f"{FAKE_CWD}/decoy/wander.ts", "ts": "2026-05-04T10:00:06.000Z", "args": {}},
        ]
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        dead = EE.derive_dead_end_paths(
            srcs,
            required_paths=["src/index.tsx"],
            optional_paths=[],
            citations=[{"path": "src/api.ts"}],
        )
        self.assertEqual(dead, ["decoy/wander.ts"])

    def test_dead_end_paths_is_null_with_no_signal(self) -> None:
        evs = self._make_events()
        srcs = EE.derive_source_read_events(evs, cwd=FAKE_CWD)
        # No required/optional/citations → return None (we have no signal to compute).
        self.assertIsNone(EE.derive_dead_end_paths(srcs, None, None, None))


class StampResultTests(unittest.TestCase):
    """End-to-end: synthesize a JSONL + a result JSON, stamp, verify, re-stamp."""

    def _setup_stamp_fixture(self, td: pathlib.Path):
        # Build a small JSONL with a known event sequence.
        jsonl = _write_jsonl(td, [
            _envelope("2026-05-04T10:00:00.000Z", [
                _tool_use("Read", {"file_path": f"{FAKE_CWD}/src/index.tsx"}),
            ]),
            _envelope("2026-05-04T10:00:01.000Z", [
                _tool_use("Read", {"file_path": f"{FAKE_CWD}/.agent-context/current/manifest.json"}),
            ]),
            _envelope("2026-05-04T10:00:02.000Z", [
                _tool_use("Grep", {"pattern": "QueryClient"}),
            ]),
            _envelope("2026-05-04T10:00:03.000Z", [
                _tool_use("Read", {"file_path": f"{FAKE_CWD}/src/api.ts"}),
            ]),
            _envelope("2026-05-04T10:00:04.000Z", [
                _tool_use("Read", {"file_path": f"{FAKE_CWD}/src/index.tsx"}),  # re-read
            ]),
        ])
        # Build a v2-shaped result JSON to stamp onto.
        result = {
            "task_id": "L1",
            "agent": "claude",
            "capture_method": "cli",
            "condition": "structured_fresh",
            "repo": "demo",
            "started_at": "2026-05-04T10:00:00Z",
            "finished_at": "2026-05-04T10:00:10Z",
            "files_opened_count": 0,
            "dead_ends": 0,
            "first_correct_file_hop": 0,
            "files_opened_after_first_correct_hop": 0,
            "post_hit_dead_ends": 0,
            "tool_calls": {},
            "duration_seconds": 10,
            "answer": "...",
            "citations": [{"path": "src/index.tsx", "line": 17, "note": "hit"}],
            "correct": "ungraded",
            "correctness_notes": "",
            "grading_method": "ungraded",
            "quality_self_score": 8,
            "risk_flag": False,
            "risk_flag_explanation": "",
        }
        result_path = td / "L1.json"
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return jsonl, result_path

    def test_stamp_with_ground_truth_populates_all_v3_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl, result_path = self._setup_stamp_fixture(tmp)
            events = EE.walk_claude_session_events(jsonl)
            gt = {
                "required": ["src/index.tsx"],
                "optional": [],
                "decoy": ["decoy/wander.ts"],
            }
            stamped = EE.stamp_result(result_path, events, cwd=FAKE_CWD, ground_truth=gt)
            EE.write_result(result_path, stamped)

            d = json.loads(result_path.read_text())
            # Event stream preserved verbatim (5 raw events including .agent-context one).
            self.assertEqual(len(d["tool_call_events"]), 5)
            # Source-read filter strips Grep + .agent-context read.
            self.assertEqual(len(d["source_read_events"]), 3)
            # Two unique source paths even though one was re-read.
            self.assertEqual(d["unique_source_paths_read"], 2)
            # First match is src/index.tsx at the first event ts.
            self.assertEqual(d["first_correct_file_ts"], "2026-05-04T10:00:00.000Z")
            # src/api.ts is not in required/optional but IS cited → not a dead end here.
            # Wait — citations have only src/index.tsx. So src/api.ts is unaccounted.
            self.assertEqual(d["dead_end_paths"], ["src/api.ts"])
            # Aggregate tool_calls re-derived from the event stream.
            self.assertEqual(d["tool_calls"], {"Read": 4, "Grep": 1})
            # Ground-truth path arrays stamped through.
            self.assertEqual(d["ground_truth_required_paths"], ["src/index.tsx"])
            self.assertEqual(d["ground_truth_decoy_paths"], ["decoy/wander.ts"])

    def test_stamp_without_ground_truth_leaves_first_correct_and_dead_ends_null(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl, result_path = self._setup_stamp_fixture(tmp)
            # Drop citations too so dead_end_paths has zero signal.
            data = json.loads(result_path.read_text())
            data["citations"] = []
            result_path.write_text(json.dumps(data, indent=2) + "\n")
            events = EE.walk_claude_session_events(jsonl)
            stamped = EE.stamp_result(result_path, events, cwd=FAKE_CWD, ground_truth=None)
            EE.write_result(result_path, stamped)
            d = json.loads(result_path.read_text())
            # Event stream + source-read derivations still computed.
            self.assertEqual(len(d["tool_call_events"]), 5)
            self.assertEqual(d["unique_source_paths_read"], 2)
            # No ground truth + no citations → can't compute either.
            self.assertIsNone(d["first_correct_file_ts"])
            self.assertIsNone(d["dead_end_paths"])
            # ground_truth_* keys are NOT added when no ground-truth was passed.
            self.assertNotIn("ground_truth_required_paths", d)

    def test_stamp_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl, result_path = self._setup_stamp_fixture(tmp)
            events = EE.walk_claude_session_events(jsonl)
            gt = {"required": ["src/index.tsx"], "optional": [], "decoy": []}
            EE.write_result(result_path, EE.stamp_result(result_path, events, cwd=FAKE_CWD, ground_truth=gt))
            first = result_path.read_bytes()
            EE.write_result(result_path, EE.stamp_result(result_path, events, cwd=FAKE_CWD, ground_truth=gt))
            second = result_path.read_bytes()
            self.assertEqual(first, second, "stamp_result must be idempotent on stable input")


class GroundTruthLoadingTests(unittest.TestCase):
    def test_load_from_per_task_json_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            gt_file = tmp / "gt.json"
            gt_file.write_text(json.dumps({
                "L1": {"required": ["a.ts"], "optional": ["b.ts"], "decoy": ["c.ts"]},
                "L2": {"required": ["d.ts"], "optional": [], "decoy": []},
            }))
            tid, payload = EE.load_ground_truth_paths(f"L1={gt_file}")
            self.assertEqual(tid, "L1")
            self.assertEqual(payload["required"], ["a.ts"])
            self.assertEqual(payload["optional"], ["b.ts"])
            self.assertEqual(payload["decoy"], ["c.ts"])

    def test_load_from_single_task_json_dict(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            gt_file = tmp / "gt.json"
            gt_file.write_text(json.dumps({"required": ["x.ts"], "optional": [], "decoy": []}))
            tid, payload = EE.load_ground_truth_paths(f"L9={gt_file}")
            self.assertEqual(tid, "L9")
            self.assertEqual(payload["required"], ["x.ts"])

    def test_load_rejects_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            EE.load_ground_truth_paths("L1=/no/such/file.json")


class SegmentEventsByTaskTests(unittest.TestCase):
    """Splits a cell-level event stream into per-task slices via Write boundaries."""

    @staticmethod
    def _ev(tool: str, path: str | None, ts: str) -> dict:
        return {"tool": tool, "path": path, "ts": ts, "args": {}}

    def test_basic_two_task_split(self) -> None:
        events = [
            self._ev("Read", "src/api.py", "t1"),
            self._ev("Grep", None, "t2"),
            self._ev("Write", "../results/cursor/bare/L1.json", "t3"),
            self._ev("Read", "src/server.py", "t4"),
            self._ev("Write", "../results/cursor/bare/L2.json", "t5"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"L1", "L2"})
        self.assertEqual([e["ts"] for e in segs["L1"]], ["t1", "t2", "t3"])
        self.assertEqual([e["ts"] for e in segs["L2"]], ["t4", "t5"])

    def test_model_aware_path_segmented(self) -> None:
        events = [
            self._ev("Read", "src/api.py", "t1"),
            self._ev("Write", "../results/cursor/bare/claude-opus-4-7-medium/M1.json", "t2"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"M1"})
        self.assertEqual(len(segs["M1"]), 2)

    def test_rewrite_accumulates_across_writes(self) -> None:
        """If a task is rewritten, events between the writes still attribute to that task."""
        events = [
            self._ev("Read", "a.py", "t1"),
            self._ev("Write", "../results/cursor/bare/L1.json", "t2"),
            self._ev("Read", "b.py", "t3"),
            self._ev("Write", "../results/cursor/bare/L1.json", "t4"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"L1"})
        self.assertEqual(len(segs["L1"]), 4)

    def test_trailing_events_without_write_dropped(self) -> None:
        """Events after the final task-write have no boundary and are excluded."""
        events = [
            self._ev("Write", "../results/cursor/bare/L1.json", "t1"),
            self._ev("Read", "some/path.py", "t2"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"L1"})
        self.assertEqual(len(segs["L1"]), 1)

    def test_non_task_writes_dont_segment(self) -> None:
        """Writes to paths that aren't task-result JSONs don't create segments."""
        events = [
            self._ev("Write", "src/output.txt", "t1"),
            self._ev("Read", "a.py", "t2"),
            self._ev("Write", "../results/cursor/bare/L1.json", "t3"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"L1"})
        # All three events accumulated until the L1 write.
        self.assertEqual(len(segs["L1"]), 3)

    def test_only_valid_task_ids_match(self) -> None:
        """Writes to L1.json segment, but writes to L99.json or other.json don't."""
        events = [
            self._ev("Write", "../results/cursor/bare/L99.json", "t1"),
            self._ev("Write", "../results/cursor/bare/other.json", "t2"),
            self._ev("Write", "../results/cursor/bare/H2.json", "t3"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"H2"})

    def test_edit_and_multiedit_count_as_boundaries(self) -> None:
        """The agent might Edit or MultiEdit a result file rather than Write it."""
        events = [
            self._ev("Read", "a.py", "t1"),
            self._ev("Edit", "../results/cursor/bare/M1.json", "t2"),
            self._ev("Read", "b.py", "t3"),
            self._ev("MultiEdit", "../results/cursor/bare/M2.json", "t4"),
        ]
        segs = EE.segment_events_by_task(events)
        self.assertEqual(set(segs.keys()), {"M1", "M2"})


class VerificationShortcutLoadingTests(unittest.TestCase):
    """load_verification_shortcut_paths reads search_scope.json from the pack."""

    def _write_search_scope(self, cell_cwd: pathlib.Path, families: dict) -> None:
        pack = cell_cwd / ".agent-context" / "current"
        pack.mkdir(parents=True, exist_ok=True)
        (pack / "search_scope.json").write_text(json.dumps({
            "version": "1.0.0",
            "task_families": families,
        }))

    def test_returns_paths_from_each_family_deduped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = pathlib.Path(td)
            self._write_search_scope(cwd, {
                "feature_work": {
                    "verification_shortcuts": [
                        {"file": "src/server.py", "look_for": "HelloHandler"},
                        {"file": "src/config.py", "look_for": "from_env"},
                    ],
                },
                "diagnosis": {
                    "verification_shortcuts": [
                        # Same path again (different look_for) — dedup to one.
                        {"file": "src/server.py", "look_for": "/hello"},
                        {"file": "src/router.py", "look_for": "match"},
                    ],
                },
            })
            paths = EE.load_verification_shortcut_paths(cwd)
            self.assertEqual(paths, ["src/server.py", "src/config.py", "src/router.py"])

    def test_returns_none_when_pack_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(EE.load_verification_shortcut_paths(pathlib.Path(td)))

    def test_returns_empty_list_when_pack_present_but_no_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = pathlib.Path(td)
            self._write_search_scope(cwd, {"feature_work": {"verification_shortcuts": []}})
            self.assertEqual(EE.load_verification_shortcut_paths(cwd), [])


class StampResultPropagatesShortcutsTest(unittest.TestCase):
    """stamp_result carries verification_shortcut_paths onto the result JSON."""

    def test_shortcut_paths_stamped_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            rp = pathlib.Path(td) / "L1.json"
            rp.write_text(json.dumps({"task_id": "L1", "citations": []}))
            shortcuts = ["src/server.py", "src/config.py"]
            data = EE.stamp_result(
                rp, events=[], cwd=None, ground_truth=None,
                verification_shortcut_paths=shortcuts,
            )
            self.assertEqual(data["verification_shortcut_paths"], shortcuts)

    def test_shortcut_paths_absent_when_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            rp = pathlib.Path(td) / "L1.json"
            rp.write_text(json.dumps({"task_id": "L1", "citations": []}))
            data = EE.stamp_result(
                rp, events=[], cwd=None, ground_truth=None,
                verification_shortcut_paths=None,
            )
            self.assertNotIn("verification_shortcut_paths", data)


if __name__ == "__main__":
    unittest.main()
