#!/usr/bin/env python3
"""Report what each registered service needs: discovery, analysis, or nothing,
which on-demand source findings no longer match the code they read, and which
feature records no longer match their feature's spec.

Reports. Decides nothing - /pave:analyse and /pave:query read this and choose.

Staleness is path-scoped, not time-based: a service is stale only when the
source directories its analysis rested on have changed. A month of commits to
CI config invalidates nothing.

Usage: pave-stale.py <hub> [service]
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

STATES = ["unreachable", "undiscovered", "missing", "stale", "orphan", "current",
          "finding-stale", "finding-current", "record-stale", "record-current"]
FINDING_SERVICE = re.compile(
    r"^\s*-\s*\{\s*service:\s*([^,\s]+)\s*,\s*commit:\s*([0-9a-fA-F]+)\s*,\s*paths:\s*\[(.*?)\]\s*\}", re.M)


def read_workspace(ws):
    """name -> {path, discovered}. Generated format, parsed by line."""
    services, cur = {}, None
    for line in ws.read_text().splitlines():
        m = re.match(r"\s*-\s*name:\s*(\S+)", line)
        if m:
            cur = m.group(1)
            services[cur] = {"path": None, "discovered": False}
            continue
        if cur:
            m = re.match(r"\s+path:\s*(\S.*?)\s*$", line)
            if m:
                services[cur]["path"] = m.group(1)
            if re.match(r"\s+language:\s*\S", line):
                services[cur]["discovered"] = True
    return services


def frontmatter(readme):
    """(commit, source_paths) from a knowledge README, or None if unusable."""
    text = readme.read_text()
    if not text.startswith("---"):
        return None
    fm = text.split("---", 2)[1]
    commit = re.search(r"^commit:\s*(\S+)", fm, re.M)
    inline = re.search(r"^source_paths:\s*\[(.*?)\]", fm, re.M | re.S)
    if inline:
        paths = [s.strip().strip("'\"") for s in inline.group(1).split(",") if s.strip()]
    else:
        block = re.search(r"^source_paths:\s*$((?:\n\s+-\s*.*)+)", fm, re.M)
        paths = ([l.split("-", 1)[1].strip().strip("'\"")
                  for l in block.group(1).strip().splitlines()] if block else [])
    if not commit or not paths:
        return None
    return commit.group(1), paths


def changed_since(repo, commit, paths):
    """Changed files under paths since commit, or None if the commit is gone."""
    r = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{commit}..HEAD", "--", *paths],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    return [l for l in r.stdout.splitlines() if l.strip()]


def classify_finding(f, services):
    """A source finding is current only while every service it read is unchanged
    under the paths it read."""
    text = f.read_text()
    fm = text.split("---", 2)[1] if text.startswith("---") else ""
    reads = FINDING_SERVICE.findall(fm)
    read = [svc for svc, _, _ in reads]
    if not reads:
        return "finding-stale", "no services recorded - cannot prove it is current", read
    for svc, commit, raw in reads:
        info = services.get(svc)
        if not info or not info["path"] or not Path(info["path"]).is_dir():
            return "finding-stale", f"{svc} is not reachable", read
        paths = [s.strip().strip("'\"") for s in raw.split(",") if s.strip()]
        changed = changed_since(info["path"], commit, paths or ["."])
        if changed is None:
            return "finding-stale", f"{svc}: cannot diff from {commit[:7]}", read
        if changed:
            return "finding-stale", f"{svc}: {len(changed)} file(s) changed under {', '.join(paths)}", read
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
    fm = frontmatter(readme)
    if not fm:
        return "missing", "knowledge README has no usable commit/source_paths"

    commit, paths = fm
    changed = changed_since(path, commit, paths)
    if changed is None:
        # The recorded commit is unreachable - rebased, squashed, or pruned.
        # Treat as missing rather than current: we cannot prove it is still valid.
        return "missing", f"cannot diff from {commit[:7]} - history rewritten or commit gone"

    if changed:
        return "stale", f"{len(changed)} file(s) changed under {', '.join(paths)}"
    return "current", f"unchanged since {commit[:7]}"


def main():
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
