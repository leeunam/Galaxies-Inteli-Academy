"""Minimal offline checks of the NEW request and post-authority type audit."""

import asyncio
import hashlib
import json
import os

import pytest

from scripts import nim_typed_request_v1 as request
from scripts import nim_typed_worker_v1 as worker
from scripts.nim_dispatch_fakes_v3 import INVENTED_KEY, INVENTED_SECRET
from scripts.nim_dispatch_ledger_v3 import create, reserve
from scripts.nim_dispatch_plan_v3 import payload_bytes as old_payload
from scripts.nim_type_observer_v1 import observe_open_response, validate_observation
from tests.test_nim_dispatch_v3 import no_remote_or_credentials  # noqa: F401

SECRET = "ENTIRELY_INVENTED_UNKNOWN_FIELD_SENTINEL"


def selection():
    fixture = json.loads(request.FIXTURE.read_bytes())
    return {"packet_sha256": fixture["packet_sha256"], "evidence_ids": ["c1_prediction"]}


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.read_count = 0
        self.wire = json.dumps(
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": json.dumps(body)},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"completion_tokens": 10},
            }
        ).encode()

    def read(self, size):
        self.read_count += 1
        assert size == 16385
        return self.wire[:size]


def test_request_delta_is_only_typed_text_not_a_new_endpoint_or_parameter():
    old = json.loads(old_payload())
    new = json.loads(request.payload_bytes())
    assert new["messages"][0]["content"].startswith(old["messages"][0]["content"])
    message = new["messages"][0]["content"]
    assert "Response contract (JSON Schema)" in message and "array<string>" in message
    new["messages"][0]["content"] = old["messages"][0]["content"]
    assert new == old
    schema = request.response_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["evidence_ids"]["items"]["type"] == "string"
    assert len(schema["properties"]["evidence_ids"]["items"]["enum"]) == 5
    assert request.configuration()["technical_review_required"] is True
    assert request.configuration()["specific_remote_authorization_id"] == request.AUTHORIZATION_ID


def test_valid_reply_preserves_authority_and_records_only_public_types():
    response = FakeResponse(selection())
    result = observe_open_response(response)
    assert result["summary"]["selection_validated"] is True
    assert result["type_audit"]["slots"]["evidence_ids"] == ["array"]
    assert result["type_audit"]["slots"]["evidence_ids[*]"] == ["string"]
    assert response.read_count == 1


def test_rejected_type_is_identified_without_coercion_or_acceptance():
    result = observe_open_response(FakeResponse(selection() | {"evidence_ids": "c1_prediction"}))
    assert result["summary"]["code"] == "schema_invalid_type"
    assert result["summary"]["selection_validated"] is False
    assert result["summary"]["safe_response_projection"] is None
    assert result["type_audit"]["slots"]["evidence_ids"] == ["string"]
    assert result["type_audit"]["slots"]["evidence_ids[*]"] == ["not_observed"]


def test_unknown_name_and_value_never_escape_safe_type_audit():
    result = observe_open_response(FakeResponse(selection() | {SECRET: SECRET}))
    assert result["summary"]["selection_validated"] is False
    assert result["summary"]["code"] == "schema_extra_field"
    assert SECRET not in json.dumps(result)


def test_diagnostic_cannot_claim_wrong_type_alongside_accepted_authority():
    result = observe_open_response(FakeResponse(selection()))
    result["type_audit"]["slots"]["evidence_ids"] = ["number"]
    with pytest.raises(ValueError, match="contradicts_accepted_authority"):
        validate_observation(result)


