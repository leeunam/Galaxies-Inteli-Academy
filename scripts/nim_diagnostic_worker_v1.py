"""Offline-only instrumented ROOT bridge; no remote route or credential access."""

import argparse
import json
import sys
import time

from orchestration.galaxies_orchestration.nim_diagnostic_contract_v1 import (
    empty_diagnostic,
    validate_diagnostic,
)
from scripts.nim_graph_bridge_v1 import MAX_LINE, BridgeSession, canonical, fake_response, unique
from scripts.nim_observed_http_worker_v3 import protocol_ok
from scripts.nim_response_observer_v2 import observe_response
from scripts.nim_selection_diagnostic_v1 import evaluate_original

CASES = {
    "valid",
    "wrong_hash",
    "secret_id",
    "http_error",
    "invalid_wire",
    "hang",
    "too_many_ids",
    "duplicate_ids",
    "scalar_ids",
    "extra_field",
    "deep_json",
}


def invented_response(case, public):
    if case not in {"too_many_ids", "duplicate_ids", "scalar_ids", "extra_field", "deep_json"}:
        return fake_response(case, public["request"]["packet_sha256"])
    ids = [fact["evidence_id"] for fact in public["request"]["packet"]["evidence"]]
    body = {"packet_sha256": public["request"]["packet_sha256"], "evidence_ids": ids[:13]}
    if case == "duplicate_ids":
        body["evidence_ids"] = [ids[0], ids[0]]
    elif case == "scalar_ids":
        body["evidence_ids"] = ids[0]
    elif case == "extra_field":
        body = {
            "packet_sha256": public["request"]["packet_sha256"],
            "evidence_ids": ids[:1],
            "ENTIRELY_INVENTED_UNKNOWN_NAME": "ENTIRELY_INVENTED_UNKNOWN_VALUE",
        }
    content = "[" * 2500 + "]" * 2500 if case == "deep_json" else canonical(body).decode()
    wire = canonical(
        {
            "choices": [
                {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
            ],
            "usage": {"completion_tokens": 96},
        }
    )

    class Response:
        status = 200

        def getheaders(self):
            return [("Content-Type", "application/json")]

        def read(self, size):
            if size != 16385:
                raise ValueError("diagnostic_bounded_read_required")
            return wire[:size]

    return Response()


class DiagnosticSession(BridgeSession):
    def __init__(self, case, run_id):
        if case not in CASES:
            raise ValueError("diagnostic_unknown_offline_case")
        super().__init__("valid", run_id)
        self.diagnostic_case = case

    def handle(self, message):
        if message.get("op") != "select":
            return super().handle(message)
        if self.events != ["analyze", "shap", "comparables", "context"]:
            raise ValueError("diagnostic_invalid_select_transition")
        self.events.append("select")
        if (
            set(message) != {"op", "request"}
            or type(message["request"]) is not str
            or (
                canonical(json.loads(message["request"], object_pairs_hook=unique))
                != canonical(self.public["request"])
            )
        ):
            raise ValueError("diagnostic_requires_fixed_public_request")
        if self.diagnostic_case == "hang":
            time.sleep(60)
        response = invented_response(self.diagnostic_case, self.public)
        captured = None

        def capture(render_message):
            nonlocal captured
            captured = render_message["selection"]
            return {"selection_observation": {}}

        if not protocol_ok(response):
            raise ValueError("diagnostic_framing_rejected")
        observed = observe_response(response, capture)["selection_observation"]
        self.transport = {
            key: observed[key] for key in ("http_status", "wire_bytes", "completion_tokens")
        }
        if captured is None:
            self.transport["code"] = observed["code"]
            phase = "transport" if observed["phase"] == "transport" else "envelope"
            diagnostic = empty_diagnostic(phase=phase, code=observed["code"])
        else:
            evaluated = evaluate_original(self.session.context, captured)
            self.selection = evaluated["selection"]
            self.selection_accepted = self.selection is not None
            self.transport["code"] = (
                "selection_accepted" if self.selection_accepted else "selection_rejected"
            )
            diagnostic = evaluated["diagnostic"]
        return {"selection": self.selection, "diagnostic": validate_diagnostic(diagnostic)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-case", choices=sorted(CASES), required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        session = DiagnosticSession(args.offline_case, args.run_id)
        for _ in range(7):
            raw = sys.stdin.buffer.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                raise ValueError("diagnostic_ipc_input_limit")
            result = session.handle(json.loads(raw, object_pairs_hook=unique))
            encoded = canonical(result) + b"\n"
            if len(encoded) > MAX_LINE:
                raise ValueError("diagnostic_ipc_output_limit")
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
    except Exception:  # noqa: BLE001 - no unknown input, values, errors or paths leave IPC
        sys.stdout.buffer.write(b'{"worker_error":"worker_failed"}\n')
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
