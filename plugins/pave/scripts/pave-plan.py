#!/usr/bin/env python3
"""Plan integrity for one feature: seal, check, prune-obsoleted-tasks.

plan.md frontmatter carries spec_hash (sha256 of spec.md) and one hash per
task document, written at the plan gate. Build and review refuse to run when
either no longer matches, so nothing is ever built against a stale plan or a
task edited outside /pave:plan.

Which task reverts which obsolete one is the planner's record, kept in the
Reverts column of plan.md's task table; task documents never carry it.

A task hash covers only what the planner wrote. It ignores the fields a
builder or reviewer legitimately changes - status, checkbox state and the
Build notes section - so a normal build does not look like an edit.

The hashes plan.md holds are also the record of what was built: check
refuses to build or review a task that differs from its sealed hash, so a
done task was built from the text sealed for it. When seal finds a done task
whose hash differs from the one the previous seal recorded, the task was
rewritten after it was built, and seal reopens it. Nothing here reads a
version control system.

usage: pave-plan.py <seal|check|prune> <feature-dir>
"""
import hashlib
import pathlib
import re
import sys

from pave_yaml import YamlError, read_frontmatter, set_key, split_frontmatter

TASK_FILE = re.compile(r"^(\d+)-.*\.md$")
CHECKBOX = re.compile(r"^(\s*[-*]\s+)\[[xX]\]", re.M)
# commit is no longer written; it stays volatile so task documents from
# before 0.6 keep the hash they were sealed with.
VOLATILE = re.compile(r"^(status|commit):.*$\n?", re.M)
NOTES = re.compile(r"^## Build notes\s*$", re.M)


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def task_hash(text):
    notes = NOTES.search(text)
    if notes:
        text = text[:notes.start()]
    fm, body = split_frontmatter(text)
    if fm is not None:
        text = "---\n" + VOLATILE.sub("", fm) + "---\n" + body
    return sha(CHECKBOX.sub(r"\1[ ]", text).rstrip() + "\n")


