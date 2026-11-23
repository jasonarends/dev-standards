"""Fails when a repo's ruff config doesn't select every rule in the standard set.

Repos keep their own ruff config, with their own per-file baselines; this check only
makes sure none of the standard rules is missing, so the configs can't drift apart.
"""

import sys
import tomllib
from pathlib import Path

CONFIGS = (".ruff.toml", "ruff.toml", "pyproject.toml")
STANDARD = Path(__file__).with_name("ruff.toml")


def standard_rules():
    """Returns the rule selectors in the packaged ruff.toml."""
    return tomllib.loads(STANDARD.read_text(encoding="utf-8"))["lint"]["select"]


class ConfigError(Exception):
    """Raised when a ruff config's `extend` chain can't be read."""


def lint_rules(data, base, seen=()):
    """Returns (selected, ignored) selectors from a ruff config, following `extend`."""
    lint = data.get("lint", data)
    selected = [*lint.get("select", []), *lint.get("extend-select", [])]
    ignored = [*lint.get("ignore", []), *lint.get("extend-ignore", [])]
    if parent := data.get("extend"):
        path = (base / parent).resolve()
        if path in seen:
            raise ConfigError(f"`extend` loops back to {parent}")
        if not path.exists():
            raise ConfigError(f"`extend` points at {parent}, which doesn't exist")
        more = lint_rules(tomllib.loads(path.read_text(encoding="utf-8")), path.parent, (*seen, path))
        selected, ignored = selected + more[0], ignored + more[1]
    return selected, ignored


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
        return name, lint_rules(data, path.parent)
    return None, None


def covered(rule, selectors):
    """True if a selector enables the rule: ALL, an exact match, or a prefix ending before a digit."""
    return any(s == "ALL" or rule == s or (rule.startswith(s) and rule[len(s)].isdigit()) for s in selectors)


def overlaps(rule, selectors):
    """True if a selector turns off any part of the rule, including a narrower code in its family."""
    return covered(rule, selectors) or any(s.startswith(rule) and s[len(rule) :].isdigit() for s in selectors)


def main():
    try:
        name, rules = repo_lint_config()
    except ConfigError as e:
        print(f"ruff-rules: {e}. Fix the path so ruff and this check read the same config.")
        return 1
    if rules is None:
        print("ruff-rules: no ruff config found. Copy dev-standards' ruff.toml `[lint] select` into ruff.toml.")
        return 1
    selected, ignored = rules
    missing = [r for r in standard_rules() if not covered(r, selected) or overlaps(r, ignored)]
    if missing:
        print(f"ruff-rules: {name} doesn't enforce {', '.join(missing)}. Select them (and drop any global")
        print("  `ignore` of them), and baseline existing violations with `per-file-ignores` so only new ones fail.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
