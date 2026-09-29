"""The hub and task templates define the status vocabulary used by prompts."""

import re
from pathlib import Path


PAVE = Path(__file__).resolve().parents[1]


def feature_status_assignments(text):
    return set(re.findall(r"\bfeature(?:'s)?(?: status)? (?:to|as|is) `([a-z-]+)`", text))


def test_feature_statuses_match_hub_rules():
    template = (PAVE / "templates" / "feature-README.md").read_text()
    hub = (PAVE / "templates" / "hub-AGENTS.md").read_text()
    feature = set(re.search(r"\*\*Status\*\* <([^>]+)>", template).group(1).split(" | "))
    explained = set(re.findall(r"^\| `([^`]+)` \|", hub.split("## Status", 1)[1], re.M))
    assert feature == explained


def test_prompt_status_assignments_appear_in_templates():
    task = (PAVE / "templates" / "task.md").read_text()
    feature = (PAVE / "templates" / "feature-README.md").read_text()
    task_values = set(re.search(r"^status:.*# (.*)$", task, re.M).group(1).split(" | "))
    feature_values = set(re.search(r"\*\*Status\*\* <([^>]+)>", feature).group(1).split(" | "))
    prompts = list((PAVE / "skills").rglob("*.md")) + list((PAVE / "agents").glob("*.md"))
    prompts.append(PAVE / "templates" / "hub-AGENTS.md")
    for path in prompts:
        text = path.read_text()
        assignments = re.findall(r"\bstatus: ([a-z-]+)", text)
        feature_assignments = feature_status_assignments(text)
        assert set(assignments) <= task_values, f"{path}: {set(assignments) - task_values}"
        assert set(feature_assignments) <= feature_values, f"{path}: {set(feature_assignments) - feature_values}"


def test_feature_status_assignment_patterns():
    assert feature_status_assignments("Set the feature to `bogus`.") == {"bogus"}
    assert feature_status_assignments("Set the feature's status to `bogus`.") == {"bogus"}
