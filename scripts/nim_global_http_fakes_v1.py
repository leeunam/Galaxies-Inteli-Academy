"""Invented opening of the exact fixed request; no socket, key getter or model."""

import json
import ssl

from orchestration.galaxies_orchestration.nim_global_selection_payload_v1 import payload_bytes
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import MODEL, canonical, digest
from scripts.nim_worker_diagnostic_v3 import fake_open_response

INVENTED_KEY = "ENTIRELY_INVENTED_OFFLINE_KEY_0123456789"


def connection_factory(case, public, trace=None, *, consumed_folder=None):
    trace = {} if trace is None else trace
    trace.update(created=0, posts=0, responses=0, closed=0)

    class Connection:
        def set_debuglevel(self, level):
            assert type(level) is int and level == 0

        def request(self, method, path, *, body, headers):
            trace["posts"] += 1
            assert trace["posts"] == 1 and trace["responses"] == 0
            assert method == "POST" and path == "/v1/chat/completions"
            assert body == payload_bytes() and len(body) == 10065
            assert (
                digest(body) == "b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987"
            )
            value = json.loads(body)
            assert value["model"] == MODEL and value["max_tokens"] == 2048
            assert value["temperature"] == 0.2 and value["stream"] is False
            assert value["chat_template_kwargs"] == {"enable_thinking": False}
            assert "response_format" not in value and "nvext" not in value
            assert headers == {
                "Authorization": "Bearer " + INVENTED_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

        def getresponse(self):
            trace["responses"] += 1
            assert trace["posts"] == 1 and trace["responses"] == 1
            if case != "twentyone_ids":
                return fake_open_response(case, public)
            # Structural simulation only: real rejected ID values were not retained.
            content = canonical(
                {
                    "packet_sha256": public["request"]["packet_sha256"],
                    "evidence_ids": [
                        fact["evidence_id"] for fact in public["request"]["packet"]["evidence"][:21]
                    ],
                }
            ).decode("ascii")
            wire = canonical(
                {
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"completion_tokens": 262},
                }
            )

            class Response:
                status = 200

                def getheaders(self):
                    return [("content-type", "application/json")]

                def read(self, size):
                    assert size == 16385
                    return wire[:size]

            return Response()

        def close(self):
            trace["closed"] += 1
            assert trace["closed"] == 1

    def factory(host, *, port, timeout, context):
        if consumed_folder is not None:
            marker = consumed_folder / "dispatch-v3.json"
            assert not marker.is_symlink() and marker.stat().st_size <= 2048
            assert json.loads(marker.read_bytes()) == {
                "state": "consumed_before_transport",
                "offline_simulation_only": True,
            }
        trace["created"] += 1
        assert trace["created"] == 1
        assert host == "integrate.api.nvidia.com" and port == 443
        assert type(timeout) in (int, float) and 0 < timeout <= 43
        assert isinstance(context, ssl.SSLContext) and context.check_hostname
        assert context.verify_mode == ssl.CERT_REQUIRED
        return Connection()

    return factory
