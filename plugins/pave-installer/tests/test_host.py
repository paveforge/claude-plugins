import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


INSTALLER = Path(__file__).resolve().parents[1]
PAVE = INSTALLER.parent / "pave"
HOST = INSTALLER / "scripts" / "pave-host.py"
VERSION = json.loads((PAVE / ".claude-plugin" / "plugin.json").read_text())["version"]
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_COUNT": "0",
}
SKILLS = {"codex": (".agents", "skills"), "kiro": (".kiro", "skills")}
HOMES = {"codex": (".codex",), "kiro": (".kiro",)}


def run_host(home, *args, source=PAVE):
    env = {**os.environ, **GIT_ENV, "HOME": str(home), "CODEX_HOME": str(home / ".codex")}
    return subprocess.run(
        [sys.executable, str(HOST), *args, "--source-root", str(source)],
        capture_output=True, text=True, cwd=str(home), env=env,
    )


def setup_dir(home, host):
    return home.joinpath(*SKILLS[host], "pave-setup")


def manifest(home, host):
    return home.joinpath(*HOMES[host], "pave-installer", "install.json")


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()


def git_source(tmp_path, remote="https://github.com/example/pave.git"):
    """A repository holding plugins/pave, as the marketplace download does."""
    repo = tmp_path / "repo"
    shutil.copytree(PAVE, repo / "plugins" / "pave", ignore=shutil.ignore_patterns("__pycache__"))
    git(repo, "init", "--quiet")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "pave")
    git(repo, "remote", "add", "origin", remote)
    return repo


def plain_source(tmp_path, repository=None):
    source = tmp_path / "plain" / "pave"
    shutil.copytree(PAVE, source, ignore=shutil.ignore_patterns("__pycache__"))
    if repository is not None:
        meta_path = source / ".claude-plugin" / "plugin.json"
        meta = json.loads(meta_path.read_text())
        meta["repository"] = repository
        meta_path.write_text(json.dumps(meta))
    return source


def script_values(script):
    text = script.read_text()
    return dict(re.findall(r"^(PAVE_[A-Z]+)=(.*)$", text, flags=re.M))


def with_values(script, dest, **values):
    """Copy an installed pave-installer.sh with some values replaced."""
    text = script.read_text()
    for key, value in values.items():
        text = re.sub(rf"^{key}=.*$", f"{key}='{value}'", text, flags=re.M)
    dest.write_text(text)
    return dest


def locate(script, env=None, tmpdir=None):
    run_env = {**os.environ, **GIT_ENV, **(env or {})}
    if tmpdir:
        run_env["TMPDIR"] = str(tmpdir)
    return subprocess.run(["/bin/bash", str(script), "locate"], capture_output=True, text=True, env=run_env)


def reported(result):
    return dict(line.split("=", 1) for line in result.stdout.splitlines())


def test_marketplace_versions_match_sources():
    marketplace = json.loads((INSTALLER.parent.parent / ".claude-plugin" / "marketplace.json").read_text())
    for name, root in (("pave", PAVE), ("pave-installer", INSTALLER)):
        source = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
        listed = next(plugin for plugin in marketplace["plugins"] if plugin["name"] == name)
        assert listed["version"] == source["version"]


@pytest.mark.parametrize("host,title,invoke", [("codex", "Codex", "$pave-setup"), ("kiro", "Kiro", "/pave-setup")])
def test_install_writes_only_pave_setup(tmp_path, host, title, invoke):
    home = tmp_path / "home"
    home.mkdir()
    result = run_host(home, "install", host, source=git_source(tmp_path) / "plugins" / "pave")
    assert result.returncode == 0, result.stderr
    assert f"run {invoke} in {title}" in result.stdout

    folder = setup_dir(home, host)
    assert sorted(p.name for p in folder.iterdir()) == ["SKILL.md", "pave-installer.sh"]
    skill = (folder / "SKILL.md").read_text()
    script = folder / "pave-installer.sh"
    for text in (skill, script.read_text()):
        assert "@@" not in text
    assert skill.startswith("---\nname: pave-setup\n")
    assert f"Pave setup for {title}" in skill
    assert f"config.{host}.yaml" in skill
    assert str(script) in skill
    assert str(home.joinpath(*HOMES[host])) in skill
    assert script.stat().st_mode & 0o111

    data = json.loads(manifest(home, host).read_text())
    assert data["host"] == host
    assert data["pave_version"] == VERSION
    assert sorted(data["files"]) == [str(folder / "SKILL.md"), str(script)]
    # Nothing else: no converted skills, agents or runtime.
    installed = {p for p in home.rglob("*") if p.is_file()}
    assert installed == {folder / "SKILL.md", script, manifest(home, host)}


