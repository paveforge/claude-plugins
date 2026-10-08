#!/usr/bin/env python3
"""Plan integrity and plan-derived reports for one feature.

spec.md and plan.md are the feature's only sources of truth. Everything else
in the feature folder - task documents, the seal, the approved-spec
snapshot, contract copies - is disposable and can be rebuilt from them.

plan.md frontmatter carries spec_hash: the hash of the spec it was approved
against, binding the two truths. The disposable seal,
artifacts/seal.yaml, carries one hash per task document as it was projected
from the plan. Build and review refuse when either no longer matches. A task
the seal cannot vouch for - edited by hand, or with no seal at all - is
rebuilt from plan.md, never trusted.

A task hash covers only what the planner wrote. It ignores the fields a
builder or reviewer legitimately changes - status, checkbox state and the
Build notes section - so a normal build does not look like an edit. When
seal finds a done task whose hash differs from the one the previous seal
recorded, the task was rewritten after it was built, and seal reopens it.

Which task reverts which obsolete one, which criteria a task satisfies and
what it depends on are the planner's record, kept in plan.md's task table.

Nothing here reads a version control system.

usage: pave-plan.py seal|check|prune|diff|overlaps|contracts <feature-dir>
       pave-plan.py attribute <feature-dir> <service> <file>...
"""
import hashlib
import pathlib
import re
import shutil
import sys

TASK_FILE = re.compile(r"^(\d+)-.*\.md$")
CHECKBOX = re.compile(r"^(\s*[-*]\s+)\[[xX]\]", re.M)
# commit is no longer written; it stays volatile so task documents from
# before 0.6 keep the hash they were sealed with.
VOLATILE = re.compile(r"^(status|commit):.*$\n?", re.M)
NOTES = re.compile(r"^## Build notes\s*$", re.M)
COMMENT = re.compile(r"<!--.*?-->", re.S)
SEAL = pathlib.Path("artifacts") / "seal.yaml"
APPROVED = pathlib.Path("artifacts") / "spec.approved.md"
# A path an item names: two or more segments, or a backticked file name.
PATH = re.compile(r"(?<![\w./@-])((?:[\w.@-]+/)+[\w.@-]*)")
TICKED = re.compile(r"`([^`\s]+)`")


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


def section(body, title):
    """The text under `## <title>` up to the next `## ` heading, comments removed."""
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    return COMMENT.sub("", m.group(1)) if m else ""


def table(body, title):
    """Rows of the first table under `## <title>`, as dicts keyed by lowercased header."""
    rows = [l for l in section(body, title).splitlines() if l.strip().startswith("|")]
    if not rows:
        return []
    head = [c.lower() for c in cells(rows[0])]
    out = []
    for row in rows[1:]:
        c = cells(row)
        if set("".join(c)) <= set("-: "):
            continue
        out.append(dict(zip(head, c)))
    return out


def numbers(cell):
    return [int(x) for x in re.findall(r"\d+", cell or "")]


def task_rows(body):
    """{task number: row} from plan.md's task table - the planner's record."""
    out = {}
    for row in table(body, "Tasks"):
        if re.fullmatch(r"\d+", row.get("#", "")):
            out[int(row["#"])] = row
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


def task_status(path):
    return scalar(split_frontmatter(path.read_text())[0], "status")


def read_plan(fdir):
    plan = fdir / "plan.md"
    if not plan.is_file():
        return None, None, None
    text = plan.read_text()
    fm, body = split_frontmatter(text)
    if fm is None:
        die(f"{plan} has no frontmatter")
    return plan, fm, body


def read_seal(fdir):
    """{task number: hash} from the seal, or None when there is no seal."""
    p = fdir / SEAL
    if not p.is_file():
        return None
    return {int(k): v for k, v in
            re.findall(r"^\s+[\"']?(\d+)[\"']?:\s*([0-9a-f]{64})", p.read_text(), re.M)}


