"""The graph's single ROOT child owns HTTP itself; it spawns no HTTP child."""

import argparse
import http.client
import json
import os
import re
import ssl
import sys
import time
from pathlib import Path

from orchestration.galaxies_orchestration import nim_graph_live_contract_v1 as contract
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import CASES, canonical, unique
from scripts.explanation_evidence import validate_selection
from scripts.nim_dispatch_ledger_v3 import authorize
from scripts.nim_graph_bridge_v1 import MAX_LINE, BridgeSession, fake_response
from scripts.nim_observed_http_worker_v3 import protocol_ok
from scripts.nim_response_observer_v2 import observe_response


def live_response(key, *, timeout):
    """One fixed direct POST. No redirect/proxy/SDK/retry; no body/error logging."""
    if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{20,512}", key):
        raise ValueError("live_graph_key_invalid")
    body = contract.payload_bytes()
    if len(body) != 8576 or contract.digest(body) != contract.PAYLOAD_SHA256:
        raise ValueError("live_graph_payload_changed_before_socket")
    if type(timeout) not in (int, float) or not 0 < timeout <= 45:
        raise ValueError("live_graph_socket_deadline_invalid")
    connection = http.client.HTTPSConnection(
        "integrate.api.nvidia.com", port=443, timeout=timeout, context=ssl.create_default_context()
    )
    try:
        connection.set_debuglevel(0)
        connection.request(
            "POST",
            "/v1/chat/completions",
            body=body,
            headers={
                "Authorization": "Bearer " + key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        return connection, connection.getresponse()
    except BaseException:
        connection.close()
        raise


class LiveBridge(BridgeSession):
    def __init__(self, folder, run_id, *, offline_case=None):
        self.plan = contract.verify_plan()
        self.offline = offline_case is not None
        self.folder = contract.simulation_folder(folder) if self.offline else contract.LEDGER
        if not self.offline and Path(folder) != contract.LEDGER:
            raise ValueError("live_graph_fixed_ledger_required")
        if (self.folder / "graph-result-live-v1.json").exists():
            raise ValueError("live_graph_attempt_already_finalized")
        self.review_hash = None if self.offline else contract.check_review(self.plan)
        self.bound = contract.check_binding(
            self.folder,
            self.plan,
            self.review_hash,
            run_id,
            offline=self.offline,
            owner_pid=os.getppid(),
        )
        self.nonce = None
        self.attempted = False
        self.offline_case = offline_case
        super().__init__("valid", run_id)

    def authorize_message(self, message):
        if (
            self.nonce is not None
            or type(message) is not dict
            or set(message) != {"op", "nonce"}
            or (
                message["op"] != "authorize"
                or type(message["nonce"]) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", message["nonce"])
            )
        ):
            raise ValueError("live_graph_initial_authorization_required")
        self.nonce = bytes.fromhex(message["nonce"])
        return {"authorization": "bound_before_context"}

    def handle(self, message):
        if self.nonce is None:
            raise ValueError("live_graph_initial_authorization_required")
        if message.get("op") == "select":
            if self.events != ["analyze", "shap", "comparables", "context"]:
                raise ValueError("live_graph_select_transition_invalid")
            self.events.append("select")
            if (
                set(message) != {"op", "request"}
                or type(message["request"]) is not str
                or (
                    canonical(json.loads(message["request"], object_pairs_hook=unique))
                    != canonical(self.public["request"])
                )
            ):
                raise ValueError("live_graph_packet_not_authorized")
            contract.verify_plan()
            review_hash = None if self.offline else contract.check_review(self.plan)
            contract.check_binding(
                self.folder,
                self.plan,
                review_hash,
                self.run_id,
                offline=self.offline,
                owner_pid=os.getppid(),
            )
            remaining = self.bound["deadline_monotonic"] - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if (self.folder / "graph-result-live-v1.json").exists():
                raise ValueError("live_graph_attempt_already_finalized")
            # Exact old codec/guard: nonce and ACTUAL direct parent PID, no spoof.
            authorize(self.folder, self.nonce, contract.PLAN_SHA256, offline=self.offline)
            connection = None
            captured = None
            self.transport = {
                "http_status": None,
                "wire_bytes": None,
                "completion_tokens": None,
                "code": "request_failed_outcome_uncertain",
            }
            try:
                if self.offline:
                    if self.offline_case == "hang":
                        time.sleep(60)
                    response = fake_response(
                        self.offline_case, self.public["request"]["packet_sha256"]
                    )
                else:
                    from orchestration.galaxies_orchestration.nim_http import existing_key

                    key = existing_key()  # only here, AFTER durable dispatch
                    self.attempted = True
                    connection, response = live_response(key, timeout=remaining)

                def capture(render_message):
                    nonlocal captured
                    captured = render_message["selection"]
                    return {"selection_observation": {}}

                if response.status == 200 and not protocol_ok(response):
                    self.transport["code"] = "protocol_rejected"
                else:
                    observation = observe_response(response, capture)["selection_observation"]
                    self.transport = {
                        k: observation[k]
                        for k in ("http_status", "wire_bytes", "completion_tokens")
                    } | {"code": observation.get("code", "envelope_valid")}
                    if captured is not None:
                        try:
                            validate_selection(self.session.context, captured)
                            self.selection = canonical(
                                json.loads(captured, object_pairs_hook=unique)
                            ).decode("ascii")
                            self.selection_accepted = True
                            self.transport["code"] = "selection_accepted"
                        except Exception:  # noqa: BLE001 - raw provider content never crosses IPC
                            self.transport["code"] = "selection_rejected"
            except Exception:  # noqa: BLE001, S110 - no raw key/header/body/exception projection
                pass
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:  # noqa: BLE001, S110
                        pass
            return {"selection": self.selection}
        result = super().handle(message)
        if message["op"] == "proof":
            result.update(
                origin="offline_fake" if self.offline else "live_nim",
                real_http_requests=0
                if self.offline
                else (
                    1
                    if self.attempted and self.transport["http_status"] is not None
                    else None
                    if self.attempted
                    else 0
                ),
                live_dispatch=None
                if self.offline
                else {
                    "run_id": self.run_id,
                    "plan_sha256": contract.PLAN_SHA256,
                    "configuration_sha256": self.plan["configuration_sha256"],
                    "specific_remote_authorization_id": contract.AUTHORIZATION_ID,
                    "technical_review_sha256": self.review_hash,
                    "state": "consumed_before_transport",
                },
            )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--released", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(CASES))
    parser.add_argument("--simulation-ledger")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.released and args.simulation_ledger is not None:
            raise ValueError("live_graph_fixed_ledger_required")
        session = LiveBridge(
            contract.LEDGER if args.released else Path(args.simulation_ledger),
            args.run_id,
            offline_case=args.offline_case,
        )
        for index in range(8):
            raw = sys.stdin.buffer.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                raise ValueError("live_graph_input_limit")
            message = json.loads(raw, object_pairs_hook=unique)
            result = session.authorize_message(message) if index == 0 else session.handle(message)
            encoded = canonical(result) + b"\n"
            if len(encoded) > MAX_LINE:
                raise ValueError("live_graph_output_limit")
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
    except Exception:  # noqa: BLE001 - stdout contains only bounded protocol or static failure
        sys.stdout.buffer.write(b'{"worker_error":"worker_failed"}\n')
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
