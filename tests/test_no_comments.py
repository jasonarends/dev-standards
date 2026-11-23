"""Exercises the no-comments hook the way pre-commit calls it."""

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from dev_standards.no_comments import comments, main


def counted(name, text):
    return comments(Path(name), text)


class CommentsTest(unittest.TestCase):
    def test_counts_prose_comments(self):
        self.assertEqual(2, len(counted("a.py", "# set x\nx = 1  # for now\n")))
        self.assertEqual(2, len(counted("a.ts", "// set x\nlet x = 1 // hack\n")))
        self.assertEqual(1, len(counted("a.sh", "#!/bin/sh\n# start\necho hi\n")))
        self.assertEqual(1, len(counted("a.kt", "/* block */\nval x = 1\n")))

    def test_ignores_strings_docs_and_directives(self):
        for name, text in [
            ("a.py", 'x = "#fff"\n'),
            ("a.py", '"""Sets x."""\nx = 1\n'),
            ("a.py", "import x  # noqa: F401\n"),
            ("a.py", "x = 1  # type: ignore[assignment]\n"),
            ("a.py", "#!/usr/bin/env python3\n"),
            ("a.py", "# https://github.com/o/r/issues/1\n"),
            ("a.ts", "/** Sets x. */\nconst u = 'https://x.y'\n"),
            ("a.ts", "// eslint-disable-next-line no-console\n"),
            ("a.rs", "/// Sets x.\n//! Crate docs.\n"),
            ("a.go", "//go:build linux\n"),
        ]:
            with self.subTest(name=name, text=text):
                self.assertEqual([], counted(name, text))

    def test_python_that_does_not_tokenize_falls_back(self):
        self.assertEqual(1, len(counted("a.py", "def f(:\n    # broken\n")))


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def run_main(self, *argv):
        out = StringIO()
        with redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()

    def test_new_comment_fails_with_fix_message(self):
        Path("a.py").write_text("# set x\nx = 1\n")
        code, out = self.run_main("a.py")
        self.assertEqual(1, code)
        self.assertIn("a.py: 1 comment line(s), baseline allows 0", out)
        self.assertIn("fix the root cause", out)

    def test_baseline_allows_existing_and_blocks_growth(self):
        Path("a.py").write_text("# one\nx = 1\n")
        self.assertEqual(0, self.run_main("--update-baseline", "a.py")[0])
        self.assertEqual({"a.py": 1}, json.loads(Path(".no-comments-baseline.json").read_text()))
        self.assertEqual(0, self.run_main("a.py")[0])
        Path("a.py").write_text("# one\n# two\nx = 1\n")
        self.assertEqual(1, self.run_main("a.py")[0])

    def test_clean_file_leaves_the_baseline(self):
        Path("a.py").write_text("# one\n")
        self.run_main("--update-baseline", "a.py")
        Path("a.py").write_text("x = 1\n")
        self.run_main("--update-baseline", "a.py")
        self.assertEqual({}, json.loads(Path(".no-comments-baseline.json").read_text()))


if __name__ == "__main__":
    unittest.main()
