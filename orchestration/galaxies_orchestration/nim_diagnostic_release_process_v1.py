"""Release-only ownership: discard bounded remaining IPC before reaping the child."""

import asyncio

from .integrated_worker_v2 import MAX_LINE, IntegratedWorker
from .nim_graph_v1 import ProbeWorker, finish


class ReleasedProbeWorker(ProbeWorker):
    def __init__(self, *args, drain_timeout=1.0, wait_timeout=1.0, cleanup_deadline=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not 0 < drain_timeout <= 1 or not 0 < wait_timeout <= 1:
            raise ValueError("diagnostic_release_cleanup_budget_invalid")
        self.drain_timeout, self.wait_timeout = drain_timeout, wait_timeout
        self.cleanup_deadline = cleanup_deadline
        self.cleanup_confirmed, self.cleanup_code = False, "not_started"

    def _phase_deadline(self, budget):
        deadline = asyncio.get_running_loop().time() + budget
        return deadline if self.cleanup_deadline is None else min(deadline, self.cleanup_deadline)

    def _close_stdout(self):
        # asyncio.Process exposes no public stdout-close API. On uncertain EOF
        # this owned pipe must be closed before bounded wait, without more reads.
        pipe = self.process._transport.get_pipe_transport(1)
        if pipe is not None:
            pipe.close()

    async def __aenter__(self):
        # Same shield/finish ownership as ProbeWorker, but cancelled startup must
        # also use this release's pipe-draining cleanup, not the sealed helper.
        spawning = asyncio.create_task(IntegratedWorker.__aenter__(self))
        try:
            return await asyncio.shield(spawning)
        except BaseException:
            try:
                await finish(spawning)
            finally:
                await finish(asyncio.create_task(self._cleanup()))
            raise

    async def _cleanup(self):
        process = self.process
        if process is None:
            return
        if process.stdin is not None:
            process.stdin.close()
        if process.returncode is None:
            try:
                process.kill()  # only the child owned by this worker
            except ProcessLookupError:
                pass
        failed = False
        try:
            async with asyncio.timeout_at(self._phase_deadline(self.drain_timeout)):
                if process.stdout is not None:
                    remaining = MAX_LINE + 1
                    while remaining:
                        # Discard immediately; never retain or project IPC bytes.
                        consumed = len(await process.stdout.read(min(65536, remaining)))
                        if consumed == 0:
                            break
                        remaining -= consumed
                    else:
                        failed = True
        except Exception:  # noqa: BLE001 - includes timeout; no arbitrary error leaves IPC
            failed = True
        if failed:
            self.cleanup_code = "drain_unconfirmed"
            self._close_stdout()
        try:
            async with asyncio.timeout_at(self._phase_deadline(self.wait_timeout)):
                # Public returncode is set by asyncio's child watcher after
                # reaping. Process.wait() can still await pipe notifications;
                # do not register that separate waiter during cleanup.
                while process.returncode is None:
                    await asyncio.sleep(0.005)
        except Exception:  # noqa: BLE001 - never claim reap after timeout/failure
            failed = True
            self.cleanup_code = "wait_unconfirmed"
            self._close_stdout()
        if failed:
            raise ValueError("diagnostic_release_cleanup_unconfirmed")
        self.cleanup_confirmed, self.cleanup_code = True, "confirmed"

    async def __aexit__(self, *args):
        _, interrupted = await finish(asyncio.create_task(self._cleanup()))
        if interrupted:
            raise asyncio.CancelledError
