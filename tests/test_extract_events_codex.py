"""Unit tests for scripts/experiments/extract-events-from-codex.py.

Hermetic — we synthesise codex-shaped JSONL fixtures and exercise the
walker / classifier / segmentation directly. The chorus helpers re-used via
importlib are already covered by test_extract_events.py; we only re-test
the codex-specific pieces here (shell command classification, apply_patch
parsing, session resolution by cwd, dedup).
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "experiments" / "extract-events-from-codex.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("extract_events_from_codex", SCRIPT_PATH)
    assert spec and spec.loader, f"could not spec-load {SCRIPT_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


CX = _load_module()


FAKE_CWD = "/tmp/agent-rerun/bare"


def _exec_event(ts: str, cmd: str) -> dict:
    """Build a codex `response_item / function_call / exec_command` envelope."""
    return {
        "timestamp": ts,
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "exec_command",
            "call_id": f"call_{ts}",
            "arguments": json.dumps({
                "cmd": cmd,
                "workdir": FAKE_CWD,
                "yield_time_ms": 1000,
                "max_output_tokens": 20000,
            }),
        },
    }


def _apply_patch_event(ts: str, patch_body: str) -> dict:
    return {
        "timestamp": ts,
        "type": "response_item",
        "payload": {
            "type": "custom_tool_call",
            "status": "completed",
            "call_id": f"call_{ts}",
            "name": "apply_patch",
            "input": patch_body,
        },
    }


def _session_meta(ts: str, sid: str, cwd: str) -> dict:
    return {
        "timestamp": ts,
        "type": "session_meta",
        "payload": {
            "id": sid,
            "timestamp": ts,
            "cwd": cwd,
            "originator": "codex_exec",
            "cli_version": "0.130.0",
        },
    }


def _write_jsonl(path: pathlib.Path, lines: list) -> pathlib.Path:
    with path.open("w", encoding="utf-8") as fh:
        for obj in lines:
            fh.write(json.dumps(obj) + "\n")
    return path


# --- Shell command classifier ----------------------------------------------

class ClassifyShellCommandTests(unittest.TestCase):
    """The classifier turns a raw zsh `cmd` string into (tool, path)."""

    def test_sed_range_extracts_path(self) -> None:
        tool, path = CX.classify_shell_command("sed -n '1,240p' ../EXPERIMENT.md")
        self.assertEqual(tool, "Read")
        self.assertEqual(path, "../EXPERIMENT.md")

    def test_cat_extracts_path(self) -> None:
        tool, path = CX.classify_shell_command("cat -- src/server.py")
        self.assertEqual(tool, "Read")
        self.assertEqual(path, "src/server.py")

    def test_nl_extracts_path(self) -> None:
        # `nl -ba <path>` is a common codex read.
        tool, path = CX.classify_shell_command("nl -ba scripts/conformance.sh")
        self.assertEqual(tool, "Read")
        self.assertEqual(path, "scripts/conformance.sh")

    def test_head_and_tail(self) -> None:
        self.assertEqual(CX.classify_shell_command("head -n 50 README.md"), ("Read", "README.md"))
        self.assertEqual(CX.classify_shell_command("tail src/main.rs"), ("Read", "src/main.rs"))

    def test_grep_with_path_returns_grep(self) -> None:
        # grep <pattern> <path> → tool=Grep, path=<path>
        tool, path = CX.classify_shell_command("grep -n TODO src/api.ts")
        self.assertEqual(tool, "Grep")
        self.assertEqual(path, "src/api.ts")

    def test_rg_without_path_returns_grep_no_path(self) -> None:
        # rg <flags> <pattern> with no positional path → search across cwd.
        tool, path = CX.classify_shell_command("rg --files -g '!node_modules'")
        self.assertEqual(tool, "Grep")
        self.assertIsNone(path)

    def test_find_extracts_root(self) -> None:
        tool, path = CX.classify_shell_command("find .. -maxdepth 3 -type f -name '*.json'")
        self.assertEqual(tool, "Glob")
        self.assertEqual(path, "..")

    def test_ls_extracts_path(self) -> None:
        tool, path = CX.classify_shell_command("ls -la scripts/")
        self.assertEqual(tool, "LS")
        self.assertEqual(path, "scripts/")

    def test_cat_redirect_is_write(self) -> None:
        # Redirected cat is a Write — overrides the cat-as-read default.
        tool, path = CX.classify_shell_command(
            "cat > ../results/codex/bare/L1.json <<'EOF'\n{...}\nEOF"
        )
        self.assertEqual(tool, "Write")
        self.assertEqual(path, "../results/codex/bare/L1.json")

    def test_tee_is_write(self) -> None:
        tool, path = CX.classify_shell_command("tee ../results/codex/bare/L2.json")
        self.assertEqual(tool, "Bash")  # tee w/o redirection isn't classified as Write
        # (deliberately strict: we only catch the >/>> shape)

    def test_echo_redirect_is_write(self) -> None:
        tool, path = CX.classify_shell_command("echo hi > /tmp/out.txt")
        self.assertEqual(tool, "Write")
        self.assertEqual(path, "/tmp/out.txt")

    def test_unknown_command_is_bash(self) -> None:
        self.assertEqual(CX.classify_shell_command("git status"), ("Bash", None))
        self.assertEqual(CX.classify_shell_command("cargo test"), ("Bash", None))
        self.assertEqual(CX.classify_shell_command(""), ("Bash", None))


# --- apply_patch path extraction --------------------------------------------

class ApplyPatchPathExtractionTests(unittest.TestCase):
    def test_add_file_marker(self) -> None:
        body = (
            "*** Begin Patch\n"
            "*** Add File: ../results/codex/bare/L1.json\n"
            "+{\"task_id\": \"L1\"}\n"
            "*** End Patch\n"
        )
        self.assertEqual(
            CX.extract_apply_patch_paths(body),
            ["../results/codex/bare/L1.json"],
        )

    def test_multi_file_patch_returns_all_in_order(self) -> None:
        body = (
            "*** Begin Patch\n"
            "*** Add File: ../results/codex/bare/L1.json\n"
            "+{...}\n"
            "*** Add File: ../results/codex/bare/L2.json\n"
            "+{...}\n"
            "*** Update File: src/server.py\n"
            "@@\n"
            "-old\n+new\n"
            "*** End Patch\n"
        )
        self.assertEqual(
            CX.extract_apply_patch_paths(body),
            [
                "../results/codex/bare/L1.json",
                "../results/codex/bare/L2.json",
                "src/server.py",
            ],
        )

    def test_unified_diff_fallback(self) -> None:
        body = (
            "--- a/src/server.py\n"
            "+++ b/src/server.py\n"
            "@@\n"
            "-old\n+new\n"
        )
        self.assertEqual(CX.extract_apply_patch_paths(body), ["src/server.py"])

    def test_empty_body_returns_empty_list(self) -> None:
        self.assertEqual(CX.extract_apply_patch_paths(""), [])


# --- JSONL walker -----------------------------------------------------------

class WalkCodexSessionEventsTests(unittest.TestCase):
    def test_mix_of_exec_and_apply_patch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [
                _session_meta("2026-05-09T19:24:44.000Z", "sid-1", FAKE_CWD),
                _exec_event("2026-05-09T19:24:51.000Z",
                            "sed -n '1,240p' ../EXPERIMENT.md"),
                _exec_event("2026-05-09T19:24:52.000Z",
                            "rg -n 'foo' src/"),
                _exec_event("2026-05-09T19:24:53.000Z",
                            "find .. -maxdepth 2 -type f"),
                _apply_patch_event(
                    "2026-05-09T19:25:00.000Z",
                    "*** Begin Patch\n"
                    "*** Add File: ../results/codex/bare/L1.json\n"
                    "+{\"task_id\": \"L1\"}\n"
                    "*** End Patch\n",
                ),
            ])
            events = CX.walk_codex_session_events(jsonl)
        # 3 exec events + 1 apply_patch (single-file) = 4 events.
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0]["tool"], "Read")
        self.assertEqual(events[0]["path"], "../EXPERIMENT.md")
        # `rg -n 'foo' src/` has both pattern and path positionals → path captured.
        self.assertEqual(events[1]["tool"], "Grep")
        self.assertEqual(events[1]["path"], "src/")
        self.assertEqual(events[2]["tool"], "Glob")
        self.assertEqual(events[2]["path"], "..")
        self.assertEqual(events[3]["tool"], "Write")
        self.assertEqual(events[3]["path"], "../results/codex/bare/L1.json")
        # args are the parsed-from-stringified-JSON dict, preserved.
        self.assertIn("cmd", events[0]["args"])

    def test_apply_patch_with_multiple_files_emits_one_event_each(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [
                _session_meta("2026-05-09T19:24:44.000Z", "sid-1", FAKE_CWD),
                _apply_patch_event(
                    "2026-05-09T19:30:00.000Z",
                    "*** Begin Patch\n"
                    "*** Add File: ../results/codex/bare/L1.json\n+{...}\n"
                    "*** Add File: ../results/codex/bare/L2.json\n+{...}\n"
                    "*** End Patch\n",
                ),
            ])
            events = CX.walk_codex_session_events(jsonl)
        self.assertEqual(len(events), 2)
        self.assertEqual([e["tool"] for e in events], ["Write", "Write"])
        self.assertEqual(
            [e["path"] for e in events],
            ["../results/codex/bare/L1.json", "../results/codex/bare/L2.json"],
        )
        # Both share the envelope's timestamp.
        self.assertEqual(events[0]["ts"], events[1]["ts"])

    def test_session_with_only_meta_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [
                _session_meta("2026-05-09T19:24:44.000Z", "sid-1", FAKE_CWD),
            ])
            self.assertEqual(CX.walk_codex_session_events(jsonl), [])

    def test_malformed_arguments_are_kept_as_bash(self) -> None:
        # arguments stringified-JSON that fails to parse → empty args dict;
        # cmd defaults to "" → tool=Bash, path=None.
        bad = {
            "timestamp": "2026-05-09T19:24:55.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "exec_command",
                "call_id": "call_x",
                "arguments": "{not json",
            },
        }
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [bad])
            events = CX.walk_codex_session_events(jsonl)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["tool"], "Bash")
        self.assertIsNone(events[0]["path"])

    def test_non_exec_function_calls_are_skipped(self) -> None:
        # write_stdin (codex's stdin-pipe tool) carries no path; we drop it
        # rather than mislabel as Bash.
        ws = {
            "timestamp": "2026-05-09T19:24:55.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "write_stdin",
                "call_id": "call_x",
                "arguments": "{\"session_id\":1,\"chars\":\"\"}",
            },
        }
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [
                _session_meta("2026-05-09T19:24:44.000Z", "sid-1", FAKE_CWD),
                ws,
            ])
            events = CX.walk_codex_session_events(jsonl)
        self.assertEqual(events, [])


# --- Session resolution by cwd matching ------------------------------------

class FindCodexSessionForCellTests(unittest.TestCase):
    def _session_dir(self, td: pathlib.Path) -> pathlib.Path:
        d = td / "sessions" / "2026" / "05" / "09"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_picks_session_with_matching_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            cell = tmp / "rerun" / "bare"
            cell.mkdir(parents=True)
            sd = self._session_dir(tmp)

            other = sd / "rollout-2026-05-09T10-00-00-other.jsonl"
            _write_jsonl(other, [
                _session_meta("2026-05-09T10:00:00.000Z", "sid-other", "/tmp/somewhere/else"),
            ])
            wanted = sd / "rollout-2026-05-09T11-00-00-wanted.jsonl"
            _write_jsonl(wanted, [
                _session_meta("2026-05-09T11:00:00.000Z", "sid-want", str(cell)),
            ])

            session = CX.find_codex_session_for_cell(str(cell), tmp / "sessions")
            self.assertIsNotNone(session)
            self.assertEqual(session["session_id"], "sid-want")
            self.assertEqual(session["file_path"], str(wanted))

    def test_picks_most_recent_when_multiple_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            cell = tmp / "rerun" / "bare"
            cell.mkdir(parents=True)
            sd = self._session_dir(tmp)

            older = sd / "rollout-2026-05-09T08-00-00-older.jsonl"
            _write_jsonl(older, [
                _session_meta("2026-05-09T08:00:00.000Z", "sid-older", str(cell)),
            ])
            newer = sd / "rollout-2026-05-09T12-00-00-newer.jsonl"
            _write_jsonl(newer, [
                _session_meta("2026-05-09T12:00:00.000Z", "sid-newer", str(cell)),
            ])
            # Force mtimes so order is deterministic regardless of write speed.
            os.utime(older, (1_700_000_000, 1_700_000_000))
            os.utime(newer, (1_800_000_000, 1_800_000_000))

            session = CX.find_codex_session_for_cell(str(cell), tmp / "sessions")
            self.assertIsNotNone(session)
            self.assertEqual(session["session_id"], "sid-newer")

    def test_returns_none_when_no_session_matches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            cell = tmp / "rerun" / "bare"
            cell.mkdir(parents=True)
            sd = self._session_dir(tmp)
            other = sd / "rollout-2026-05-09T10-00-00-other.jsonl"
            _write_jsonl(other, [
                _session_meta("2026-05-09T10:00:00.000Z", "sid-other", "/tmp/elsewhere"),
            ])
            self.assertIsNone(CX.find_codex_session_for_cell(str(cell), tmp / "sessions"))

    def test_dedup_skips_already_used_session(self) -> None:
        """A session whose id is in seen_session_ids is not re-returned."""
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            cell = tmp / "rerun" / "bare"
            cell.mkdir(parents=True)
            sd = self._session_dir(tmp)
            f = sd / "rollout-2026-05-09T11-00-00-x.jsonl"
            _write_jsonl(f, [
                _session_meta("2026-05-09T11:00:00.000Z", "sid-1", str(cell)),
            ])
            # First call returns it.
            seen: set = set()
            first = CX.find_codex_session_for_cell(str(cell), tmp / "sessions", seen)
            self.assertIsNotNone(first)
            seen.add(first["session_id"])
            # Second call (same cell) — already used → None (no other session for this cwd).
            second = CX.find_codex_session_for_cell(str(cell), tmp / "sessions", seen)
            self.assertIsNone(second)


# --- End-to-end: walk → segment → stamp ------------------------------------

class EndToEndStampTests(unittest.TestCase):
    """Synthesize a full codex session, run the walker, segment, stamp."""

    def test_per_task_segmentation_via_apply_patch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [
                _session_meta("2026-05-09T19:24:44.000Z", "sid-1", FAKE_CWD),
                # L1 work: read the EXPERIMENT, sed a config, then write L1.
                _exec_event("2026-05-09T19:25:00.000Z",
                            "sed -n '1,240p' ../EXPERIMENT.md"),
                _exec_event("2026-05-09T19:25:01.000Z",
                            "rg -n 'redact' src/"),
                _apply_patch_event(
                    "2026-05-09T19:25:30.000Z",
                    "*** Begin Patch\n"
                    "*** Add File: ../results/codex/bare/L1.json\n+{...}\n"
                    "*** End Patch\n",
                ),
                # L2 work: another read, then write L2.
                _exec_event("2026-05-09T19:26:00.000Z",
                            "cat src/server.py"),
                _apply_patch_event(
                    "2026-05-09T19:26:30.000Z",
                    "*** Begin Patch\n"
                    "*** Add File: ../results/codex/bare/L2.json\n+{...}\n"
                    "*** End Patch\n",
                ),
            ])
            events = CX.walk_codex_session_events(jsonl)
            segments = CX.segment_events_by_task(events)

        self.assertEqual(set(segments.keys()), {"L1", "L2"})
        # L1 segment: 2 exec reads + 1 apply_patch Write = 3 events.
        self.assertEqual(len(segments["L1"]), 3)
        self.assertEqual(segments["L1"][0]["tool"], "Read")
        self.assertEqual(segments["L1"][1]["tool"], "Grep")
        self.assertEqual(segments["L1"][2]["tool"], "Write")
        # L2 segment: 1 cat-read + 1 apply_patch Write = 2 events.
        self.assertEqual(len(segments["L2"]), 2)
        self.assertEqual(segments["L2"][0]["tool"], "Read")
        self.assertEqual(segments["L2"][0]["path"], "src/server.py")

    def test_stamp_result_after_codex_walk_populates_v3_fields(self) -> None:
        """End-to-end: walk a fixture JSONL → segment → stamp → re-read."""
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            jsonl = _write_jsonl(tmp / "session.jsonl", [
                _session_meta("2026-05-09T19:24:44.000Z", "sid-1", FAKE_CWD),
                _exec_event("2026-05-09T19:25:00.000Z",
                            "sed -n '1,200p' src/api.ts"),
                _exec_event("2026-05-09T19:25:01.000Z",
                            "cat src/server.py"),
                _apply_patch_event(
                    "2026-05-09T19:25:30.000Z",
                    "*** Begin Patch\n"
                    "*** Add File: ../results/codex/bare/L1.json\n+{...}\n"
                    "*** End Patch\n",
                ),
            ])
            events = CX.walk_codex_session_events(jsonl)
            segments = CX.segment_events_by_task(events)

            # Build a minimal result JSON to stamp onto.
            rp = tmp / "L1.json"
            rp.write_text(json.dumps({
                "task_id": "L1",
                "agent": "codex",
                "capture_method": "cli",
                "condition": "bare",
                "repo": "demo",
                "started_at": "2026-05-09T19:24:00Z",
                "finished_at": "2026-05-09T19:30:00Z",
                "files_opened_count": 0,
                "dead_ends": 0,
                "first_correct_file_hop": 0,
                "files_opened_after_first_correct_hop": 0,
                "post_hit_dead_ends": 0,
                "tool_calls": {},
                "duration_seconds": 360,
                "answer": "...",
                "citations": [{"path": "src/api.ts", "line": 17, "note": "hit"}],
                "correct": "ungraded",
                "correctness_notes": "",
                "grading_method": "ungraded",
                "quality_self_score": 8,
                "risk_flag": False,
                "risk_flag_explanation": "",
            }, indent=2))

            gt = {"required": ["src/api.ts"], "optional": [], "decoy": []}
            stamped = CX.stamp_result(rp, segments["L1"], cwd=FAKE_CWD, ground_truth=gt)
            CX.write_result(rp, stamped)
            d = json.loads(rp.read_text())

        # 3 raw events stamped: 2 reads + 1 apply_patch Write.
        self.assertEqual(len(d["tool_call_events"]), 3)
        # Source reads strip the Write (it's a result-JSON write).
        # NB: ../results/codex/bare/L1.json is OUTSIDE FAKE_CWD so normalise_path
        # leaves it absolute-ish; but with path=None it's already filtered. Here
        # the Write has a non-None path so it shows up in source_read_events
        # unless we filter it. Schema treats Write to result JSON as a real
        # event; it just shouldn't be in source_read_events. The chorus
        # extractor's filter is "path != null AND not under .agent-context/".
        # `../results/...` isn't under .agent-context/, so the Write IS in
        # source_read_events. That's the documented behaviour.
        self.assertEqual(d["unique_source_paths_read"], 3)
        # First match for src/api.ts is the first event ts.
        self.assertEqual(d["first_correct_file_ts"], "2026-05-09T19:25:00.000Z")
        # tool_calls aggregate re-derived.
        self.assertEqual(d["tool_calls"], {"Read": 2, "Write": 1})
        # Ground-truth path arrays stamped through.
        self.assertEqual(d["ground_truth_required_paths"], ["src/api.ts"])


if __name__ == "__main__":
    unittest.main()
