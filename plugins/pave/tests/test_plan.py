from conftest import commit_all, make_feature


def seal(hub, feature_id):
    return hub.run("seal", env={"SESSION_FEATURE_ID": feature_id})


def check(hub, feature_id):
    return hub.run("check", env={"SESSION_FEATURE_ID": feature_id})


def prune(hub, feature_id):
    return hub.run("prune-obsoleted-tasks", env={"SESSION_FEATURE_ID": feature_id})


def test_check_no_plan(hub):
    fdir = hub.feature_dir("feat-1")
    fdir.mkdir(parents=True)
    (fdir / "spec.md").write_text("---\nfeature: feat-1\nversion: 1\n---\n# X\n")
    r = check(hub, "feat-1")
    assert r.returncode == 2
    assert "no-plan" in r.stdout


def test_check_unsealed(hub):
    make_feature(hub.path, "feat-1")
    r = check(hub, "feat-1")
    assert r.returncode == 2
    assert "unsealed" in r.stdout


def test_seal_then_check_ok(hub):
    make_feature(hub.path, "feat-1")
    r = seal(hub, "feat-1")
    assert r.returncode == 0, r.stderr
    r = check(hub, "feat-1")
    assert r.returncode == 0
    assert "ok:" in r.stdout


def test_check_passes_after_builder_only_changes(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    text = task.read_text()
    text = text.replace("status: pending", "status: done")
    text = text.replace("commit:\n", "commit: abc1234\n")
    text = text.replace("- [ ] Do the thing.", "- [x] Do the thing.")
    text = text.replace("## Build notes\n", "## Build notes\n\nDid the thing.\n")
    task.write_text(text)
    r = check(hub, "feat-1")
    assert r.returncode == 0, r.stdout + r.stderr


def test_check_fails_on_edited_spec(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    spec = fdir / "spec.md"
    spec.write_text(spec.read_text().replace("Does a thing.", "Does another thing."))
    r = check(hub, "feat-1")
    assert r.returncode == 1
    assert "spec.md changed" in r.stdout


def test_check_fails_on_edited_task(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("Do the thing.", "Do a different thing."))
    r = check(hub, "feat-1")
    assert r.returncode == 1
    assert "01-task.md was edited" in r.stdout


def test_check_fails_on_added_task(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    (fdir / "tasks" / "02-extra.md").write_text(
        "---\nservice: svc\nfeature: feat-1\nkind: build\nstatus: pending\n---\n# Extra\n## Build notes\n"
    )
    r = check(hub, "feat-1")
    assert r.returncode == 1
    assert "02-extra.md was added" in r.stdout


def test_check_fails_on_deleted_task(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    (fdir / "tasks" / "01-task.md").unlink()
    r = check(hub, "feat-1")
    assert r.returncode == 1
    assert "task 01 was deleted" in r.stdout


def test_crlf_spec_hashes_agree_between_seal_and_stale(hub):
    from conftest import sha256_text
    fdir = make_feature(hub.path, "feat-1")
    spec = fdir / "spec.md"
    lf_text = spec.read_text()
    crlf_text = lf_text.replace("\n", "\r\n")
    spec.write_bytes(crlf_text.encode())

    seal(hub, "feat-1")
    r = check(hub, "feat-1")
    assert r.returncode == 0, r.stdout

    plan_text = (fdir / "plan.md").read_text()
    recorded = [l.split(":", 1)[1].strip() for l in plan_text.splitlines() if l.startswith("spec_hash:")][0]
    # pathlib.Path.read_text() applies universal-newline translation, so both
    # pave-plan.py (seal) and pave-stale.py (record staleness) hash the
    # CRLF file as if it were LF - they agree with each other.
    assert recorded == sha256_text(lf_text)


def test_prune_refuses_when_revert_not_done(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=1)
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("status: pending", "status: obsolete"))
    (fdir / "tasks" / "02-revert.md").write_text(
        "---\nservice: svc\nfeature: feat-1\nkind: revert\npriority: high\nstatus: pending\n"
        "depends_on: []\nreverts: [1]\nsatisfies: []\nbranch: feature/feat-1\nderives_from:\n"
        "  - plan.md#approach\ncommit:\n---\n# Revert task 1\n## Build notes\n"
    )
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 1
    assert "refused" in r.stdout
    assert (fdir / "tasks" / "01-task.md").exists()
    assert (fdir / "tasks" / "02-revert.md").exists()


def test_prune_removes_obsolete_and_revert_and_keeps_check_ok(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=1)
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("status: pending", "status: obsolete"))
    (fdir / "tasks" / "02-revert.md").write_text(
        "---\nservice: svc\nfeature: feat-1\nkind: revert\npriority: high\nstatus: done\n"
        "depends_on: []\nreverts: [1]\nsatisfies: []\nbranch: feature/feat-1\nderives_from:\n"
        "  - plan.md#approach\ncommit: deadbee\n---\n# Revert task 1\n## Build notes\n"
    )
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pruned" in r.stdout
    assert not (fdir / "tasks" / "01-task.md").exists()
    assert not (fdir / "tasks" / "02-revert.md").exists()

    plan_text = (fdir / "plan.md").read_text()
    assert "spec_hash:" in plan_text
    assert "next_task: 3" in plan_text

    r = check(hub, "feat-1")
    assert r.returncode == 0, r.stdout


def test_prune_never_lowers_next_task(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    task1 = fdir / "tasks" / "01-task.md"
    task1.write_text(task1.read_text().replace("status: pending", "status: obsolete"))
    (fdir / "tasks" / "03-revert.md").write_text(
        "---\nservice: svc\nfeature: feat-1\nkind: revert\npriority: high\nstatus: done\n"
        "depends_on: []\nreverts: [1]\nsatisfies: []\nbranch: feature/feat-1\nderives_from:\n"
        "  - plan.md#approach\ncommit: deadbee\n---\n# Revert task 1\n## Build notes\n"
    )
    seal(hub, "feat-1")
    plan_before = (fdir / "plan.md").read_text()
    assert "next_task: 4" in plan_before
    r = prune(hub, "feat-1")
    assert r.returncode == 0, r.stdout + r.stderr
    plan_after = (fdir / "plan.md").read_text()
    assert "next_task: 4" in plan_after


def test_prune_refuses_revert_naming_non_obsolete_task(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    task1 = fdir / "tasks" / "01-task.md"
    task1.write_text(task1.read_text().replace("status: pending", "status: obsolete"))
    (fdir / "tasks" / "03-revert.md").write_text(
        "---\nservice: svc\nfeature: feat-1\nkind: revert\npriority: high\nstatus: done\n"
        "depends_on: []\nreverts: [1, 2]\nsatisfies: []\nbranch: feature/feat-1\nderives_from:\n"
        "  - plan.md#approach\ncommit: deadbee\n---\n# Revert tasks 1 and 2\n## Build notes\n"
    )
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode != 0
    assert "not obsolete" in (r.stdout + r.stderr)
    assert (fdir / "tasks" / "02-task.md").exists()


def test_prune_nothing_to_prune(hub):
    make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 0
    assert "nothing to prune" in r.stdout
