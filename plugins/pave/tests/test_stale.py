import hashlib
import os
import re

from conftest import make_feature, make_repo, snapshot


def write_workspace(hub, services):
    lines = ["services:\n"]
    for s in services:
        lines.append(f"\n  - name: {s['name']}\n    path: {s['path']}\n")
        if s.get("discovered"):
            lines.append("    language: go\n")
    (hub.path / "workspace.yaml").write_text("".join(lines))


def knowledge_readme(hub, service, source_paths, extra=""):
    """A service README as the analyst writes it: source_paths, no hash yet."""
    kdir = hub.path / "artifacts" / "knowledge" / "services" / service
    kdir.mkdir(parents=True, exist_ok=True)
    readme = kdir / "README.md"
    paths = ", ".join(source_paths)
    readme.write_text(
        f"---\nservice: {service}\nsource_paths: [{paths}]\n{extra}capabilities: [x]\n---\n\n# {service}\n"
    )
    return readme


def service(tmp_path, vcs, name="svc", files=None):
    svc = make_repo(tmp_path / name, vcs)
    for rel, text in (files or {"src/a.py": "x = 1\n"}).items():
        (svc / rel).parent.mkdir(parents=True, exist_ok=True)
        (svc / rel).write_text(text)
    snapshot(svc, vcs, "init")
    return svc


def analysed(hub, tmp_path, vcs, source_paths=("src",), files=None):
    """A registered, discovered, analysed and stamped service."""
    svc = service(tmp_path, vcs, files=files)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    readme = knowledge_readme(hub, "svc", list(source_paths))
    r = hub.run("stamp", str(readme))
    assert r.returncode == 0, r.stderr
    return svc, readme


def state_of(r, name):
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == name:
            return parts[0]
    return None


def test_stamp_records_source_hash(hub, tmp_path, vcs):
    _, readme = analysed(hub, tmp_path, vcs)
    text = readme.read_text()
    assert re.search(r"^source_hash: [0-9a-f]{64}$", text, re.M)
    # Right after source_paths, and the rest of the file untouched.
    assert "source_paths: [src]\nsource_hash: " in text
    assert text.endswith("capabilities: [x]\n---\n\n# svc\n")


def test_stamp_again_replaces_the_hash(hub, tmp_path, vcs):
    svc, readme = analysed(hub, tmp_path, vcs)
    first = readme.read_text()
    (svc / "src" / "a.py").write_text("x = 2\n")
    assert hub.run("stamp", str(readme)).returncode == 0
    second = readme.read_text()
    assert second.count("source_hash:") == 1
    assert second != first


