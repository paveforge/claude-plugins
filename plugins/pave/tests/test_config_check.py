import importlib.util
from pathlib import Path

import pytest

TEMPLATE = (Path(__file__).resolve().parents[1] / "templates" / "config.yaml").read_text()

HAVE_TOML = (importlib.util.find_spec("tomllib") or importlib.util.find_spec("tomli")) is not None

# A hub from before 0.4.
PRE_04 = """\
# Pave policy. Shared by the team - commit this file.

# Model capability order, weakest to strongest.
model_ranking: [haiku, sonnet, opus, fable]

agents:
  analyst:  { model: sonnet, effort: medium }   # reads business logic
  builder:  { model: sonnet, effort: medium }   # executes one task document
  explorer: { model: haiku,  effort: low    }   # mechanical repo scanning
  reviewer: { model: sonnet, effort: low    }   # one per task: plan vs code
  advisor:  { model: sonnet, effort: low    }   # answers ad hoc questions

  # Design runs on exactly this model.
  designer: { model: fable, effort: max }       # planning decides the feature

execution:
  mode: parallel                 # parallel | sequential
  monorepo_strategy: sequential  # sequential | worktree | shared-tree
  max_parallel: 4

branch:
  pattern: feature/{feature-slug}

contracts:
  land_before_fanout: true       # generate and commit stubs before agents spawn
"""

# The template's config, in TOML, with one leftover, one missing agent and one
# value of the wrong kind.
TOML = """\
model_ranking = ["haiku", "sonnet"]

[agents]
analyst = { model = "sonnet", effort = "medium" }
builder = { model = "sonnet", effort = "medium" }
explorer = { model = "haiku", effort = "low" }
reviewer = { model = "sonnet", effort = "low" }
retriever = { model = "sonnet", effort = "low" }

[execution]
mode = "parallel"
monorepo_strategy = "sequential"
max_parallel = "four"

[branch]
pattern = "feature/{feature-id}"

[contracts]
land_contracts = true
"""


def check(hub, name, text):
    (hub.path / name).write_text(text)
    r = hub.run("config-check")
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()[1:]


def test_current_config_is_clean(hub):
    assert check(hub, "config.yaml", TEMPLATE) == ["result: nothing to fix"]


def test_pre_04_config(hub):
    out = check(hub, "config.yaml", PRE_04)
    assert out == [
        "leftover  model_ranking = [haiku, sonnet, opus, fable]",
        "leftover  agents.advisor = { model: sonnet, effort: low }",
        "leftover  agents.designer = { model: fable, effort: max }",
        "missing   agents.retriever (template: { model: sonnet, effort: low })",
        "missing   agents.planner (template: { model: opus, effort: high })",
        "leftover  contracts.land_before_fanout = true",
        "missing   contracts.land_contracts (template: true)",
        "result: 7 to fix - run /pave:init",
    ]


def test_check_changes_nothing(hub):
    check(hub, "config.yaml", PRE_04)
    assert (hub.path / "config.yaml").read_text() == PRE_04


@pytest.mark.skipif(not HAVE_TOML, reason="needs tomllib or tomli")
def test_toml_config(hub):
    out = check(hub, "config.toml", TOML)
    assert out == [
        "leftover  model_ranking = [haiku, sonnet]",
        "missing   agents.planner (template: { model: opus, effort: high })",
        "invalid   execution.max_parallel = four (template has a number: 4)",
        "result: 3 to fix - run /pave:init",
    ]


def test_agent_entry_of_the_wrong_kind(hub):
    out = check(hub, "config.yaml", TEMPLATE.replace(
        "builder:   { model: sonnet, effort: medium }", "builder:   opus"))
    assert "invalid   agents.builder = opus (template has a mapping: { model: sonnet, effort: medium })" in out


def test_no_config_is_error(hub):
    r = hub.run("config-check")
    assert r.returncode != 0
    assert "/pave:init" in r.stderr


def test_unparseable_config_is_error(hub):
    (hub.path / "config.yaml").write_text("agents:\n  builder: { model: [x }\n")
    r = hub.run("config-check")
    assert r.returncode != 0
