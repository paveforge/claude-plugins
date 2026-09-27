import shutil
import subprocess
from pathlib import Path

import pytest

PAVE_SH = Path(__file__).resolve().parents[1] / "scripts" / "pave.sh"


def test_bash_syntax():
    r = subprocess.run(["bash", "-n", str(PAVE_SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_shellcheck():
    env = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    r = subprocess.run(
        ["shellcheck", "--severity=warning", str(PAVE_SH)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stdout + r.stderr
