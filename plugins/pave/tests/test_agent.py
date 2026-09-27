def test_agent_default_when_no_config(hub):
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert "model=sonnet" in r.stdout
    assert "effort=medium" in r.stdout
    assert "source=default" in r.stdout


def test_agent_unknown(hub):
    r = hub.run("agent", "nonexistent")
    assert r.returncode != 0
    assert "unknown agent" in r.stderr


def test_agent_config_wins_yaml(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  builder: { model: opus, effort: high }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert "model=opus" in r.stdout
    assert "effort=high" in r.stdout
    assert "source=config" in r.stdout


def test_agent_config_yml_extension(hub):
    (hub.path / "config.yml").write_text(
        "agents:\n  builder: { model: opus, effort: high }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert "model=opus" in r.stdout
    assert "source=config" in r.stdout


def test_agent_config_toml_extension(hub):
    (hub.path / "config.toml").write_text(
        '[agents.builder]\nmodel = "opus"\neffort = "high"\n'
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert "model=opus" in r.stdout
    assert "effort=high" in r.stdout
    assert "source=config" in r.stdout


def test_agent_config_partial_falls_back_to_default_effort(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  builder: { model: opus }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert "model=opus" in r.stdout
    assert "effort=medium" in r.stdout
    assert "source=config" in r.stdout


def test_agent_two_config_files_is_error(hub):
    (hub.path / "config.yaml").write_text("agents: {}\n")
    (hub.path / "config.toml").write_text("[agents]\n")
    r = hub.run("agent", "builder")
    assert r.returncode != 0
    assert "more than one config file" in r.stderr


def test_agent_missing_entry_in_config_uses_default(hub):
    (hub.path / "config.yaml").write_text(
        "agents:\n  reviewer: { model: opus, effort: high }\n"
    )
    r = hub.run("agent", "builder")
    assert r.returncode == 0
    assert "model=sonnet" in r.stdout
    assert "source=default" in r.stdout
