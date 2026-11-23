"""Fails when a file gains comment lines beyond its baseline.

The baseline (`.no-comments-baseline.json`, read from the current directory, which
is the repo root under pre-commit) records each file's comment count when the check
was adopted, so existing comments don't fail the build but new ones do. Shrink it
with `--update-baseline` as files are cleaned up.

Never counted: shebangs, encoding lines, license headers, lint and type directives,
doc comments (docstrings, `/** */`, `///`, `//!`, `/*!`, Go doc comments above a
top-level declaration), and a comment that is only a URL to an external bug.

Known limits: outside Python, comments are found per line, so `//` or ` # ` inside a
string, template literal, raw string, or heredoc can be counted, and a trailing
comment with no space after the marker (`x=1 #note`) is missed.
"""

import argparse
import io
import json
import re
import sys
import tokenize
from pathlib import Path

BASELINE = Path(".no-comments-baseline.json")
HASH = {".py", ".sh", ".bash", ".zsh"}
ALLOWED = re.compile(
    r"^#!|-\*-\s*coding|SPDX-License|^//go:|^///|^//!|^/\*!"
    r"|^(?:#|//)\s*https?://\S+\s*$"
    r"|^#\s*(?:noqa|type:\s*ignore|pragma|pylint:|ruff:|pyright:|mypy:|nosec|isort:"
    r"|fmt:\s*(?:off|on|skip)|shellcheck)"
    r"|^(?://|/\*)\s*(?:eslint-|@ts-|ktlint-disable|prettier-ignore)"
)
SHELL_COMMENT = re.compile(r"^\s*(#.*)$|\S\s+(#\s.*)$")
SLASH_COMMENT = re.compile(r"^\s*(//.*|/\*(?!\*).*)$|\S\s+(//\s.*)$")
GO_DECLARATION = re.compile(r"^(?:func|type|var|const|package)\b")

MESSAGE = """\
{path}: {count} comment line(s), baseline allows {allowed}.
  Comments are banned here. Say it with a name, a type, a test, or a check whose message
  explains the fix. If the comment justifies a workaround, fix the root cause or file an
  issue. Allowed: doc comments on public APIs and a comment that is only a link to an
  external bug. If you renamed this file, move its baseline with
  `no-comments --update-baseline {path}`."""


def python_comments(text):
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return regex_comments(text.splitlines(), SHELL_COMMENT)
    return [t.string for t in tokens if t.type == tokenize.COMMENT]


def regex_comments(lines, pattern):
    return [(m.group(1) or m.group(2)).strip() for line in lines if (m := pattern.search(line))]


def go_code_lines(text):
    """Drops `//` blocks that sit directly above a top-level declaration: Go's doc comments."""
    lines = text.splitlines()
    keep, block = [], []
    for line in lines:
        if line.startswith("//"):
            block.append(line)
            continue
        if not GO_DECLARATION.match(line):
            keep += block
        block = []
        keep.append(line)
    return keep + block


def comments(path, text):
    """Returns the counted comments in a file's text."""
    if path.suffix == ".py":
        raw = python_comments(text)
    elif path.suffix in HASH or text.startswith("#!"):
        raw = regex_comments(text.splitlines(), SHELL_COMMENT)
    elif path.suffix == ".go":
        raw = regex_comments(go_code_lines(text), SLASH_COMMENT)
    else:
        raw = regex_comments(text.splitlines(), SLASH_COMMENT)
    return [c for c in raw if not ALLOWED.search(c)]


def load_baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}


def update_baseline(baseline, counts):
    merged = {**baseline, **counts}
    return {f: n for f, n in sorted(merged.items()) if n and Path(f).exists()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="record the given files' current counts and drop entries for deleted files",
    )
    args = parser.parse_args(argv)

    baseline = load_baseline()
    counts = {
        str(f): len(comments(f, f.read_text(encoding="utf-8", errors="replace"))) for f in args.files if f.is_file()
    }

    if args.update_baseline:
        baseline = update_baseline(baseline, counts)
        BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"baseline: {sum(baseline.values())} comment line(s) in {len(baseline)} file(s)")
        return 0

    failures = [(f, n, baseline.get(f, 0)) for f, n in counts.items() if n > baseline.get(f, 0)]
    for f, n, allowed in failures:
        print(MESSAGE.format(path=f, count=n, allowed=allowed))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
