import pytest

from conftest import make_feature

COMMANDS = ["seal", "check", "prune-obsoleted-tasks"]


@pytest.mark.parametrize("cmd", COMMANDS)
def test_refuses_without_session_feature_id(hub, cmd):
    make_feature(hub.path, "feat-1")
    r = hub.run(cmd, env={"SESSION_FEATURE_ID": ""})
    assert r.returncode != 0
    assert "SESSION_FEATURE_ID is not set" in r.stderr


@pytest.mark.parametrize("cmd", COMMANDS)
def test_refuses_id_as_argument(hub, cmd):
    make_feature(hub.path, "feat-1")
    r = hub.run(cmd, "feat-1", env={"SESSION_FEATURE_ID": ""})
    assert r.returncode != 0
    assert "takes no arguments" in r.stderr


@pytest.mark.parametrize("cmd", COMMANDS)
def test_refuses_unknown_feature(hub, cmd):
    r = hub.run(cmd, env={"SESSION_FEATURE_ID": "feat-999"})
    assert r.returncode != 0
    assert "no such feature" in r.stderr


def test_add_works_without_session_feature_id(hub, tmp_path):
    svc = tmp_path / "svc"
    svc.mkdir()
    r = hub.run("add", str(svc), env={"SESSION_FEATURE_ID": ""})
    assert r.returncode == 0


def test_feature_propose_works_without_session_feature_id(hub):
    r = hub.run("feature", "propose", "TICKET-1", "some title", env={"SESSION_FEATURE_ID": ""})
    assert r.returncode == 0


def test_feature_create_works_without_session_feature_id(hub):
    r = hub.run("feature", "create", "feat-1", "Title", env={"SESSION_FEATURE_ID": ""})
    assert r.returncode == 0


def test_stale_works_without_session_feature_id(hub):
    r = hub.run("stale", env={"SESSION_FEATURE_ID": ""})
    assert r.returncode == 0


def test_agent_works_without_session_feature_id(hub):
    (hub.path / "config.yaml").write_text("agents:\n  builder: { model: sonnet, effort: medium }\n")
    r = hub.run("agent", "builder", env={"SESSION_FEATURE_ID": ""})
    assert r.returncode == 0
