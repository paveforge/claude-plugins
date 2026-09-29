#!/usr/bin/env python3
"""Install and remove Pave adapters for supported coding-agent hosts.

The source Pave plugin remains authoritative. Host installations are generated
from it and tracked by content hash so updates and removal never silently
overwrite user edits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


ROLES = ("analyst", "builder", "explorer", "planner", "retriever", "reviewer")
READ_ONLY_ROLES = {"explorer", "retriever", "reviewer"}
MANIFEST_VERSION = 1


class HostError(Exception):
    pass


@dataclass(frozen=True)
class Target:
    path: Path
    content: bytes
    executable: bool = False

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def beneath(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def managed_path(path: Path, skills: Path, agents: Path, runtime: Path) -> bool:
    if beneath(path, runtime):
        return True
    if path.parent == agents and path.name.startswith("pave_") and path.suffix == ".toml":
        return True
    try:
        rel = path.relative_to(skills)
    except ValueError:
        return False
    return len(rel.parts) >= 2 and rel.parts[0].startswith("pave-")


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_pave_source() -> Path:
    return plugin_root().parent / "pave"


def plugin_version(source: Path) -> str:
    path = source / ".claude-plugin" / "plugin.json"
    try:
        return str(json.loads(path.read_text(encoding="utf-8"))["version"])
    except (OSError, KeyError, ValueError) as e:
        raise HostError(f"cannot read Pave version from {path}: {e}") from e


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise HostError("Markdown file has no frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise HostError("Markdown frontmatter is not closed")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip()] = value.strip()
    return values, text[end + 5 :]


def codex_text(text: str, runtime: Path) -> str:
    roles = "|".join(ROLES)
    text = re.sub(
        rf'(?:"\$\{{CLAUDE_PLUGIN_ROOT\}}"/scripts/)?pave\.sh agent ({roles})',
        lambda m: f'python3 "{runtime}/adapters/codex/config.py" agent {m.group(1)}',
        text,
    )
    text = text.replace("${CLAUDE_PLUGIN_ROOT}", str(runtime))
    text = text.replace("$ARGUMENTS", "{arguments}")
    text = re.sub(r"/pave:([a-z]+)", r"$pave-\1", text)
    text = text.replace("Claude's Artifact tool", "the host's artifact tool")
    text = text.replace("`SendMessage`", "the host's agent messaging tool")
    for role in ROLES:
        text = text.replace(f"`{role}`", f"`pave_{role}`")
    return text


def codex_host_text(text: str, runtime: Path) -> str:
    """Translate user-facing hub references for the Codex host."""
    text = codex_text(text, runtime)
    text = re.sub(
        r"\bconfig\.(?!codex\.)(toml|yaml|yml)\b",
        r"config.codex.\1",
        text,
    )
    text = re.sub(
        r'(?:"[^"\n]+"/scripts/)?pave\.sh config-check',
        f'python3 "{runtime}/adapters/codex/config.py" config-check',
        text,
    )
    return text


def codex_runtime_script(text: str, runtime: Path) -> str:
    """Remove Claude-only settings writes from the installed Pave runtime."""
    text = codex_text(text, runtime)
    text = text.replace('  local settings="$hub/.claude/settings.json"\n', "")
    text = re.sub(
        r"\n    if have_python; then\n"
        r"      PAVE_DIR=.*?"
        r"\n    fi\n",
        "\n",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"# agent <name>\n.*?(?=# find_config <hub>)",
        """# agent <name>
