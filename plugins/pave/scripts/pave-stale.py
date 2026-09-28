#!/usr/bin/env python3
"""Report what each registered service needs: discovery, analysis, or nothing,
which on-demand source findings no longer match the code they read, and which
feature records no longer match their feature's spec.

Reports. Decides nothing - /pave:analyse and /pave:query read this and choose.

Staleness is path-scoped, not time-based: a service is stale only when the
content of the source directories its analysis rested on has changed. A month
of changes to CI config invalidates nothing. It is decided from the files
alone, never from a version control system: a repo may use git, another VCS
or none.

--stamp records the hash of those directories in a knowledge file once an
analyst has written it: `source_hash` in a service README, `hash` on each
line of a source finding's `services:`.

Usage: pave-stale.py <hub> [service]
       pave-stale.py --stamp <hub> <knowledge file>
"""
import hashlib
import os
import re
import sys
from pathlib import Path

STATES = ["unreachable", "undiscovered", "missing", "stale", "orphan", "current",
          "finding-stale", "finding-current", "record-stale", "record-current"]
# One line of a finding's services: `- { service: s, paths: [a, b], hash: h }`.
# hash is absent until --stamp writes it.
FINDING_SERVICE = re.compile(
    r"^([ \t]*-[ \t]*)\{[ \t]*service:[ \t]*([^,\s}]+)[ \t]*,[ \t]*paths:[ \t]*\[([^\]\n]*)\]"
    r"(?:[ \t]*,[ \t]*hash:[ \t]*([0-9a-f]*))?[ \t]*\}[ \t]*$", re.M)
HASH = re.compile(r"^[0-9a-f]{64}$")

# Never part of what an analysis read: version control metadata, and
# dependency and cache directories that tools rewrite on every run.
SKIP_DIRS = {".git", ".hg", ".svn", ".bzr", ".jj", "_darcs", "CVS",
             "node_modules", "__pycache__", ".venv", ".tox", ".pytest_cache",
             ".mypy_cache", ".ruff_cache", ".gradle", ".terraform", ".next"}
SKIP_FILES = {".DS_Store"}


def read_workspace(ws):
    """name -> {path, discovered}. Generated format, parsed by line.

    Only a service's own keys count: those indented exactly as its `name`.
    Deeper lines belong to nested lists - a contract has a `path:` of its
    own, relative to the repo, and must never be taken for the service's."""
    services, cur, indent = {}, None, None
    for line in ws.read_text().splitlines():
        m = re.match(r"(\s*-\s*)name:\s*(\S+)", line)
        if m and (indent is None or len(m.group(1)) <= indent):
            cur, indent = m.group(2), len(m.group(1))
            services[cur] = {"path": None, "discovered": False}
            continue
        if not cur or not line.strip() or line.lstrip().startswith("#"):
            continue
        if len(line) - len(line.lstrip()) != indent:
            continue
        m = re.match(r"\s*path:\s*(\S.*?)\s*(?:#.*)?$", line)
        if m:
            services[cur]["path"] = m.group(1)
        if re.match(r"\s*language:\s*[^\s#]", line):
            services[cur]["discovered"] = True
    return services


def split_paths(raw):
    return [p.strip().strip("'\"") for p in raw.split(",") if p.strip()]


def frontmatter(text):
    """The frontmatter block of a knowledge file, or None."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 else None


def readme_fields(text):
    """(source_paths, source_hash) from a service README's frontmatter."""
    fm = frontmatter(text) or ""
    inline = re.search(r"^source_paths:\s*\[(.*?)\]", fm, re.M | re.S)
    if inline:
        paths = split_paths(inline.group(1))
    else:
        block = re.search(r"^source_paths:\s*$((?:\n\s+-\s*.*)+)", fm, re.M)
        paths = ([l.split("-", 1)[1].strip().strip("'\"")
                  for l in block.group(1).strip().splitlines()] if block else [])
    recorded = re.search(r"^source_hash:\s*([0-9a-f]{64})\s*$", fm, re.M)
    return paths, recorded.group(1) if recorded else None


