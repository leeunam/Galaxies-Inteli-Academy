"""Identified offline transports. No socket or real credential lookup exists here."""

import json
import time

from orchestration.galaxies_orchestration.observation_cases_v2 import (
    EXPECTED,
    WIRE_EXPECTED,
    content,
)
from scripts.nim_response_observer_v2 import invented_response

INVENTED_KEY = "entirely-invented-v3-test-key-00000000"
INVENTED_SECRET = "f" * 64
CASES = (
    frozenset(EXPECTED)
    | frozenset(WIRE_EXPECTED)
    | {
        "redirect",
        "send_failure",
        "hang",
        "crash",
        "bad_content_type",
        "compressed",
        "large_content_length",
        "ambiguous_length",
        "bad_transfer_encoding",
        "tokens_limit",
        "bad_status",
        "bad_wire_type",
        "close_failure",
    }
)


def connection_factory(case):
    if case not in CASES:
        raise ValueError("v3_unknown_offline_case")

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def set_debuglevel(self, level):
            if level != 0:
                raise ValueError("v3_debug_forbidden")

        def request(self, *args, **kwargs):
            if case == "send_failure":
                raise RuntimeError(INVENTED_SECRET)
            if case == "crash":
                import os

                os._exit(17)
            if case == "hang":
                time.sleep(60)

        def getresponse(self):
            response = invented_response(
                case if case in WIRE_EXPECTED else "valid", secret=INVENTED_SECRET
            )
            if case in EXPECTED:
                wire = json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": content(case, secret=INVENTED_SECRET),
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"completion_tokens": 10},
                    }
                ).encode()
                response.read = lambda size: wire[:size]
            if case == "tokens_limit":
                response.read = lambda size: b'{"choices":[],"usage":{"completion_tokens":2049}}'
            if case == "redirect":
                response.status = 302
            if case == "bad_status":
                response.status = True
            if case == "bad_wire_type":
                response.read = lambda size: INVENTED_SECRET
            headers = [("Content-Type", "application/json"), ("X-Invented-Secret", INVENTED_SECRET)]
            if case == "bad_content_type":
                headers[0] = ("Content-Type", "text/html")
            if case == "compressed":
                headers.append(("Content-Encoding", "gzip"))
            if case == "large_content_length":
                headers.append(("Content-Length", "16385"))
            if case == "ambiguous_length":
                headers.extend([("Content-Length", "10"), ("Transfer-Encoding", "chunked")])
            if case == "bad_transfer_encoding":
                headers.append(("Transfer-Encoding", "invented"))
            response.getheaders = lambda: headers
            return response

        def close(self):
            if case == "close_failure":
                raise RuntimeError(INVENTED_SECRET)

    return Connection
