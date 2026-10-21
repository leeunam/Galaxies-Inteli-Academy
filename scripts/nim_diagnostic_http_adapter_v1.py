"""Consume an already-open response; owns no socket, credential or authorization."""

from orchestration.galaxies_orchestration.nim_diagnostic_contract_v1 import (
    empty_diagnostic,
    validate_diagnostic,
)
from scripts.nim_observed_http_worker_v3 import protocol_ok
from scripts.nim_response_observer_v2 import observe_response
from scripts.nim_selection_diagnostic_v1 import evaluate_original


def observe_opened_response(context, response):
    captured = None

    def capture(message):
        nonlocal captured
        captured = message["selection"]
        return {"selection_observation": {}}

    try:
        framing_valid = response.status != 200 or protocol_ok(response)
    except Exception:  # noqa: BLE001 - arbitrary headers/errors never leave the adapter
        framing_valid = False
    if not framing_valid:
        return {
            "selection": None,
            "diagnostic": empty_diagnostic(phase="transport", code="protocol_rejected"),
            "transport": {
                "http_status": None,
                "wire_bytes": None,
                "completion_tokens": None,
                "code": "protocol_rejected",
            },
        }
    observed = observe_response(response, capture)["selection_observation"]
    transport = {key: observed[key] for key in ("http_status", "wire_bytes", "completion_tokens")}
    if captured is None:
        transport["code"] = observed["code"]
        phase = "transport" if observed["phase"] == "transport" else "envelope"
        result = {
            "selection": None,
            "diagnostic": empty_diagnostic(phase=phase, code=observed["code"]),
        }
    else:
        result = evaluate_original(context, captured)
        transport["code"] = (
            "selection_accepted" if result["selection"] is not None else "selection_rejected"
        )
    validate_diagnostic(result["diagnostic"])
    return result | {"transport": transport}
