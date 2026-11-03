"""The isolated runtime verifier cannot reuse operator state as a fixture."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.verify_cloud_runtime import phase


def fixture_directory():
    return Path(tempfile.mkdtemp(prefix="cx1-runtime-check-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None))


class RuntimeFixtureIsolation(unittest.TestCase):
    def test_prepare_refuses_existing_content_before_touching_the_budget(self):
        directory = fixture_directory()
        budget = directory / "budget.yaml"
        budget.write_bytes(b"operator-sentinel")
        try:
            with patch("harness.budget.BudgetGuard.initialize_ledger",
                       side_effect=AssertionError("must not open a fixture ledger")):
                with self.assertRaisesRegex(RuntimeError, "empty fixture directory"):
                    phase(directory, False)
        finally:
            self.assertEqual(budget.read_bytes(), b"operator-sentinel")

    def test_restart_refuses_non_fixture_state_before_opening_any_ledger(self):
        directory = fixture_directory()
        (directory / "fixture.json").write_text(json.dumps({"accounts": {}}))
        with self.assertRaisesRegex(RuntimeError, "recognized runtime fixture"):
            phase(directory, True)
        self.assertEqual(sorted(p.name for p in directory.iterdir()), ["fixture.json"])

    def test_fixture_directory_must_not_be_a_symlink(self):
        directory = fixture_directory()
        link = directory / "alias"
        link.symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "fixture directory"):
            phase(link, False)


if __name__ == "__main__":
    unittest.main()
