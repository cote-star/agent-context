"""Sanity checks for scripts/experiments/result.schema.json (the experiment-result schema).

Stdlib-only: we don't pull `jsonschema` to avoid a confirm-tier dep, so we
cover the structural invariants that matter rather than full draft-07 semantics.
"""

from __future__ import annotations

import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "scripts" / "experiments" / "result.schema.json"


class SchemaShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text())

    def test_schema_is_v3(self) -> None:
        self.assertEqual(self.schema.get("version"), 3)
        self.assertIn("AgentContextFreshPackResult", self.schema.get("title", ""))

    def test_v2_required_fields_still_required(self) -> None:
        """v3 is additive — every v2-required field must still be required."""
        v2_required = {
            "task_id", "agent", "capture_method", "condition", "repo",
            "started_at", "finished_at", "files_opened_count", "dead_ends",
            "first_correct_file_hop", "files_opened_after_first_correct_hop",
            "post_hit_dead_ends", "tool_calls", "duration_seconds", "answer",
            "citations", "correct", "correctness_notes", "grading_method",
            "quality_self_score", "risk_flag", "risk_flag_explanation",
        }
        self.assertTrue(v2_required.issubset(set(self.schema["required"])))

    def test_v3_additive_fields_present(self) -> None:
        """The whole point of v3 is these new fields."""
        v3_new = {
            "tool_call_events",
            "source_read_events",
            "unique_source_paths_read",
            "dead_end_paths",
            "first_correct_file_ts",
            "ground_truth_required_paths",
            "ground_truth_optional_paths",
            "ground_truth_decoy_paths",
            "verification_shortcut_paths",
            "pack_content_origin_version",
            "validator_cli_version",
            "tokens_thinking",
        }
        self.assertTrue(
            v3_new.issubset(set(self.schema["properties"].keys())),
            msg=f"missing v3 fields: {v3_new - set(self.schema['properties'].keys())}",
        )

    def test_legacy_provenance_field_preserved(self) -> None:
        """agent_context_cli_version stays for backward compat with v2 readers."""
        self.assertIn("agent_context_cli_version", self.schema["properties"])

    def test_tool_call_events_event_shape(self) -> None:
        """Each event has required tool + ts; path is optional (e.g., shell calls)."""
        events = self.schema["properties"]["tool_call_events"]
        self.assertIn("array", events["type"])
        item = events["items"]
        self.assertEqual(set(item["required"]), {"tool", "ts"})
        self.assertIn("path", item["properties"])

    def test_agent_enum_unchanged(self) -> None:
        self.assertEqual(
            set(self.schema["properties"]["agent"]["enum"]),
            {"claude", "codex", "cursor", "opencode"},
        )

    def test_capture_method_constraint_block_intact(self) -> None:
        """The if/then block requiring tool_calls when capture_method=cli must remain."""
        self.assertIn("if", self.schema)
        self.assertIn("then", self.schema)
        self.assertEqual(
            self.schema["if"]["properties"]["capture_method"]["const"], "cli"
        )

    def test_no_additional_top_level_properties(self) -> None:
        """additionalProperties: false keeps the result shape disciplined."""
        self.assertEqual(self.schema.get("additionalProperties"), False)


if __name__ == "__main__":
    unittest.main()
