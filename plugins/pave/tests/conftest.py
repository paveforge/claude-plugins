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


@pytest.fixture
def hub(tmp_path):
    h = tmp_path / "hub"
    h.mkdir()
    (h / ".pave-hub").write_text("")
    (h / "workspace.yaml").write_text("services:\n")
    (h / "features").mkdir()
    git_init(h)
    commit_all(h, "init hub")
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
kind: {kind}
priority: low
status: pending
depends_on: []
reverts: {reverts}
satisfies: [AC-1]
branch: feature/{feature_id}
derives_from:
  - plan.md#approach
commit:
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

| # | Task | Service | Kind | Priority | Size | Satisfies | Depends on | Change |
|---|---|---|---|---|---|---|---|---|
| 01 | Do the thing | svc | build | low | S | AC-1 | - | new |
"""


def make_feature(hub_path, feature_id, title="Test Feature", n_tasks=1, reverts_map=None):
    fdir = hub_path / "features" / feature_id
    (fdir / "tasks").mkdir(parents=True, exist_ok=True)
    (fdir / "contracts").mkdir(parents=True, exist_ok=True)
    (fdir / "artifacts").mkdir(parents=True, exist_ok=True)
    (fdir / "spec.md").write_text(SPEC_TEMPLATE.format(feature_id=feature_id, title=title))
    (fdir / "plan.md").write_text(PLAN_TEMPLATE.format(feature_id=feature_id, title=title, next_task=n_tasks + 1))
    reverts_map = reverts_map or {}
    for i in range(1, n_tasks + 1):
        reverts = reverts_map.get(i, [])
        (fdir / "tasks" / f"{i:02d}-task.md").write_text(
            TASK_TEMPLATE.format(service="svc", feature_id=feature_id, kind="build",
                                  title=f"Task {i}", reverts=reverts)
        )
    return fdir
