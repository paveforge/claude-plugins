import importlib.util
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "config.yaml"

HAVE_TOML = (importlib.util.find_spec("tomllib") or importlib.util.find_spec("tomli")) is not None
needs_toml = pytest.mark.skipif(not HAVE_TOML, reason="needs tomllib or tomli")

# A hub from before 0.4: model_ranking, designer, advisor, the old contracts key.
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

TOML = """\
# Team policy
model_ranking = ["haiku", "sonnet", "opus", "fable"]

[agents]
analyst = { model = "sonnet", effort = "medium" }  # reads business logic
builder = { model = "sonnet", effort = "medium" }
designer = { model = "fable", effort = "max" }

[execution]
mode = "paralell"   # parallel | sequential
max_parallel = 4

[contracts]
land_contracts = true
"""


def write(hub, name, text):
    (hub.path / name).write_text(text)
    return hub.path / name


def lines(r, kind):
    return [x for x in r.stdout.splitlines() if x.startswith(kind)]


def test_template_is_clean(hub):
    write(hub, "config.yaml", TEMPLATE.read_text())
    r = hub.run("config-check")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == "result: nothing to fix"
    assert len(r.stdout.splitlines()) == 2


def test_template_agents_match_pave_defaults(hub):
    for line in TEMPLATE.read_text().splitlines():
        m = re.match(r"\s+(\w+):\s*\{ model: (\w+),\s*effort: (\w+)", line)
        if m:
            r = hub.run("agent", m.group(1))
            assert f"model={m.group(2)}" in r.stdout
            assert f"effort={m.group(3)}" in r.stdout


def test_current_config_clean_and_no_drift(hub):
    write(hub, "config.yaml", TEMPLATE.read_text())
    r = hub.run("agent", "planner")
    assert "source=config" in r.stdout
    assert "drift=" not in r.stdout


def test_no_config(hub):
    r = hub.run("config-check")
    assert r.returncode == 0
    assert "no config file" in r.stdout
    assert "drift=no config file" in hub.run("agent", "builder").stdout


def test_pre_04_reports(hub):
    write(hub, "config.yaml", PRE_04)
    r = hub.run("config-check")
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "leftover  model_ranking: no longer used" in out
    assert "leftover  agents.designer: renamed - becomes agents.planner" in out
    assert "leftover  agents.advisor: renamed - becomes agents.retriever" in out
    assert "leftover  contracts.land_before_fanout: renamed - becomes contracts.land_contracts" in out
    assert "invalid   branch.pattern: is feature/{feature-slug}" in out
    # designer and advisor supply planner and retriever: nothing reported missing
    assert not lines(r, "missing")
    assert out.splitlines()[-1].startswith("result: 5 to fix")


def test_pre_04_agent_reports_drift(hub):
    write(hub, "config.yaml", PRE_04)
    r = hub.run("agent", "planner")
    assert "model=opus" in r.stdout
    assert "source=default" in r.stdout
    assert "drift=5 config fixes pending - run /pave:init" in r.stdout


def test_check_changes_nothing(hub):
    f = write(hub, "config.yaml", PRE_04)
    hub.run("config-check")
    assert f.read_text() == PRE_04


def test_pre_04_fix_keeps_comments_and_format(hub):
    f = write(hub, "config.yaml", PRE_04)
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == "result: nothing to fix"
    assert len(lines(r, "fixed")) == 5
    after = f.read_text()
    expected = (PRE_04
                .replace("# Model capability order, weakest to strongest.\nmodel_ranking: [haiku, sonnet, opus, fable]\n",
                         "# Model capability order, weakest to strongest.\n")
                .replace("  advisor:  { model: sonnet, effort: low    }",
                         "  retriever: { model: sonnet, effort: low    }")
                .replace("  designer: { model: fable, effort: max }       #",
                         "  planner: { model: fable, effort: max }        #")
                .replace("feature/{feature-slug}", "feature/{feature-id}")
                .replace("  land_before_fanout: true       #",
                         "  land_contracts: true           #"))
    assert after == expected
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"
    r = hub.run("agent", "planner")
    assert "model=fable" in r.stdout and "effort=max" in r.stdout
    assert "source=config" in r.stdout and "drift=" not in r.stdout


def test_missing_agents_added_aligned(hub):
    f = write(hub, "config.yaml",
              "agents:\n"
              "  analyst:   { model: sonnet, effort: medium }   # reads\n"
              "  builder:   { model: sonnet, effort: medium }\n"
              "\n"
              "execution:\n"
              "  mode: parallel\n")
    r = hub.run("config-check")
    missing = lines(r, "missing")
    assert [m.split(":")[0].split()[-1] for m in missing] == [
        "agents.explorer", "agents.reviewer", "agents.retriever", "agents.planner"]
    assert "add  planner: { model: opus, effort: high }" in r.stdout
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    text = f.read_text()
    assert "  planner:   { model: opus, effort: high }\n\nexecution:" in text
    assert "  analyst:   { model: sonnet, effort: medium }   # reads\n" in text
    assert "source=config" in hub.run("agent", "retriever").stdout


