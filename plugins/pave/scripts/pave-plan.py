#!/usr/bin/env python3
"""Plan integrity for one feature: seal, check, prune-obsoleted-tasks - and
done, which marks one task document built.

plan.md frontmatter carries spec_hash (sha256 of spec.md) and one hash per
task document, written at the plan gate. Build and review refuse to run when
either no longer matches, so nothing is ever built against a stale plan or a
task edited outside /pave:plan.

Which task reverts which obsolete one is the planner's record, kept in the
Reverts column of plan.md's task table; task documents never carry it.

A task hash covers only what the planner wrote. It ignores the fields a
builder or reviewer legitimately changes - status, executed_hash, checkbox
state and the Build notes section - so a normal build does not look like an
edit.

A done task records executed_hash: the hash of the version of the task that
was executed. When a re-plan rewrites a done task without reopening it, the
two no longer match, and seal reopens it. Nothing here reads a version control system.

usage: pave-plan.py <seal|check|prune> <feature-dir>
       pave-plan.py done <task-document>
"""
import hashlib
import pathlib
import re
import sys

TASK_FILE = re.compile(r"^(\d+)-.*\.md$")
CHECKBOX = re.compile(r"^(\s*[-*]\s+)\[[xX]\]", re.M)
# commit is no longer written; it stays volatile so task documents from
# before executed_hash keep the hash they were sealed with.
VOLATILE = re.compile(r"^(status|executed_hash|commit):.*$\n?", re.M)
NOTES = re.compile(r"^## Build notes\s*$", re.M)


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end < 0:
        return None, text
    close = text.find("\n", end + 1)
    close = len(text) if close < 0 else close + 1
    return text[4:end + 1], text[close:]


def task_hash(text):
    notes = NOTES.search(text)
    if notes:
        text = text[:notes.start()]
    fm, body = split_frontmatter(text)
    if fm is not None:
        text = "---\n" + VOLATILE.sub("", fm) + "---\n" + body
    return sha(CHECKBOX.sub(r"\1[ ]", text).rstrip() + "\n")


def scalar(fm, key):
    m = re.search(rf"^{key}:\s*([^#\n]*)", fm or "", re.M)
    return m.group(1).strip().strip("'\"") if m else ""


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
    text = plan.read_text()
    fm, body = split_frontmatter(text)
    if fm is None:
        die(f"{plan} has no frontmatter")
    hashes = {}
    block = re.search(r"^tasks:\s*\n((?:[ \t]+.*\n?)*)", fm, re.M)
    if block:
        for key, val in re.findall(r"^\s+[\"']?(\d+)[\"']?:\s*([0-9a-f]{64})", block.group(1), re.M):
            hashes[int(key)] = val
    return plan, fm, body, hashes


def write_plan(plan, fm, body, spec_hash, hashes, next_task):
    fm = re.sub(r"^tasks:\s*\n(?:[ \t]+.*\n?)*", "", fm, flags=re.M)
    fm = re.sub(r"^(spec_hash|tasks):.*\n?", "", fm, flags=re.M)
    fm = re.sub(r"^next_task:.*\n?", "", fm, flags=re.M)
    fm = fm.rstrip("\n") + "\n" if fm.strip() else ""
    fm += f"next_task: {next_task}\n"
    fm += f"spec_hash: {spec_hash}\n"
    fm += "tasks:\n" + "".join(f'  "{n:02d}": {h}\n' for n, h in sorted(hashes.items())) if hashes else "tasks: {}\n"
    plan.write_text("---\n" + fm + "---\n" + body)


def set_field(text, key, value):
    """Set one frontmatter scalar, adding it after status if absent."""
    fm, body = split_frontmatter(text)
    if fm is None:
        return None
    line = f"{key}: {value}"
    if re.search(rf"^{key}:.*$", fm, re.M):
        fm = re.sub(rf"^{key}:[^\n]*", lambda _: line, fm, count=1, flags=re.M)
    elif re.search(r"^status:.*$", fm, re.M):
        fm = re.sub(r"^(status:[^\n]*\n)", lambda m: m.group(1) + line + "\n", fm, count=1, flags=re.M)
    else:
        fm += line + "\n"
    return "---\n" + fm + "---\n" + body


def cmd_seal(fdir):
    plan, fm, body, _ = read_plan(fdir)
    if plan is None:
        die("no plan.md - nothing to seal")
    spec = fdir / "spec.md"
    if not spec.is_file():
        die("no spec.md - a plan cannot be sealed against nothing")
    all_tasks = tasks(fdir)
    hashes = {n: task_hash(p.read_text()) for n, p in all_tasks.items()}
    # A done task whose executed version differs was rewritten without being
    # reopened: what was built is not what the task now says.
    for n, p in sorted(all_tasks.items()):
        text = p.read_text()
        tfm, _ = split_frontmatter(text)
        executed = scalar(tfm, "executed_hash")
        if scalar(tfm, "status") == "done" and executed and executed != hashes[n]:
            p.write_text(set_field(text, "status", "reopened"))
            print(f"reopened: {p.name} - done, but changed since it was built")
    try:
        declared = int(scalar(fm, "next_task") or 1)
    except ValueError:
        declared = 1
    next_task = max([declared] + [n + 1 for n in all_tasks])
    spec_text = spec.read_text()
    write_plan(plan, fm, body, sha(spec_text), hashes, next_task)
    (fdir / "artifacts").mkdir(exist_ok=True)
    (fdir / "artifacts" / "spec.approved.md").write_text(spec_text)
    print(f"sealed: spec v{scalar(split_frontmatter(spec_text)[0], 'version') or '?'}, "
          f"{len(hashes)} task(s), next_task {next_task}")


def cmd_check(fdir):
    plan, fm, _, hashes = read_plan(fdir)
    if plan is None:
        print("no-plan: plan.md does not exist → run /pave:plan")
        sys.exit(2)
    recorded = scalar(fm, "spec_hash")
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
    plan, fm, body, hashes = read_plan(fdir)
    if plan is None:
        die("no plan.md")
    meta = {}
    for n, p in tasks(fdir).items():
        tfm, _ = split_frontmatter(p.read_text())
        meta[n] = {"path": p, "status": scalar(tfm, "status")}
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
    write_plan(plan, fm, body, scalar(fm, "spec_hash"), hashes, scalar(fm, "next_task") or 1)


def cmd_done(task):
    """Mark one task document done, recording the hash of the executed version."""
    if not task.is_file() or not TASK_FILE.match(task.name):
        die(f"not a task document: {task}")
    text = task.read_text()
    if split_frontmatter(text)[0] is None:
        die(f"{task} has no frontmatter")
    h = task_hash(text)
    text = set_field(set_field(text, "status", "done"), "executed_hash", h)
    task.write_text(text)
    print(f"done: {task.name} executed_hash {h[:7]}")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "done":
        cmd_done(pathlib.Path(sys.argv[2]))
        return
    if len(sys.argv) != 3 or sys.argv[1] not in ("seal", "check", "prune"):
        die("usage: pave-plan.py <seal|check|prune> <feature-dir> | done <task-document>")
    fdir = pathlib.Path(sys.argv[2])
    if not fdir.is_dir():
        die(f"no such feature folder: {fdir}")
    {"seal": cmd_seal, "check": cmd_check, "prune": cmd_prune}[sys.argv[1]](fdir)


if __name__ == "__main__":
    main()
