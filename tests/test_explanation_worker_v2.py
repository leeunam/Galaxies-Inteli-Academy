"""Real light processes for launcher cleanup; no models, media source or network."""

import io
import json
import os
import subprocess
import sys
import time

import pytest

from scripts.explanation_worker_v2 import _terminate_tree, serve, supervised_launcher


def test_terminate_freezes_and_collects_descendants_without_touching_control(tmp_path):
    pidfile = tmp_path / "child.json"
    code = (
        "import json,subprocess,sys,time; from pathlib import Path; "
        "p=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(60)']); "
        "Path(sys.argv[1]).write_text(json.dumps(p.pid)); time.sleep(60)"
    )
    control = subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(60)"])
    parent = subprocess.Popen(
        [sys.executable, "-B", "-c", code, str(pidfile)], start_new_session=True
    )
    try:
        deadline = time.monotonic() + 5
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert pidfile.exists()
        child = json.loads(pidfile.read_bytes())
        _terminate_tree(parent)
        assert parent.returncode is not None
        # This direct test is not the dedicated subreaper. A terminated orphan
        # can be zombie until init collects it; it cannot write scratch.
        import psutil

        try:
            assert psutil.Process(child).status() == psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            pass
        assert control.poll() is None
    finally:
        if parent.poll() is None:
            os.killpg(parent.pid, 9)
            parent.wait()
        control.kill()
        control.wait()


def test_launcher_requires_external_owned_group_and_fails_before_spawn(tmp_path, monkeypatch):
    monkeypatch.delenv("GALAXIES_SUPERVISED_GROUP", raising=False)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **kw: pytest.fail("spawned without supervisor")
    )
    with pytest.raises(RuntimeError, match="supervisor_required"):
        supervised_launcher(tmp_path, 1)


@pytest.mark.parametrize("raw", [b"[]\n", b"{bad\n", b"x" * 262145])
def test_worker_protocol_never_echoes_invalid_input(raw):
    out = io.BytesIO()
    serve(object(), io.BytesIO(raw), out)
    assert out.getvalue() == b'{"worker_error":"worker_failed"}\n'