def test_stamp_block_source_paths(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    kdir = hub.path / "artifacts" / "knowledge" / "services" / "svc"
    kdir.mkdir(parents=True)
    readme = kdir / "README.md"
    readme.write_text("---\nservice: svc\nsource_paths:\n  - src\nterms: []\n---\n# svc\n")
    assert hub.run("stamp", str(readme)).returncode == 0
    assert "  - src\nsource_hash: " in readme.read_text()
    assert state_of(hub.run("stale"), "svc") == "current"


def test_stamp_refuses_unregistered_service(hub, tmp_path, vcs):
    write_workspace(hub, [])
    readme = knowledge_readme(hub, "ghost", ["src"])
    before = readme.read_text()
    r = hub.run("stamp", str(readme))
    assert r.returncode != 0
    assert "nothing stamped" in r.stderr
    assert readme.read_text() == before


def test_stale_current_when_no_changes(hub, tmp_path, vcs):
    analysed(hub, tmp_path, vcs)
    r = hub.run("stale")
    assert r.returncode == 0
    assert state_of(r, "svc") == "current"


def test_stale_when_source_file_edited(hub, tmp_path, vcs):
    svc, _ = analysed(hub, tmp_path, vcs)
    (svc / "src" / "a.py").write_text("x = 2\n")
    snapshot(svc, vcs, "change")
    r = hub.run("stale")
    assert state_of(r, "svc") == "stale"
    assert "files changed under src" in r.stdout


def test_stale_without_committing(hub, tmp_path, vcs):
    # Content decides, not history: an uncommitted edit is a change too.
    svc, _ = analysed(hub, tmp_path, vcs)
    (svc / "src" / "a.py").write_text("x = 2\n")
    assert state_of(hub.run("stale"), "svc") == "stale"


def test_stale_when_file_added_removed_or_renamed(hub, tmp_path, vcs):
    svc, readme = analysed(hub, tmp_path, vcs)
    (svc / "src" / "b.py").write_text("")
    assert state_of(hub.run("stale"), "svc") == "stale"

    hub.run("stamp", str(readme))
    (svc / "src" / "b.py").unlink()
    assert state_of(hub.run("stale"), "svc") == "stale"

    hub.run("stamp", str(readme))
    (svc / "src" / "a.py").rename(svc / "src" / "c.py")
    assert state_of(hub.run("stale"), "svc") == "stale"


def test_stale_when_source_path_deleted(hub, tmp_path, vcs):
    svc, _ = analysed(hub, tmp_path, vcs)
    (svc / "src" / "a.py").unlink()
    (svc / "src").rmdir()
    assert state_of(hub.run("stale"), "svc") == "stale"


def test_stale_unaffected_by_changes_outside_source_paths(hub, tmp_path, vcs):
    svc, _ = analysed(hub, tmp_path, vcs, files={"src/a.py": "x = 1\n", "ci/config.yml": "a: 1\n"})
    (svc / "ci" / "config.yml").write_text("a: 2\n")
    snapshot(svc, vcs, "ci change")
    assert state_of(hub.run("stale"), "svc") == "current"


def test_stale_ignores_vcs_metadata_and_caches(hub, tmp_path, vcs):
    svc, _ = analysed(hub, tmp_path, vcs, source_paths=["."])
    (svc / "src" / "__pycache__").mkdir()
    (svc / "src" / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\0")
    (svc / "node_modules" / "dep").mkdir(parents=True)
    (svc / "node_modules" / "dep" / "index.js").write_text("")
    snapshot(svc, vcs, "no-op")  # under git, .git/ changes; the hash must not
    assert state_of(hub.run("stale"), "svc") == "current"


def test_stale_unreachable_service(hub, tmp_path, vcs):
    write_workspace(hub, [{"name": "svc", "path": str(tmp_path / "missing"), "discovered": True}])
    r = hub.run("stale")
    assert r.returncode == 0
    assert state_of(r, "svc") == "unreachable"


def test_stale_undiscovered_service(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": False}])
    assert state_of(hub.run("stale"), "svc") == "undiscovered"


def test_stale_missing_knowledge(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    assert state_of(hub.run("stale"), "svc") == "missing"


def test_stale_unstamped_readme_is_missing(hub, tmp_path, vcs):
    # An analyst that wrote its README but was never stamped - it failed, or
    # the README predates content hashes and records a commit - is not current.
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    knowledge_readme(hub, "svc", ["src"], extra="commit: 0818f6e\n")
    r = hub.run("stale")
    assert state_of(r, "svc") == "missing"
    assert "source_hash" in r.stdout


def test_stale_orphan_knowledge(hub, tmp_path, vcs):
    write_workspace(hub, [])
    knowledge_readme(hub, "ghost", ["src"])
    r = hub.run("stale")
    assert r.returncode == 0
    assert state_of(r, "ghost") == "orphan"


def test_stale_filter_by_service(hub, tmp_path, vcs):
    svc1 = service(tmp_path, vcs, "svc1")
    svc2 = service(tmp_path, vcs, "svc2")
    write_workspace(hub, [
        {"name": "svc1", "path": str(svc1), "discovered": True},
        {"name": "svc2", "path": str(svc2), "discovered": True},
    ])
    hub.run("stamp", str(knowledge_readme(hub, "svc1", ["."])))
    hub.run("stamp", str(knowledge_readme(hub, "svc2", ["."])))

    r = hub.run("stale", "svc1")
    assert r.returncode == 0
    assert state_of(r, "svc1") == "current"
    assert "svc2" not in r.stdout


def test_stale_unknown_service_filter(hub, vcs):
    write_workspace(hub, [])
    r = hub.run("stale", "nope")
    assert r.returncode == 0
    assert "no service named nope" in r.stdout


def source_finding(hub, name, service, paths, hash_=None):
    fdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "source"
    fdir.mkdir(parents=True, exist_ok=True)
    paths_str = ", ".join(paths)
    tail = f", hash: {hash_}" if hash_ else ""
    f = fdir / name
    f.write_text(
        f"---\nkind: source-finding\nquestion: how?\nservices:\n"
        f"  - {{ service: {service}, paths: [{paths_str}]{tail} }}\n---\n\n# finding\n"
    )
    return f


def test_source_finding_stamped_current_then_stale(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    f = source_finding(hub, "q1.md", "svc", ["src"])

    r = hub.run("stamp", str(f))
    assert r.returncode == 0, r.stderr
    assert re.search(r"^  - \{ service: svc, paths: \[src\], hash: [0-9a-f]{64} \}$", f.read_text(), re.M)
    assert "finding-current" in hub.run("stale").stdout

    (svc / "src" / "a.py").write_text("2\n")
    snapshot(svc, vcs, "change")
    assert "finding-stale" in hub.run("stale").stdout


def test_source_finding_several_services(hub, tmp_path, vcs):
    a = service(tmp_path, vcs, "a")
    b = service(tmp_path, vcs, "b")
    write_workspace(hub, [{"name": "a", "path": str(a)}, {"name": "b", "path": str(b)}])
    fdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "source"
    fdir.mkdir(parents=True)
    f = fdir / "q.md"
    f.write_text("---\nservices:\n  - { service: a, paths: [src] }\n  - { service: b, paths: [src] }\n---\n# q\n")
    assert hub.run("stamp", str(f)).returncode == 0
    assert f.read_text().count("hash: ") == 2
    assert "finding-current" in hub.run("stale").stdout

    (b / "src" / "a.py").write_text("changed\n")
    r = hub.run("stale")
    assert "finding-stale" in r.stdout
    assert "b: files changed under src" in r.stdout


def test_source_finding_without_hash_is_stale(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    source_finding(hub, "q1.md", "svc", ["src"])
    r = hub.run("stale")
    assert "finding-stale" in r.stdout
    assert "no content hash" in r.stdout


def test_source_finding_with_a_commit_is_stale(hub, tmp_path, vcs):
    # The format before content hashes. It no longer proves anything.
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    fdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "source"
    fdir.mkdir(parents=True)
    (fdir / "old.md").write_text(
        "---\nservices:\n  - { service: svc, commit: 0818f6e, paths: [src] }\n---\n# old\n")
    assert "finding-stale" in hub.run("stale").stdout


def test_feature_record_stale_and_current(hub, vcs):
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


def test_feature_record_stale_when_hash_missing(hub, vcs):
    make_feature(hub.path, "feat-1")
    rdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "features"
    rdir.mkdir(parents=True)
    (rdir / "feat-1.md").write_text("---\nkind: feature-record\nfeature: feat-1\n---\n\n# feat-1\n")
    write_workspace(hub, [])
    r = hub.run("stale")
    assert "record-stale" in r.stdout
    assert "no feature or spec_hash" in r.stdout


def test_stale_never_runs_git(hub, tmp_path, vcs):
    # With no git on PATH at all, staleness works the same.
    svc, _ = analysed(hub, tmp_path, vcs)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "git"
    fake.write_text("#!/bin/sh\necho 'git must not be called' >&2\nexit 99\n")
    fake.chmod(0o755)
    env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    r = hub.run("stale", env=env)
    assert state_of(r, "svc") == "current"
    assert "git must not be called" not in r.stderr
    (svc / "src" / "a.py").write_text("x = 3\n")
    r = hub.run("stale", env=env)
    assert state_of(r, "svc") == "stale"
    assert "git must not be called" not in r.stderr


def test_stamp_takes_a_relative_path_from_the_hub(hub, tmp_path, vcs):
    # The skills pass hub-relative paths; the shell may be anywhere below it.
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    knowledge_readme(hub, "svc", ["src"])
    rel = "artifacts/knowledge/services/svc/README.md"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    for cwd in (hub.path / "features", elsewhere):
        r = hub.run("stamp", rel, cwd=cwd)
        assert r.returncode == 0, r.stderr
    assert state_of(hub.run("stale"), "svc") == "current"


def test_contract_path_is_not_the_service_path(hub, tmp_path, vcs):
    """A discovered service lists contracts, each with a `path:` of its own,
    relative to the repo. Only the service's own path decides where it is."""
    svc, _ = analysed(hub, tmp_path, vcs)
    (hub.path / "workspace.yaml").write_text(
        "services:\n\n"
        "  - name: svc\n"
        f"    path: {svc}\n"
        "    # --- below here: filled by /pave:analyse ---\n"
        "    language: go   # discovered\n"
        "    commands:\n"
        "      build: make build\n"
        "    contracts:\n"
        "      - kind: protobuf\n"
        "        path: proto/order/v1/order.proto\n"
        "        role: producer\n"
        "      - name: events\n"
        "        path: schemas/\n"
        "    consumes: []\n"
    )
    r = hub.run("stale")
    assert r.returncode == 0, r.stderr
    assert state_of(r, "svc") == "current", r.stdout
    assert state_of(r, "events") is None, r.stdout


# Any valid YAML layout a model writes reads the same (issue #14).

def finding(hub, name, frontmatter):
    fdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "source"
    fdir.mkdir(parents=True, exist_ok=True)
    f = fdir / name
    f.write_text(f"---\nkind: source-finding\nquestion: how?\n{frontmatter}---\n\n# finding\n")
    return f


def test_block_form_finding_is_stamped_and_rewritten_in_one_form(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    f = finding(hub, "q.md", "# the dirs read\nservices:\n- paths:\n    - src\n  service: svc\nterms: [x]\n")
    r = hub.run("stamp", str(f))
    assert r.returncode == 0, r.stderr
    text = f.read_text()
    assert re.search(r"^  - \{ service: svc, paths: \[src\], hash: [0-9a-f]{64} \}\nterms: \[x\]$", text, re.M)
    assert "# the dirs read\nservices:" in text
    assert state_of(hub.run("stale"), "on-demand/source/q.md") == "finding-current"


def test_every_entry_of_a_mixed_layout_finding_is_stamped(hub, tmp_path, vcs):
    # Before: only the entry in the one-line form was hashed, and the finding
    # read current while resting on code never hashed.
    a = service(tmp_path, vcs, "a")
    b = service(tmp_path, vcs, "b")
    write_workspace(hub, [{"name": "a", "path": str(a)}, {"name": "b", "path": str(b)}])
    f = finding(hub, "q.md", "services:\n  - { service: a, paths: [src] }\n  - service: b\n    paths: [src]\n")
    assert hub.run("stamp", str(f)).returncode == 0
    assert f.read_text().count("hash: ") == 2
    (b / "src" / "a.py").write_text("changed\n")
    r = hub.run("stale")
    assert state_of(r, "on-demand/source/q.md") == "finding-stale"
    assert "b: files changed under src" in r.stdout


def test_finding_entry_without_paths_is_refused(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs)
    write_workspace(hub, [{"name": "svc", "path": str(svc)}])
    f = finding(hub, "q.md", "services:\n  - { service: svc }\n")
    before = f.read_text()
    r = hub.run("stamp", str(f))
    assert r.returncode != 0
    assert "entry 1 has no paths" in r.stderr
    assert f.read_text() == before


def test_unparseable_finding_is_an_error_not_stale(hub, tmp_path, vcs):
    write_workspace(hub, [])
    finding(hub, "bad.md", "services:\n  - { service: svc, paths: [src }\n")
    r = hub.run("stale")
    assert r.returncode != 0
    assert "bad.md" in r.stderr and "does not parse" in r.stderr


def test_multi_line_flow_source_paths(hub, tmp_path, vcs):
    svc = service(tmp_path, vcs, files={"src/a.py": "1\n", "lib/b.py": "2\n"})
    write_workspace(hub, [{"name": "svc", "path": str(svc), "discovered": True}])
    kdir = hub.path / "artifacts" / "knowledge" / "services" / "svc"
    kdir.mkdir(parents=True)
    readme = kdir / "README.md"
    readme.write_text("---\nservice: svc\nsource_paths: [\n  src,\n  lib,\n]\ncapabilities: [x]\n---\n# svc\n")
    r = hub.run("stamp", str(readme))
    assert r.returncode == 0, r.stderr
    assert re.search(r"^  lib,\n\]\nsource_hash: [0-9a-f]{64}\ncapabilities", readme.read_text(), re.M)
    assert state_of(hub.run("stale"), "svc") == "current"
    (svc / "lib" / "b.py").write_text("3\n")
    assert state_of(hub.run("stale"), "svc") == "stale"


def test_workspace_in_any_layout(hub, tmp_path, vcs):
    svc, _ = analysed(hub, tmp_path, vcs)
    (hub.path / "workspace.yaml").write_text(
        f"services: [{{ language: go, path: '{svc}', name: svc }}]\n")
    assert state_of(hub.run("stale"), "svc") == "current"
    (hub.path / "workspace.yaml").write_text(f"services:\n- language: go\n  path: {svc}\n  name: svc\n")
    assert state_of(hub.run("stale"), "svc") == "current"


def test_unparseable_workspace_is_an_error(hub, tmp_path, vcs):
    (hub.path / "workspace.yaml").write_text("services:\n  - name: svc\n    path: [x\n")
    r = hub.run("stale")
    assert r.returncode != 0
    assert "workspace.yaml" in r.stderr


def test_workspace_service_without_a_name_is_an_error(hub, tmp_path, vcs):
    (hub.path / "workspace.yaml").write_text("services:\n  - path: /x\n")
    r = hub.run("stale")
    assert r.returncode != 0
    assert "entry 1 has no name" in r.stderr


def test_feature_record_in_flow_form(hub, vcs):
    fdir = make_feature(hub.path, "feat-1")
    spec_hash = hashlib.sha256((fdir / "spec.md").read_text().encode()).hexdigest()
    rdir = hub.path / "artifacts" / "knowledge" / "on-demand" / "features"
    rdir.mkdir(parents=True)
    (rdir / "feat-1.md").write_text(
        f"---\n{{ kind: feature-record, spec_hash: '{spec_hash}', feature: \"feat-1\" }}\n---\n# feat-1\n")
    write_workspace(hub, [])
    assert "record-current" in hub.run("stale").stdout
