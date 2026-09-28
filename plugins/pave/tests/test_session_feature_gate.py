import json
import os
import subprocess
from pathlib import Path

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


# The session record: .pave-sessions/<PAVE_SESSION_ID>, written by pave.sh
# whenever it is given SESSION_FEATURE_ID, read when it is not.

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "pave-session-start.sh"


def record(hub, token):
    return hub.path / ".pave-sessions" / token


def test_use_records_the_feature(hub):
    make_feature(hub.path, "feat-1")
    r = hub.run("use", env={"SESSION_FEATURE_ID": "feat-1", "PAVE_SESSION_ID": "abc"})
    assert r.returncode == 0, r.stderr
    assert r.stdout == "feature: feat-1\n"
    assert record(hub, "abc").read_text() == "feat-1\n"


@pytest.mark.parametrize("cmd", COMMANDS)
def test_feature_scoped_commands_record_the_feature(hub, cmd):
    make_feature(hub.path, "feat-1")
    hub.run(cmd, env={"SESSION_FEATURE_ID": "feat-1", "PAVE_SESSION_ID": "abc"})
    assert record(hub, "abc").read_text() == "feat-1\n"


@pytest.mark.parametrize("cmd", COMMANDS + ["use"])
def test_falls_back_to_the_recorded_feature(hub, cmd):
    make_feature(hub.path, "feat-1")
    hub.run("use", env={"SESSION_FEATURE_ID": "feat-1", "PAVE_SESSION_ID": "abc"})
    r = hub.run(cmd, env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "abc"})
    assert r.stdout.startswith("feature: feat-1\n"), r.stdout + r.stderr


def test_session_feature_id_wins_over_the_record(hub):
    make_feature(hub.path, "feat-1")
    make_feature(hub.path, "feat-2")
    hub.run("use", env={"SESSION_FEATURE_ID": "feat-1", "PAVE_SESSION_ID": "abc"})
    r = hub.run("use", env={"SESSION_FEATURE_ID": "feat-2", "PAVE_SESSION_ID": "abc"})
    assert r.stdout == "feature: feat-2\n"
    # Switching is recorded, and the fallback follows it.
    assert record(hub, "abc").read_text() == "feat-2\n"
    r = hub.run("use", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "abc"})
    assert r.stdout == "feature: feat-2\n"


def test_sessions_keep_separate_features(hub):
    make_feature(hub.path, "feat-1")
    make_feature(hub.path, "feat-2")
    hub.run("use", env={"SESSION_FEATURE_ID": "feat-1", "PAVE_SESSION_ID": "one"})
    hub.run("use", env={"SESSION_FEATURE_ID": "feat-2", "PAVE_SESSION_ID": "two"})
    assert hub.run("use", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "one"}).stdout == "feature: feat-1\n"
    assert hub.run("use", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "two"}).stdout == "feature: feat-2\n"


def test_without_a_token_nothing_is_recorded(hub):
    make_feature(hub.path, "feat-1")
    r = hub.run("use", env={"SESSION_FEATURE_ID": "feat-1"})
    assert r.returncode == 0, r.stderr
    assert not (hub.path / ".pave-sessions").exists()


def test_unknown_feature_is_not_recorded(hub):
    r = hub.run("use", env={"SESSION_FEATURE_ID": "feat-999", "PAVE_SESSION_ID": "abc"})
    assert r.returncode != 0
    assert "no such feature" in r.stderr
    assert not record(hub, "abc").exists()


def test_refuses_with_a_token_but_no_record(hub):
    make_feature(hub.path, "feat-1")
    r = hub.run("check", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "abc"})
    assert r.returncode != 0
    assert "/pave:spec" in r.stderr


@pytest.mark.parametrize("content", ["", "\n", "../feat-1\n", "a b\n"])
def test_refuses_an_invalid_record(hub, content):
    make_feature(hub.path, "feat-1")
    record(hub, "abc").parent.mkdir()
    record(hub, "abc").write_text(content)
    r = hub.run("check", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "abc"})
    assert r.returncode != 0
    assert "not hold a valid feature id" in r.stderr


def test_refuses_a_recorded_feature_that_no_longer_exists(hub):
    record(hub, "abc").parent.mkdir()
    record(hub, "abc").write_text("feat-1\n")
    r = hub.run("check", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": "abc"})
    assert r.returncode != 0
    assert "no such feature" in r.stderr


@pytest.mark.parametrize("token", ["../x", "a/b", "a b", "abc.def"])
def test_an_unsafe_token_blocks_nothing_and_records_nothing(hub, token):
    make_feature(hub.path, "feat-1")
    r = hub.run("use", env={"SESSION_FEATURE_ID": "feat-1", "PAVE_SESSION_ID": token})
    assert r.returncode == 0, r.stderr
    assert r.stdout == "feature: feat-1\n"
    assert not (hub.path / ".pave-sessions").exists()


@pytest.mark.parametrize("token", ["../x", "a/b", "abc.def"])
def test_refuses_an_unsafe_token_for_the_fallback(hub, token):
    make_feature(hub.path, "feat-1")
    r = hub.run("check", env={"SESSION_FEATURE_ID": "", "PAVE_SESSION_ID": token})
    assert r.returncode != 0
    assert "PAVE_SESSION_ID" in r.stderr


def test_recording_leaves_no_temp_file(hub):
    make_feature(hub.path, "feat-1")
    make_feature(hub.path, "feat-2")
    for fid in ("feat-1", "feat-2"):
        hub.run("use", env={"SESSION_FEATURE_ID": fid, "PAVE_SESSION_ID": "abc"})
    assert sorted(p.name for p in (hub.path / ".pave-sessions").iterdir()) == ["abc"]


def test_use_refuses_an_argument(hub):
    make_feature(hub.path, "feat-1")
    r = hub.run("use", "feat-1", env={"SESSION_FEATURE_ID": ""})
    assert r.returncode != 0
    assert "takes no arguments" in r.stderr


def run_hook(tmp_path, stdin, env_file=True):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_ENV_FILE"}
    target = tmp_path / "env"
    if env_file:
        target.write_text("")
        env["CLAUDE_ENV_FILE"] = str(target)
    r = subprocess.run([str(HOOK)], input=stdin, capture_output=True, text=True, env=env)
    return r, target


def test_hook_exports_the_session_id(tmp_path):
    r, target = run_hook(tmp_path, json.dumps({"session_id": "abc-123", "source": "startup"}))
    assert r.returncode == 0, r.stderr
    assert target.read_text() == "export PAVE_SESSION_ID=abc-123\n"


@pytest.mark.parametrize("stdin", ["", "not json", json.dumps({}), json.dumps({"session_id": "../x"})])
def test_hook_writes_nothing_without_a_safe_id(tmp_path, stdin):
    r, target = run_hook(tmp_path, stdin)
    assert r.returncode == 0
    assert target.read_text() == ""


def test_hook_does_nothing_without_an_env_file(tmp_path):
    r, target = run_hook(tmp_path, json.dumps({"session_id": "abc"}), env_file=False)
    assert r.returncode == 0
    assert not target.exists()
