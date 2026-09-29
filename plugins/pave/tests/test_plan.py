import re

from conftest import make_feature


def seal(hub, feature_id):
    return hub.run("seal", env={"SESSION_FEATURE_ID": feature_id})


def check(hub, feature_id):
    return hub.run("check", env={"SESSION_FEATURE_ID": feature_id})


def prune(hub, feature_id):
    return hub.run("prune-obsoleted-tasks", env={"SESSION_FEATURE_ID": feature_id})


def add_revert(fdir, n, reverts, status):
    """A task that reverts others: an ordinary task, linked only in plan.md's Reverts column."""
    (fdir / "tasks" / f"{n:02d}-revert.md").write_text(
        f"---\nservice: svc\nfeature: feat-1\npriority: high\nstatus: {status}\n"
        "depends_on: []\nsatisfies: []\nderives_from:\n"
        f"  - plan.md#approach\n---\n# Remove what task {reverts[0]} built\n## Build notes\n"
    )
    named = ", ".join(f"{r:02d}" for r in reverts)
    plan = fdir / "plan.md"
    plan.write_text(plan.read_text() + f"| {n:02d} | Remove it | svc | high | S | - | - | {named} | new |\n")


def obsolete(fdir, n):
    task = fdir / "tasks" / f"{n:02d}-task.md"
    task.write_text(task.read_text().replace("status: pending", "status: obsolete"))


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
        "---\nservice: svc\nfeature: feat-1\nstatus: pending\n---\n# Extra\n## Build notes\n"
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
    obsolete(fdir, 1)
    add_revert(fdir, 2, [1], "pending")
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 1
    assert "refused" in r.stdout
    assert (fdir / "tasks" / "01-task.md").exists()
    assert (fdir / "tasks" / "02-revert.md").exists()


def test_prune_removes_obsolete_and_revert_and_keeps_check_ok(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=1)
    obsolete(fdir, 1)
    add_revert(fdir, 2, [1], "done")
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
    obsolete(fdir, 1)
    add_revert(fdir, 3, [1], "done")
    seal(hub, "feat-1")
    plan_before = (fdir / "plan.md").read_text()
    assert "next_task: 4" in plan_before
    r = prune(hub, "feat-1")
    assert r.returncode == 0, r.stdout + r.stderr
    plan_after = (fdir / "plan.md").read_text()
    assert "next_task: 4" in plan_after


