"""pave_yaml: every layout a model may write reads the same, with or without
PyYAML, and anything the built-in parser cannot read is an error."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pave_yaml  # noqa: E402
from pave_yaml import YamlError, flow, load_builtin, set_key, split_frontmatter  # noqa: E402

try:
    import yaml  # noqa: F401
    HAVE_PYYAML = True
except ImportError:
    HAVE_PYYAML = False

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
H = "a" * 64


def parsers():
    out = [load_builtin]
    if HAVE_PYYAML:
        out.append(pave_yaml.load)
    return out


def read_all(text):
    """The value of text under every parser available - they must agree."""
    values = [p(text) for p in parsers()]
    for v in values[1:]:
        assert v == values[0], f"parsers disagree on:\n{text}"
    return values[0]


SAME = [
    pytest.param(
        "services:\n  - { service: a, paths: [src, lib], hash: " + H + " }\n",
        "services:\n  - service: a\n    paths:\n      - src\n      - lib\n    hash: " + H + "\n",
        "services:\n- hash: " + H + "\n  paths: [src, lib]\n  service: a\n",
        "services: [{service: a, paths: [src, lib], hash: " + H + "}]\n",
        "services:\n  - {\n      service: a,\n      paths: [src,\n              lib],\n"
        "      hash: " + H + "\n    }\n",
        id="finding-services",
    ),
    pytest.param(
        'tasks:\n  "01": ' + H + '\n  "10": ' + H + "\n",
        'tasks: {"01": ' + H + ', "10": ' + H + "}\n",
        "tasks: {'01': " + H + ", '10': " + H + "}\n",
        id="plan-tasks",
    ),
    pytest.param(
        "source_paths: [src, internal/api]\n",
        "source_paths:\n  - src\n  - internal/api\n",
        "source_paths:\n- src\n- internal/api\n",
        "source_paths: [\n  src,\n  internal/api,\n]\n",
        "source_paths: ['src', \"internal/api\"]   # the dirs read\n",
        id="source-paths",
    ),
    pytest.param(
        "services:\n  - name: svc\n    path: /x/svc\n    language: go\n",
        "services:\n- name: svc\n  path: /x/svc\n  language: go\n",
        "services: [{ name: svc, path: /x/svc, language: go }]\n",
        "services:\n  - language: go\n    path: /x/svc\n    name: svc\n",
        id="workspace",
    ),
]


@pytest.mark.parametrize("texts", [p.values for p in SAME], ids=[p.id for p in SAME])
def test_every_layout_reads_the_same(texts):
    first = read_all(texts[0])
    for t in texts[1:]:
        assert read_all(t) == first, t


@pytest.mark.parametrize("text,expected", [
    ("v: 01", "01"),
    ("v: 10", 10),
    ("v: -3", -3),
    ("v: 1.5", 1.5),
    ("v: yes", True),
    ("v: Off", False),
    ("v: ~", None),
    ("v:", None),
    ("v: 2026-09-29", "2026-09-29"),
    ("v: plan.md#approach", "plan.md#approach"),
    ("v: go test ./...  # comment", "go test ./..."),
    ("v: 'it''s'", "it's"),
    ('v: "a \\"b\\""', 'a "b"'),
    ("v: don't # stop", "don't"),
    ("v: [a, 'b, c', {x: [1, 2]}]", ["a", "b, c", {"x": [1, 2]}]),
    ("v: { a: , b: 1 }", {"a": None, "b": 1}),
    ("v: " + "1" * 64, int("1" * 64)),
])
def test_scalars_resolve_the_same_everywhere(text, expected):
    assert read_all(text + "\n") == {"v": expected}


@pytest.mark.parametrize("text", [
    "a: &anchor value\n",
    "a:\n\tb: 1\n",
    "a: [x\n",
    "a: { b: 1\n",
    "a: [x]]\n",
    "a: b: c\n",
    "a: 1\na: 2\n",
    "a: { b: 1, b: 2 }\n",
    "a: 'open\n",
    "a: 1\n  b: 2\n",
    "- a\nb: 1\n",
])
def test_builtin_rejects_what_it_cannot_read(text):
    with pytest.raises(YamlError):
        load_builtin(text)


@pytest.mark.skipif(not HAVE_PYYAML, reason="PyYAML not installed")
def test_pyyaml_refuses_duplicate_keys_too():
    with pytest.raises(YamlError):
        pave_yaml.load("a: 1\na: 2\n")


@pytest.mark.parametrize("name", ["workspace.yaml", "config.yaml"])
def test_templates_read_the_same_under_both_parsers(name):
    data = read_all((TEMPLATES / name).read_text())
    assert isinstance(data, dict) and data


@pytest.mark.parametrize("v", [
    "plain", "01", "10", "yes", "null", "", "a: b", "x, y", "[x]", "#x", "it's", 'say "hi"',
    " padded ", "back\\slash", 5, 1.5, True, None, [], ["src", "lib/x"],
    {"service": "a", "paths": ["src"], "hash": H}, "1" * 64,
])
def test_flow_reads_back_as_written(v):
    assert read_all(f"k: {flow(v)}\n") == {"k": v}


FM = """feature: f
# a comment the planner wrote
next_task: 3   # allocate from here
tasks:
  "01": old
  "02": old

services:
- { service: a, paths: [src] }
terms: [x]
"""


def test_set_key_replaces_only_its_key():
    out = set_key(FM, "tasks", 'tasks: {"01": new}')
    assert 'tasks: {"01": new}\n\nservices:' in out
    assert out.replace('tasks: {"01": new}\n', 'tasks:\n  "01": old\n  "02": old\n') == FM


def test_set_key_replaces_an_indentless_list():
    out = set_key(FM, "services", "services:\n  - { service: a, paths: [src], hash: h }")
    assert "- { service: a, paths: [src] }" not in out
    assert out.endswith("  - { service: a, paths: [src], hash: h }\nterms: [x]\n")


def test_set_key_inserts_after_its_anchor_or_at_the_end():
    assert set_key("a: 1\nb: 2\n", "h", "h: x", after="a") == "a: 1\nh: x\nb: 2\n"
    assert set_key("a: 1\nb: 2", "h", "h: x") == "a: 1\nb: 2\nh: x\n"
    assert set_key("a: 1\n", "h", "h: x", after="missing") == "a: 1\nh: x\n"


def test_set_key_does_not_match_a_longer_key():
    assert set_key("source_hash_old: 1\n", "source_hash", "source_hash: 2") == \
        "source_hash_old: 1\nsource_hash: 2\n"


def test_split_frontmatter():
    assert split_frontmatter("---\na: 1\n---\nbody\n") == ("a: 1\n", "body\n")
    assert split_frontmatter("---\n---\nbody") == ("", "body")
    assert split_frontmatter("---\na: ---x\n----\n---\n# b") == ("a: ---x\n----\n", "# b")
    assert split_frontmatter("# no frontmatter\n") == (None, "# no frontmatter\n")


def test_set_key_replaces_a_multi_line_flow_value():
    fm = "a: [\n  x,\n]\nb: 1\n"
    assert set_key(fm, "a", "a: [y]") == "a: [y]\nb: 1\n"
    assert set_key(fm, "h", "h: z", after="a") == "a: [\n  x,\n]\nh: z\nb: 1\n"


def test_a_whole_document_in_flow_form():
    assert read_all("{ a: 1, b: [x] }\n") == {"a": 1, "b": ["x"]}
    with pytest.raises(YamlError):
        load_builtin("{ a: 1 }\nb: 2\n")