def test_block_style_and_phases(hub):
    f = write(hub, "config.yaml",
              "hub:\n"
              "  name: platform\n"
              "phases:\n"
              "  design:\n"
              "    model: fable\n"
              "    effort: max        # planning decides\n"
              "  build:\n"
              "    model: sonnet\n"
              "agents:\n"
              "  explorer:\n"
              "    model: haiku\n"
              "    effort: low\n"
              "  analyst:\n"
              "    model: sonnet\n"
              "    effort: medium\n")
    r = hub.run("config-check")
    assert "leftover  hub: no longer used" in r.stdout
    assert "phases.design → agents.planner" in r.stdout
    assert "add it with phases.design's value" in r.stdout
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    text = f.read_text()
    assert "phases" not in text and "hub:" not in text
    assert "  planner:\n    model: fable\n    effort: max\n" in text
    r = hub.run("agent", "planner")
    assert "model=fable" in r.stdout and "effort=max" in r.stdout
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"


def test_no_agents_section(hub):
    f = write(hub, "config.yaml", "execution:\n  mode: parallel\n")
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    assert f.read_text().startswith("execution:\n  mode: parallel\n\nagents:\n  analyst: { model: sonnet")
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"


def test_designer_and_planner_both_set(hub):
    f = write(hub, "config.yaml", TEMPLATE.read_text().replace(
        "  planner:", "  designer: { model: fable, effort: max }\n  planner:"))
    r = hub.run("config-check")
    assert "agents.designer: no longer read, and agents.planner is set - remove it" in r.stdout
    hub.run("config-check", "--fix")
    assert "designer" not in f.read_text()
    assert "model=opus" in hub.run("agent", "planner").stdout


def test_invalid_values(hub):
    f = write(hub, "config.yaml",
              TEMPLATE.read_text()
              .replace("mode: parallel ", "mode: fast     ")
              .replace("max_parallel: 4", "max_parallel: 0")
              .replace("land_contracts: true ", "land_contracts: maybe")
              .replace("builder:   { model: sonnet, effort: medium }",
                       "builder:   { model: sonnet, effort: medium, color: red }"))
    r = hub.run("config-check")
    assert "invalid   execution.mode: is fast, must be parallel or sequential - set to parallel" in r.stdout
    assert "invalid   execution.max_parallel: is 0" in r.stdout
    assert "invalid   contracts.land_contracts: is maybe, must be true or false - set to true" in r.stdout
    assert "leftover  agents.builder.color: Pave does not read it" in r.stdout
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    text = f.read_text()
    assert "  mode: parallel                 # parallel | sequential" in text
    assert "builder:   { model: sonnet, effort: medium }" in text
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"


def test_agent_entry_not_a_mapping(hub):
    write(hub, "config.yaml", TEMPLATE.read_text().replace(
        "builder:   { model: sonnet, effort: medium }", "builder:   opus"))
    r = hub.run("config-check")
    assert "invalid   agents.builder: is opus, must be a model and an effort" in r.stdout
    hub.run("config-check", "--fix")
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"


@needs_toml
def test_fix_it_cannot_make_is_left_by_hand(hub):
    # agents written as one inline table cannot be edited line by line
    text = 'agents = { builder = { model = "sonnet", effort = "medium" } }\n'
    f = write(hub, "config.toml", text)
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    assert f.read_text() == text
    assert "by hand   agents.planner:" in r.stdout
    assert "(agents is written inline)" in r.stdout
    assert r.stdout.splitlines()[-1] == "result: 5 left to fix by hand"


def test_unparseable_config_is_error(hub):
    write(hub, "config.yaml", "agents:\n  builder: { model: [x }\n")
    r = hub.run("config-check")
    assert r.returncode != 0


@needs_toml
def test_toml_reports_and_fix(hub):
    f = write(hub, "config.toml", TOML)
    r = hub.run("config-check")
    assert r.returncode == 0, r.stderr
    assert "leftover  model_ranking: no longer used" in r.stdout
    assert "leftover  agents.designer: renamed - becomes agents.planner" in r.stdout
    assert 'add  explorer = { model = "haiku", effort = "low" }' in r.stdout
    assert "invalid   execution.mode: is paralell" in r.stdout
    assert f.read_text() == TOML

    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    text = f.read_text()
    assert text.startswith("# Team policy\n\n[agents]\n")
    assert 'analyst = { model = "sonnet", effort = "medium" }  # reads business logic\n' in text
    assert 'planner = { model = "fable", effort = "max" }\n' in text
    assert 'retriever = { model = "sonnet", effort = "low" }\n' in text
    assert 'mode = "parallel"   # parallel | sequential\n' in text
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"
    r = hub.run("agent", "planner")
    assert "model=fable" in r.stdout and "source=config" in r.stdout


@needs_toml
def test_toml_table_per_agent(hub):
    f = write(hub, "config.toml",
              '[agents.designer]\nmodel = "fable"\neffort = "max"\n\n'
              '[agents.builder]\nmodel = "sonnet"\neffort = "medium"\n\n'
              '[hub]\nname = "platform"\n')
    r = hub.run("config-check", "--fix")
    assert r.returncode == 0, r.stderr
    text = f.read_text()
    assert "[agents.planner]\nmodel = \"fable\"" in text
    assert "[agents.explorer]\nmodel = \"haiku\"\neffort = \"low\"\n" in text
    assert "[hub]" not in text
    assert hub.run("config-check").stdout.splitlines()[-1] == "result: nothing to fix"
