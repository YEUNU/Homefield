import os
import subprocess
import time

from evalkit.run import stop_leftovers


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A killed child of this test stays as a zombie until someone waits for it.
    return "Z" not in open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0]


def wait_for(path, timeout=5.0) -> int:
    end = time.time() + timeout
    while time.time() < end:
        if path.exists() and path.read_text().strip():
            return int(path.read_text())
        time.sleep(0.05)
    raise AssertionError(f"{path} was not written")


def test_stop_leftovers_stops_a_child_in_its_own_session(tmp_path):
    # The harness starts a tool command in a new session; a kill of the harness process group does not reach it.
    work = tmp_path / "ep" / "work"
    work.mkdir(parents=True)
    proc = subprocess.Popen(
        ["sh", "-c", "setsid sh -c 'echo $$ > ../child.pid; exec sleep 60' & sleep 60"],
        cwd=work,
        start_new_session=True,
    )
    child = wait_for(tmp_path / "ep" / "child.pid")
    stop_leftovers(proc.pid, tmp_path / "ep")
    proc.wait(timeout=5)
    time.sleep(0.2)
    assert not alive(child)


def test_stop_leftovers_stops_an_orphan_after_the_harness_ended(tmp_path):
    # The harness ended, but a command it started still runs in the episode folder.
    work = tmp_path / "ep" / "work"
    work.mkdir(parents=True)
    proc = subprocess.Popen(
        ["sh", "-c", "setsid sh -c 'echo $$ > ../child.pid; exec sleep 60' &"], cwd=work, start_new_session=True
    )
    proc.wait(timeout=5)
    child = wait_for(tmp_path / "ep" / "child.pid")
    assert alive(child)
    stop_leftovers(proc.pid, tmp_path / "ep")
    time.sleep(0.2)
    assert not alive(child)


def test_stop_leftovers_keeps_processes_outside_the_episode(tmp_path):
    (tmp_path / "ep").mkdir()
    (tmp_path / "other").mkdir()
    other = subprocess.Popen(["sleep", "60"], cwd=tmp_path / "other", start_new_session=True)
    try:
        stop_leftovers(2**22 + 1, tmp_path / "ep")
        assert other.poll() is None
    finally:
        other.kill()
        other.wait()
