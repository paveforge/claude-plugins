import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PAVE = Path(__file__).resolve().parents[1]
HOST = PAVE / "scripts" / "pave-host.py"


def run_host(home, *args, source=PAVE, cwd=None):
    env = {
        **os.environ,
        "HOME": str(home),
        "CODEX_HOME": str(home / ".codex"),
    }
    return subprocess.run(
        [sys.executable, str(HOST), *args, "--source-root", str(source)],
        capture_output=True,
        text=True,
        cwd=str(cwd or home),
        env=env,
    )


def installed_skill(home, name="spec"):
    return home / ".agents" / "skills" / f"pave-{name}" / "SKILL.md"


def manifest(home):
    return home / ".codex" / "pave" / "install.json"


def copy_source(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(PAVE, source)
    return source


def test_codex_install_generates_skills_agents_and_runtime(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    result = run_host(home, "install", "codex")
    assert result.returncode == 0, result.stderr

    skill = installed_skill(home)
    text = skill.read_text()
    assert "name: pave-spec" in text
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    assert "$pave-plan" in text
    assert "{arguments}" in text

    agent = home / ".codex" / "agents" / "pave_builder.toml"
    agent_text = agent.read_text()
    assert 'name = "pave_builder"' in agent_text
    assert "task document" in agent_text
    runtime = home / ".codex" / "pave" / "runtime"
    assert (runtime / "scripts" / "pave.sh").stat().st_mode & 0o111
    assert (runtime / "templates" / "config.yaml").exists()
    assert (runtime / "templates" / "config.codex.yaml").exists()
    assert (runtime / "agents" / "builder.md").exists()
    help_text = installed_skill(home, "help").read_text()
    assert str(home / ".agents" / "skills" / "pave-*" / "SKILL.md") in help_text
    assert "runtime/skills" not in help_text
    init_text = installed_skill(home, "init").read_text()
    assert "`.claude/settings.json`" not in init_text
    assert "config.codex.yaml" in init_text
    assert "templates/config.codex.yaml" in init_text
    assert "config-check codex" in init_text
    assert "config.yaml" not in init_text.replace("config.codex.yaml", "")

    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / ".pave-hub").write_text("")
    shutil.copy(runtime / "templates" / "config.codex.yaml", hub / "config.codex.yaml")
    lookup = subprocess.run(
        [str(runtime / "scripts" / "pave.sh"), "agent", "builder", "codex"],
        capture_output=True,
        text=True,
        cwd=hub,
    )
    assert lookup.returncode == 0, lookup.stderr
    assert lookup.stdout == "model=gpt-6-sol\neffort=medium\n"

    data = json.loads(manifest(home).read_text())
    assert data["host"] == "codex"
    assert data["pave_version"] == "0.8.0"
    assert str(skill) in data["files"]


def test_codex_install_is_idempotent(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    first = run_host(home, "install", "codex")
    assert first.returncode == 0
    before = manifest(home).read_text()

    second = run_host(home, "install", "codex")
    assert second.returncode == 0, second.stderr
    assert "unchanged" in second.stdout
    assert manifest(home).read_text() == before


def test_codex_update_replaces_only_unchanged_managed_files(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    source = copy_source(tmp_path)
    assert run_host(home, "install", "codex", source=source).returncode == 0

    spec = installed_skill(home)
    build = installed_skill(home, "build")
    spec.write_text(spec.read_text() + "\nuser edit\n")
    source_spec = source / "skills" / "spec" / "SKILL.md"
    source_spec.write_text(source_spec.read_text() + "\nnew release\n")
    source_build = source / "skills" / "build" / "SKILL.md"
    source_build.write_text(source_build.read_text() + "\nnew release\n")

    result = run_host(home, "install", "codex", source=source)
    assert result.returncode == 2
    assert f"conflict  {spec}" in result.stdout
    assert f"update    {build}" in result.stdout
    assert spec.read_text().endswith("user edit\n")
    assert build.read_text().endswith("new release\n")


def test_codex_uninstall_preserves_modified_files_and_hub(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    hub = tmp_path / "hub"
    hub.mkdir()
    feature = hub / "features" / "F-1" / "spec.md"
    feature.parent.mkdir(parents=True)
    feature.write_text("owned by the user\n")
    assert run_host(home, "install", "codex").returncode == 0

    changed = installed_skill(home)
    changed.write_text(changed.read_text() + "\nuser edit\n")
    result = run_host(home, "uninstall", "codex")
    assert result.returncode == 2
    assert f"preserve  {changed}" in result.stdout
    assert changed.exists()
    assert feature.read_text() == "owned by the user\n"
    data = json.loads(manifest(home).read_text())
    assert list(data["files"]) == [str(changed)]

    changed.unlink()
    result = run_host(home, "uninstall", "codex")
    assert result.returncode == 0, result.stderr
    assert not manifest(home).exists()
    assert not (home / ".codex" / "pave").exists()
    assert (home / ".agents" / "skills").exists()
    assert (home / ".codex" / "agents").exists()


def test_codex_project_scope_stays_inside_project(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    result = run_host(
        home,
        "install",
        "codex",
        "--scope",
        "project",
        "--project-root",
        str(project),
    )
    assert result.returncode == 0, result.stderr
    assert (project / ".agents" / "skills" / "pave-plan" / "SKILL.md").exists()
    assert (project / ".codex" / "agents" / "pave_planner.toml").exists()
    assert not (home / ".agents").exists()


def test_uninstall_rejects_manifest_paths_outside_adapter(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    assert run_host(home, "install", "codex").returncode == 0
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("keep me\n")
    data = json.loads(manifest(home).read_text())
    data["files"][str(unrelated)] = {
        "sha256": hashlib.sha256(unrelated.read_bytes()).hexdigest(),
        "executable": False,
    }
    manifest(home).write_text(json.dumps(data))

    result = run_host(home, "uninstall", "codex")
    assert result.returncode == 1
    assert "outside the Codex adapter" in result.stderr
    assert unrelated.read_text() == "keep me\n"


def test_native_codex_plugin_is_left_to_its_manager(tmp_path):
    home = tmp_path / "home"
    native = home / ".codex" / "plugins" / "pave"
    native.mkdir(parents=True)

    install = run_host(home, "install", "codex")
    assert install.returncode == 1
    assert "update it through that manager" in install.stderr
    uninstall = run_host(home, "uninstall", "codex")
    assert uninstall.returncode == 1
    assert "uninstall it through that manager" in uninstall.stderr
    assert native.exists()
