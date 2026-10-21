"""One ROOT child owns the authorized HTTP transport after the original nonce guard."""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from orchestration.galaxies_orchestration import nim_worker_diagnostic_contract_v3 as c
from orchestration.galaxies_orchestration.nim_diagnostic_contract_v1 import empty_diagnostic
from scripts.nim_diagnostic_worker_v1 import invented_response
from scripts.nim_dispatch_ledger_v3 import authorize
from scripts.nim_graph_bridge_v1 import MAX_LINE, BridgeSession, canonical, unique
from scripts.nim_graph_live_worker_v1 import live_response
from scripts.nim_http_error_observer_v1 import observe_opened_response

CASES = c.FAKE_CASES


def fake_open_response(case, public):
    # Invented error body is deliberately unreadable; never a replay/provider.
    if case.startswith("adapter_invalid_"):
        return fake_open_response("valid" if case.endswith("200") else "http_503", public)
    if case.startswith("http_"):
        from email.message import Message

        class Response:
            status = int(case.split("_")[1])

            def __init__(self):
                self.headers = Message()
                self.headers["content-type"] = "application/json"
                self.headers["content-length"] = "128"
                self.headers["authorization"] = "ENTIRELY_INVENTED_SECRET"
                self.headers["set-cookie"] = "ENTIRELY_INVENTED_SECRET"
                if not case.endswith("missing"):
                    self.headers["nvcf-reqid"] = (
                        "ENTIRELY_INVENTED_SECRET"
                        if case.endswith("invalid")
                        else "12345678-1234-1234-1234-123456789abc"
                    )
                if case.endswith("duplicate"):
                    self.headers["NVCF-REQID"] = "12345678-1234-1234-1234-123456789abc"
                if case.endswith("long"):
                    self.headers.replace_header("nvcf-reqid", "x" * 129)
                    self.headers.replace_header("content-type", "x" * 129)
                if case.endswith("exception"):
                    self.headers = BrokenHeaders()

            def read(self, size):
                raise AssertionError("worker_diagnostic_error_body_forbidden")

            def getheaders(self):
                raise AssertionError("worker_diagnostic_error_header_enumeration_forbidden")

        class BrokenHeaders:
            def get_all(self, name):
                raise RuntimeError("ENTIRELY_INVENTED_SECRET")

        return Response()
    if case in {
        "wire_limit",
        "wire_at_limit",
        "headers_at_limit",
        "headers_excess",
        "header_chars_at_limit",
        "header_chars_excess",
    }:
        original_response = invented_response("valid", public)

        class Response:
            status = 200

            def getheaders(self):
                entries = [("content-type", "application/json")]
                if case.startswith("header_chars_"):
                    total = 16384 if case == "header_chars_at_limit" else 16385
                    name, secret = "x-invented-aggregate-padding", "ENTIRELY_INVENTED_SECRET"
                    fixed = sum(len(key) + len(value) for key, value in entries) + len(name)
                    entries.append((name, secret + "x" * (total - fixed - len(secret))))
                    assert len(entries) == 2
                    assert sum(len(key) + len(value) for key, value in entries) == total
                if case.startswith("headers_"):
                    entries += [("x-invented-unknown", "ENTIRELY_INVENTED_SECRET")] * (
                        99 if case == "headers_at_limit" else 100
                    )
                return entries

            def read(self, size):
                if size != 16385:
                    raise AssertionError("worker_diagnostic_bounded_read_required")
                if case == "wire_limit":
                    return b"x" * size
                wire = original_response.read(size)
                return wire + b" " * (16384 - len(wire)) if case == "wire_at_limit" else wire

        return Response()
    return invented_response(case, public)


