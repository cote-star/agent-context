"""Basic tests for the bin/agent-context CLI and verifier."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "bin" / "agent-context"
EXAMPLE = REPO_ROOT / "examples" / "hello-service"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(CLI)] + args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


class VerifyExampleTests(unittest.TestCase):
    """The worked example must verify out of the box."""

    def test_verify_passes_on_hello_service(self) -> None:
        result = _run(["verify", str(EXAMPLE)])
        self.assertEqual(
            result.returncode, 0,
            msg=f"verify failed. stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        self.assertIn("OK:", result.stdout)


class DoctorTests(unittest.TestCase):
    """doctor always exits zero and prints environment info."""

    def test_doctor_exits_zero(self) -> None:
        result = _run(["doctor"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("agent-context doctor", result.stdout)


class InitThenVerifyTests(unittest.TestCase):
    """Freshly-init'd pack has REPLACE markers; verify must fail until filled."""

    def test_init_then_verify_fails_on_empty_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result_init = _run(["init", tmpdir])
            self.assertEqual(result_init.returncode, 0, msg=result_init.stderr)

            pack_dir = pathlib.Path(tmpdir) / ".agent-context" / "current"
            self.assertTrue(pack_dir.is_dir())
            tools_dir = pathlib.Path(tmpdir) / ".agent-context" / "tools"
            self.assertTrue((tools_dir / "verify_agent_context.py").is_file())
            old_verifier_name = "verify_" + "context" + "_pack.py"
            self.assertFalse((tools_dir / old_verifier_name).exists())

            # Verifier should fail: search_scope.json has _EXAMPLE_feature_work marker.
            result_verify = _run(["verify", tmpdir])
            self.assertNotEqual(result_verify.returncode, 0,
                                msg="verify unexpectedly passed on raw templates")

    def test_filling_one_field_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _run(["init", tmpdir])
            pack_dir = pathlib.Path(tmpdir) / ".agent-context" / "current"
            # Replace a single REPLACE marker in the search_scope JSON — still invalid
            # (still has template markers elsewhere, still has _EXAMPLE prefix).
            scope_file = pack_dir / "search_scope.json"
            text = scope_file.read_text()
            text = text.replace(
                '"REPLACE: describe a common task type for this repo"',
                '"a common task type for this repo"',
                1,
            )
            scope_file.write_text(text)

            result_verify = _run(["verify", tmpdir])
            self.assertNotEqual(result_verify.returncode, 0,
                                msg="verify unexpectedly passed with partial fill")


if __name__ == "__main__":
    unittest.main()
