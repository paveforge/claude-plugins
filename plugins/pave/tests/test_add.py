from conftest import make_repo


def test_add_registers_a_folder_with_or_without_git(hub, tmp_path, vcs):
    svc = make_repo(tmp_path / "svc", vcs)
    r = hub.run("add", str(svc))
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("added  svc")
    assert f"path: {svc}" in (hub.path / "workspace.yaml").read_text()
    # Without git it is information only, never a WARN or a refusal.
    assert ("not a git repository" in r.stdout) == (vcs == "plain")
    assert "WARN" not in r.stdout
