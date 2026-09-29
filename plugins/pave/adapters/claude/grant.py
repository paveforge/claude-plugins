#!/usr/bin/env python3
"""Grant Claude Code access to services already registered in a Pave hub."""

import json
import os
import pathlib
import sys


def die(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def find_hub():
    current = pathlib.Path(os.environ.get("PAVE_HUB", os.getcwd())).resolve()
    for path in (current, *current.parents):
        if (path / ".pave-hub").exists():
            return path
    die("no .pave-hub found. Run /pave:init first, or set PAVE_HUB.")


def registered(workspace, path):
    absolute = str(path)
    for line in workspace.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition(":")
        if sep and key == "path" and value.strip().strip("'\"") == absolute:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        die("usage: grant.py <folder>...")
    hub = find_hub()
    workspace = hub / "workspace.yaml"
    settings = hub / ".claude" / "settings.json"
    try:
        raw = settings.read_text(encoding="utf-8") if settings.exists() else ""
        config = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError) as e:
        die(f"cannot read {settings}: {e}")
    if not isinstance(config, dict):
        die(f"{settings} must contain a JSON object")
    directories = config.setdefault("additionalDirectories", [])
    if not isinstance(directories, list):
        die(f"additionalDirectories in {settings} must be an array")
    changed = False
    for raw_path in sys.argv[1:]:
        path = pathlib.Path(raw_path).resolve()
        if not registered(workspace, path):
            print(f"skip   {path} — not registered in {workspace}")
            continue
        if str(path) not in directories:
            directories.append(str(path))
            changed = True
            print(f"grant  {path}")
    if changed:
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
