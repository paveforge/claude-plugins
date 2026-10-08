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


# ---- the seal is disposable and lives outside plan.md -------------------

SEAL = ("artifacts", "seal.yaml")


def test_seal_writes_task_hashes_to_the_seal_not_plan(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=2)
    assert seal(hub, "feat-1").returncode == 0
    plan_fm = (fdir / "plan.md").read_text().split("---")[1]
    assert "spec_hash:" in plan_fm
    assert "tasks:" not in plan_fm
    sealed = fdir.joinpath(*SEAL).read_text()
    assert '"01":' in sealed and '"02":' in sealed
    assert (fdir / "artifacts" / "spec.approved.md").read_text() == (fdir / "spec.md").read_text()


def test_seal_drops_a_legacy_tasks_block_from_plan(hub):
    fdir = make_feature(hub.path, "feat-1")
    plan = fdir / "plan.md"
    plan.write_text(plan.read_text().replace(
        "next_task: 2\n", "next_task: 2\ntasks:\n  \"01\": " + "a" * 64 + "\n"))
    seal(hub, "feat-1")
    assert "tasks:" not in plan.read_text().split("---")[1]


def test_check_without_seal_asks_for_the_tasks_to_be_rebuilt(hub):
    # A fresh clone that kept only spec.md and plan.md, or a hub from before
    # the seal moved out of plan.md: the tasks cannot be vouched for.
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    fdir.joinpath(*SEAL).unlink()
    r = check(hub, "feat-1")
    assert r.returncode == 1
    assert "unverified" in r.stdout
    assert seal(hub, "feat-1").returncode == 0
    assert check(hub, "feat-1").returncode == 0


def test_prune_updates_the_seal(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=1)
    obsolete(fdir, 1)
    add_revert(fdir, 2, [1], "done")
    seal(hub, "feat-1")
    assert prune(hub, "feat-1").returncode == 0
    assert '"01"' not in fdir.joinpath(*SEAL).read_text()


# ---- diff ---------------------------------------------------------------

def diff(hub, feature_id):
    return hub.run("diff", env={"SESSION_FEATURE_ID": feature_id})


def edit_spec(fdir, old, new):
    spec = fdir / "spec.md"
    spec.write_text(spec.read_text().replace(old, new))


def test_diff_without_baseline_allows_only_a_full_replan(hub):
    make_feature(hub.path, "feat-1")
    r = diff(hub, "feat-1")
    assert r.returncode == 2
    assert "no-baseline" in r.stdout
    assert "full re-plan" in r.stdout


def test_diff_reports_criteria_and_the_tasks_they_reach(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=1)
    seal(hub, "feat-1")
    edit_spec(fdir, "- **AC-1** it works", "- **AC-1** it works, in blue\n- **AC-2** it fails politely")
    r = diff(hub, "feat-1")
    assert r.returncode == 0, r.stderr
    assert "changed: AC-1" in r.stdout
    assert "added: AC-2" in r.stdout
    assert "removed: -" in r.stdout
    assert "01  svc  AC-1  (pending)" in r.stdout
    assert "services: svc" in r.stdout


