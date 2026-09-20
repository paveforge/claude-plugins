#!/usr/bin/env python3
"""Report what each registered service needs: discovery, analysis, or nothing.

Reports. Decides nothing - /pave:analyse reads this and chooses what to spawn.

Staleness is path-scoped, not time-based: a service is stale only when the
source directories its analysis rested on have changed. A month of commits to
CI config invalidates nothing.

Usage: pave-stale.py <hub> [service]
"""
import re
import subprocess
import sys
from pathlib import Path

STATES = ["unreachable", "undiscovered", "missing", "stale", "orphan", "current"]


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
    r = subprocess.run(
        ["git", "-C", str(path), "diff", "--name-only", f"{commit}..HEAD", "--", *paths],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        # The recorded commit is unreachable - rebased, squashed, or pruned.
        # Treat as missing rather than current: we cannot prove it is still valid.
        return "missing", f"cannot diff from {commit[:7]} - history rewritten or commit gone"

    changed = [l for l in r.stdout.splitlines() if l.strip()]
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

    if not rows:
        print(f"no service named {only}" if only
              else "no services registered. Run /pave:add <folder> first.")
        return

    for state in STATES:
        for s, n, note in rows:
            if s == state:
                print(f"{s:<13}{n:<28}{note}")
    print()
    print("  ".join(f"{counts[s]} {s}" for s in STATES if s in counts))


if __name__ == "__main__":
    main()
