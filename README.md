# dev-standards

Shared checks for the repos owned by [@jasonarends](https://github.com/jasonarends). The
repo contains these pieces:

- A pre-commit hook, `no-comments`, that bans new code comments and tracks existing ones in
  a per-file baseline.
- A pre-commit hook, `ruff-rules`, that fails when a repo's Ruff config doesn't select every
  rule in the canonical config. It doesn't lint code. To lint code, you add Astral's
  `ruff-check` hook, as described in the adoption steps.
- A canonical Ruff config, [`src/dev_standards/ruff.toml`](src/dev_standards/ruff.toml).
- A reusable GitHub Actions lint workflow, `.github/workflows/lint.yml`.

## Why

Code written by AI agents drifts from the way the owner wants it written. Each time a
correction repeats, it becomes a deterministic check instead of a review comment. Every
check prints an error message that explains how to fix the problem, so an agent or a person
can resolve a failure without guessing.

## Adopt the standards in a repo

Follow these steps in order.

1. Add the hooks to `.pre-commit-config.yaml`, pinned to a tag:

   ```yaml
   repos:
     - repo: https://github.com/jasonarends/dev-standards
       rev: v0.1.0
       hooks:
         - id: no-comments
         - id: ruff-rules
   ```

   To pin to a commit SHA instead, see [Pin what you call](#pin-what-you-call). Add the
   `ruff-rules` hook after you finish step 3, because it fails until your Ruff config
   selects the standard rules.

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

   1. Write the baseline from the repo root. List every file the hook checks, not only
      Python and shell files. The hook checks Python, shell, JavaScript, TypeScript, Kotlin,
      Java, Go, Rust, Swift, C, C++, C#, Dart, and Scala files. It also checks extensionless
      scripts, such as `gradlew`, that it identifies as shell by their shebang. Add a
      pattern to `git ls-files` for each extension your repo contains. This example covers
      Python, shell, and Kotlin files:

      ```sh
      git ls-files -z '*.py' '*.sh' '*.kt' '*.kts' gradlew | xargs -0 no-comments --update-baseline
      ```

      Pass the file list straight to the command, as `xargs` does here. Don't store it in a
      shell variable first: zsh doesn't split an unquoted variable into words, so the tool
      receives one argument that names no file, and it writes an empty `{}` baseline
      without an error. The `-z` and `-0` options keep file names that contain spaces intact.

   1. Check that the baseline isn't empty. The command prints the number of files that have
      comments. If it prints `0` and you know the repo has comments, the file list was wrong:

      ```sh
      jq length .no-comments-baseline.json
      ```

   1. Commit `.no-comments-baseline.json` with the pre-commit config.

1. Copy the `[lint] select` list from
   [`src/dev_standards/ruff.toml`](src/dev_standards/ruff.toml) into the repo's own Ruff
   config (`ruff.toml`, `.ruff.toml`, or the `[tool.ruff]` table in `pyproject.toml`). Baseline
   existing violations with `per-file-ignores`, so only new violations fail. Keep the
   `line-length` value too. Then add the hooks:

   1. Set `target-version` in the Ruff config, or `requires-python` in `pyproject.toml`, to
      the Python version your code runs on. Without it, Ruff falls back to a default
      version, and the baseline can drift.

   1. Add the `ruff-rules` hook so the config can't drift. It checks only the config, so it
      never lints code.

   1. Add Astral's `ruff-check` hook to `.pre-commit-config.yaml`. This hook lints code, so
      it's what enforces the `per-file-ignores` baseline. Use the same Ruff version you
      used to write the baseline, because a different version reports different
      violations. Pin the hook to a commit, because it's a third-party repo whose tag can
      move. Put the version in a `# frozen:` comment. The `pre-commit autoupdate --freeze`
      command writes this form:

      ```yaml
      - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: 9026c9127e153371d7a78dfcb0c45ae2046a3d10  # frozen: v0.17.6
        hooks:
          - id: ruff-check
      ```

   1. Confirm that the hook lints code. Add an unused import, such as `import os`, to a
      Python file, then run the hook on that file. The hook must fail:

      ```sh
      pre-commit run ruff-check --files path/to/file.py
      ```

1. Call the reusable workflow from a workflow file such as `.github/workflows/ci.yml`:

   ```yaml
   jobs:
     lint:
       uses: jasonarends/dev-standards/.github/workflows/lint.yml@v0.1.0
   ```

   The workflow runs `pre-commit run --all-files`, so the repo needs a
   `.pre-commit-config.yaml`. The workflow caches `~/.cache/pre-commit`, keyed on that file.
   Add the optional `python-version` input to change the Python version. Default: `3.13`.

   ```yaml
   jobs:
     lint:
       uses: jasonarends/dev-standards/.github/workflows/lint.yml@v0.1.0
       with:
         python-version: "3.12"
   ```

## Pin what you call

Your CI runs code from this repo, so pin it to an immutable commit instead of a tag that
can move.

- Pin `rev:` in `.pre-commit-config.yaml` to a commit SHA, with a `# frozen: vX.Y.Z`
  comment. To rewrite your `rev:` values this way, run:

  ```sh
  pre-commit autoupdate --freeze
  ```

- Call the reusable workflow at a commit SHA, with the tag in a comment. Replace `SHA` with
  the full commit SHA of the release:

  ```yaml
  jobs:
    lint:
      uses: jasonarends/dev-standards/.github/workflows/lint.yml@SHA  # v0.1.0
  ```

- Don't pass `secrets: inherit` to the workflow. The workflow needs no secrets, and
  inheriting them gives the called code access to all of your repo's secrets.

The workflow itself pins its own actions to commit SHAs.

## What counts as a comment

The `no-comments` hook counts every comment line in these files:

- Hash comments (`#`) in Python and shell files. Python comments come from the tokenizer, so
  a `#` inside a string isn't counted. If a Python file doesn't tokenize, the hook falls back
  to a line-based search.
- Slash comments (`//` and `/* */`) in JavaScript, TypeScript, Kotlin, Java, Go, Rust, Swift,
  C, C++, C#, Dart, and Scala files.

The hook never counts these:

- Shebangs, encoding lines, and license headers (`SPDX-License`).
- Lint and type directives, such as `noqa`, `type: ignore`, `pragma`, `pylint:`,
  `fmt: off`, `fmt: on`, `fmt: skip`, `shellcheck`, `isort:`, `ruff:`, `pyright:`, `mypy:`,
  `nosec`, `eslint-`, `@ts-`,
  `ktlint-disable`, `prettier-ignore`, and `//go:`.
- Doc comments: docstrings, `/** */`, `///`, `//!`, `/*!`, and Go doc comments above a
  top-level declaration.
- A comment that is only a link (`http://` or `https://`), such as a link to an external bug.

A file fails when its count is higher than its baseline entry. A file with no entry has a
baseline of zero.

### Known limits

Outside Python, the hook finds comments line by line, so it has two blind spots:

- A `//` or ` # ` inside a string, template literal, raw string, or heredoc can be counted
  as a comment.
- A trailing comment with no space after the marker, such as `x=1 #note`, is missed.

## Check the Ruff rules

The `ruff-rules` hook reads your repo's Ruff config from `ruff.toml`, `.ruff.toml`, or the
`[tool.ruff]` table in `pyproject.toml`, and follows `extend` to a parent config. It fails
if the config doesn't select every rule in
[`src/dev_standards/ruff.toml`](src/dev_standards/ruff.toml). A broader selector, such as
`ALL`, covers the rules under it. The hook runs on every commit, even when no Python file
changed, and it doesn't check per-file ignores.

## Shrink the baseline

To reduce the baseline as you clean up a file:

1. Remove the comments from the file. Say the same thing with a name, a type, or a test.
1. Run the update command on the files you changed:

   ```sh
   no-comments --update-baseline path/to/file.py
   ```

1. Review the diff of `.no-comments-baseline.json`. A file with no comments left drops out
   of the baseline, and so does a file you deleted.
1. Commit the baseline with the cleanup.

`--update-baseline` records the current count for each file you pass, even if the count went
up. Pass only the files you cleaned, and check the diff before you commit.

If you rename a file, run `no-comments --update-baseline NEW_PATH` to move its baseline
entry, where `NEW_PATH` is the file's new path. The entry for the old path drops out
because that file no longer exists.

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