# Delegates host policy to the Codex adapter installed beside this runtime.
cmd_agent() {
  [ $# -eq 1 ] || die "usage: pave.sh agent <name>"
  python3 "$SCRIPTS/../adapters/codex/config.py" agent "$1"
}

# config-check
cmd_config_check() {
  [ $# -eq 0 ] || die "usage: pave.sh config-check"
  python3 "$SCRIPTS/../adapters/codex/config.py" config-check
}

""",
        text,
        flags=re.DOTALL,
    )
    return text


def codex_skill(source_skill: Path, runtime: Path, skill_root: Path) -> bytes:
    meta, body = frontmatter(source_skill.read_text(encoding="utf-8"))
    name = meta.get("name", source_skill.parent.name)
    description = codex_host_text(meta.get("description", "Pave workflow"), runtime)
    if name == "add":
        description = description.replace(
            "and grants Claude access to it",
            "for use by Pave on Codex",
        )
        body = body.replace(
            "Run the script. It does the whole job:",
            "Run the deterministic registration script. Codex access to sibling service\n"
            "folders follows the sandbox and permission mode selected for this session:",
        )
        body = body.replace(
            "Run the deterministic registration script, then the Claude adapter that grants\n"
            "this session access to every folder the script successfully registered:",
            "Run the deterministic registration script. Codex access to sibling service\n"
            "folders follows the sandbox and permission mode selected for this session:",
        )
        body = re.sub(
            r'\npython3 "\$\{CLAUDE_PLUGIN_ROOT\}"/adapters/claude/grant\.py \$ARGUMENTS',
            "",
            body,
        )
        body = body.replace(
            "The adapter separately merges\nregistered paths into `additionalDirectories`.\n",
            "\n",
        )
        body = body.replace(
            "absolute path, append to `workspace.yaml`, merge into `additionalDirectories`.",
            "absolute path and append to `workspace.yaml`. Filesystem access is controlled\n"
            "by the current Codex permission profile.",
        )
        body = re.sub(
            r"\| `WARN` \| `settings\.json`.*?\n",
            "",
            body,
        )
        body = re.sub(r"\| adapter error \|.*?\n", "", body)
        body = body.replace(
            "Do not edit `workspace.yaml` or `settings.json` yourself.",
            "Do not edit `workspace.yaml` yourself.",
        )
    elif name == "init":
        body = re.sub(r"\| `\.claude/settings\.json` \|.*?\n", "", body)
        body = body.replace(
            "`.claude/settings.json` belongs to Claude Code, not to Pave. Merge into it;\n"
            "never replace it.\n\n",
            "",
        )
    elif name == "help":
        body = body.replace(
            "`${CLAUDE_PLUGIN_ROOT}/skills/*/SKILL.md`",
            f"`{skill_root}/pave-*/SKILL.md`",
        )
    prefix = (
        "\nCodex adapter rules:\n"
        "- `{arguments}` in a command is a placeholder. Replace it with the "
        "arguments from the user's invocation, shell-quoted safely; never run "
        "the placeholder literally.\n"
        "- Spawn Pave custom agents by the `pave_<role>` names used below.\n"
        f'- Use the model and reasoning effort printed by `python3 "{runtime}/adapters/codex/config.py" agent <role>`.\n'
    )
    rendered = (
        "---\n"
        f"name: pave-{name}\n"
        f"description: {description}\n"
        "---\n"
        + prefix
        + codex_host_text(body, runtime)
    )
    return rendered.encode()


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_agent(source_agent: Path) -> bytes:
    meta, body = frontmatter(source_agent.read_text(encoding="utf-8"))
    role = meta.get("name", source_agent.stem)
    description = codex_text(meta.get("description", f"Pave {role}"), Path("<PAVE_RUNTIME>"))
    instructions = codex_text(body, Path("<PAVE_RUNTIME>"))
    rows = [
        f'name = "pave_{role}"',
        f"description = {toml_string(description)}",
    ]
    if role in READ_ONLY_ROLES:
        rows.append('sandbox_mode = "read-only"')
    rows.extend(("developer_instructions = '''", instructions.rstrip(), "'''", ""))
    return "\n".join(rows).encode()


def install_paths(scope: str, project_root: Optional[Path]) -> tuple[Path, Path, Path, Path]:
    if scope == "user":
        home = Path(os.environ.get("HOME", "")).expanduser()
        if not str(home):
            raise HostError("HOME is not set")
        codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).expanduser()
        skill_root = home / ".agents" / "skills"
        agent_root = codex_home / "agents"
        state_root = codex_home / "pave"
    else:
        root = (project_root or Path.cwd()).resolve()
        skill_root = root / ".agents" / "skills"
        agent_root = root / ".codex" / "agents"
        state_root = root / ".codex" / "pave"
    return skill_root, agent_root, state_root / "runtime", state_root / "install.json"


def native_plugin_path(scope: str, project_root: Optional[Path]) -> Path:
    if scope == "user":
        home = Path(os.environ.get("HOME", "")).expanduser()
        codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).expanduser()
        return codex_home / "plugins" / "pave"
    return (project_root or Path.cwd()).resolve() / "plugins" / "pave"


def codex_targets(source: Path, scope: str, project_root: Optional[Path]) -> tuple[list[Target], Path]:
    skills, agents, runtime, manifest = install_paths(scope, project_root)
    targets: list[Target] = []

    for skill in sorted((source / "skills").glob("*/SKILL.md")):
        if skill.parent.name in {"install", "uninstall"}:
            continue
        dest_dir = skills / f"pave-{skill.parent.name}"
        targets.append(Target(dest_dir / "SKILL.md", codex_skill(skill, runtime, skills)))
        for extra in sorted(skill.parent.rglob("*")):
            if extra.is_file() and extra.name != "SKILL.md":
                rel = extra.relative_to(skill.parent)
                if extra.suffix in {".md", ".txt", ".yaml", ".yml", ".toml", ".json"}:
                    content = codex_text(extra.read_text(encoding="utf-8"), runtime).encode()
                else:
                    content = extra.read_bytes()
                targets.append(Target(dest_dir / rel, content))

    for agent in sorted((source / "agents").glob("*.md")):
        targets.append(Target(agents / f"pave_{agent.stem}.toml", codex_agent(agent)))

    for folder in ("agents", "scripts", "templates"):
        for item in sorted((source / folder).rglob("*")):
            if not item.is_file() or "__pycache__" in item.parts:
                continue
            rel = item.relative_to(source)
            content = item.read_bytes()
            if folder == "scripts" and item.name == "pave.sh":
                content = codex_runtime_script(content.decode(), runtime).encode()
            elif folder == "scripts" and (item.suffix == ".py" or item.name in {
                "toml-reader",
                "yaml-reader",
            }):
                content = codex_text(content.decode(), runtime).encode()
            elif folder == "templates" and (
                item.name == "hub-AGENTS.md" or item.name.startswith("config.codex.")
            ):
                content = codex_host_text(content.decode(), runtime).encode()
            targets.append(Target(runtime / rel, content, os.access(item, os.X_OK)))

    installer = plugin_root()
    codex_config = installer / "templates" / "config.codex.yaml"
    config_adapter = installer / "adapters" / "codex" / "config.py"
    targets.append(
        Target(
            runtime / "templates" / "config.codex.yaml",
            codex_host_text(codex_config.read_text(encoding="utf-8"), runtime).encode(),
        )
    )
    targets.append(
        Target(
            runtime / "adapters" / "codex" / "config.py",
            config_adapter.read_bytes(),
            executable=True,
        )
    )

    portable_manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "pave",
        "version": plugin_version(source),
        "description": "Plan cross-service features and build them with isolated agents.",
    }
    targets.append(
        Target(
            runtime / "plugin.json",
            (json.dumps(portable_manifest, indent=2) + "\n").encode(),
        )
    )
    return targets, manifest


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"manifest_version": MANIFEST_VERSION, "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HostError(f"cannot read installation manifest {path}: {e}") from e
    if data.get("manifest_version") != MANIFEST_VERSION or not isinstance(data.get("files"), dict):
        raise HostError(f"unsupported installation manifest {path}")
    return data


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


def install(source: Path, scope: str, project_root: Optional[Path], apply: bool) -> int:
    targets, manifest_path = codex_targets(source, scope, project_root)
    skills, agents, runtime, _ = install_paths(scope, project_root)
    native = native_plugin_path(scope, project_root)
    if not manifest_path.exists() and native.exists():
        raise HostError(
            f"Pave appears to be installed through the Codex plugin manager at {native}; "
            "update it through that manager"
        )
    old = load_manifest(manifest_path)
    old_files = old.get("files", {})
    for raw in old_files:
        if not managed_path(Path(raw), skills, agents, runtime):
            raise HostError(f"manifest contains a path outside the Codex adapter: {raw}")
    desired = {str(t.path): t for t in targets}
    actions = [(classify(t, old_files), t) for t in targets]

    obsolete: list[tuple[str, Path]] = []
    for raw, info in old_files.items():
        if raw in desired:
            continue
        path = Path(raw)
        if path.is_symlink():
            state = "preserve"
        elif not path.exists():
            state = "missing"
        elif sha256(path) == info.get("sha256"):
            state = "remove"
        else:
            state = "preserve"
        obsolete.append((state, path))

    verb = "install" if apply else "plan"
    print(f"{verb}: codex ({scope})")
    for action, target in actions:
        print(f"{action:<9} {target.path}")
    for action, path in obsolete:
        print(f"{action:<9} {path} (obsolete)")

    if not apply:
        return 0

    recorded = dict(old_files)
    for action, target in actions:
        if action in {"create", "update"}:
            target.path.parent.mkdir(parents=True, exist_ok=True)
            target.path.write_bytes(target.content)
            if target.executable:
                target.path.chmod(target.path.stat().st_mode | 0o111)
        if action != "conflict":
            recorded[str(target.path)] = {
                "sha256": target.digest,
                "executable": target.executable,
            }
    for action, path in obsolete:
        if action in {"remove", "missing"}:
            if action == "remove":
                path.unlink()
            recorded.pop(str(path), None)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "manifest_version": MANIFEST_VERSION,
        "host": "codex",
        "scope": scope,
        "pave_version": plugin_version(source),
        "source": str(source),
        "files": recorded,
    }
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest  {manifest_path}")
    conflicts = [str(t.path) for a, t in actions if a == "conflict"]
    if conflicts:
        print("result: installed with conflicts; preserved modified files", file=sys.stderr)
        return 2
    print("result: installed; start a new Codex session if the skills are not visible")
    return 0


def empty_parents(path: Path, stops: set[Path]) -> None:
    parent = path.parent
    while parent not in stops and parent != parent.parent:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def uninstall(scope: str, project_root: Optional[Path], apply: bool) -> int:
    skills, agents, runtime, manifest_path = install_paths(scope, project_root)
    if not manifest_path.exists():
        native = native_plugin_path(scope, project_root)
        if native.exists():
            raise HostError(
                f"Pave appears to be installed through the Codex plugin manager at {native}; "
                "uninstall it through that manager"
            )
        raise HostError(f"no Pave-managed Codex installation at {manifest_path}")
    data = load_manifest(manifest_path)
    files = data["files"]
    actions: list[tuple[str, Path]] = []
    for raw, info in sorted(files.items()):
        path = Path(raw)
        if not managed_path(path, skills, agents, runtime):
            raise HostError(f"manifest contains a path outside the Codex adapter: {path}")
        if path.is_symlink():
            action = "preserve"
        elif not path.exists():
            action = "missing"
        elif sha256(path) == info.get("sha256"):
            action = "remove"
        else:
            action = "preserve"
        actions.append((action, path))

    verb = "uninstall" if apply else "plan"
    print(f"{verb}: codex ({scope})")
    for action, path in actions:
        print(f"{action:<9} {path}")
    if not apply:
        return 0

    remaining: dict[str, dict] = {}
    managed_stops = {skills, agents, manifest_path.parent}
    for action, path in actions:
        if action == "remove":
            path.unlink()
            empty_parents(path, managed_stops)
        elif action == "preserve":
            remaining[str(path)] = files[str(path)]
    if remaining:
        data["files"] = remaining
        manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("result: partial uninstall; preserved modified files", file=sys.stderr)
        return 2
    manifest_path.unlink()
    empty_parents(
        manifest_path,
        {skills, agents, agents.parent, Path.home(), Path.cwd().resolve()},
    )
    print("result: uninstalled")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan-install", "install", "plan-uninstall", "uninstall"))
    p.add_argument("host", choices=("codex",))
    p.add_argument("--scope", choices=("user", "project"), default="user")
    p.add_argument("--project-root", type=Path)
    p.add_argument("--source-root", type=Path, default=default_pave_source(), help=argparse.SUPPRESS)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        if args.scope == "user" and args.project_root:
            raise HostError("--project-root requires --scope project")
        if args.action in {"plan-install", "install"}:
            return install(
                args.source_root.resolve(),
                args.scope,
                args.project_root,
                args.action == "install",
            )
        return uninstall(args.scope, args.project_root, args.action == "uninstall")
    except HostError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
