"""Root worker in the supervisor-owned group, with explicit Python/code paths."""

import asyncio
import json
import os
from pathlib import Path

MAX_LINE = 262144


class IntegratedWorker:
    def __init__(
        self, python, root, arguments=(), *, module="scripts.explanation_worker_v2", timeout=420
    ):
        self.python, self.root, self.arguments = str(python), Path(root), tuple(arguments)
        self.module, self.timeout = module, timeout
        self.process = None

    async def __aenter__(self):
        environment = {
            "PATH": os.defpath,
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "LANGSMITH_TRACING": "false",
            "LANGCHAIN_TRACING_V2": "false",
            "CUDA_VISIBLE_DEVICES": "",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "4",
            "GALAXIES_SUPERVISED_GROUP": str(os.getpgrp()),
        }
        self.deadline = asyncio.get_running_loop().time() + self.timeout
        self.process = await asyncio.create_subprocess_exec(
            self.python,
            "-B",
            "-m",
            self.module,
            *self.arguments,
            cwd=self.root,
            env=environment,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=MAX_LINE + 1,
            start_new_session=False,
        )
        return self

    async def __aexit__(self, *args):
        if self.process and self.process.returncode is None:
            self.process.kill()
            await self.process.wait()
        # Supervisor additionally kills/reaps all group descendants, then scratch.

    async def request(self, message):
        raw = json.dumps(message, allow_nan=False).encode() + b"\n"
        if len(raw) > MAX_LINE:
            raise ValueError("worker_input_limit")
        remaining = self.deadline - asyncio.get_running_loop().time()
        async with asyncio.timeout(max(0, remaining)):
            self.process.stdin.write(raw)
            await self.process.stdin.drain()
            reader = asyncio.create_task(self.process.stdout.readline())

            async def watch_exit():
                # Process.wait() may itself wait for inherited pipe closure.
                while self.process.returncode is None:
                    await asyncio.sleep(0.01)

            exited = asyncio.create_task(watch_exit())
            try:
                await asyncio.wait((reader, exited), return_when=asyncio.FIRST_COMPLETED)
                if not reader.done():
                    # A grandchild can hold stdout open after its parent dies.
                    # Do not wait on inherited pipe EOF; the supervisor owns it.
                    raise ValueError("worker_exited_before_reply")
                reply = reader.result()
            finally:
                for task in (reader, exited):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(reader, exited, return_exceptions=True)
        if len(reply) > MAX_LINE or not reply.endswith(b"\n"):
            raise ValueError("worker_output_limit")
        body = json.loads(reply)
        if type(body) is not dict or "worker_error" in body:
            raise ValueError("worker_failed")
        return body
