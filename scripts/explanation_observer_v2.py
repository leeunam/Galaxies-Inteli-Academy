"""Additive synthetic root worker: sealed validation first, safe observation next."""

import sys

from scripts.explanation_synthetic_worker import SyntheticSession
from scripts.explanation_worker import serve
from scripts.nim_response_observer_v2 import invented_response, observe_response
from scripts.selection_observation_v2 import after_authority_exception, after_sealed_validation


class ObservationSession(SyntheticSession):
    def handle(self, message):
        if message.get("op") == "observe_http_fixture":
            from orchestration.galaxies_orchestration.observation_cases_v2 import WIRE_EXPECTED

            if (
                not self.prepared
                or self.finished
                or message.get("case") not in WIRE_EXPECTED
                or set(message) != {"op", "case", "fixture_secret"}
            ):
                raise ValueError("invalid_offline_response_request")
            secret = message["fixture_secret"]
            if secret is not None and (
                type(secret) is not str
                or len(secret) != 64
                or any(c not in "0123456789abcdef" for c in secret)
            ):
                raise ValueError("invalid_invented_fixture_secret")
            return observe_response(invented_response(message["case"], secret=secret), self.handle)
        try:
            result = super().handle(message)  # unchanged sealed authority and rendering
        except Exception as error:
            if message.get("op") != "render":
                raise
            return {
                "observer_worker_failure": True,
                "selection_observation": after_authority_exception(
                    self.context, message.get("selection"), error
                ),
            }
        if message["op"] == "render":
            if message["selection"] is None:
                result["selection_observation"] = {
                    "phase": "validation",
                    "code": "not_invoked",
                    "authority_accepted": False,
                    "authority_status": "not_invoked",
                    "rendering_status": "not_completed",
                    "safe_response_projection": None,
                    "retained_projection_sha256": None,
                    "raw_response_sha256": None,
                    "retention": "suppressed_untrusted_source",
                }
            else:
                result["selection_observation"] = after_sealed_validation(
                    self.context, message["selection"], result
                )
        return result


if __name__ == "__main__":
    serve(ObservationSession(), sys.stdin.buffer, sys.stdout.buffer)