def write_seal(fdir, hashes):
    p = fdir / SEAL
    p.parent.mkdir(exist_ok=True)
    lines = "".join(f'  "{n:02d}": {h}\n' for n, h in sorted(hashes.items()))
    p.write_text("# Written by `pave.sh seal`: the hash of every task document as it was\n"
                 "# projected from plan.md. Disposable - if it is lost, /pave:plan rebuilds\n"
                 "# the tasks from plan.md. Never edit it by hand.\n"
                 + ("tasks:\n" + lines if hashes else "tasks: {}\n"))


def write_plan(plan, fm, body, spec_hash, next_task):
    # A `tasks:` block in plan.md is from before the seal moved out of it.
    fm = re.sub(r"^tasks:\s*\n(?:[ \t]+.*\n?)*", "", fm, flags=re.M)
    fm = re.sub(r"^(spec_hash|tasks|next_task):.*\n?", "", fm, flags=re.M)
    fm = fm.rstrip("\n") + "\n" if fm.strip() else ""
    fm += f"next_task: {next_task}\nspec_hash: {spec_hash}\n"
    plan.write_text("---\n" + fm + "---\n" + body)


def cmd_seal(fdir):
    plan, fm, body = read_plan(fdir)
    if plan is None:
        die("no plan.md - nothing to seal")
    spec = fdir / "spec.md"
    if not spec.is_file():
        die("no spec.md - a plan cannot be sealed against nothing")
    sealed = read_seal(fdir) or {}
    all_tasks = tasks(fdir)
    hashes = {n: task_hash(p.read_text()) for n, p in all_tasks.items()}
    # A done task was built from the text the previous seal recorded. If that
    # text changed and the task was not reopened, what was built is not what
    # the task now says.
    for n, p in sorted(all_tasks.items()):
        text = p.read_text()
        tfm, body_ = split_frontmatter(text)
        if scalar(tfm, "status") == "done" and n in sealed and sealed[n] != hashes[n]:
            tfm = re.sub(r"^status:[^\n]*", "status: reopened", tfm, count=1, flags=re.M)
            p.write_text("---\n" + tfm + "---\n" + body_)
            print(f"reopened: {p.name} - done, but changed since it was sealed and built")
    try:
        declared = int(scalar(fm, "next_task") or 1)
    except ValueError:
        declared = 1
    next_task = max([declared] + [n + 1 for n in all_tasks] + [n + 1 for n in task_rows(body)])
    spec_text = spec.read_text()
    write_plan(plan, fm, body, sha(spec_text), next_task)
    write_seal(fdir, hashes)
    (fdir / APPROVED).write_text(spec_text)
    print(f"sealed: spec v{scalar(split_frontmatter(spec_text)[0], 'version') or '?'}, "
          f"{len(hashes)} task(s), next_task {next_task}")


