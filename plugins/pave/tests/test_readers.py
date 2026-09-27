import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
YAML_READER = SCRIPTS / "yaml-reader"
TOML_READER = SCRIPTS / "toml-reader"

try:
    import yaml as _pyyaml
    HAVE_PYYAML = True
except ImportError:
    HAVE_PYYAML = False


def run_reader(reader, path, key, no_pyyaml=False):
    env = None
    if no_pyyaml:
        import os
        env = {**os.environ}
        env["PYTHONPATH"] = ""
    code = None
    if no_pyyaml:
        code = f"""
import sys
sys.modules['yaml'] = None
sys.argv = [{str(reader)!r}, {str(path)!r}, {key!r}]
exec(open({str(reader)!r}).read())
"""
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return subprocess.run([sys.executable, str(reader), str(path), key], capture_output=True, text=True)


@pytest.fixture(params=[False, True], ids=["with-pyyaml", "without-pyyaml"])
def block_pyyaml(request):
    return request.param


YAML_CASES = [
    ("plain: value\n", "plain", "value"),
    ("num: 42\n", "num", "42"),
    ("flag: true\n", "flag", "true"),
    ("quoted: 'hello world'\n", "quoted", "hello world"),
]


@pytest.mark.parametrize("text,key,expected", YAML_CASES)
def test_yaml_reader_matches_expected(tmp_path, text, key, expected, block_pyyaml):
    f = tmp_path / "c.yaml"
    f.write_text(text)
    r = run_reader(YAML_READER, f, key, no_pyyaml=block_pyyaml)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == expected


@pytest.mark.parametrize("text,key,expected", YAML_CASES)
@pytest.mark.skipif(not HAVE_PYYAML, reason="PyYAML not installed")
def test_pyyaml_agrees_with_reader(tmp_path, text, key, expected):
    import yaml
    data = yaml.safe_load(text)
    val = data[key]
    if isinstance(val, bool):
        val = "true" if val else "false"
    assert str(val) == expected


def test_yaml_reader_nested_mapping(tmp_path, block_pyyaml):
    f = tmp_path / "c.yaml"
    f.write_text("agents:\n  builder: { model: opus, effort: high }\n")
    r = run_reader(YAML_READER, f, "agents.builder", no_pyyaml=block_pyyaml)
    assert r.returncode == 0, r.stderr
    assert "model=opus" in r.stdout
    assert "effort=high" in r.stdout


def test_yaml_reader_missing_key_exit_3(tmp_path, block_pyyaml):
    f = tmp_path / "c.yaml"
    f.write_text("a: 1\n")
    r = run_reader(YAML_READER, f, "b", no_pyyaml=block_pyyaml)
    assert r.returncode == 3


def test_yaml_reader_rejects_anchor_syntax(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("a: &anchor value\n")
    r = run_reader(YAML_READER, f, "a", no_pyyaml=True)
    assert r.returncode != 0
    assert r.returncode != 3


def test_yaml_reader_rejects_tab_indentation(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("a:\n\tb: 1\n")
    r = run_reader(YAML_READER, f, "a.b", no_pyyaml=True)
    assert r.returncode != 0
    assert r.returncode != 3


def test_toml_reader_scalar(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text('a = "value"\n')
    r = subprocess.run([sys.executable, str(TOML_READER), str(f), "a"], capture_output=True, text=True)
    assert r.returncode == 0
    assert r.stdout.strip() == "value"


def test_toml_reader_table(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text('[agents.builder]\nmodel = "opus"\neffort = "high"\n')
    r = subprocess.run([sys.executable, str(TOML_READER), str(f), "agents.builder"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "model=opus" in r.stdout
    assert "effort=high" in r.stdout


def test_toml_reader_missing_key_exit_3(tmp_path):
    f = tmp_path / "c.toml"
    f.write_text('a = 1\n')
    r = subprocess.run([sys.executable, str(TOML_READER), str(f), "b"], capture_output=True, text=True)
    assert r.returncode == 3


def test_toml_and_yaml_reader_agree_on_equivalent_config(tmp_path):
    yf = tmp_path / "c.yaml"
    yf.write_text("agents:\n  builder: { model: opus, effort: high }\n")
    tf = tmp_path / "c.toml"
    tf.write_text('[agents.builder]\nmodel = "opus"\neffort = "high"\n')
    ry = subprocess.run([sys.executable, str(YAML_READER), str(yf), "agents.builder"], capture_output=True, text=True)
    rt = subprocess.run([sys.executable, str(TOML_READER), str(tf), "agents.builder"], capture_output=True, text=True)
    assert set(ry.stdout.splitlines()) == set(rt.stdout.splitlines())