def test_diff_ignores_why_and_what(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    edit_spec(fdir, "Does a thing.", "Does a thing, described better.")
    edit_spec(fdir, "Test feature.", "A better reason.")
    r = diff(hub, "feat-1")
    assert "changed: -" in r.stdout
    assert "tasks: -" in r.stdout
    assert "no criterion, guardrail or exclusion changed" in r.stdout


def test_diff_flags_guardrails_and_out_of_scope(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    edit_spec(fdir, "- none", "- v1 clients keep working")
    edit_spec(fdir, "Nothing else.", "No refunds.")
    r = diff(hub, "feat-1")
    assert "guardrails: changed" in r.stdout
    assert "out-of-scope: changed" in r.stdout


def test_diff_reports_a_removed_criterion(hub):
    fdir = make_feature(hub.path, "feat-1")
    seal(hub, "feat-1")
    edit_spec(fdir, "- **AC-1** it works", "- **AC-2** something else")
    r = diff(hub, "feat-1")
    assert "removed: AC-1" in r.stdout
    assert "01  svc  AC-1" in r.stdout


# ---- overlaps and attribution -------------------------------------------

def write_task(fdir, n, item, service="svc", status="pending", depends="-"):
    (fdir / "tasks" / f"{n:02d}-task.md").write_text(
        f"---\nservice: {service}\nfeature: feat-1\npriority: low\nstatus: {status}\n"
        "depends_on: []\nsatisfies: [AC-1]\nderives_from:\n  - plan.md#approach\n---\n"
        f"# Task {n}\n\n## Tasks\n\n- [ ] {item}\n\n## Build notes\n"
        "Touched `notes/ignored.go` while building.\n"
    )
    plan = fdir / "plan.md"
    rows = [l for l in plan.read_text().splitlines(keepends=True) if not l.startswith(f"| {n:02d} |")]
    plan.write_text("".join(rows) + f"| {n:02d} | Task {n} | {service} | low | S | AC-1 | {depends} | - | new |\n")


def overlaps(hub, feature_id):
    return hub.run("overlaps", env={"SESSION_FEATURE_ID": feature_id})


def test_overlaps_flags_two_tasks_naming_one_file(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=0)
    write_task(fdir, 1, "Extend `Order` (internal/api/order.go) with tracking_url")
    write_task(fdir, 2, "`internal/api/order.go` drops the legacy helper")
    r = overlaps(hub, "feat-1")
    assert r.returncode == 1
    assert "01 and 02 (svc) both name internal/api/order.go" in r.stdout


def test_overlaps_accepts_an_ordering_in_either_direction(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=0)
    write_task(fdir, 1, "Extend `Order` (internal/api/order.go)")
    write_task(fdir, 2, "Stop using a helper in internal/api/order.go", depends="01")
    assert overlaps(hub, "feat-1").returncode == 0


def test_overlaps_allows_parallel_work_on_different_files_and_services(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=0)
    write_task(fdir, 1, "Extend `Order` (internal/api/order.go)")
    write_task(fdir, 2, "Add `internal/api/refund.go`")
    write_task(fdir, 3, "Extend `Order` (internal/api/order.go)", service="billing")
    write_task(fdir, 4, "Rewrite internal/api/order.go", status="done")
    r = overlaps(hub, "feat-1")
    assert r.returncode == 0, r.stdout
    # Paths in the Build notes are the builder's, not the planner's.
    assert "notes/ignored.go" not in r.stdout


def attribute(hub, feature_id, *args):
    return hub.run("attribute", *args, env={"SESSION_FEATURE_ID": feature_id})


def test_attribute_sorts_failing_files_by_the_tasks_that_name_them(hub):
    fdir = make_feature(hub.path, "feat-1", n_tasks=0)
    write_task(fdir, 1, "Extend `Order` (internal/api/order.go)")
    write_task(fdir, 2, "Add `internal/api/refund.go`")
    write_task(fdir, 3, "Rename a type in internal/api/refund.go", depends="02")
    r = attribute(hub, "feat-1", "svc", "internal/api/order.go",
                  "internal/api/refund.go", "tests/__snapshots__/order.json")
    assert r.returncode == 0, r.stderr
    assert "internal/api/order.go\ttask\t01" in r.stdout
    assert "internal/api/refund.go\tshared\t02,03" in r.stdout
    assert "tests/__snapshots__/order.json\tunnamed\t-" in r.stdout


def test_attribute_takes_absolute_paths_inside_the_service(hub, tmp_path):
    fdir = make_feature(hub.path, "feat-1", n_tasks=0)
    svc = tmp_path / "svc-repo"
    svc.mkdir()
    (hub.path / "workspace.yaml").write_text(f"services:\n  - name: svc\n    path: {svc}\n")
    write_task(fdir, 1, "Extend `Order` (internal/api/order.go)")
    r = attribute(hub, "feat-1", "svc", f"{svc}/internal/api/order.go")
    assert f"{svc}/internal/api/order.go\ttask\t01" in r.stdout


def test_attribute_needs_a_service_and_a_file(hub):
    make_feature(hub.path, "feat-1")
    assert attribute(hub, "feat-1", "svc").returncode != 0


# ---- contracts: a record copied after a clean review ---------------------

def contracts(hub, feature_id):
    return hub.run("contracts", env={"SESSION_FEATURE_ID": feature_id})


def contract_setup(hub, tmp_path, status):
    fdir = make_feature(hub.path, "feat-1", n_tasks=0)
    write_task(fdir, 1, "Add `tracking_url` to `OrderResponse` (proto/order/v1/order.proto)", status=status)
    plan = fdir / "plan.md"
    plan.write_text(plan.read_text().replace(
        "## Tasks",
        "## Service map\n\n| Service | State | Role / why |\n|---|---|---|\n"
        "| svc | modify | returns the field |\n| billing | read-only | reads it |\n\n## Tasks", 1))
    repo = tmp_path / "svc-repo"
    (repo / "proto" / "order" / "v1").mkdir(parents=True)
    (repo / "proto" / "order" / "v1" / "order.proto").write_text("message OrderResponse {}\n")
    (repo / "schemas").mkdir()
    (repo / "schemas" / "event.json").write_text("{}\n")
    (hub.path / "workspace.yaml").write_text(
        "services:\n\n"
        f"  - name: svc\n    path: {repo}\n    repo_root: {repo}\n    language: go\n"
        "    commands:\n      build: make\n"
        "    contracts:\n"
        "      - kind: protobuf\n        path: proto/order/v1/order.proto\n        role: producer\n"
        "      - kind: json-schema\n        path: schemas/\n        role: producer\n"
        "      - { kind: openapi, path: api/billing.yaml, role: consumer }\n"
        "    consumes: [billing]\n\n"
        f"  - name: billing\n    path: {tmp_path / 'billing'}\n    contracts:\n"
        "      - kind: openapi\n        path: api/billing.yaml\n        role: producer\n")
    return fdir


def test_contracts_copies_producer_contracts_of_modified_services(hub, tmp_path):
    fdir = contract_setup(hub, tmp_path, "done")
    r = contracts(hub, "feat-1")
    assert r.returncode == 0, r.stdout + r.stderr
    out = fdir / "artifacts" / "contracts"
    assert (out / "svc" / "proto" / "order" / "v1" / "order.proto").read_text() == "message OrderResponse {}\n"
    assert (out / "svc" / "schemas" / "event.json").is_file()
    # A consumer contract, and a service the plan does not modify, are not copied.
    assert not (out / "billing").exists()
    assert "2 copied" in r.stdout


def test_contracts_refuses_until_every_task_is_done(hub, tmp_path):
    fdir = contract_setup(hub, tmp_path, "failed")
    r = contracts(hub, "feat-1")
    assert r.returncode == 1
    assert "refused" in r.stdout
    assert not (fdir / "artifacts" / "contracts").exists()


def test_contracts_is_rebuilt_from_scratch(hub, tmp_path):
    fdir = contract_setup(hub, tmp_path, "done")
    stale = fdir / "artifacts" / "contracts" / "svc" / "old.proto"
    stale.parent.mkdir(parents=True)
    stale.write_text("gone\n")
    assert contracts(hub, "feat-1").returncode == 0
    assert not stale.exists()
