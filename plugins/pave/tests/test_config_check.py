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

# The template's config, in TOML, with one leftover and one missing agent.
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
max_parallel = 4

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


def fix(hub, mode):
    r = hub.run("config-fix", mode)
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
        "missing   agents.retriever = { model: sonnet, effort: low }",
        "missing   agents.planner = { model: opus, effort: high }",
        "leftover  contracts.land_before_fanout = true",
        "missing   contracts.land_contracts = true",
        "result: 7 to fix - run /pave:init",
    ]


def test_check_changes_nothing(hub):
    check(hub, "config.yaml", PRE_04)
    assert (hub.path / "config.yaml").read_text() == PRE_04


def test_fix_all(hub):
    check(hub, "config.yaml", PRE_04)
    out = fix(hub, "all")
    assert "removed   agents.designer = { model: fable, effort: max }" in out
    assert "added     agents.planner = { model: opus, effort: high }" in out
    assert out[-1] == "result: nothing to fix"
    text = (hub.path / "config.yaml").read_text()
    assert text.startswith("# Pave policy. Shared by the team - commit this file.\n\nagents:\n")
    assert "model_ranking" not in text and "Model capability order" not in text
    assert "  planner: { model: opus, effort: high }\n" in text
    assert "  pattern: feature/{feature-slug}\n" in text  # values are kept as they are
    assert check(hub, "config.yaml", text) == ["result: nothing to fix"]
    assert hub.run("agent", "planner").stdout == "model=opus\neffort=high\n"


def test_fix_add_keeps_leftovers(hub):
    check(hub, "config.yaml", PRE_04)
    out = fix(hub, "add")
    assert [x.split()[0] for x in out] == ["added", "added", "added", "result:"]
    assert out[-1] == "result: 4 left - run /pave:init"
    text = (hub.path / "config.yaml").read_text()
    assert "designer: { model: fable, effort: max }" in text
    assert "planner: { model: opus, effort: high }" in text


def test_fix_remove_keeps_missing(hub):
    check(hub, "config.yaml", PRE_04)
    out = fix(hub, "remove")
    assert [x.split()[0] for x in out] == ["removed"] * 4 + ["result:"]
    assert out[-1] == "result: 3 left - run /pave:init"
    assert "no entry for agents.planner" in hub.run("agent", "planner").stderr


def test_fix_nothing_to_change(hub):
    check(hub, "config.yaml", TEMPLATE)
    assert fix(hub, "all") == ["result: nothing to change"]
    assert (hub.path / "config.yaml").read_text() == TEMPLATE


def test_fix_keeps_nested_leftovers_readable(hub):
    check(hub, "config.yaml", TEMPLATE + "phases:\n  design:\n    model: opus\n    effort: high\n")
    fix(hub, "add")
    assert "phases:\n  design:\n    model: opus\n    effort: high\n" in (hub.path / "config.yaml").read_text()
    assert check(hub, "config.yaml", (hub.path / "config.yaml").read_text())[0] == \
        "leftover  phases = { design: { model: opus, effort: high } }"


def test_fix_bad_option(hub):
    check(hub, "config.yaml", PRE_04)
    r = hub.run("config-fix", "everything")
    assert r.returncode != 0
    assert "usage" in r.stderr
    assert (hub.path / "config.yaml").read_text() == PRE_04


@pytest.mark.skipif(not HAVE_TOML, reason="needs tomllib or tomli")
def test_toml_config(hub):
    out = check(hub, "config.toml", TOML)
    assert out == [
        "leftover  model_ranking = [haiku, sonnet]",
        "missing   agents.planner = { model: opus, effort: high }",
        "result: 2 to fix - run /pave:init",
    ]


@pytest.mark.skipif(not HAVE_TOML, reason="needs tomllib or tomli")
def test_toml_fix_all(hub):
    check(hub, "config.toml", "# Team policy\n" + TOML)
    out = fix(hub, "all")
    assert out[-1] == "result: nothing to fix"
    text = (hub.path / "config.toml").read_text()
    assert text.startswith("# Team policy\n\n[agents]\n")
    assert 'planner = { model = "opus", effort = "high" }\n' in text
    assert "model_ranking" not in text
    assert check(hub, "config.toml", text) == ["result: nothing to fix"]
    assert hub.run("agent", "planner").stdout == "model=opus\neffort=high\n"


def test_no_config_is_error(hub):
    for args in (["config-check"], ["config-fix", "all"]):
        r = hub.run(*args)
        assert r.returncode != 0
        assert "/pave:init" in r.stderr


def test_unparseable_config_is_error(hub):
    (hub.path / "config.yaml").write_text("agents:\n  builder: { model: [x }\n")
    r = hub.run("config-check")
    assert r.returncode != 0
