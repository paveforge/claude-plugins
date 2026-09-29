#!/usr/bin/env python3
"""Resolve and validate Pave's Codex-specific hub configuration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def find_hub() -> Path:
    raw = os.environ.get("PAVE_HUB")
    current = Path(raw).expanduser() if raw else Path.cwd()
    try:
        current = current.resolve(strict=True)
    except OSError as exc:
        die(f"cannot resolve {current}: {exc}")
    for candidate in (current, *current.parents):
        if (candidate / ".pave-hub").exists():
            return candidate
    die("no .pave-hub found. Run $pave-init first, or set PAVE_HUB.")


def find_config(hub: Path) -> Path:
    matches = [
        hub / name
        for name in ("config.codex.toml", "config.codex.yaml", "config.codex.yml")
        if (hub / name).is_file()
    ]
    if not matches:
        die(f"no Codex config file in {hub}. Run $pave-init to write one.")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        die(f"more than one Codex config file in {hub}: {names}. Keep exactly one.")
    return matches[0]


def runtime_root() -> Path:
    return Path(__file__).resolve().parents[2]


def reader(config: Path) -> Path:
    name = "toml-reader" if config.suffix == ".toml" else "yaml-reader"
    return runtime_root() / "scripts" / name


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True)


def agent(role: str) -> int:
    if role not in {"analyst", "builder", "explorer", "planner", "retriever", "reviewer"}:
        die(f"unknown agent: {role}")
    config = find_config(find_hub())
    result = run([sys.executable, str(reader(config)), str(config), f"agents.{role}"])
    if result.returncode == 3:
        die(f"{config} has no entry for agents.{role}. Run $pave-init to bring it up to date.")
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        die(f"cannot read {config}")
    values = dict(
        line.split("=", 1)
        for line in result.stdout.splitlines()
        if "=" in line
    )
    if not values.get("model") or not values.get("effort"):
        die(f"agents.{role} in {config} needs both model and effort. Run $pave-init to bring it up to date.")
    print(f"model={values['model']}")
    print(f"effort={values['effort']}")
    return 0


def config_check() -> int:
    config = find_config(find_hub())
    template = runtime_root() / "templates" / "config.codex.yaml"
    return subprocess.call(
        [sys.executable, str(runtime_root() / "scripts" / "pave-config.py"), str(config), str(template)]
    )


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "agent":
        return agent(sys.argv[2])
    if len(sys.argv) == 2 and sys.argv[1] == "config-check":
        return config_check()
    die("usage: config.py agent <role> | config-check")


if __name__ == "__main__":
    raise SystemExit(main())
