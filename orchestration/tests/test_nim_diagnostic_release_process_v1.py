"""Real stdlib children exercise pipe-blocked wait and exclusive cleanup ownership."""

import asyncio
import sys
from pathlib import Path

import pytest

from galaxies_orchestration.integrated_worker_v2 import MAX_LINE
from galaxies_orchestration.nim_diagnostic_release_process_v1 import ReleasedProbeWorker


async def child(size, *, limit=1024):
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-B",
        "-u",
        "-c",
        f"import os,time;os.write(1,b'x'*{size});time.sleep(60)",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=limit,
    )


def owner(process, tmp_path):
    worker = ReleasedProbeWorker(sys.executable, tmp_path)
    worker.process = process
    return worker


def test_cleanup_drains_paused_pipe_before_registered_wait(tmp_path):
    async def scenario():
        process = await child(65536)
        worker = owner(process, tmp_path)
        waiting = asyncio.create_task(process.wait())
        await asyncio.sleep(0.1)
        process.kill()
        async with asyncio.timeout(2):
            while process.returncode is None:
                await asyncio.sleep(0.01)
        # Real child is dead, but registered wait still needs pipe disconnection.
        assert not waiting.done()
        async with asyncio.timeout(2):
            await worker.__aexit__(None, None, None)
            await waiting
        assert process.returncode is not None
        assert not Path(f"/proc/{process.pid}").exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["overflow", "read_error"])
def test_cleanup_failure_closes_owned_pipe_and_reaps(tmp_path, monkeypatch, failure):
    async def scenario():
        process = await child(MAX_LINE + 2, limit=MAX_LINE + 1)
        worker = owner(process, tmp_path)
        await asyncio.sleep(0.1)
        if failure == "read_error":

            async def fail(*args):
                raise RuntimeError("ENTIRELY_INVENTED_FAILURE_NOT_PROJECTED")

            monkeypatch.setattr(process.stdout, "read", fail)
        async with asyncio.timeout(2):
            with pytest.raises(ValueError, match="^diagnostic_release_cleanup_unconfirmed$"):
                await worker.__aexit__(None, None, None)
        assert process.returncode is not None
        assert not Path(f"/proc/{process.pid}").exists()

    asyncio.run(scenario())


def test_repeated_cancel_retains_sole_cleanup_owner(tmp_path, monkeypatch):
    async def scenario():
        process = await child(65536)
        worker = owner(process, tmp_path)
        entered, release = asyncio.Event(), asyncio.Event()
        original = process.stdout.read

        async def read(size):
            entered.set()
            await release.wait()
            return await original(size)

        monkeypatch.setattr(process.stdout, "read", read)
        task = asyncio.create_task(worker.__aexit__(None, None, None))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        async with asyncio.timeout(2):
            with pytest.raises(asyncio.CancelledError):
                await task
        assert process.returncode is not None
        assert not Path(f"/proc/{process.pid}").exists()

    asyncio.run(scenario())


def test_cancelled_spawn_uses_draining_cleanup(tmp_path, monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            entered.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        worker = ReleasedProbeWorker(
            sys.executable, tmp_path, ("-n", "1", "-r", "1", "pass"), module="timeit"
        )
        task = asyncio.create_task(worker.__aenter__())
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        async with asyncio.timeout(2):
            with pytest.raises(asyncio.CancelledError):
                await task
        assert len(processes) == 1
        assert processes[0].returncode is not None
        assert not Path(f"/proc/{processes[0].pid}").exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["drain", "wait"])
def test_cleanup_never_completing_phase_is_bounded_and_unconfirmed(tmp_path, monkeypatch, phase):
    async def scenario():
        process = await child(100)
        worker = ReleasedProbeWorker(
            sys.executable, tmp_path, drain_timeout=0.05, wait_timeout=0.05
        )
        worker.process = process

        async def never(*args):
            await asyncio.Future()

        if phase == "drain":
            monkeypatch.setattr(process.stdout, "read", never)
        else:

            class UnknownExit:
                @property
                def returncode(self):
                    return None

                def __getattr__(self, name):
                    return getattr(process, name)

            worker.process = UnknownExit()
        async with asyncio.timeout(1):
            with pytest.raises(ValueError, match="^diagnostic_release_cleanup_unconfirmed$"):
                await worker.__aexit__(None, None, None)
        assert worker.cleanup_confirmed is False
        assert worker.cleanup_code == phase + "_unconfirmed"
        assert process.returncode is not None
        assert not Path(f"/proc/{process.pid}").exists()

    asyncio.run(scenario())


def test_never_completing_wait_does_not_override_confirmed_reap(tmp_path, monkeypatch):
    async def scenario():
        process = await child(100)
        worker = owner(process, tmp_path)

        async def never():
            await asyncio.Future()

        monkeypatch.setattr(process, "wait", never)
        waiting = asyncio.create_task(process.wait())
        async with asyncio.timeout(2):
            await worker.__aexit__(None, None, None)
        assert not waiting.done()
        assert process.returncode is not None
        assert worker.cleanup_confirmed is True
        assert worker.cleanup_code == "confirmed"
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting

    asyncio.run(scenario())
