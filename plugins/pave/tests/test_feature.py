from conftest import make_feature


def test_propose_ticket_id(hub):
    r = hub.run("feature", "propose", "PROJ-42", "fix the widget")
    assert r.returncode == 0
    assert "kind: ticket" in r.stdout
    assert "id: PROJ-42" in r.stdout
    assert not (hub.path / "features" / "PROJ-42").exists()


def test_propose_description(hub):
    r = hub.run("feature", "propose", "add", "dark", "mode")
    assert r.returncode == 0
    assert "kind: description" in r.stdout
    assert "next: feat-1" in r.stdout
    assert not list((hub.path / "features").iterdir())


def test_propose_existing_folder(hub):
    make_feature(hub.path, "feat-1", title="Existing Thing")
    r = hub.run("feature", "propose", "feat-1")
    assert r.returncode == 0
    assert "kind: existing" in r.stdout
    assert "Existing Thing" in r.stdout


def test_create_rejects_invalid_id(hub):
    r = hub.run("feature", "create", "bad id!")
    assert r.returncode != 0
    assert "invalid id" in r.stderr


def test_create_rejects_id_over_30_chars(hub):
    long_id = "a" * 31
    r = hub.run("feature", "create", long_id)
    assert r.returncode != 0
    assert "longer than 30 characters" in r.stderr


def test_create_accepts_id_at_30_chars(hub):
    ok_id = "a" * 30
    r = hub.run("feature", "create", ok_id)
    assert r.returncode == 0


def test_create_is_idempotent(hub):
    r1 = hub.run("feature", "create", "feat-1", "First Title")
    assert r1.returncode == 0
    assert "status: new" in r1.stdout
    r2 = hub.run("feature", "create", "feat-1")
    assert r2.returncode == 0
    assert "status: exists" in r2.stdout
    for sub in ("tasks", "artifacts"):
        assert (hub.path / "features" / "feat-1" / sub).is_dir()
    # Contracts are a disposable record under artifacts/, never planned input.
    assert not (hub.path / "features" / "feat-1" / "contracts").exists()


def test_create_reads_title_from_existing_spec(hub):
    fdir = make_feature(hub.path, "feat-1", title="Spec Title")
    r = hub.run("feature", "create", "feat-1")
    assert r.returncode == 0
    assert "status: exists" in r.stdout
    assert "Spec Title" in r.stdout
