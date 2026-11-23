"""Checks the ruff-rules drift hook against sample repo configs."""

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from dev_standards.ruff_rules import main, standard_rules


class RuffRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def run_main(self):
        out = StringIO()
        with redirect_stdout(out):
            code = main()
        return code, out.getvalue()

    def test_standard_set_loads(self):
        self.assertIn("BLE", standard_rules())

    def test_full_selection_passes(self):
        rules = ", ".join(f'"{r}"' for r in standard_rules())
        Path("ruff.toml").write_text(f"[lint]\nselect = [{rules}]\n")
        self.assertEqual(0, self.run_main()[0])

    def test_all_and_prefixes_cover_rules(self):
        Path("pyproject.toml").write_text('[tool.ruff.lint]\nselect = ["ALL"]\n')
        self.assertEqual(0, self.run_main()[0])

    def test_extend_is_followed(self):
        rules = ", ".join(f'"{r}"' for r in standard_rules())
        Path("base.toml").write_text(f"[lint]\nselect = [{rules}]\n")
        Path("pyproject.toml").write_text('[tool.ruff]\nextend = "base.toml"\n')
        self.assertEqual(0, self.run_main()[0])

    def test_a_family_prefix_does_not_cover_another_family(self):
        Path("ruff.toml").write_text('[lint]\nselect = ["B", "E", "F"]\n')
        code, out = self.run_main()
        self.assertEqual(1, code)
        for rule in ("BLE", "ERA", "FIX002"):
            self.assertIn(rule, out)

    def test_prefix_ending_before_a_digit_covers(self):
        rules = ", ".join(f'"{r}"' for r in standard_rules() if r not in ("S110", "S112"))
        Path("ruff.toml").write_text(f'[lint]\nselect = [{rules}, "S1"]\n')
        self.assertEqual(0, self.run_main()[0])

    def test_global_ignore_counts_as_missing(self):
        rules = ", ".join(f'"{r}"' for r in standard_rules())
        Path("ruff.toml").write_text(f'[lint]\nselect = [{rules}]\nignore = ["BLE001"]\n')
        code, out = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("BLE", out)

    def test_dot_ruff_toml_wins(self):
        Path(".ruff.toml").write_text('[lint]\nselect = ["ALL"]\n')
        Path("ruff.toml").write_text('[lint]\nselect = ["E"]\n')
        self.assertEqual(0, self.run_main()[0])

    def test_broken_extend_fails_with_a_message(self):
        Path("ruff.toml").write_text('extend = "ruff.toml"\n')
        self.assertIn("loops", self.run_main()[1])
        Path("ruff.toml").write_text('extend = "nope.toml"\n')
        self.assertIn("doesn't exist", self.run_main()[1])

    def test_missing_rules_are_named(self):
        Path("pyproject.toml").write_text('[tool.ruff.lint]\nselect = ["E", "F"]\n')
        code, out = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("BLE", out)
        self.assertIn("per-file-ignores", out)

    def test_no_config_fails_with_fix(self):
        code, out = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("ruff.toml", out)


if __name__ == "__main__":
    unittest.main()