class AttemptSession(BridgeSession):
    def __init__(self, folder, run_id, *, offline_case=None):
        self.offline = offline_case is not None
        if not self.offline:
            c.require_new_authorization()  # BEFORE any file, key, context or socket
        elif offline_case not in CASES:
            raise ValueError("worker_diagnostic_unknown_case")
        self.plan = c.verify_plan()
        self.folder = c.simulation_folder(folder) if self.offline else c.LEDGER
        if not self.offline and Path(folder) != c.LEDGER:
            raise ValueError("worker_diagnostic_fixed_ledger_required")
        if (self.folder / c.RESULT_NAME).exists():
            raise ValueError("worker_diagnostic_already_finalized")
        self.review_hash = None if self.offline else c.check_review(self.plan)
        self.bound = c.check_binding(
            self.folder,
            self.plan,
            self.review_hash,
            run_id,
            offline=self.offline,
            owner_pid=os.getppid(),
        )
        self.nonce = None
        self.offline_case = offline_case
        self.attempted = False
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
            raise ValueError("worker_diagnostic_nonce_required")
        self.nonce = bytes.fromhex(message["nonce"])
        return {"authorization": "bound_before_context"}

    def handle(self, message):
        if self.nonce is None:
            raise ValueError("worker_diagnostic_nonce_required")
        if message.get("op") != "select":
            result = super().handle(message)
            if message["op"] == "proof":
                result.update(
                    origin="offline_fake" if self.offline else "live_nim",
                    real_http_requests=0
                    if self.offline
                    else 1
                    if self.transport["http_status"] is not None
                    else None,
                    live_dispatch=None if self.offline else self.bound_proof(),
                )
            return result
        if self.events != ["analyze", "shap", "comparables", "context"]:
            raise ValueError("worker_diagnostic_select_consumed")
        self.events.append("select")
        if (
            set(message) != {"op", "request"}
            or type(message["request"]) is not str
            or canonical(json.loads(message["request"], object_pairs_hook=unique))
            != canonical(self.public["request"])
        ):
            raise ValueError("worker_diagnostic_packet_changed")
        c.verify_plan()
        review_hash = None if self.offline else c.check_review(self.plan)
        c.check_binding(
            self.folder,
            self.plan,
            review_hash,
            self.run_id,
            offline=self.offline,
            owner_pid=os.getppid(),
        )
        remaining = self.bound["work_deadline_monotonic"] - time.monotonic()
        if remaining <= 0 or (self.folder / c.RESULT_NAME).exists():
            raise ValueError("worker_diagnostic_expired_or_finalized")
        authorize(self.folder, self.nonce, c.PLAN_SHA256, offline=self.offline)
        connection = None
        response_opened = False
        try:
            if self.offline:
                if self.offline_case == "hang":
                    time.sleep(60)
                if self.offline_case == "send_failure":
                    raise RuntimeError("ENTIRELY_INVENTED_UNKNOWN_FAILURE")
                response = fake_open_response(self.offline_case, self.public)
            else:
                c.require_new_authorization()
                from orchestration.galaxies_orchestration.nim_http import existing_key

                self.attempted = True
                connection, response = live_response(existing_key(), timeout=remaining)
            response_opened = True
            evaluated = observe_opened_response(self.session.context, response)
            if self.offline and self.offline_case.startswith("adapter_invalid_"):
                # Closed offline fault injection, never selected by remote mode.
                evaluated["http_error_metadata"] = {"unknown": "ENTIRELY_INVENTED_SECRET"}
            self.selection = evaluated["selection"]
            self.selection_accepted = self.selection is not None
            self.transport = evaluated["transport"]
            metadata, state = c.bound_error_metadata(
                evaluated.get("http_error_metadata"), self.transport["http_status"]
            )
            if "http_error_metadata" not in evaluated:
                metadata, state = None, "invalid_ipc_metadata"
            return {
                "selection": self.selection,
                "diagnostic": evaluated["diagnostic"],
                "http_error_metadata": metadata,
                "http_error_metadata_state": state,
            }
        except Exception:  # noqa: BLE001 - preserve the report with closed failure metadata
            self.selection = None
            self.selection_accepted = False
            self.transport = {
                "http_status": None,
                "wire_bytes": None,
                "completion_tokens": None,
                "code": "request_failed_outcome_uncertain",
            }
            return {
                "selection": None,
                "http_error_metadata": None,
                "http_error_metadata_state": "not_applicable",
                "diagnostic": empty_diagnostic(
                    "failed_before_result" if response_opened else "not_invoked"
                ),
            }
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:  # noqa: BLE001, S110 - no arbitrary error leaves IPC
                    pass

    def bound_proof(self):
        return {
            key: self.bound[key]
            for key in (
                "protocol",
                "plan_sha256",
                "configuration_sha256",
                "specific_remote_authorization_id",
                "authorization_receipt_sha256",
                "technical_review_sha256",
                "run_id",
            )
        } | {"state": "consumed_before_transport"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--released", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(CASES))
    parser.add_argument("--simulation-ledger")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.released:
            c.require_new_authorization()
            if args.simulation_ledger is not None:
                raise ValueError("worker_diagnostic_fixed_ledger_required")
        session = AttemptSession(
            c.LEDGER if args.released else Path(args.simulation_ledger),
            args.run_id,
            offline_case=args.offline_case,
        )
        for index in range(8):
            raw = sys.stdin.buffer.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                raise ValueError("worker_diagnostic_ipc_limit")
            message = json.loads(raw, object_pairs_hook=unique)
            reply = session.authorize_message(message) if index == 0 else session.handle(message)
            encoded = canonical(reply) + b"\n"
            if len(encoded) > MAX_LINE:
                raise ValueError("worker_diagnostic_ipc_limit")
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
    except Exception:  # noqa: BLE001 - no key/body/headers/unknown values/errors leave IPC
        sys.stdout.buffer.write(b'{"worker_error":"worker_failed"}\n')
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