def test_install_records_https_remote_and_commit(tmp_path):
    repo = git_source(tmp_path, remote="https://user:secret@github.com/example/pave.git")
    home = tmp_path / "home"
    home.mkdir()
    assert run_host(home, "install", "kiro", source=repo / "plugins" / "pave").returncode == 0
    values = script_values(setup_dir(home, "kiro") / "pave-installer.sh")
    assert values["PAVE_REPOSITORY"] == "https://github.com/example/pave.git"
    assert values["PAVE_COMMIT"] == git(repo, "rev-parse", "HEAD")
    assert values["PAVE_VERSION"] == VERSION
    assert values["PAVE_LOCAL"] == str(repo / "plugins" / "pave")
    assert values["PAVE_REINSTALL"] == "'/pave-installer:install kiro'"


def test_install_falls_back_to_plugin_repository_without_git(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    source = plain_source(tmp_path, "https://github.com/example/pave")
    assert run_host(home, "install", "kiro", source=source).returncode == 0
    values = script_values(setup_dir(home, "kiro") / "pave-installer.sh")
    assert values["PAVE_REPOSITORY"] == "https://github.com/example/pave"
    assert values["PAVE_COMMIT"] == "''"


def test_install_refuses_a_repository_that_is_not_https(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    ssh = git_source(tmp_path, remote="git@github.com:example/pave.git")
    meta = ssh / "plugins" / "pave" / ".claude-plugin" / "plugin.json"
    meta.write_text(json.dumps({**json.loads(meta.read_text()), "repository": "git@github.com:example/pave.git"}))
    result = run_host(home, "install", "kiro", source=ssh / "plugins" / "pave")
    assert result.returncode == 1
    assert "no HTTPS repository" in result.stderr
    assert not setup_dir(home, "kiro").exists()
    assert not manifest(home, "kiro").exists()


def test_install_is_idempotent(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    assert run_host(home, "install", "kiro").returncode == 0
    before = manifest(home, "kiro").read_text()
    second = run_host(home, "install", "kiro")
    assert second.returncode == 0, second.stderr
    assert "unchanged" in second.stdout
    assert "create" not in second.stdout
    assert manifest(home, "kiro").read_text() == before


def test_update_replaces_only_unchanged_files(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    source = plain_source(tmp_path)
    assert run_host(home, "install", "codex", source=source).returncode == 0
    skill = setup_dir(home, "codex") / "SKILL.md"
    script = setup_dir(home, "codex") / "pave-installer.sh"
    skill.write_text(skill.read_text() + "\nuser edit\n")
    meta = source / ".claude-plugin" / "plugin.json"
    meta.write_text(meta.read_text().replace(f'"version": "{VERSION}"', '"version": "9.9.9"'))

    result = run_host(home, "install", "codex", source=source)
    assert result.returncode == 2
    assert f"conflict  {skill}" in result.stdout
    assert f"update    {script}" in result.stdout
    assert skill.read_text().endswith("user edit\n")
    assert script_values(script)["PAVE_VERSION"] == "9.9.9"


def test_existing_skill_not_written_by_installer_is_preserved(tmp_path):
    home = tmp_path / "home"
    skill = setup_dir(home, "kiro") / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("mine\n")
    result = run_host(home, "install", "kiro")
    assert result.returncode == 2
    assert f"conflict  {skill}" in result.stdout
    assert skill.read_text() == "mine\n"
    assert str(skill) not in json.loads(manifest(home, "kiro").read_text())["files"]


def test_uninstall_removes_pave_setup_and_keeps_edits(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / "config.kiro.yaml").write_text("owned by the user\n")
    assert run_host(home, "install", "kiro").returncode == 0
    built = home / ".kiro" / "skills" / "pave-spec" / "SKILL.md"  # what the host built
    built.parent.mkdir(parents=True)
    built.write_text("host's own\n")

    skill = setup_dir(home, "kiro") / "SKILL.md"
    skill.write_text(skill.read_text() + "\nuser edit\n")
    result = run_host(home, "uninstall", "kiro")
    assert result.returncode == 2
    assert f"preserve  {skill}" in result.stdout
    assert not (setup_dir(home, "kiro") / "pave-installer.sh").exists()
    assert list(json.loads(manifest(home, "kiro").read_text())["files"]) == [str(skill)]

    skill.unlink()
    result = run_host(home, "uninstall", "kiro")
    assert result.returncode == 0, result.stderr
    assert not setup_dir(home, "kiro").exists()
    assert not manifest(home, "kiro").exists()
    assert built.read_text() == "host's own\n"
    assert (hub / "config.kiro.yaml").read_text() == "owned by the user\n"


def test_uninstall_without_installation_fails(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    result = run_host(home, "uninstall", "kiro")
    assert result.returncode == 1
    assert "no pave-setup installed" in result.stderr


def test_manifest_paths_outside_pave_setup_are_rejected(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    assert run_host(home, "install", "kiro").returncode == 0
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("keep me\n")
    data = json.loads(manifest(home, "kiro").read_text())
    data["files"][str(unrelated)] = {"sha256": hashlib.sha256(unrelated.read_bytes()).hexdigest()}
    manifest(home, "kiro").write_text(json.dumps(data))

    for action in ("install", "uninstall"):
        result = run_host(home, action, "kiro")
        assert result.returncode == 1
        assert "outside" in result.stderr
    assert unrelated.read_text() == "keep me\n"


def test_project_scope_is_not_accepted(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    result = run_host(home, "install", "kiro", "--scope", "project")
    assert result.returncode == 2
    assert not setup_dir(home, "kiro").exists()


def legacy_install(home):
    """Files and manifest as Pave Installer 0.1 left them for Codex."""
    kept = home / ".agents" / "skills" / "pave-spec" / "SKILL.md"
    edited = home / ".codex" / "agents" / "pave_builder.toml"
    runtime = home / ".codex" / "pave" / "runtime" / "scripts" / "pave.sh"
    files = {}
    for path in (kept, edited, runtime):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{path.name}\n")
        files[str(path)] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "executable": False}
    edited.write_text("user edit\n")
    legacy = home / ".codex" / "pave" / "install.json"
    legacy.write_text(json.dumps({"manifest_version": 1, "host": "codex", "files": files}))
    return kept, edited, runtime, legacy


@pytest.mark.parametrize("action", ["install", "uninstall"])
def test_codex_legacy_files_are_removed_keeping_edits(tmp_path, action):
    home = tmp_path / "home"
    home.mkdir()
    if action == "uninstall":
        assert run_host(home, "install", "codex").returncode == 0
    kept, edited, runtime, legacy = legacy_install(home)

    plan = run_host(home, f"plan-{action}", "codex")
    assert plan.returncode == 0, plan.stderr
    assert f"remove    {kept} (Pave Installer 0.1)" in plan.stdout
    assert f"preserve  {edited} (Pave Installer 0.1)" in plan.stdout
    assert kept.exists()

    result = run_host(home, action, "codex")
    assert result.returncode == 2
    assert not kept.exists()
    assert not runtime.exists()
    assert edited.read_text() == "user edit\n"
    assert list(json.loads(legacy.read_text())["files"]) == [str(edited)]
    assert (setup_dir(home, "codex") / "SKILL.md").exists() == (action == "install")

    edited.unlink()
    result = run_host(home, action, "codex")
    assert result.returncode == 0, result.stderr
    assert not legacy.exists()


def test_codex_legacy_manifest_outside_old_adapter_is_rejected(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("keep me\n")
    legacy = home / ".codex" / "pave" / "install.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"manifest_version": 1, "files": {
        str(unrelated): {"sha256": hashlib.sha256(unrelated.read_bytes()).hexdigest()},
    }}))
    result = run_host(home, "install", "codex")
    assert result.returncode == 1
    assert "outside the old Codex adapter" in result.stderr
    assert unrelated.exists()


def test_kiro_install_ignores_codex_legacy_manifest(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    kept, _, _, legacy = legacy_install(home)
    assert run_host(home, "install", "kiro").returncode == 0
    assert kept.exists()
    assert legacy.exists()


@pytest.fixture
def installed(tmp_path):
    repo = git_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    assert run_host(home, "install", "kiro", source=repo / "plugins" / "pave").returncode == 0
    work = tmp_path / "tmp"
    work.mkdir()
    return repo, setup_dir(home, "kiro") / "pave-installer.sh", work


def test_locate_uses_the_local_source(installed):
    repo, script, work = installed
    result = locate(script, tmpdir=work)
    assert result.returncode == 0, result.stderr
    assert reported(result) == {"source": "local", "version": VERSION, "path": str(repo / "plugins" / "pave")}
    assert list(work.iterdir()) == []


@pytest.mark.parametrize("pinned", [True, False])
def test_locate_clones_when_the_local_source_is_gone(installed, tmp_path, pinned):
    repo, script, work = installed
    commit = git(repo, "rev-parse", "HEAD") if pinned else ""
    runner = with_values(script, tmp_path / "run.sh",
                         PAVE_LOCAL=str(tmp_path / "gone"), PAVE_REPOSITORY=str(repo), PAVE_COMMIT=commit)
    result = locate(runner, tmpdir=work)
    assert result.returncode == 0, result.stderr
    found = reported(result)
    assert found["source"] == "clone"
    assert found["version"] == VERSION
    clone = Path(found["path"])
    assert (clone / "skills" / "plan" / "SKILL.md").exists()
    assert work in clone.parents

    cleanup = subprocess.run(["/bin/bash", str(runner), "cleanup", str(clone)], capture_output=True, text=True)
    assert cleanup.returncode == 0, cleanup.stderr
    assert list(work.iterdir()) == []


def test_locate_pins_the_installed_commit(installed, tmp_path):
    repo, script, work = installed
    commit = git(repo, "rev-parse", "HEAD")
    meta = repo / "plugins" / "pave" / ".claude-plugin" / "plugin.json"
    meta.write_text(meta.read_text().replace(f'"version": "{VERSION}"', '"version": "9.9.9"'))
    git(repo, "commit", "--quiet", "-am", "next release")
    runner = with_values(script, tmp_path / "run.sh",
                         PAVE_LOCAL=str(tmp_path / "gone"), PAVE_REPOSITORY=str(repo), PAVE_COMMIT=commit)
    result = locate(runner, tmpdir=work)
    assert result.returncode == 0, result.stderr
    assert reported(result)["version"] == VERSION


def test_locate_rejects_a_clone_of_another_version(installed, tmp_path):
    repo, script, work = installed
    runner = with_values(script, tmp_path / "run.sh",
                         PAVE_LOCAL=str(tmp_path / "gone"), PAVE_REPOSITORY=str(repo),
                         PAVE_COMMIT="", PAVE_VERSION="9.9.9")
    result = locate(runner, tmpdir=work)
    assert result.returncode == 1
    assert "holds version " + VERSION in result.stderr
    assert "/pave-installer:install kiro" in result.stderr
    assert list(work.iterdir()) == []


def test_locate_rejects_a_local_source_of_another_version(installed, tmp_path):
    repo, script, work = installed
    runner = with_values(script, tmp_path / "run.sh", PAVE_REPOSITORY=str(tmp_path / "nowhere"), PAVE_VERSION="9.9.9")
    result = locate(runner, tmpdir=work)
    assert result.returncode == 1
    assert "could not fetch" in result.stderr
    assert list(work.iterdir()) == []


def test_locate_without_git_says_what_to_do(installed, tmp_path):
    _, script, work = installed
    runner = with_values(script, tmp_path / "run.sh", PAVE_LOCAL=str(tmp_path / "gone"))
    result = locate(runner, env={"PATH": str(tmp_path / "empty")}, tmpdir=work)
    assert result.returncode == 1
    assert "git is not installed" in result.stderr
    assert "Run /pave-installer:install kiro in Claude Code again" in result.stderr


def test_cleanup_refuses_folders_it_did_not_clone(installed, tmp_path):
    repo, script, _ = installed
    for target in (repo / "plugins" / "pave", tmp_path):
        result = subprocess.run(["/bin/bash", str(script), "cleanup", str(target)], capture_output=True, text=True)
        assert result.returncode == 1
        assert "refusing to delete" in result.stderr
    assert (repo / "plugins" / "pave" / ".claude-plugin" / "plugin.json").exists()


def test_pave_setup_names_every_pave_skill_and_agent():
    # pave-setup explains Pave's parts; a new skill or agent must not go unmentioned.
    text = (INSTALLER / "templates" / "pave-setup" / "SKILL.md").read_text()
    for skill in (PAVE / "skills").iterdir():
        if (skill / "SKILL.md").exists():
            assert f"`{skill.name}`" in text, skill.name
    for agent in (PAVE / "agents").glob("*.md"):
        assert f"`{agent.stem}`" in text, agent.stem