def source_hash(root, paths):
    """sha256 over the content of every file under paths, relative to root.

    Each file contributes its path and the sha256 of its bytes, in sorted
    order, so adding, removing, renaming or editing any file changes the
    hash. A path that does not exist contributes its name and "missing"."""
    root = Path(root)
    h = hashlib.sha256()
    for rel in sorted(set(paths or ["."])):
        top = root / rel
        if not top.exists() and not top.is_symlink():
            h.update(f"{rel}\0missing\n".encode())
            continue
        files = [top] if not top.is_dir() or top.is_symlink() else []
        if not files:
            for d, dirs, names in os.walk(top):
                dirs[:] = [n for n in dirs if n not in SKIP_DIRS]
                files += [Path(d, n) for n in names if n not in SKIP_FILES]
                # A symlinked directory is recorded as a link, never followed.
                files += [Path(d, n) for n in dirs if Path(d, n).is_symlink()]
        for name, f in sorted((Path(os.path.relpath(f, root)).as_posix(), f) for f in files):
            if f.is_symlink():
                digest = "link:" + os.readlink(f)
            else:
                try:
                    digest = hashlib.sha256(f.read_bytes()).hexdigest()
                except OSError:
                    digest = "unreadable"
            h.update(f"{name}\0{digest}\n".encode())
    return h.hexdigest()


def classify_finding(f, services):
    """A source finding is current only while every service it read is unchanged
    under the paths it read."""
    reads = FINDING_SERVICE.findall(frontmatter(f.read_text()) or "")
    read = [svc for _, svc, _, _ in reads]
    if not reads:
        return "finding-stale", "no services recorded - cannot prove it is current", read
    for _, svc, raw, recorded in reads:
        info = services.get(svc)
        if not info or not info["path"] or not Path(info["path"]).is_dir():
            return "finding-stale", f"{svc} is not reachable", read
        if not HASH.match(recorded or ""):
            return "finding-stale", f"{svc}: no content hash recorded - cannot prove it is current", read
        paths = split_paths(raw)
        if source_hash(info["path"], paths) != recorded:
            return "finding-stale", f"{svc}: files changed under {', '.join(paths or ['.'])}", read
    return "finding-current", f"unchanged in {', '.join(read)}", read


def classify_record(f, hub):
    """A feature record is current only while its feature's spec.md is the one
    it was recorded against - the same sha256 plan.md's spec_hash uses."""
    text = f.read_text()
    fm = text.split("---", 2)[1] if text.startswith("---") else ""
    feature = re.search(r"^feature:\s*([^#\s]+)", fm, re.M)
    recorded = re.search(r"^spec_hash:\s*([0-9a-f]{64})", fm, re.M)
    if not feature or not recorded:
        return "record-stale", "no feature or spec_hash recorded - cannot prove it is current"
    spec = hub / "features" / feature.group(1) / "spec.md"
    if not spec.is_file():
        return "record-stale", f"features/{feature.group(1)}/spec.md no longer exists"
    if hashlib.sha256(spec.read_text().encode()).hexdigest() != recorded.group(1):
        return "record-stale", f"features/{feature.group(1)}/spec.md changed since it was recorded"
    return "record-current", f"matches features/{feature.group(1)}/spec.md"


def classify(name, info, kdir):
    path = Path(info["path"]) if info["path"] else None
    if not path or not path.is_dir():
        return "unreachable", f"{info['path']} is not a directory"
    if not info["discovered"]:
        return "undiscovered", "no language in workspace.yaml"

    readme = kdir / name / "README.md"
    if not readme.exists():
        return "missing", "no knowledge folder"
    paths, recorded = readme_fields(readme.read_text())
    if not paths or not recorded:
        # Never stamped: the analysis did not finish, or predates content
        # hashes. Nothing proves it is still valid.
        return "missing", "knowledge README has no usable source_paths/source_hash"

    if source_hash(path, paths) != recorded:
        return "stale", f"files changed under {', '.join(paths)}"
    return "current", f"unchanged since {recorded[:7]}"


