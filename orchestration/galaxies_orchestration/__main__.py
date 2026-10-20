"""Local graph CLI. No provider is configured by this command."""

import argparse
import asyncio
import json
import sys

from galaxies_orchestration.graph import build_graph
from galaxies_orchestration.worker import MAX_LINE_BYTES, RootWorker, WorkerError


async def run(payload, arguments):
    async with RootWorker(arguments=arguments) as worker:
        return (await build_graph(worker).ainvoke({"payload": payload}))["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-arguments", nargs=argparse.REMAINDER, default=[])
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_LINE_BYTES + 1)
        if len(raw) > MAX_LINE_BYTES:
            raise ValueError("input_limit")
        payload = json.loads(raw)
        if type(payload) is not dict:
            raise ValueError("input_object_required")
        result = asyncio.run(run(payload, args.worker_arguments))
    except (ValueError, WorkerError):
        print('{"orchestration_error":"local_graph_failed"}')
        return
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
