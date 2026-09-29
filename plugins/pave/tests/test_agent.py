def test_agent_no_config_is_error(hub):
    r = hub.run("agent", "builder")
    assert r.returncode != 0
    assert "no config file" in r.stderr
    assert "/pave:init" in r.stderr
    assert r.stdout == ""


def test_agent_unknown(hub):
    (hub.path / "config.yaml").write_text("agents:\n  builder: { model: opus, effort: high }\n")
    r = hub.run("agent", "nonexistent")
    assert r.returncode != 0
    assert "unknown agent" in r.stderr


def test_agent_config_yaml(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  builder: { model: opus, effort: high }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert r.stdout == "model=opus\neffort=high\n"


def test_agent_host_config(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n"
        "  builder: { model: sonnet, effort: high }\n"
    )
    (hub.path / "config.codex.yaml").write_text(
        "agents:\n"
        "  builder: { model: gpt-6-sol, effort: medium }\n"
    )
    claude = hub.run("agent", "builder")
    assert claude.returncode == 0, claude.stderr
    assert claude.stdout == "model=sonnet\neffort=high\n"
    r = hub.run("agent", "builder", "codex")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "model=gpt-6-sol\neffort=medium\n"


def test_agent_missing_host_config_is_error(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  builder: { model: sonnet, effort: medium }\n"
    )
    r = hub.run("agent", "builder", "codex")
    assert r.returncode != 0
    assert "no codex config file" in r.stderr


def test_agent_codex_toml_config(hub):
    (hub.path / "config.codex.toml").write_text(
        '[agents.builder]\nmodel = "gpt-6-sol"\neffort = "medium"\n'
    )
    r = hub.run("agent", "builder", "codex")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "model=gpt-6-sol\neffort=medium\n"


def test_agent_config_yml_extension(hub):
    (hub.path / "config.yml").write_text(
        "agents:\n  builder: { model: opus, effort: high }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert r.stdout == "model=opus\neffort=high\n"


def test_agent_config_toml_extension(hub):
    (hub.path / "config.toml").write_text(
        '[agents.builder]\nmodel = "opus"\neffort = "high"\n'
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert r.stdout == "model=opus\neffort=high\n"


def test_agent_partial_entry_is_error(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  builder: { model: opus }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode != 0
    assert "needs both model and effort" in r.stderr
    assert "/pave:init" in r.stderr
    assert r.stdout == ""


def test_agent_two_config_files_is_error(hub):
    (hub.path / "config.yaml").write_text("agents: {}\n")
    (hub.path / "config.toml").write_text("[agents]\n")
    r = hub.run("agent", "builder")
    assert r.returncode != 0
    assert "more than one config file" in r.stderr


def test_agent_missing_entry_is_error(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  reviewer: { model: opus, effort: high }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode != 0
    assert "no entry for agents.builder" in r.stderr
    assert "/pave:init" in r.stderr
    assert r.stdout == ""


def test_agent_every_definition_has_a_template_entry(hub):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    (hub.path / "config.yaml").write_text((root / "templates" / "config.yaml").read_text())
    for md in (root / "agents").glob("*.md"):
        r = hub.run("agent", md.stem)
        assert r.returncode == 0, (md.stem, r.stderr)


def test_agent_every_definition_has_a_codex_template_entry(hub):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    (hub.path / "config.codex.yaml").write_text(
        (root / "templates" / "config.codex.yaml").read_text()
    )
    for md in (root / "agents").glob("*.md"):
        r = hub.run("agent", md.stem, "codex")
        assert r.returncode == 0, (md.stem, r.stderr)
