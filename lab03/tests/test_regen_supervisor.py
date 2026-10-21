"""Tests for scripts/regen_supervisor.sh with a stub in place of `uv` (needs util-linux `flock`)."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "regen_supervisor.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("flock") is None or shutil.which("bash") is None,
    reason="flock (util-linux) not available",
)

# Fails the first two times (the second one after making progress), then "completes".
STUB_UV = """#!/usr/bin/env bash
home="$REGEN_HOME"
n=$(cat "$home/.calls" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" >"$home/.calls"
echo "token ghp_SECRET0123456789abcdefghijklmnopqrstuvwx used" 
echo "Token abcdefgh1234 returned 401"
mkdir -p "$home/lab03/dados/.regenerar"
if [ "$n" -eq 1 ]; then exit 1; fi
echo '{"record": {}}' >>"$home/lab03/dados/.regenerar/checkpoint.jsonl"
if [ "$n" -eq 2 ]; then exit 3; fi
echo bundle >"$home/outputs-2026-10-22.tar.gz"
echo "abc  outputs-2026-10-22.tar.gz" >"$home/outputs-2026-10-22.tar.gz.sha256"
exit 0
"""


def _setup(tmp_path: Path) -> tuple[dict[str, str], Path]:
    home = tmp_path / "regen"
    (home / "lab03").mkdir(parents=True)
    stub = tmp_path / "uv"
    stub.write_text(STUB_UV, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    env = {
        **os.environ,
        "REGEN_HOME": str(home),
        "REGEN_UV": str(stub),
        "REGEN_MIN_WAIT": "1",
        "REGEN_MAX_WAIT": "2",
    }
    return env, home


def test_supervisor_restarts_until_the_bundle_exists_then_writes_done(tmp_path):
    env, home = _setup(tmp_path)
    proc = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60, check=False
    )

    assert proc.returncode == 0, proc.stderr
    assert (home / ".calls").read_text().strip() == "3"
    done = (home / "DONE").read_text().splitlines()
    assert done[1] == "outputs-2026-10-22.tar.gz"
    log = (home / "supervisor.log").read_text()
    assert "attempt 1 ended rc=1" in log and "attempt 2 ended rc=3" in log
    assert "DONE written" in log
    # backoff is reset after progress (checkpoint grew) and tokens never reach the logs
    assert "retrying in 1s" in log
    run_log = (home / "regen.log").read_text()
    assert "SECRET0123456789" not in run_log and "abcdefgh1234" not in run_log
    assert "ghp_***" in run_log and "Token ********" in run_log


def test_supervisor_does_nothing_when_done_exists(tmp_path):
    env, home = _setup(tmp_path)
    (home / "DONE").write_text("2026-10-22T00:00:00Z\n")
    proc = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0
    assert not (home / ".calls").exists()
    assert "DONE marker exists" in (home / "supervisor.log").read_text()


def test_only_one_supervisor_runs_at_a_time(tmp_path):
    env, home = _setup(tmp_path)
    lock = subprocess.Popen(
        ["bash", "-c", f'exec 9>"{home}/.supervisor.lock"; flock -n 9 && sleep 20']
    )
    try:
        import time

        time.sleep(1)
        proc = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0
        assert not (home / ".calls").exists()  # the pipeline was not started
        assert "another supervisor holds the lock" in (home / "supervisor.log").read_text()
    finally:
        lock.kill()
