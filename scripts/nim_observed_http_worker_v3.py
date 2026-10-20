"""Bounded child: fixed request, then sealed validation/observation before stdout."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import ssl
import sys
import time
from pathlib import Path

from scripts.nim_dispatch_ledger_v3 import authorize
from scripts.nim_dispatch_plan_v3 import HOST, PATH, payload_bytes, verify_plan
from scripts.nim_dispatch_seal_v3 import PLAN_SHA256
from scripts.nim_dispatch_summary_v3 import summarize, transport_failure


def protocol_ok(response):
    """Read only framing fields; never retain arbitrary headers or their hashes."""
    headers = response.getheaders()
    if len(headers) > 100 or sum(len(k) + len(v) for k, v in headers) > 16384:
        return False
    fields = {}
    for key, value in headers:
        name = key.lower()
        if name in {"content-type", "content-length", "content-encoding", "transfer-encoding"}:
            if name in fields:
                return False
            fields[name] = value.strip().lower()
    length, transfer = fields.get("content-length"), fields.get("transfer-encoding")
    return (
        fields.get("content-type", "").split(";", 1)[0] == "application/json"
        and fields.get("content-encoding", "identity") == "identity"
        and transfer in {None, "chunked"}
        and not (length is not None and transfer is not None)
        and (length is None or (length.isascii() and length.isdecimal() and int(length) <= 16384))
    )


def exchange(key, *, factory, timeout=45):
    """Private implementation seam; caller must have durably authorized first.

    factory is mandatory: the offline route never defaults to a real socket.
    The remote route below is separately sealed and currently unreachable.
    """
    if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{20,512}", key):
        return transport_failure("request_failed_outcome_uncertain")
    connection = None
    try:
        body = payload_bytes()
        from scripts.explanation_observer_v2 import ObservationSession
        from scripts.nim_response_observer_v2 import observe_response

        session = ObservationSession()
        session.handle({"op": "prepare", "payload": {}})
        connection = factory(HOST, port=443, timeout=timeout, context=ssl.create_default_context())
        connection.set_debuglevel(0)
        connection.request(
            "POST",
            PATH,
            body=body,
            headers={
                "Authorization": "Bearer " + key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status == 200 and not protocol_ok(response):
            return transport_failure("protocol_rejected")
        return summarize(observe_response(response, session.handle))
    except Exception:  # noqa: BLE001 - never project exception, key, header or raw body
        return transport_failure("request_failed_outcome_uncertain")
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001, S110 - transport exceptions must not be logged
                pass


def remote_exchange(folder, nonce):
    """Prepared entrypoint, blocked before reservation/credential/socket access.

    No CLI calls this function. Future release requires a new reviewed plan and
    external seal, including applicable account evidence; changing a flag cannot
    authorize the current offline plan. The remote ledger has no caller override.
    """
    from scripts.nim_dispatch_plan_v3 import LEDGER

    verify_plan(remote=True)
    if folder != LEDGER:
        raise ValueError("v3_fixed_remote_ledger_required")
    authorize(LEDGER, nonce, PLAN_SHA256, offline=False)
    # Importing this function does not access a credential; call is after both gates.
    from orchestration.galaxies_orchestration.nim_http import existing_key

    return exchange(existing_key(), factory=http.client.HTTPSConnection)


def main():
    # Remote mode is refused by the current external seal before any key/socket.
    from scripts.nim_dispatch_fakes_v3 import CASES, INVENTED_KEY, connection_factory

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline-case", choices=sorted(CASES))
    mode.add_argument("--released-remote", action="store_true")
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args()
    result = {"worker_status": "worker_failed_outcome_uncertain"}
    try:
        started = time.monotonic()
        verify_plan(remote=args.released_remote)
        nonce = sys.stdin.buffer.read(33)
        if args.released_remote:
            summary = remote_exchange(Path(args.ledger), nonce)
        else:
            authorize(args.ledger, nonce, PLAN_SHA256, offline=True)
            remaining = 45 - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError
            summary = exchange(
                INVENTED_KEY, factory=connection_factory(args.offline_case), timeout=remaining
            )
        result = {
            "worker_status": "observed",
            "summary": summary,
        }
    except Exception:  # noqa: BLE001, S110 - sanitized stdout only, never exception logs
        pass
    sys.stdout.write(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