def stamp(hub, target):
    """Record the current source hash in one knowledge file. Writes nothing
    unless every service it names can be hashed."""
    hub, target = Path(hub).resolve(), Path(target)
    # A relative path that is not there from here is taken from the hub, so
    # the skills' hub-relative paths work from any folder.
    if not target.is_absolute() and not target.exists():
        target = hub / target
    target = target.resolve()
    if not target.is_file():
        sys.exit(f"error: no such file: {target}")
    services = read_workspace(hub / "workspace.yaml")

    def root_of(svc):
        info = services.get(svc)
        if not info or not info["path"] or not Path(info["path"]).is_dir():
            sys.exit(f"error: {svc} is not a reachable service in workspace.yaml - nothing stamped")
        return info["path"]

    text = target.read_text()
    fm = frontmatter(text)
    if fm is None:
        sys.exit(f"error: {target} has no frontmatter")
    kdir = hub / "artifacts" / "knowledge" / "services"

    if target.name == "README.md" and target.parent.parent == kdir:
        svc = target.parent.name
        paths, _ = readme_fields(text)
        if not paths:
            sys.exit(f"error: {target} has no source_paths - nothing stamped")
        h = source_hash(root_of(svc), paths)
        if re.search(r"^source_hash:.*$", fm, re.M):
            new_fm = re.sub(r"^source_hash:.*$", f"source_hash: {h}", fm, count=1, flags=re.M)
        else:
            # Right after source_paths, inline or block form.
            m = re.search(r"^source_paths:[ \t]*(?:\[[^\]]*\][^\n]*\n|\n(?:[ \t]+-[^\n]*\n)*)",
                          fm, re.M)
            new_fm = fm[:m.end()] + f"source_hash: {h}\n" + fm[m.end():]
        print(f"stamped: {svc} {h[:7]} ({', '.join(paths)})")
    else:
        reads = FINDING_SERVICE.findall(fm)
        if not reads:
            sys.exit(f"error: {target} records no `- {{ service: ..., paths: [...] }}` line - nothing stamped")
        hashes = {}
        for _, svc, raw, _ in reads:
            hashes[(svc, raw)] = source_hash(root_of(svc), split_paths(raw))

        def line(m):
            svc, raw = m.group(2), m.group(3)
            return f"{m.group(1)}{{ service: {svc}, paths: [{raw.strip()}], hash: {hashes[(svc, raw)]} }}"
        new_fm = FINDING_SERVICE.sub(line, fm)
        for (svc, raw), h in hashes.items():
            print(f"stamped: {svc} {h[:7]} ({', '.join(split_paths(raw)) or '.'})")

    target.write_text("---" + new_fm + "---" + text.split("---", 2)[2])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stamp":
        if len(sys.argv) != 4:
            sys.exit("usage: pave-stale.py --stamp <hub> <knowledge file>")
        stamp(sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) < 2:
        sys.exit("usage: pave-stale.py <hub> [service]")
    hub = Path(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 else None

    ws = hub / "workspace.yaml"
    if not ws.exists():
        sys.exit("error: no workspace.yaml. Run /pave:init first.")
    kdir = hub / "artifacts" / "knowledge" / "services"

    services = read_workspace(ws)
    rows, counts = [], {}

    def add(state, name, note):
        rows.append((state, name, note))
        counts[state] = counts.get(state, 0) + 1

    for name, info in services.items():
        if only and name != only:
            continue
        state, note = classify(name, info, kdir)
        add(state, name, note)

    # Knowledge for a service nobody registered any more. Design would happily
    # plan against a service that cannot be built.
    if kdir.is_dir() and not only:
        for d in sorted(kdir.iterdir()):
            if d.is_dir() and d.name not in services:
                add("orphan", d.name, "knowledge folder, no such service in workspace.yaml")

    fdir = hub / "artifacts" / "knowledge" / "on-demand" / "source"
    if fdir.is_dir():
        for f in sorted(fdir.glob("*.md")):
            state, note, read = classify_finding(f, services)
            if only and only not in read:
                continue
            add(state, f"on-demand/source/{f.name}", note)

    rdir = hub / "artifacts" / "knowledge" / "on-demand" / "features"
    if rdir.is_dir() and not only:
        for f in sorted(rdir.glob("*.md")):
            state, note = classify_record(f, hub)
            add(state, f"on-demand/features/{f.name}", note)

    if not rows:
        print(f"no service named {only}" if only
              else "no services registered. Run /pave:add <folder> first.")
        return

    for state in STATES:
        for s, n, note in rows:
            if s == state:
                print(f"{s:<16}{n:<40}{note}")
    print()
    print("  ".join(f"{counts[s]} {s}" for s in STATES if s in counts))


if __name__ == "__main__":
    main()