def test_prune_refuses_revert_naming_non_obsolete_task(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    obsolete(fdir, 1)
    add_revert(fdir, 3, [1, 2], "done")
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode != 0
    assert "not obsolete" in (r.stdout + r.stderr)
    assert (fdir / "tasks" / "02-task.md").exists()


def test_prune_refuses_obsolete_task_no_row_reverts(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    obsolete(fdir, 1)
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 1
    assert "Reverts column" in r.stdout
    assert (fdir / "tasks" / "01-task.md").exists()


def test_prune_ignores_reverts_in_task_frontmatter(hub):
    # The link lives only in plan.md. A task document claiming it is not enough.
    fdir = make_feature(hub.path, "feat-1", n_tasks=1)
    obsolete(fdir, 1)
    (fdir / "tasks" / "02-revert.md").write_text(
        "---\nservice: svc\nfeature: feat-1\npriority: high\nstatus: done\n"
        "reverts: [1]\n---\n# Remove it\n## Build notes\n"
    )
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 1
    assert (fdir / "tasks" / "01-task.md").exists()
    assert (fdir / "tasks" / "02-revert.md").exists()


def test_prune_nothing_to_prune(hub):
    make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    r = prune(hub, "feat-1")
    assert r.returncode == 0
    assert "nothing to prune" in r.stdout



def mark_done(task):
    """What a builder does to a task when it finishes it."""
    text = task.read_text().replace("status: pending", "status: done")
    task.write_text(text.replace("- [ ] ", "- [x] "))


def status(task):
    return re.search(r"^status: (\S+)", task.read_text(), re.M).group(1)


def test_seal_reopens_a_done_task_rewritten_since_it_was_built(hub, vcs):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    seal(hub, "feat-1")
    t1, t2 = fdir / "tasks" / "01-task.md", fdir / "tasks" / "02-task.md"
    mark_done(t1)
    mark_done(t2)
    # A re-plan rewrites task 01 in place and forgets to reopen it.
    t1.write_text(t1.read_text().replace("Do the thing.", "Do the thing, now in blue."))
    r = seal(hub, "feat-1")
    assert r.returncode == 0, r.stderr
    assert "reopened: 01-task.md" in r.stdout
    assert "02-task.md" not in r.stdout
    assert status(t1) == "reopened"
    assert status(t2) == "done"
    # Only the status changed: the rewrite and the builder's ticks are kept.
    assert "now in blue" in t1.read_text()
    assert check(hub, "feat-1").returncode == 0


def test_seal_reopens_a_task_edited_during_its_build(hub, vcs):
    # Built from the sealed text, edited while it was built: the edit is
    # caught by check, and when a re-plan keeps it, seal reopens the task.
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("Do the thing.", "Do another thing."))
    mark_done(task)
    assert check(hub, "feat-1").returncode == 1
    r = seal(hub, "feat-1")
    assert "reopened: 01-task.md" in r.stdout
    assert status(task) == "reopened"


def test_reseal_without_changes_leaves_done_tasks_done(hub, vcs):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    mark_done(task)
    r = seal(hub, "feat-1")
    assert "reopened" not in r.stdout
    assert status(task) == "done"


def test_first_seal_reopens_nothing(hub, vcs):
    # No previous seal: nothing was built from a sealed text yet.
    fdir = make_feature(hub.path, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    mark_done(task)
    r = seal(hub, "feat-1")
    assert "reopened" not in r.stdout
    assert status(task) == "done"


def test_legacy_commit_field_does_not_change_the_task_hash(hub, vcs):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("status: pending", "status: done\ncommit: 0818f6e"))
    assert check(hub, "feat-1").returncode == 0
    r = seal(hub, "feat-1")
    assert "reopened" not in r.stdout


# plan.md and task frontmatter are read as YAML, in any layout (issue #14).

def test_check_reads_sealed_hashes_in_flow_form(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    seal(hub, "feat-1")
    plan = fdir / "plan.md"
    text = plan.read_text()
    hashes = re.findall(r'^  "(\d+)": ([0-9a-f]{64})$', text, re.M)
    assert len(hashes) == 2
    flow = "tasks: {" + ", ".join(f"'{n}': {h}" for n, h in hashes) + "}\n"
    plan.write_text(re.sub(r'^tasks:\n(?:  .*\n)+', flow, text, flags=re.M))
    r = check(hub, "feat-1")
    assert r.returncode == 0, r.stdout + r.stderr


def test_seal_keeps_the_planners_frontmatter(hub):
    fdir = make_feature(hub.path, "feat-1")
    plan = fdir / "plan.md"
    plan.write_text(plan.read_text().replace("spec_version: 1\n", "spec_version: 1   # answers v1\n# a note\n"))
    assert seal(hub, "feat-1").returncode == 0
    text = plan.read_text()
    assert "spec_version: 1   # answers v1\n# a note\n" in text
    assert re.search(r"^next_task: 2\nspec_hash: [0-9a-f]{64}\ntasks:\n  \"01\": [0-9a-f]{64}\n---", text, re.M)
    assert seal(hub, "feat-1").returncode == 0
    assert plan.read_text().count("spec_hash:") == 1
    assert check(hub, "feat-1").returncode == 0


def test_seal_reads_status_in_any_form(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("status: pending", 'status: "done"   # built')
                    .replace("Do the thing.", "Do the thing, rewritten."))
    r = seal(hub, "feat-1")
    assert "reopened: 01-task.md" in r.stdout
    assert "status: reopened\n" in task.read_text()


def test_unparseable_task_frontmatter_is_an_error(hub):
    fdir = make_feature(hub.path, "feat-1")
    task = fdir / "tasks" / "01-task.md"
    task.write_text(task.read_text().replace("depends_on: []", "depends_on: [01"))
    r = seal(hub, "feat-1")
    assert r.returncode != 0
    assert "01-task.md" in r.stderr and "does not parse" in r.stderr


def test_malformed_sealed_hashes_are_an_error(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    plan = fdir / "plan.md"
    plan.write_text(re.sub(r'^  "01": [0-9a-f]{64}$', '  "01": not-a-hash', plan.read_text(), flags=re.M))
    r = check(hub, "feat-1")
    assert r.returncode != 0
    assert "tasks: 01: not-a-hash" in r.stderr
