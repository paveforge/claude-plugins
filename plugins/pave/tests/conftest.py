import hashlib
import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PAVE_SH = SCRIPTS / "pave.sh"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.com"},
    )


def git_init(repo):
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    return repo


def commit_all(repo, message="commit"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message, "--allow-empty")
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


class Hub:
    def __init__(self, path):
        self.path = path

    def run(self, *args, env=None, cwd=None):
        full_env = {**os.environ, "PAVE_HUB": str(self.path)}
        if env:
            full_env.update(env)
        return subprocess.run(
            [str(PAVE_SH), *args],
            capture_output=True, text=True,
            env=full_env, cwd=str(cwd or self.path),
        )

    def feature_dir(self, feature_id):
        return self.path / "features" / feature_id


@pytest.fixture(params=["plain", "git"])
def vcs(request):
    """Every test that uses it runs twice: on plain folders, and on git repos.
    Pave must behave the same either way."""
    return request.param


def make_repo(path, vcs):
    """A folder for a hub or a service: a git repository only when vcs is "git"."""
    path.mkdir(parents=True, exist_ok=True)
    if vcs == "git":
        git_init(path)
    return path


def snapshot(repo, vcs, message="commit"):
    """Commit everything when the repo is under git; nothing to do otherwise."""
    if vcs == "git":
        commit_all(repo, message)


@pytest.fixture
def hub(tmp_path, vcs):
    h = make_repo(tmp_path / "hub", vcs)
    (h / ".pave-hub").write_text("")
    (h / "workspace.yaml").write_text("services:\n")
    (h / "features").mkdir()
    snapshot(h, vcs, "init hub")
    return Hub(h)


SPEC_TEMPLATE = """---
feature: {feature_id}
version: 1
---

# {title}

## Why
Test feature.

## What
Does a thing.

## Acceptance criteria

- **AC-1** it works

## Guardrails

- none

## Out of scope
Nothing else.

## Open questions

- None.
"""

TASK_TEMPLATE = """---
service: {service}
feature: {feature_id}
priority: low
status: pending
depends_on: []
satisfies: [AC-1]
derives_from:
  - plan.md#approach
---

# {title}

## Objective & Context
**Goal:** do the thing.

## Tasks

- [ ] Do the thing.

## Build notes
"""

PLAN_TEMPLATE = """---
feature: {feature_id}
spec_version: 1
next_task: {next_task}
---

# {title} - Plan

## Approach
Do the thing.

## Tasks

| # | Task | Service | Priority | Size | Satisfies | Depends on | Reverts | Change |
|---|---|---|---|---|---|---|---|---|
{rows}"""

PLAN_ROW = "| {n:02d} | Task {n} | svc | low | S | AC-1 | - | - | new |\n"


def make_feature(hub_path, feature_id, title="Test Feature", n_tasks=1):
    fdir = hub_path / "features" / feature_id
    (fdir / "tasks").mkdir(parents=True, exist_ok=True)
    (fdir / "contracts").mkdir(parents=True, exist_ok=True)
    (fdir / "artifacts").mkdir(parents=True, exist_ok=True)
    (fdir / "spec.md").write_text(SPEC_TEMPLATE.format(feature_id=feature_id, title=title))
    rows = "".join(PLAN_ROW.format(n=i) for i in range(1, n_tasks + 1))
    (fdir / "plan.md").write_text(
        PLAN_TEMPLATE.format(feature_id=feature_id, title=title, next_task=n_tasks + 1, rows=rows)
    )
    for i in range(1, n_tasks + 1):
        (fdir / "tasks" / f"{i:02d}-task.md").write_text(
            TASK_TEMPLATE.format(service="svc", feature_id=feature_id, title=f"Task {i}")
        )
    return fdir
