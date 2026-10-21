"""Invented six-stage ROOT bridge; existing Session remains numerical authority."""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from orchestration.galaxies_orchestration.nim_graph_contract_v1 import (
    CASES,
    canonical,
    fixture,
    unique,
    verify_plan,
)
from scripts.explanation_evidence import validate_selection
from scripts.explanation_session_v2 import Session
from scripts.m1_evidence import M1Evidence
from scripts.nim_observed_http_worker_v3 import protocol_ok
from scripts.nim_response_observer_v2 import observe_response
from scripts.training_comparables import ComparableResult
from scripts.training_manifest import PredictorInputs

MAX_LINE = 262144


def invented_session(data):
    """All callbacks are invented. No loader, trained model, media or index is read."""
    report = data["report"]
    ids = [candidate["creative_id"] for candidate in report["candidates"]]
    ready = tuple(
        (
            cid,
            PredictorInputs(
                sector="moda",
                duration_seconds=7.0,
                aspect_ratio_height_over_width=1.5,
                text_status="extracted",
                text_embedding=tuple([float(i + 1)] * 384),
            ),
            "f" * 64,
        )
        for i, cid in enumerate(ids)
    )
    handoff = SimpleNamespace(
        _features=None,
        ready_inputs=lambda _: ready,
        context=(None, None, None),
        settings=None,
    )
    references = iter(
        ComparableResult.model_validate_json(json.dumps(data["comparables"][cid])) for cid in ids
    )
    index = SimpleNamespace(
        training_samples=124,
        model_artifact_sha256=report["model_artifact_sha256"],
        search=lambda *a, **kw: next(references),
    )

    def analyze(payload):
        if payload != {}:
            raise ValueError("nim_graph_only_empty_synthetic_input")
        return report, handoff

    return Session(
        analyze,
        evidence_root=Path("entirely-invented-not-opened"),
        minimum_similarity=0.5,
        shap_explainer=lambda *a: tuple(
            M1Evidence.model_validate_json(json.dumps(data["shap"][cid])) for cid in ids
        ),
        index_loader=lambda *a, **kw: index,
    )


def fake_response(case, packet_hash):
    selection = {
        "packet_sha256": "0" * 64 if case == "wrong_hash" else packet_hash,
        "evidence_ids": ["ENTIRELY_INVENTED_SECRET_ID"]
        if case == "secret_id"
        else [
            "c1_prediction",
            "c2_prediction",
            "c3_prediction",
            "c1_shap_speech_embedding",
            "c2_shap_speech_embedding",
            "c3_shap_speech_embedding",
            "c1_reference_1",
            "c2_reference_1",
            "c3_reference_1",
        ],
    }
    wire = canonical(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": canonical(selection).decode()},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"completion_tokens": 96},
        }
    )
    if case == "invalid_wire":
        wire = b"ENTIRELY_INVENTED_SECRET_BODY"

    class Response:
        status = 503 if case == "http_error" else 200

        def getheaders(self):
            return [("Content-Type", "application/json")]

        def read(self, size):
            if size != 16385:
                raise ValueError("bounded_read_required")
            return wire[:size]

    return Response()


class BridgeSession:
    OPERATIONS = ("analyze", "shap", "comparables", "context", "select", "render", "proof")

    def __init__(self, case, run_id):
        if case not in CASES or not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("nim_graph_invalid_offline_configuration")
        verify_plan()
        self.public = fixture()
        self.session = invented_session(self.public["data"])
        self.case, self.run_id = case, run_id
        self.events, self.selection, self.final = [], None, None
        self.transport = {
            "http_status": None,
            "wire_bytes": None,
            "completion_tokens": None,
            "code": "not_observed",
        }
        self.selection_accepted = False

    def handle(self, message):
        op = self.OPERATIONS[len(self.events)] if len(self.events) < 7 else None
        if type(message) is not dict or message.get("op") != op:
            raise ValueError("nim_graph_invalid_transition")
        self.events.append(op)  # consumed before a callback, blocking or failure
        if op == "select":
            if set(message) != {"op", "request"} or type(message["request"]) is not str:
                raise ValueError("nim_graph_invalid_selector_input")
            request = json.loads(message["request"], object_pairs_hook=unique)
            if canonical(request) != canonical(self.public["request"]):
                raise ValueError("nim_graph_packet_not_authorized")
            if self.case == "hang":
                time.sleep(60)  # exclusively a fake cancellation/deadline control
            response = fake_response(self.case, request["packet_sha256"])
            captured = None

            def capture(render_message):
                nonlocal captured
                captured = render_message["selection"]
                return {"selection_observation": {}}

            if not protocol_ok(response):
                raise ValueError("nim_graph_framing_rejected")
            observation = observe_response(response, capture)["selection_observation"]
            self.transport = {
                key: observation[key] for key in ("http_status", "wire_bytes", "completion_tokens")
            } | {"code": observation.get("code", "envelope_valid")}
            if captured is not None:
                try:
                    # Original content FIRST reaches unchanged root authority.
                    # Only public known selection values can leave this process.
                    validate_selection(self.session.context, captured)
                    body = json.loads(captured, object_pairs_hook=unique)
                    self.selection = canonical(body).decode("ascii")
                    self.selection_accepted = True
                    self.transport["code"] = "selection_accepted"
                except Exception:  # noqa: BLE001 - never emit input/error/value/hash
                    self.transport["code"] = "selection_rejected"
            return {"selection": self.selection}
        if op == "proof":
            if set(message) != {"op"} or self.final is None:
                raise ValueError("nim_graph_invalid_proof_request")
            return {
                "origin": "offline_fake",
                "run_id": self.run_id,
                "packet_sha256": self.public["request"]["packet_sha256"],
                "real_http_requests": 0,
                "live_dispatch": None,
                "root_selection_accepted": self.selection_accepted,
                "root_render_accepted": self.final["explanation"]["status"]
                == "validated_catalogue_selection",
                "transport": self.transport,
                "events": list(self.events),
            }
        if op == "render" and message.get("selection") != self.selection:
            raise ValueError("nim_graph_selection_changed_after_root_validation")
        result = self.session.handle(message)
        if op == "render":
            self.final = result
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-case", required=True, choices=sorted(CASES))
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        session = BridgeSession(args.offline_case, args.run_id)
        for _ in range(7):
            raw = sys.stdin.buffer.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                raise ValueError("nim_graph_input_limit")
            result = session.handle(json.loads(raw, object_pairs_hook=unique))
            encoded = canonical(result) + b"\n"
            if len(encoded) > MAX_LINE:
                raise ValueError("nim_graph_output_limit")
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
    except Exception:  # noqa: BLE001 - no raw request, provider content, exception or path
        sys.stdout.buffer.write(b'{"worker_error":"worker_failed"}\n')
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