def field(path, key, text=None):
    """One frontmatter value of a file as text, "" when absent."""
    data, _, _ = read_frontmatter(path, text)
    v = (data or {}).get(key)
    return "" if v is None else str(v)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def reverts_table(body):
    """{task: [tasks it reverts]} from the Reverts column of the table under ## Tasks."""
    section = re.search(r"^## Tasks\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    rows = [l for l in (section.group(1) if section else "").splitlines() if l.strip().startswith("|")]
    if not rows:
        return {}
    head = [c.lower() for c in cells(rows[0])]
    if "#" not in head or "reverts" not in head:
        return {}
    num, rev = head.index("#"), head.index("reverts")
    out = {}
    for row in rows[1:]:
        c = cells(row)
        if len(c) <= max(num, rev) or not re.fullmatch(r"\d+", c[num]):
            continue
        out[int(c[num])] = [int(x) for x in re.findall(r"\d+", c[rev])]
    return out


def tasks(fdir):
    out = {}
    tdir = fdir / "tasks"
    for p in sorted(tdir.glob("*.md")) if tdir.is_dir() else []:
        m = TASK_FILE.match(p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n in out:
            die(f"two task documents numbered {n:02d}: {out[n].name}, {p.name}")
        out[n] = p
    return out


def read_plan(fdir):
    plan = fdir / "plan.md"
    if not plan.is_file():
        return None, None, None, {}
    data, fm, body = read_frontmatter(plan)
    if data is None:
        die(f"{plan} has no frontmatter")
    # Written by seal alone, but read as YAML: any layout of it reads the same.
    sealed = data.get("tasks") or {}
    if not isinstance(sealed, dict):
        die(f"{plan}: tasks: is not a mapping of task number to hash → run /pave:plan")
    hashes = {}
    for key, val in sealed.items():
        if not re.fullmatch(r"\d+", str(key)) or not re.fullmatch(r"[0-9a-f]{64}", str(val)):
            die(f"{plan}: tasks: {key}: {val} is not a task number and its hash → run /pave:plan")
        hashes[int(str(key))] = str(val)
    return plan, data, (fm, body), hashes


def write_plan(plan, doc, spec_hash, hashes, next_task):
    """Rewrite the keys seal owns - next_task, spec_hash, tasks - in place,
    leaving every other line of the frontmatter as the planner wrote it."""
    fm, body = doc
    fm = set_key(fm, "next_task", f"next_task: {next_task}")
    fm = set_key(fm, "spec_hash", f"spec_hash: {spec_hash}", after="next_task")
    tasks_block = ("tasks:\n" + "".join(f'  "{n:02d}": {h}\n' for n, h in sorted(hashes.items()))
                   if hashes else "tasks: {}")
    fm = set_key(fm, "tasks", tasks_block, after="spec_hash")
    plan.write_text("---\n" + fm + "---\n" + body)


def cmd_seal(fdir):
    plan, data, doc, sealed = read_plan(fdir)
    if plan is None:
        die("no plan.md - nothing to seal")
    spec = fdir / "spec.md"
    if not spec.is_file():
        die("no spec.md - a plan cannot be sealed against nothing")
    all_tasks = tasks(fdir)
    hashes = {n: task_hash(p.read_text()) for n, p in all_tasks.items()}
    # A done task was built from the text the previous seal recorded. If that
    # text changed and the task was not reopened, what was built is not what
    # the task now says.
    for n, p in sorted(all_tasks.items()):
        tdata, tfm, body_ = read_frontmatter(p)
        if tdata and tdata.get("status") == "done" and n in sealed and sealed[n] != hashes[n]:
            p.write_text("---\n" + set_key(tfm, "status", "status: reopened") + "---\n" + body_)
            print(f"reopened: {p.name} - done, but changed since it was sealed and built")
    try:
        declared = int(str(data.get("next_task") or 1))
    except ValueError:
        declared = 1
    next_task = max([declared] + [n + 1 for n in all_tasks])
    spec_text = spec.read_text()
    write_plan(plan, doc, sha(spec_text), hashes, next_task)
    (fdir / "artifacts").mkdir(exist_ok=True)
    (fdir / "artifacts" / "spec.approved.md").write_text(spec_text)
    print(f"sealed: spec v{field(spec, 'version', spec_text) or '?'}, "
          f"{len(hashes)} task(s), next_task {next_task}")


def cmd_check(fdir):
    plan, data, _, hashes = read_plan(fdir)
    if plan is None:
        print("no-plan: plan.md does not exist → run /pave:plan")
        sys.exit(2)
    recorded = "" if data.get("spec_hash") is None else str(data["spec_hash"])
    if not recorded:
        print("unsealed: plan.md was never approved at the plan gate → run /pave:plan")
        sys.exit(2)
    problems = []
    spec = fdir / "spec.md"
    if not spec.is_file():
        problems.append("spec.md is missing → run /pave:spec")
    elif sha(spec.read_text()) != recorded:
        problems.append("spec.md changed since the plan was approved → run /pave:plan")
    found = tasks(fdir)
    for n in sorted(set(found) | set(hashes)):
        if n not in hashes:
            problems.append(f"tasks/{found[n].name} was added outside /pave:plan → run /pave:plan")
        elif n not in found:
            problems.append(f"task {n:02d} was deleted outside /pave:plan → run /pave:plan")
        elif task_hash(found[n].read_text()) != hashes[n]:
            problems.append(f"tasks/{found[n].name} was edited outside /pave:plan → run /pave:plan")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print(f"ok: plan matches spec.md and {len(hashes)} task(s)")


def cmd_prune(fdir):
    plan, data, doc, hashes = read_plan(fdir)
    if plan is None:
        die("no plan.md")
    body = doc[1]
    meta = {}
    for n, p in tasks(fdir).items():
        meta[n] = {"path": p, "status": field(p, "status")}
    obsolete = sorted(n for n, t in meta.items() if t["status"] == "obsolete")
    if not obsolete:
        print("nothing to prune: no obsolete tasks")
        return
    table = reverts_table(body)
    reverts_of = {n: sorted(r for r, named in table.items() if r in meta and n in named)
                  for n in obsolete}
    problems = []
    for n in obsolete:
        if not reverts_of[n]:
            problems.append(f"{n:02d} is obsolete but no task in plan.md's Reverts column names it")
        for r in reverts_of[n]:
            if meta[r]["status"] != "done":
                problems.append(f"{n:02d} is obsolete but its revert {r:02d} is {meta[r]['status'] or 'unset'}, not done")
    if problems:
        print("refused - nothing was removed:\n  " + "\n  ".join(problems))
        sys.exit(1)
    remove = set(obsolete)
    for n in obsolete:
        remove.update(reverts_of[n])
    for r in sorted(remove - set(obsolete)):
        stray = [t for t in table[r] if t not in remove]
        if stray:
            die(f"revert {r:02d} also names {', '.join(f'{t:02d}' for t in stray)}, which are not obsolete")
    for n in sorted(remove):
        meta[n]["path"].unlink()
        hashes.pop(n, None)
        label = "revert" if n not in obsolete else "obsolete"
        print(f"pruned: {meta[n]['path'].name} ({label})")
    write_plan(plan, doc, data.get("spec_hash") or "", hashes, data.get("next_task") or 1)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("seal", "check", "prune"):
        die("usage: pave-plan.py <seal|check|prune> <feature-dir>")
    fdir = pathlib.Path(sys.argv[2])
    if not fdir.is_dir():
        die(f"no such feature folder: {fdir}")
    try:
        {"seal": cmd_seal, "check": cmd_check, "prune": cmd_prune}[sys.argv[1]](fdir)
    except YamlError as e:
        die(str(e))


if __name__ == "__main__":
    main()
