import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import make_repo


GRANT = Path(__file__).resolve().parents[1] / "adapters" / "claude" / "grant.py"


def test_add_registers_a_folder_with_or_without_git(hub, tmp_path, vcs):
    svc = make_repo(tmp_path / "svc", vcs)
    r = hub.run("add", str(svc))
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("added  svc")
    assert f"path: {svc}" in (hub.path / "workspace.yaml").read_text()
    # Without git it is information only, never a WARN or a refusal.
    assert ("not a git repository" in r.stdout) == (vcs == "plain")
    assert "WARN" not in r.stdout
    assert not (hub.path / ".claude" / "settings.json").exists()


def test_claude_adapter_grants_only_registered_folders(hub, tmp_path):
    registered = tmp_path / "registered"
    unregistered = tmp_path / "unregistered"
    registered.mkdir()
    unregistered.mkdir()
    assert hub.run("add", str(registered)).returncode == 0

    result = subprocess.run(
        [sys.executable, str(GRANT), str(registered), str(unregistered)],
        capture_output=True,
        text=True,
        env={**os.environ, "PAVE_HUB": str(hub.path)},
    )
    assert result.returncode == 0, result.stderr
    settings = json.loads((hub.path / ".claude" / "settings.json").read_text())
    assert settings["additionalDirectories"] == [str(registered.resolve())]
    assert "not registered" in result.stdout
