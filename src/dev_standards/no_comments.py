"""Fails when a file gains comment lines beyond its baseline.

The baseline (`.no-comments-baseline.json` at the repo root) records each file's
comment count when the check was adopted, so existing comments don't fail the
build but new ones do. Shrink it with `--update-baseline` as files are cleaned up.

Allowed and never counted: shebangs, encoding lines, license headers, lint and
type directives, doc comments (docstrings, `/** */`, `///`, `//!`), and a line
whose comment is a link to an external bug.
"""

import argparse
import io
import json
import re
import sys
import tokenize
from pathlib import Path

BASELINE = Path(".no-comments-baseline.json")
HASH = {".py", ".sh", ".bash", ".zsh", ".rb"}
ALLOWED = re.compile(
    r"https?://|^#!|-\*-\s*coding|SPDX-License|^//go:|^///|^//!"
    r"|^#\s*(?:noqa|type:\s*ignore|pragma|pylint:|fmt:\s*(?:off|on|skip)|shellcheck|isort:)"
    r"|^(?://|/\*)\s*(?:eslint-|@ts-|ktlint-disable|prettier-ignore)"
)
SHELL_COMMENT = re.compile(r"^\s*(#.*)$|\S\s+(#\s.*)$")
SLASH_COMMENT = re.compile(r"^\s*(//.*|/\*(?!\*).*)$|\S\s+(//\s.*)$")

MESSAGE = """\
{path}: {count} comment line(s), baseline allows {allowed}.
  Comments are banned here. Say it with a name, a type, a test, or a check whose message
  explains the fix. If the comment justifies a workaround, fix the root cause or file an
  issue. Allowed: doc comments on public APIs and a one-line link to an external bug."""


def python_comments(text):
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return regex_comments(text, SHELL_COMMENT)
    return [t.string for t in tokens if t.type == tokenize.COMMENT]


def regex_comments(text, pattern):
    found = []
    for line in text.splitlines():
        if m := pattern.search(line):
            found.append((m.group(1) or m.group(2)).strip())
    return found


def comments(path, text):
    """Returns the counted comments in a file's text."""
    if path.suffix == ".py":
        raw = python_comments(text)
    elif path.suffix in HASH or text.startswith("#!"):
        raw = regex_comments(text, SHELL_COMMENT)
    else:
        raw = regex_comments(text, SLASH_COMMENT)
    return [c for c in raw if not ALLOWED.search(c)]


def load_baseline():
    return json.loads(BASELINE.read_text()) if BASELINE.exists() else {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument(
        "--update-baseline", action="store_true", help="record the current counts of the given files as their baseline"
    )
    args = parser.parse_args(argv)

    baseline = load_baseline()
    counts = {str(f): len(comments(f, f.read_text(errors="replace"))) for f in args.files if f.is_file()}

    if args.update_baseline:
        baseline.update({f: n for f, n in counts.items() if n})
        for f in [f for f, n in counts.items() if not n]:
            baseline.pop(f, None)
        BASELINE.write_text(json.dumps(dict(sorted(baseline.items())), indent=2) + "\n")
        print(f"baseline: {sum(baseline.values())} comment line(s) in {len(baseline)} file(s)")
        return 0

    failures = [(f, n, baseline.get(f, 0)) for f, n in counts.items() if n > baseline.get(f, 0)]
    for f, n, allowed in failures:
        print(MESSAGE.format(path=f, count=n, allowed=allowed))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
