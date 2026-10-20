"""Offline-only observation demo. No NIM execution flag or credential lookup."""

import argparse
import asyncio
import json
import os
import socket
import uuid
from pathlib import Path

from galaxies_orchestration.observation_cases_v2 import EXPECTED, WIRE_EXPECTED, content
from galaxies_orchestration.observation_v2 import Reply, run_observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case")
    parser.add_argument("--http-case")
    parser.add_argument("--output-dir", type=Path)
    args, unknown = parser.parse_known_args()
    local_content = args.case in {*EXPECTED, "json_depth"} and args.http_case is None
    local_http = args.http_case in WIRE_EXPECTED and args.case is None
    if unknown or not (local_content or local_http) or args.output_dir is None:
        print('{"status":"invalid_local_arguments"}')
        return

    def forbidden(*args, **kwargs):
        raise RuntimeError("network_forbidden_in_local_observation")

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.getaddrinfo = forbidden
    os.environ.pop("NVIDIA_API_KEY", None)
    # This is a generated test string, never an API credential or authorization nonce.
    fake_secret = uuid.uuid4().hex + uuid.uuid4().hex
    raw = (
        ""
        if local_http
        else (
            "[" * 2500 + "]" * 2500
            if args.case == "json_depth"
            else content(args.case, secret=fake_secret)
        )
    )

    async def callback(request):
        return Reply(raw, wire_bytes=len(raw.encode("utf-8", errors="surrogatepass")) + 64)

    try:
        result = asyncio.run(
            run_observed(
                None if local_http else callback, args.output_dir, envelope_case=args.http_case
            )
        )
        safe = result["observation"]
    except Exception:  # noqa: BLE001 - never echo arguments, paths, input or errors
        safe = {"status": "local_observation_stopped"}
    print(json.dumps(safe, allow_nan=False))


if __name__ == "__main__":
    main()
