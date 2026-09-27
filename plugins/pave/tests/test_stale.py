import hashlib

from conftest import commit_all, git_init, make_feature


def write_workspace(hub, services):
    lines = ["services:\n"]
    for s in services:
        lines.append(f"\n  - name: {s['name']}\n    path: {s['path']}\n")
        if s.get("discovered"):
            lines.append("    language: go\n")
    (hub.path / "workspace.yaml").write_text("".join(lines))


def knowledge_readme(hub, service, commit, source_paths):
    kdir = hub.path / "artifacts" / "knowledge" / "services" / service
    kdir.mkdir(parents=True, exist_ok=True)
    paths = ", ".join(source_paths)
    (kdir / "README.md").write_text(
        f"---\ncommit: {commit}\nsource_paths: [{paths}]\n---\n\n# {service}\n"
    )


def test_stale_current_when_no_changes(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    (svc / "src").mkdir()
    (svc / "src" / "a.py").write_text("x = 1\n")
    commit = commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    knowledge_readme(hub, "svc", commit, ["src"])

    r = hub.run("stale")
    assert r.returncode == 0
    assert "current" in r.stdout
    assert "stale " not in r.stdout.replace("stale-", "")


def test_stale_when_source_paths_changed(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    (svc / "src").mkdir()
    (svc / "src" / "a.py").write_text("x = 1\n")
    commit = commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    knowledge_readme(hub, "svc", commit, ["src"])

    (svc / "src" / "a.py").write_text("x = 2\n")
    commit_all(svc, "change")

    r = hub.run("stale")
    assert r.returncode == 0
    lines = [l for l in r.stdout.splitlines() if l.startswith("stale")]
    assert any("svc" in l for l in lines)


def test_stale_unaffected_by_changes_outside_source_paths(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    (svc / "src").mkdir()
    (svc / "src" / "a.py").write_text("x = 1\n")
    (svc / "ci").mkdir()
    (svc / "ci" / "config.yml").write_text("a: 1\n")
    commit = commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    knowledge_readme(hub, "svc", commit, ["src"])

    (svc / "ci" / "config.yml").write_text("a: 2\n")
    commit_all(svc, "ci change")

    r = hub.run("stale")
    assert r.returncode == 0
    lines = [l for l in r.stdout.splitlines() if l.startswith("current")]
    assert any("svc" in l for l in lines)


def test_stale_unreachable_service(hub, tmp_path):
    write_workspace(hub, [{"name": "svc", "path": str(tmp_path / "missing"), "discovered": True}])
    r = hub.run("stale")
    assert r.returncode == 0
    assert "unreachable" in r.stdout


def test_stale_undiscovered_service(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": False}])
    r = hub.run("stale")
    assert r.returncode == 0
    assert "undiscovered" in r.stdout


def test_stale_missing_knowledge(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    r = hub.run("stale")
    assert r.returncode == 0
    assert "missing" in r.stdout


def test_stale_unreachable_commit_is_missing(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    (svc / "src").mkdir()
    (svc / "src" / "a.py").write_text("x\n")
    commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    knowledge_readme(hub, "svc", "0" * 40, ["src"])

    r = hub.run("stale")
    assert r.returncode == 0
    lines = [l for l in r.stdout.splitlines() if l.startswith("missing")]
    assert any("svc" in l for l in lines)
    assert any("history rewritten" in l or "cannot diff" in l for l in lines)


def test_stale_orphan_knowledge(hub, tmp_path):
    write_workspace(hub, [])
    kdir = hub.path / "artifacts" / "knowledge" / "services" / "ghost"
    kdir.mkdir(parents=True)
    (kdir / "README.md").write_text("---\ncommit: abc\nsource_paths: [src]\n---\n# ghost\n")
    r = hub.run("stale")
    assert r.returncode == 0
    assert "orphan" in r.stdout
    assert "ghost" in r.stdout


def test_stale_filter_by_service(hub, tmp_path):
    svc1 = git_init(tmp_path / "svc1")
    commit1 = commit_all(svc1, "init")
    svc2 = git_init(tmp_path / "svc2")
    commit2 = commit_all(svc2, "init")
    write_workspace(hub, [
        {"name": "svc1", "path": str(svc1), "discovered": True},
        {"name": "svc2", "path": str(svc2), "discovered": True},
    ])
    knowledge_readme(hub, "svc1", commit1, ["."])
    knowledge_readme(hub, "svc2", commit2, ["."])

    r = hub.run("stale", "svc1")
    assert r.returncode == 0
    assert "svc1" in r.stdout
    assert "svc2" not in r.stdout


def test_stale_unknown_service_filter(hub):
    write_workspace(hub, [])
    r = hub.run("stale", "nope")
    assert r.returncode == 0
    assert "no service named nope" in r.stdout


def source_finding(hub, name, service, commit, paths):
    fdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "source"
    fdir.mkdir(parents=True, exist_ok=True)
    paths_str = ", ".join(paths)
    (fdir / name).write_text(
        f"---\nfound_by: on-demand\nreads:\n  - {{ service: {service}, commit: {commit}, "
        f"paths: [{paths_str}] }}\n---\n\n# finding\n"
    )


def test_source_finding_current_and_stale(hub, tmp_path):
    svc = git_init(tmp_path / "svc")
    (svc / "src").mkdir()
    (svc / "src" / "a.py").write_text("1\n")
    commit = commit_all(svc, "init")
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    source_finding(hub, "q1.md", "svc", commit, ["src"])

    r = hub.run("stale")
    assert r.returncode == 0
    assert "finding-current" in r.stdout

    (svc / "src" / "a.py").write_text("2\n")
    commit_all(svc, "change")
    r = hub.run("stale")
    assert "finding-stale" in r.stdout


def test_feature_record_stale_and_current(hub):
    fdir = make_feature(hub.path, "feat-1")
    spec_text = (fdir / "spec.md").read_text()
    spec_hash = hashlib.sha256(spec_text.encode()).hexdigest()

    rdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "features"
    rdir.mkdir(parents=True)
    (rdir / "feat-1.md").write_text(
        f"---\nkind: feature-record\nfeature: feat-1\nspec_hash: {spec_hash}\n---\n\n# feat-1\n"
    )
    write_workspace(hub, [])
    r = hub.run("stale")
    assert "record-current" in r.stdout

    (fdir / "spec.md").write_text(spec_text.replace("Does a thing.", "Does something else."))
    r = hub.run("stale")
    assert "record-stale" in r.stdout


def test_feature_record_stale_when_hash_missing(hub):
    make_feature(hub.path, "feat-1")
    rdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "features"
    rdir.mkdir(parents=True)
    (rdir / "feat-1.md").write_text("---\nkind: feature-record\nfeature: feat-1\n---\n\n# feat-1\n")
    write_workspace(hub, [])
    r = hub.run("stale")
    assert "record-stale" in r.stdout
    assert "no feature or spec_hash" in r.stdout