def cmd_check(fdir):
    plan, fm, _ = read_plan(fdir)
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
    hashes = read_seal(fdir)
    found = tasks(fdir)
    if hashes is None:
        problems.append(f"unverified: {SEAL} is missing, so no task can be vouched for "
                        "→ run /pave:plan to rebuild the tasks from plan.md")
        hashes = {}
    else:
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
    plan, fm, body = read_plan(fdir)
    if plan is None:
        die("no plan.md")
    hashes = read_seal(fdir)
    if hashes is None:
        die(f"{SEAL} is missing - run /pave:plan to rebuild the tasks first")
    meta = {n: {"path": p, "status": task_status(p)} for n, p in tasks(fdir).items()}
    obsolete = sorted(n for n, t in meta.items() if t["status"] == "obsolete")
    if not obsolete:
        print("nothing to prune: no obsolete tasks")
        return
    table_ = {n: numbers(r.get("reverts")) for n, r in task_rows(body).items()}
    reverts_of = {n: sorted(r for r, named in table_.items() if r in meta and n in named)
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
        stray = [t for t in table_[r] if t not in remove]
        if stray:
            die(f"revert {r:02d} also names {', '.join(f'{t:02d}' for t in stray)}, which are not obsolete")
    for n in sorted(remove):
        meta[n]["path"].unlink()
        hashes.pop(n, None)
        label = "revert" if n not in obsolete else "obsolete"
        print(f"pruned: {meta[n]['path'].name} ({label})")
    write_seal(fdir, hashes)


# ---- diff: what a spec change reaches -----------------------------------

def criteria(body):
    """{AC id: text} from the Acceptance criteria section. An id is permanent."""
    out, cur = {}, None
    for line in section(body, "Acceptance criteria").splitlines():
        m = re.match(r"\s*[-*]\s+\*\*(AC-\d+)\*\*\s*(.*)$", line)
        if m:
            cur = m.group(1)
            out[cur] = [m.group(2).strip()]
        elif re.match(r"\s*[-*]\s+", line):
            cur = None
        elif cur and line.strip():
            out[cur].append(line.strip())
    return {k: " ".join(v) for k, v in out.items()}


def normalised(text):
    return "\n".join(l.rstrip() for l in text.strip().splitlines() if l.strip())


def cmd_diff(fdir):
    """Which acceptance criteria, guardrails and exclusions changed since the
    plan was approved, and which tasks and services they reach. Why and What
    are prose for people: they are not compared."""
    spec, approved = fdir / "spec.md", fdir / APPROVED
    if not spec.is_file():
        die("no spec.md")
    if not approved.is_file():
        print(f"no-baseline: {APPROVED} is missing, so what changed cannot be known "
              "→ only a full re-plan is possible")
        sys.exit(2)
    old_fm, old = split_frontmatter(approved.read_text())
    new_fm, new = split_frontmatter(spec.read_text())
    a, b = criteria(old), criteria(new)
    added = sorted(set(b) - set(a), key=lambda k: int(k[3:]))
    removed = sorted(set(a) - set(b), key=lambda k: int(k[3:]))
    changed = sorted((k for k in set(a) & set(b) if a[k] != b[k]), key=lambda k: int(k[3:]))
    guard = normalised(section(old, "Guardrails")) != normalised(section(new, "Guardrails"))
    scope = normalised(section(old, "Out of scope")) != normalised(section(new, "Out of scope"))
    print(f"spec: v{scalar(old_fm, 'version') or '?'} → v{scalar(new_fm, 'version') or '?'}")
    for label, ids in (("changed", changed), ("added", added), ("removed", removed)):
        print(f"{label}: {', '.join(ids) or '-'}")
    print(f"guardrails: {'changed' if guard else 'unchanged'}")
    print(f"out-of-scope: {'changed' if scope else 'unchanged'}")

    _, _, body = read_plan(fdir)
    moved = set(changed) | set(removed)
    docs = tasks(fdir)
    reached, services = [], set()
    for n, row in sorted(task_rows(body or "").items()):
        hit = sorted(set(re.findall(r"AC-\d+", row.get("satisfies", ""))) & moved,
                     key=lambda k: int(k[3:]))
        if not hit or row.get("change", "").strip() == "obsolete":
            continue
        service = row.get("service", "?")
        status = task_status(docs[n]) if n in docs else "no document"
        reached.append(f"  {n:02d}  {service}  {', '.join(hit)}  ({status})")
        services.add(service)
    print("tasks:" + ("\n" + "\n".join(reached) if reached else " -"))
    print(f"services: {', '.join(sorted(services)) or '-'}")
    if not (added or removed or changed or guard or scope):
        print("note: no criterion, guardrail or exclusion changed")


# ---- files a task names: overlaps and attribution -----------------------

def named_paths(text):
    """The paths a task document names above its Build notes."""
    notes = NOTES.search(text)
    if notes:
        text = text[:notes.start()]
    _, body = split_frontmatter(text)
    body = COMMENT.sub("", body)
    found = set(PATH.findall(body))
    found |= {t for t in TICKED.findall(body) if re.search(r"\.\w+$", t) or "/" in t}
    out = set()
    for p in found:
        p = p.strip(".,;:()'\"").removeprefix("./")
        if p and not p.startswith(("plan.md", "http", "contracts/")) and "://" not in p:
            out.add(p)
    return out


def same_place(a, b):
    """True when two repo paths name the same file or one is a folder holding the other."""
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or a.endswith("/" + b) or b.endswith("/" + a) \
        or a.startswith(b + "/") or b.startswith(a + "/")


def task_docs(fdir, body):
    """[(number, service, status, named paths)] for every task document."""
    rows = task_rows(body)
    out = []
    for n, p in sorted(tasks(fdir).items()):
        text = p.read_text()
        fm, _ = split_frontmatter(text)
        service = scalar(fm, "service") or rows.get(n, {}).get("service", "")
        out.append((n, service, scalar(fm, "status"), named_paths(text)))
    return out


def cmd_overlaps(fdir):
    """Two tasks of one service that name the same place may not run at once:
    there must be a depends_on path between them, in either direction."""
    plan, _, body = read_plan(fdir)
    if plan is None:
        die("no plan.md")
    deps = {n: set(numbers(r.get("depends on"))) for n, r in task_rows(body).items()}

    def reaches(x, y, seen=None):
        seen = seen or set()
        for d in deps.get(x, ()):
            if d == y or (d not in seen and reaches(d, y, seen | {d})):
                return True
        return False

    live = [t for t in task_docs(fdir, body) if t[2] not in ("done", "obsolete")]
    problems = []
    for i, (n, svc, _, paths) in enumerate(live):
        for m, svc2, _, paths2 in live[i + 1:]:
            if svc != svc2 or reaches(n, m) or reaches(m, n):
                continue
            shared = sorted({p for p in paths for q in paths2 if same_place(p, q)})
            if shared:
                problems.append(f"{n:02d} and {m:02d} ({svc}) both name {', '.join(shared)} "
                                "and no depends_on orders them")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print(f"ok: no two tasks that can run at once name the same place ({len(live)} to build)")


def cmd_attribute(fdir, service, files):
    """For each failing file, the tasks of `service` that name it. One task:
    that task's work. None, or several: the plan did not separate it."""
    plan, _, body = read_plan(fdir)
    if plan is None:
        die("no plan.md")
    roots = [p for p in service_paths(fdir.parent.parent, service) if p]
    docs = [t for t in task_docs(fdir, body) if t[1] == service and t[2] != "obsolete"]
    for f in files:
        rel = f
        for root in roots:
            if f.startswith(root.rstrip("/") + "/"):
                rel = f[len(root.rstrip("/")) + 1:]
                break
        owners = [f"{n:02d}" for n, _, _, paths in docs if any(same_place(rel, p) for p in paths)]
        kind = "task" if len(owners) == 1 else ("shared" if owners else "unnamed")
        print(f"{f}\t{kind}\t{','.join(owners) or '-'}")


# ---- contracts: a record of what was built ------------------------------

def workspace(hub):
    """{service: {path, repo_root, contracts: [{kind, path, role}]}} from
    workspace.yaml. Generated format, parsed by line."""
    ws = hub / "workspace.yaml"
    if not ws.is_file():
        die(f"no workspace.yaml in {hub}")
    services, cur, key_indent, in_contracts, item = {}, None, None, False, None
    for line in ws.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        m = re.match(r"(\s*-\s*)name:\s*(\S+)", line)
        if m and (key_indent is None or len(m.group(1)) <= key_indent):
            cur, key_indent, in_contracts = m.group(2), len(m.group(1)), False
            services[cur] = {"path": None, "repo_root": None, "contracts": []}
            continue
        if cur is None:
            continue
        if indent == key_indent:
            in_contracts = bool(re.match(r"\s*contracts:\s*(#.*)?$", line))
            m = re.match(r"\s*(path|repo_root):\s*(\S.*?)\s*(?:#.*)?$", line)
            if m:
                services[cur][m.group(1)] = m.group(2)
            continue
        if in_contracts and indent > key_indent:
            flow = re.match(r"\s*-\s*\{(.*)\}", line)
            if flow:
                item = dict(re.findall(r"(\w+):\s*([^,}]+?)\s*(?=,|$)", flow.group(1)))
                services[cur]["contracts"].append(item)
                continue
            m = re.match(r"\s*(-\s*)?(kind|path|role):\s*(\S.*?)\s*(?:#.*)?$", line)
            if m:
                if m.group(1):
                    item = {}
                    services[cur]["contracts"].append(item)
                if item is not None:
                    item[m.group(2)] = m.group(3).strip("'\"")
    return services


def service_paths(hub, service):
    info = workspace(hub).get(service, {})
    return [info.get("path"), info.get("repo_root")]


def cmd_contracts(fdir):
    """Copy every producer contract of every service the plan modifies into
    artifacts/contracts/<service>/. Run after a clean review: the copy records
    what was built and verified. Disposable - run it again to rebuild it."""
    plan, _, body = read_plan(fdir)
    if plan is None:
        die("no plan.md")
    unfinished = [f"{n:02d} ({s or 'unset'})" for n, p in sorted(tasks(fdir).items())
                  if (s := task_status(p)) not in ("done", "obsolete")]
    if unfinished:
        print(f"refused: not every task is done - {', '.join(unfinished)}")
        sys.exit(1)
    modified = [r.get("service", "") for r in table(body, "Service map")
                if r.get("state", "").strip().lower() == "modify"]
    services = workspace(fdir.parent.parent)
    out = fdir / "artifacts" / "contracts"
    if out.exists():
        shutil.rmtree(out)
    copied = 0
    for svc in modified:
        info = services.get(svc)
        if not info:
            print(f"skip: {svc} is not in workspace.yaml")
            continue
        for c in info["contracts"]:
            if c.get("role") != "producer" or not c.get("path"):
                continue
            src = next((pathlib.Path(r) / c["path"] for r in (info["path"], info["repo_root"])
                        if r and (pathlib.Path(r) / c["path"]).exists()), None)
            if src is None:
                print(f"missing: {svc} {c['path']} - not found under {info['path']}")
                continue
            dst = out / svc / c["path"].rstrip("/")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            copied += 1
            print(f"copied: {svc} {c['path']} ({c.get('kind', '?')})")
    print(f"contracts: {copied} copied into {out.relative_to(fdir)}")


def main():
    cmds = {"seal": cmd_seal, "check": cmd_check, "prune": cmd_prune, "diff": cmd_diff,
            "overlaps": cmd_overlaps, "contracts": cmd_contracts}
    if len(sys.argv) >= 3 and sys.argv[1] == "attribute":
        if len(sys.argv) < 5:
            die("usage: pave-plan.py attribute <feature-dir> <service> <file>...")
        fdir = pathlib.Path(sys.argv[2])
        if not fdir.is_dir():
            die(f"no such feature folder: {fdir}")
        return cmd_attribute(fdir, sys.argv[3], sys.argv[4:])
    if len(sys.argv) != 3 or sys.argv[1] not in cmds:
        die("usage: pave-plan.py <seal|check|prune|diff|overlaps|contracts> <feature-dir>\n"
            "       pave-plan.py attribute <feature-dir> <service> <file>...")
    fdir = pathlib.Path(sys.argv[2])
    if not fdir.is_dir():
        die(f"no such feature folder: {fdir}")
    cmds[sys.argv[1]](fdir)


if __name__ == "__main__":
    main()
