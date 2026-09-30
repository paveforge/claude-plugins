#!/usr/bin/env python3
"""Install and remove the pave-setup skill for supported coding-agent hosts.

Pave Installer does not convert Pave. It installs one skill, pave-setup, that
tells the host where the Pave source is and what must hold after the host
converts it. Every installed file is tracked by content hash, so updates and
removal never silently overwrite user edits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlsplit, urlunsplit


MANIFEST_VERSION = 2
LEGACY_MANIFEST_VERSION = 1
PLACEHOLDER = re.compile(r"@@[A-Z_]+@@")


class HostError(Exception):
    pass


def home() -> Path:
    raw = os.environ.get("HOME", "")
    if not raw:
        raise HostError("HOME is not set")
    return Path(raw).expanduser()


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(home() / ".codex"))).expanduser()


@dataclass(frozen=True)
class Host:
    name: str
    title: str
    invoke: str
    home: Callable[[], Path]
    skills: Callable[[], Path]


HOSTS = {
    "codex": Host("codex", "Codex", "$pave-setup", codex_home, lambda: home() / ".agents" / "skills"),
    "kiro": Host("kiro", "Kiro", "/pave-setup", lambda: home() / ".kiro", lambda: home() / ".kiro" / "skills"),
}


@dataclass(frozen=True)
class Target:
    path: Path
    content: bytes
    executable: bool = False

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class Source:
    local: Path
    version: str
    repository: str
    commit: str


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_pave_source() -> Path:
    return plugin_root().parent / "pave"


def setup_dir(host: Host) -> Path:
    return host.skills() / "pave-setup"


def manifest_path(host: Host) -> Path:
    return host.home() / "pave-installer" / "install.json"


def git(source: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source), *args], capture_output=True, text=True
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def https_url(raw: str) -> str:
    """Return raw as an HTTPS URL without credentials, or '' if it is not HTTPS."""
    parts = urlsplit(raw.strip())
    if parts.scheme != "https" or not parts.hostname:
        return ""
    netloc = parts.hostname + (f":{parts.port}" if parts.port else "")
    return urlunsplit(("https", netloc, parts.path, "", ""))


def read_source(local: Path) -> Source:
    path = local / ".claude-plugin" / "plugin.json"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        version = str(meta["version"])
    except (OSError, KeyError, ValueError) as e:
        raise HostError(f"cannot read Pave version from {path}: {e}") from e
    repository = https_url(git(local, "remote", "get-url", "origin"))
    commit = git(local, "rev-parse", "HEAD") if repository else ""
    if not repository:
        repository = https_url(str(meta.get("repository", "")))
    if not repository:
        raise HostError(
            f"no HTTPS repository for Pave: neither the git remote of {local} "
            f"nor the repository in {path} is an https:// URL"
        )
    return Source(local, version, repository, commit)


def render(template: Path, values: dict[str, str]) -> bytes:
    text = template.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(f"@@{key}@@", value)
    left = PLACEHOLDER.findall(text)
    if left:
        raise HostError(f"unfilled placeholders in {template.name}: {', '.join(sorted(set(left)))}")
    return text.encode()


def setup_targets(host: Host, source: Source) -> list[Target]:
    templates = plugin_root() / "templates" / "pave-setup"
    folder = setup_dir(host)
    script = folder / "pave-installer.sh"
    skill = render(
        templates / "SKILL.md",
        {
            "HOST": host.name,
            "HOST_TITLE": host.title,
            "HOST_HOME": str(host.home()),
            "SKILLS_DIR": str(host.skills()),
            "SCRIPT": str(script),
        },
    )
    runner = render(
        templates / "pave-installer.sh",
        {
            "LOCAL": shlex.quote(str(source.local)),
            "VERSION": shlex.quote(source.version),
            "REPOSITORY": shlex.quote(source.repository),
            "COMMIT": shlex.quote(source.commit),
            "REINSTALL": shlex.quote(f"/pave-installer:install {host.name}"),
        },
    )
    return [Target(folder / "SKILL.md", skill), Target(script, runner, executable=True)]


def load_manifest(path: Path, version: int) -> dict:
    if not path.exists():
        return {"manifest_version": version, "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HostError(f"cannot read installation manifest {path}: {e}") from e
    if data.get("manifest_version") != version or not isinstance(data.get("files"), dict):
        raise HostError(f"unsupported installation manifest {path}")
    return data


def write_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def beneath(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def state_of(path: Path, recorded: Optional[str]) -> str:
    """How an installed file compares with what the manifest recorded."""
    if path.is_symlink():
        return "preserve"
    if not path.exists():
        return "missing"
    return "remove" if sha256(path) == recorded else "preserve"


def classify(target: Target, old_files: dict[str, dict]) -> str:
    path = target.path
    if path.is_symlink():
        return "conflict"
    if not path.exists():
        return "create"
    current = sha256(path)
    if current == target.digest:
        return "unchanged"
    previous = old_files.get(str(path), {}).get("sha256")
    return "update" if previous and current == previous else "conflict"


def empty_parents(path: Path, stops: set[Path]) -> None:
    parent = path.parent
    while parent not in stops and parent != parent.parent:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


# Pave Installer 0.1 generated Codex skills, agents and a runtime itself. Its
# manifest lives in $CODEX_HOME/pave/install.json; those files are removed
# once, keeping any the user edited.
def legacy_manifest(host: Host) -> Optional[Path]:
    return host.home() / "pave" / "install.json" if host.name == "codex" else None


def legacy_managed(path: Path, host: Host) -> bool:
    skills, agents = host.skills(), host.home() / "agents"
    if beneath(path, host.home() / "pave" / "runtime"):
        return True
    if path.parent == agents and path.name.startswith("pave_") and path.suffix == ".toml":
        return True
    try:
        rel = path.relative_to(skills)
    except ValueError:
        return False
    return len(rel.parts) >= 2 and rel.parts[0].startswith("pave-") and rel.parts[0] != "pave-setup"


def legacy_actions(host: Host) -> list[tuple[str, Path]]:
    path = legacy_manifest(host)
    if path is None or not path.exists():
        return []
    files = load_manifest(path, LEGACY_MANIFEST_VERSION)["files"]
    actions = []
    for raw, info in sorted(files.items()):
        file = Path(raw)
        if not legacy_managed(file, host):
            raise HostError(f"legacy manifest {path} contains a path outside the old Codex adapter: {raw}")
        actions.append((state_of(file, info.get("sha256")), file))
    return actions


def apply_legacy(host: Host, actions: list[tuple[str, Path]]) -> list[Path]:
    """Remove unchanged legacy files. Return the ones preserved."""
    path = legacy_manifest(host)
    if path is None or not actions:
        return []
    data = load_manifest(path, LEGACY_MANIFEST_VERSION)
    stops = {host.skills(), host.home() / "agents", path.parent}
    preserved = []
    for action, file in actions:
        if action == "preserve":
            preserved.append(file)
            continue
        if action == "remove":
            file.unlink()
        empty_parents(file, stops)
    if preserved:
        data["files"] = {str(f): data["files"][str(f)] for f in preserved}
        write_manifest(path, data)
    else:
        path.unlink()
        empty_parents(path, {host.home()})
    return preserved


def print_legacy(actions: list[tuple[str, Path]]) -> None:
    for action, path in actions:
        print(f"{action:<9} {path} (Pave Installer 0.1)")


def install(host: Host, local: Path, apply: bool) -> int:
    source = read_source(local)
    targets = setup_targets(host, source)
    manifest = manifest_path(host)
    old_files = load_manifest(manifest, MANIFEST_VERSION)["files"]
    folder = setup_dir(host)
    for raw in old_files:
        if not beneath(Path(raw), folder):
            raise HostError(f"manifest {manifest} contains a path outside {folder}: {raw}")
    legacy = legacy_actions(host)
    actions = [(classify(t, old_files), t) for t in targets]

    print(f"{'install' if apply else 'plan'}: pave-setup for {host.title}")
    print(f"source    Pave {source.version} at {source.local}")
    print(f"fallback  {source.repository}" + (f" at {source.commit}" if source.commit else ""))
    for action, target in actions:
        print(f"{action:<9} {target.path}")
    print_legacy(legacy)
    if not apply:
        return 0

    preserved = apply_legacy(host, legacy)
    recorded = dict(old_files)
    for action, target in actions:
        if action in {"create", "update"}:
            target.path.parent.mkdir(parents=True, exist_ok=True)
            target.path.write_bytes(target.content)
            if target.executable:
                target.path.chmod(target.path.stat().st_mode | 0o111)
        if action != "conflict":
            recorded[str(target.path)] = {"sha256": target.digest}
    write_manifest(
        manifest,
        {
            "manifest_version": MANIFEST_VERSION,
            "host": host.name,
            "pave_version": source.version,
            "files": recorded,
        },
    )
    print(f"manifest  {manifest}")
    conflicts = [str(t.path) for a, t in actions if a == "conflict"]
    if conflicts or preserved:
        print("result: installed; preserved files the user edited", file=sys.stderr)
        return 2
    print(f"result: installed; run {host.invoke} in {host.title} to build Pave")
    return 0


def uninstall(host: Host, apply: bool) -> int:
    manifest = manifest_path(host)
    legacy = legacy_actions(host)
    if not manifest.exists() and not legacy:
        raise HostError(f"no pave-setup installed by Pave Installer for {host.title} ({manifest})")
    data = load_manifest(manifest, MANIFEST_VERSION)
    folder = setup_dir(host)
    actions = []
    for raw, info in sorted(data["files"].items()):
        path = Path(raw)
        if not beneath(path, folder):
            raise HostError(f"manifest {manifest} contains a path outside {folder}: {raw}")
        actions.append((state_of(path, info.get("sha256")), path))

    print(f"{'uninstall' if apply else 'plan'}: pave-setup for {host.title}")
    for action, path in actions:
        print(f"{action:<9} {path}")
    print_legacy(legacy)
    if not apply:
        return 0

    preserved = apply_legacy(host, legacy)
    remaining = {}
    for action, path in actions:
        if action == "preserve":
            remaining[str(path)] = data["files"][str(path)]
            continue
        if action == "remove":
            path.unlink()
        empty_parents(path, {host.skills()})
    if remaining:
        data["files"] = remaining
        write_manifest(manifest, data)
    elif manifest.exists():
        manifest.unlink()
        empty_parents(manifest, {host.home()})
    if remaining or preserved:
        print("result: partial uninstall; preserved files the user edited", file=sys.stderr)
        return 2
    print("result: uninstalled")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan-install", "install", "plan-uninstall", "uninstall"))
    p.add_argument("host", choices=tuple(HOSTS))
    p.add_argument("--source-root", type=Path, default=default_pave_source(), help=argparse.SUPPRESS)
    return p


def main() -> int:
    args = parser().parse_args()
    host = HOSTS[args.host]
    try:
        if args.action in {"plan-install", "install"}:
            return install(host, args.source_root.resolve(), args.action == "install")
        return uninstall(host, args.action == "uninstall")
    except HostError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
