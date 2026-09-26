#!/usr/bin/env python3
"""Plan integrity for one feature: seal, check, prune-obsoleted-tasks.

plan.md frontmatter carries spec_hash (sha256 of spec.md) and one hash per
task document, written at the plan gate. Build and review refuse to run when
either no longer matches, so nothing is ever built against a stale plan or a
task edited outside /pave:plan.

A task hash covers only what the planner wrote. It ignores the fields a
builder or reviewer legitimately changes - status, commit, checkbox state and
the Build notes section - so a normal build does not look like an edit.

usage: pave-plan.py <seal|check|prune> <feature-dir>
"""
import hashlib
import pathlib
import re
import sys

TASK_FILE = re.compile(r"^(\d+)-.*\.md$")
CHECKBOX = re.compile(r"^(\s*[-*]\s+)\[[xX]\]", re.M)
VOLATILE = re.compile(r"^(status|commit):.*$\n?", re.M)
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


def int_list(fm, key):
    raw = scalar(fm, key)
    return [int(x) for x in re.findall(r"\d+", raw)] if raw.startswith("[") else []


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


def cmd_seal(fdir):
    plan, fm, body, _ = read_plan(fdir)
    if plan is None:
        die("no plan.md - nothing to seal")
    spec = fdir / "spec.md"
    if not spec.is_file():
        die("no spec.md - a plan cannot be sealed against nothing")
    all_tasks = tasks(fdir)
    hashes = {n: task_hash(p.read_text()) for n, p in all_tasks.items()}
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
        meta[n] = {"path": p, "status": scalar(tfm, "status"), "kind": scalar(tfm, "kind"),
                   "reverts": int_list(tfm, "reverts")}
    obsolete = sorted(n for n, t in meta.items() if t["status"] == "obsolete")
    if not obsolete:
        print("nothing to prune: no obsolete tasks")
        return
    reverts_of = {n: sorted(r for r, t in meta.items() if t["kind"] == "revert" and n in t["reverts"])
                  for n in obsolete}
    problems = []
    for n in obsolete:
        if not reverts_of[n]:
            problems.append(f"{n:02d} is obsolete but no revert task names it")
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
        stray = [t for t in meta[r]["reverts"] if t not in remove]
        if stray:
            die(f"revert {r:02d} also names {', '.join(f'{t:02d}' for t in stray)}, which are not obsolete")
    for n in sorted(remove):
        meta[n]["path"].unlink()
        hashes.pop(n, None)
        label = "revert" if n not in obsolete else "obsolete"
        print(f"pruned: {meta[n]['path'].name} ({label})")
    write_plan(plan, fm, body, scalar(fm, "spec_hash"), hashes, scalar(fm, "next_task") or 1)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("seal", "check", "prune"):
        die("usage: pave-plan.py <seal|check|prune> <feature-dir>")
    fdir = pathlib.Path(sys.argv[2])
    if not fdir.is_dir():
        die(f"no such feature folder: {fdir}")
    {"seal": cmd_seal, "check": cmd_check, "prune": cmd_prune}[sys.argv[1]](fdir)


if __name__ == "__main__":
    main()
