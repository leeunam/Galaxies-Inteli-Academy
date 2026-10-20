"""Bounded stdio client; child credentials and provider/tracing settings omitted."""

from __future__ import annotations

import asyncio
import json
import os
import signal
from pathlib import Path

MAX_LINE_BYTES = 262144
ROOT = Path(__file__).resolve().parents[2]


class WorkerError(RuntimeError):
    pass


class RootWorker:
    def __init__(self, root=ROOT, *, arguments=(), timeout_seconds=480):
        if not 0 < timeout_seconds <= 480:
            raise ValueError("invalid_worker_deadline")
        self.root = Path(root).resolve()
        self.arguments = tuple(arguments)  # trusted operator CLI, never host/tool fields
        self.timeout = timeout_seconds
        self.process = None
        self.deadline = None

    async def __aenter__(self):
        environment = {
            k: v
            for k, v in os.environ.items()
            if k in {"PATH", "LANG", "LC_ALL", "TMPDIR", "HF_HOME", "HF_HUB_CACHE"}
        }
        environment.update(
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            LANGSMITH_TRACING="false",
            LANGCHAIN_TRACING_V2="false",
            CUDA_VISIBLE_DEVICES="",
        )
        self.deadline = asyncio.get_running_loop().time() + self.timeout
        self.process = await asyncio.create_subprocess_exec(
            str(self.root / ".venv/bin/python"),
            "-m",
            "scripts.explanation_worker",
            *self.arguments,
            cwd=self.root,
            env=environment,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=MAX_LINE_BYTES + 1,
            start_new_session=True,
        )
        return self

    async def close(self):
        if self.process and self.process.returncode is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await self.process.wait()

    async def __aexit__(self, *args):
        await self.close()

    async def request(self, message):
        if self.process is None:
            raise WorkerError("worker_not_started")
        try:
            raw = json.dumps(message, allow_nan=False).encode() + b"\n"
            if len(raw) > MAX_LINE_BYTES:
                raise ValueError("input_limit")
            remaining = self.deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError
            async with asyncio.timeout(remaining):
                self.process.stdin.write(raw)
                await self.process.stdin.drain()
                reply = await self.process.stdout.readline()
            if len(reply) > MAX_LINE_BYTES or not reply.endswith(b"\n"):
                raise ValueError("invalid_worker_output")
            result = json.loads(reply)
            if type(result) is not dict or "worker_error" in result:
                raise ValueError("invalid_worker_output")
            return result
        except asyncio.CancelledError:
            await self.close()
            raise
        except Exception:  # noqa: BLE001 - sanitize IPC errors and always reap the child
            await self.close()
            raise WorkerError("worker_failed") from None
