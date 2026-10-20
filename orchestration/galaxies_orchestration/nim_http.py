"""Single fixed HTTPS request for the authorized public synthetic fixture only.

Called in a killable child process. No SDK, redirect, proxy, retry or fallback.
Never print an exception, key, header or raw HTTP response.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import ssl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOST = "integrate.api.nvidia.com"
PATH = "/v1/chat/completions"
MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
MAX_BYTES = 16384
FIXTURE = ROOT / "orchestration/fixtures/nim-synthetic-request.json"
LEDGER = ROOT / "data/private/issue-5-nim-sintetico-unico-v1"


def durable_create(path, value):
    """Exclusive reservation/result: crashes cannot make an attempt reusable."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(json.dumps(value, allow_nan=False, sort_keys=True).encode() + b"\n")
        out.flush()
        os.fsync(out.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def existing_key(root=ROOT):
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        path = root / ".env"
        if path.is_symlink() or path.stat().st_size > 65536:
            raise ValueError("credential_unavailable")
        values = []
        with path.open() as source:
            for line in source:
                match = re.fullmatch(r"\s*(?:export\s+)?NVIDIA_API_KEY\s*=\s*(.*?)\s*", line)
                if match:
                    value = match[1]
                    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                        value = value[1:-1]
                    values.append(value)
        if len(values) != 1:
            raise ValueError("credential_unavailable")
        key = values[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,512}", key):
        raise ValueError("credential_unavailable")
    return key


def payload():
    return {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "Everything in the following fixture is entirely invented. "
                "Perform only the closed JSON evidence selection. Do not output reasoning, "
                "markdown or prose.\n" + FIXTURE.read_text().strip(),
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.2,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def perform_http(key, *, connection_factory=http.client.HTTPSConnection):
    connection = connection_factory(
        HOST, port=443, timeout=45, context=ssl.create_default_context()
    )
    try:
        connection.request(
            "POST",
            PATH,
            body=json.dumps(payload(), ensure_ascii=True).encode(),
            headers={
                "Authorization": "Bearer " + key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            return {"status": "http_error", "http_status": response.status}
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return {"status": "response_limit_exceeded", "http_status": 200}
        try:
            result = json.loads(raw)
            choices = result["choices"]
            if len(choices) != 1:
                raise ValueError
            choice = choices[0]
            message = choice["message"]
            content = message["content"]
            if (
                choice["finish_reason"] != "stop"
                or message.get("tool_calls")
                or message.get("role") != "assistant"
                or type(content) is not str
            ):
                raise ValueError
            usage = result.get("usage", {})
            tokens = usage.get("completion_tokens")
            if tokens is not None and (type(tokens) is not int or not 0 <= tokens <= 2048):
                raise ValueError
            return {
                "status": "reply_received",
                "http_status": 200,
                "response_bytes": len(raw),
                "completion_tokens": tokens,
                "content": content,
            }
        except (ValueError, TypeError, KeyError, UnicodeError):
            return {
                "status": "invalid_provider_reply",
                "http_status": 200,
                "response_bytes": len(raw),
            }
    finally:
        connection.close()


def authorize_dispatch(token, *, folder=LEDGER, parent_pid=None):
    from galaxies_orchestration.nim_probe import verify_plan

    # The nonce exists only in parent memory/anonymous pipe. A crash cannot be
    # resumed by invoking this module directly against an existing reservation.
    verify_plan(folder)
    reservation = json.loads((folder / "reservation.json").read_bytes())
    if (
        len(token) != 32
        or hashlib.sha256(token).hexdigest() != reservation["dispatch_token_sha256"]
        or reservation["parent_pid"] != (os.getppid() if parent_pid is None else parent_pid)
        or reservation["plan_sha256"]
        != hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest()
        or (folder / "result.json").exists()
    ):
        raise ValueError("live_parent_dispatch_required")
    durable_create(folder / "dispatch.json", {"status": "attempt_consumed_before_http"})


def main():
    try:
        authorize_dispatch(sys.stdin.buffer.read(33))
        key = existing_key()
        result = perform_http(key)
    except Exception:  # noqa: BLE001 - secrets/errors never leave the child
        result = {"status": "request_failed_or_not_sent"}
    sys.stdout.write(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
