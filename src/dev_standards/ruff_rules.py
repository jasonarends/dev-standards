"""Fails when a repo's ruff config doesn't select every rule in the standard set.

Repos keep their own ruff config, with their own per-file baselines; this check only
makes sure none of the standard rules is missing, so the configs can't drift apart.
"""

import sys
import tomllib
from importlib.resources import files
from pathlib import Path

CONFIGS = ("ruff.toml", ".ruff.toml", "pyproject.toml")


def standard_rules():
    """Returns the rule selectors in the packaged ruff.toml."""
    return tomllib.loads(files("dev_standards").joinpath("ruff.toml").read_text())["lint"]["select"]


def selected_rules(data, base):
    """Returns the selectors a ruff config enables, following `extend` to a parent config."""
    lint = data.get("lint", data)
    rules = [*lint.get("select", []), *lint.get("extend-select", [])]
    if parent := data.get("extend"):
        path = base / parent
        rules += selected_rules(tomllib.loads(path.read_text(encoding="utf-8")), path.parent)
    return rules


def repo_lint_config():
    for name in CONFIGS:
        path = Path(name)
        if not path.exists():
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if name == "pyproject.toml":
            data = data.get("tool", {}).get("ruff")
            if data is None:
                continue
        return name, selected_rules(data, path.parent)
    return None, None


def covered(rule, selected):
    return any(s == "ALL" or rule.startswith(s) for s in selected)


def main():
    name, selected = repo_lint_config()
    if selected is None:
        print("ruff-rules: no ruff config found. Copy dev-standards' ruff.toml `[lint] select` into ruff.toml.")
        return 1
    missing = [r for r in standard_rules() if not covered(r, selected)]
    if missing:
        print(f"ruff-rules: {name} doesn't select {', '.join(missing)}. Add them to `select`, and baseline any")
        print("  existing violations with `per-file-ignores` so only new ones fail.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
