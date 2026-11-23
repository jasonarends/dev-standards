# dev-standards

Shared checks for the repos owned by [@jasonarends](https://github.com/jasonarends). The
repo contains three pieces:

- A pre-commit hook, `no-comments`, that bans new code comments and tracks existing ones in
  a per-file baseline.
- A canonical Ruff config, `ruff.toml`.
- A reusable GitHub Actions lint workflow, `.github/workflows/lint.yml`.

## Why

Code written by AI agents drifts from the way the owner wants it written. Each time a
correction repeats, it becomes a deterministic check instead of a review comment. Every
check prints an error message that explains how to fix the problem, so an agent or a person
can resolve a failure without guessing.

## Adopt the standards in a repo

Follow these steps in order.

1. Add the hook to `.pre-commit-config.yaml`, pinned to a tag:

   ```yaml
   repos:
     - repo: https://github.com/jasonarends/dev-standards
       rev: v0.1.0
       hooks:
         - id: no-comments
   ```

1. Record the comments that already exist, so that only new comments fail.

   1. Run the hook on all files. It fails if any file has comments:

      ```sh
      pre-commit run no-comments --all-files
      ```

   1. Install the `no-comments` command. The following command installs it from the same
      tag you pinned in step 1:

      ```sh
      pipx install git+https://github.com/jasonarends/dev-standards@v0.1.0
      ```

   1. Write the baseline from the repo root. List the files with the same extensions the
      hook checks. This example covers Python and shell files:

      ```sh
      no-comments --update-baseline $(git ls-files '*.py' '*.sh')
      ```

   1. Commit `.no-comments-baseline.json` with the pre-commit config.

1. Copy the rule selection from [`ruff.toml`](ruff.toml) into the repo's own Ruff config
   (`ruff.toml` or the `[tool.ruff]` table in `pyproject.toml`). Keep the `line-length`
   value too. Run `ruff check` and fix or deliberately ignore what it reports.

1. Call the reusable workflow from a workflow file such as `.github/workflows/ci.yml`:

   ```yaml
   jobs:
     lint:
       uses: jasonarends/dev-standards/.github/workflows/lint.yml@v0.1.0
   ```

   The workflow runs `pre-commit run --all-files`, so the repo needs a
   `.pre-commit-config.yaml`. Add the optional `python-version` input to change the Python
   version. Default: `3.13`.

   ```yaml
   jobs:
     lint:
       uses: jasonarends/dev-standards/.github/workflows/lint.yml@v0.1.0
       with:
         python-version: "3.12"
   ```

## What counts as a comment

The `no-comments` hook counts every comment line in these files:

- Hash comments (`#`) in Python and shell files. Python comments come from the tokenizer, so
  a `#` inside a string isn't counted. If a Python file doesn't tokenize, the hook falls back
  to a line-based search.
- Slash comments (`//` and `/* */`) in JavaScript, TypeScript, Kotlin, Java, Go, Rust, Swift,
  C, C++, C#, Dart, and Scala files.

The hook never counts these:

- Shebangs, encoding lines, and `SPDX-License` headers.
- Lint and type directives, such as `noqa`, `type: ignore`, `pragma`, `pylint:`,
  `fmt: off`, `fmt: on`, `fmt: skip`, `shellcheck`, `isort:`, `eslint-`, `@ts-`,
  `ktlint-disable`, `prettier-ignore`, and `//go:`.
- Doc comments: docstrings, `/** */`, `///`, and `//!`.
- A comment that contains an `http://` or `https://` link, such as a link to an external bug.

A file fails when its count is higher than its baseline entry. A file with no entry has a
baseline of zero.

## Shrink the baseline

To reduce the baseline as you clean up a file:

1. Remove the comments from the file. Say the same thing with a name, a type, or a test.
1. Run the update command on the files you changed:

   ```sh
   no-comments --update-baseline path/to/file.py
   ```

1. Review the diff of `.no-comments-baseline.json`. A file with no comments left drops out
   of the baseline.
1. Commit the baseline with the cleanup.

`--update-baseline` records the current count for each file you pass, even if the count went
up. Pass only the files you cleaned, and check the diff before you commit.

## Develop

To work on this repo, set up a virtual environment and run the tests:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

The `ci.yml` workflow runs the same tests and then calls the reusable lint workflow on this
repo.

To release a change, merge it to `main` and push a tag, such as `v0.1.1`. Repos that pin
an earlier tag don't change until they update their `rev` and workflow reference.