def test_remote_refuses_before_reservation_or_key(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("must_not_reserve_or_start_remote")

    monkeypatch.setattr(request, "reserve", forbidden)
    monkeypatch.setattr(request, "REVIEW", tmp_path / "missing-review.json")
    with pytest.raises(FileNotFoundError):
        asyncio.run(request.execute_remote())
    assert not request.LEDGER.exists()


def test_simulations_never_use_real_namespaces():
    for path in (
        request.LEDGER,
        request.ROOT / "data/private/issue-5-nim-release-v1",
        request.ROOT / "data/private/issue-5-nim-sintetico-unico-v1",
        request.ROOT / "data/private/issue-5-nim-dispatch-v3",
        request.REVIEW.parent,
    ):
        for folder in (path, path / "invented-descendant"):
            with pytest.raises(ValueError):
                asyncio.run(request.simulate("valid", folder))


def review_fixture(plan):
    return {
        "protocol": request.PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": request.PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "financial_evidence_id": request.EVIDENCE_ID,
        "specific_remote_authorization_id": request.AUTHORIZATION_ID,
        "reviewer_thread_id": request.SUPERVISOR,
        "source_message_id": "ENTIRELY_INVENTED_OFFLINE_REVIEW",
        "execution_root_sha256": request.digest(str(request.ROOT.resolve()).encode()),
    }


@pytest.mark.parametrize(
    "field",
    [
        "plan_sha256",
        "configuration_sha256",
        "specific_remote_authorization_id",
        "financial_evidence_id",
        "reviewer_thread_id",
        "execution_root_sha256",
    ],
)
def test_review_rejects_wrong_bindings_before_consumption(tmp_path, monkeypatch, field):
    plan = request.verify_plan()
    review = review_fixture(plan)
    review[field] = "ENTIRELY_INVENTED_WRONG_BINDING"
    path = tmp_path / "review.json"
    create(path, review)
    monkeypatch.setattr(request, "REVIEW", path)

    def forbidden(*args, **kwargs):
        raise AssertionError("review_must_fail_before_consumption")

    monkeypatch.setattr(request, "reserve", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(request.execute_remote())
    assert not request.LEDGER.exists()


@pytest.mark.parametrize(
    "case, code, slot, category",
    [
        ("valid", "accepted", "evidence_ids", "array"),
        ("scalar_ids", "schema_invalid_type", "evidence_ids", "string"),
        ("object_item", "schema_invalid_type", "evidence_ids[*]", "object"),
        ("double_encoded", "schema_invalid_type", "selection", "string"),
        ("duplicate_ids", "duplicate_evidence_id", "evidence_ids[*]", "string"),
        ("secret_fieldname", "schema_extra_field", "selection", "object"),
        ("secret_id", "unknown_evidence_id", "evidence_ids[*]", "string"),
        ("redirect", "http_error", "envelope", "not_observed"),
        ("http_429", "http_error", "envelope", "not_observed"),
        ("http_503", "http_error", "envelope", "not_observed"),
        ("send_failure", "request_failed_outcome_uncertain", "envelope", "not_observed"),
        ("compressed", "protocol_rejected", "envelope", "not_observed"),
        ("wire_limit", "wire_byte_limit", "envelope", "not_observed"),
    ],
)
def test_pipeline_consumes_once_with_safe_types(tmp_path, case, code, slot, category):
    folder = tmp_path / case
    receipt = asyncio.run(request.simulate(case, folder))
    assert receipt["outcome"] == "observed"
    assert receipt["summary"]["code"] == code
    assert receipt["observation"]["summary"] == receipt["summary"]
    assert receipt["observation"]["type_audit"]["slots"][slot] == [category]
    assert receipt["real_requests"] == 0 and receipt["offline_simulation_only"] is True
    assert (folder / "dispatch-v3.json").exists()
    assert (folder.stat().st_mode & 0o777) == 0o700
    assert all((path.stat().st_mode & 0o777) == 0o600 for path in folder.iterdir())
    with pytest.raises(FileExistsError):
        asyncio.run(request.simulate(case, folder))
    retained = b"".join(path.read_bytes() for path in folder.iterdir())
    for forbidden in (
        INVENTED_KEY,
        INVENTED_SECRET,
        hashlib.sha256(INVENTED_SECRET.encode()).hexdigest(),
    ):
        assert forbidden.encode() not in retained


@pytest.mark.parametrize("tamper", [None, "nonce", "binding"])
def test_remote_getter_runs_after_durable_bound_dispatch_only(tmp_path, monkeypatch, tamper):
    from orchestration.galaxies_orchestration import nim_http

    plan = request.verify_plan()
    review = tmp_path / "review.json"
    create(review, review_fixture(plan))
    monkeypatch.setattr(request, "REVIEW", review)
    review_hash = request.check_review(plan)
    folder, nonce = reserve(tmp_path / "invented-remote", request.PLAN_SHA256, offline=False)
    value = request.binding(plan, review_hash, offline=False)
    if tamper == "binding":
        value["specific_remote_authorization_id"] = "ENTIRELY_INVENTED_WRONG_BINDING"
    create(folder / "typed-binding.json", value)
    monkeypatch.setattr(worker, "LEDGER", folder)
    monkeypatch.setattr(os, "getppid", os.getpid)
    calls = []

    def invented_getter():
        assert (folder / "dispatch-v3.json").exists()
        calls.append("invented-key-after-durable-dispatch")
        return INVENTED_KEY

    original = worker.exchange

    def fake_exchange(key, *, factory, timeout):
        return original(key, factory=worker.fake_connection("valid"), timeout=timeout)

    monkeypatch.setattr(nim_http, "existing_key", invented_getter)
    monkeypatch.setattr(worker, "exchange", fake_exchange)
    if tamper:
        with pytest.raises(ValueError):
            worker.released(b"x" * 32 if tamper == "nonce" else nonce, remaining=45)
        assert calls == [] and not (folder / "dispatch-v3.json").exists()
    else:
        assert worker.released(nonce, remaining=45)["summary"]["selection_validated"] is True
        with pytest.raises(FileExistsError):
            worker.released(nonce, remaining=45)
        assert len(calls) == 1


def test_timeout_remains_consumed(tmp_path):
    folder = tmp_path / "hang"
    receipt = asyncio.run(request.simulate("hang", folder, timeout=1.5))
    assert receipt["outcome"] == "timeout_outcome_uncertain"
    assert receipt["observation"] is None
    with pytest.raises(FileExistsError):
        asyncio.run(request.simulate("valid", folder))


def test_cancellation_remains_consumed(tmp_path):
    async def exercise():
        entered = asyncio.Event()

        async def runner(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(request.simulate("valid", tmp_path / "cancel", runner=runner))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    receipt = json.loads((tmp_path / "cancel/result-v3.json").read_bytes())
    assert receipt["outcome"] == "cancelled_outcome_uncertain"
    with pytest.raises(FileExistsError):
        asyncio.run(request.simulate("valid", tmp_path / "cancel"))


def test_child_summary_without_matching_safe_sidecar_is_rejected(tmp_path):
    summary = observe_open_response(FakeResponse(selection()))["summary"]

    async def runner(*args, **kwargs):
        return {"outcome": "observed", "summary": summary}

    receipt = asyncio.run(request.simulate("valid", tmp_path / "missing", runner=runner))
    assert receipt["outcome"] == "invalid_child_protocol" and receipt["observation"] is None
