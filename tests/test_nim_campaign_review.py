"""Explicitly invented cases and controlled transports; no native/provider proof."""

import asyncio
import copy
import json
import math
import os
import socket
import stat
import sys
from pathlib import Path

import pytest
from fastmcp import Client

from scripts import explanation_review_service_v1 as historical
from scripts import nim_campaign_review as nim
from scripts.campaign_evidence_v1 import CampaignCase, brief_digest
from scripts.channel_partitions import digest
from scripts.explanation_evidence import build_explanation_context, validate_selection
from scripts.explanation_graph_service_v2 import GraphSettings
from scripts.explanation_review_mcp_v1 import create_server
from scripts.explanation_review_service_v1 import ReviewSettings
from scripts.m1_evidence import M1Evidence
from scripts.training_comparables import ComparableResult
from tests.native_v2_fixture import public_data


@pytest.fixture(autouse=True)
def no_real_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("real_network_forbidden_in_invented_test")

    monkeypatch.delenv(nim.KEY_ENV, raising=False)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def invented(count=3, *, signed=True, references=False):
    data = public_data(count)
    for row in data["shap"].values():
        if signed:
            values = (0.1, -0.2, 0.3, 0.4)
            row["base_value_log"] = row["prediction_log"] - math.fsum(values)
            for driver, value in zip(row["drivers"], values, strict=True):
                driver["contribution_log"] = value
    if references:
        for row in data["comparables"].values():
            row.update(
                reason_code=None,
                references=[
                    {
                        "sample_id": "invented-training-reference",
                        "sector": "moda",
                        "source_url": "https://example.invalid/invented",
                        "published_at_utc": "invented",
                        "observed_at_utc": "invented",
                        "similarity": 0.8,
                    }
                ],
            )
    context = build_explanation_context(
        data["report"],
        shap={k: M1Evidence.model_validate_json(json.dumps(v)) for k, v in data["shap"].items()},
        comparables={
            k: ComparableResult.model_validate_json(json.dumps(v))
            for k, v in data["comparables"].items()
        },
    )
    source = validate_selection(
        context,
        json.dumps({"packet_sha256": context.packet_sha256, "evidence_ids": ["c1_prediction"]}),
    )
    source["evidence_packet"] = context.packet.model_dump(mode="json")
    request = {
        "campaign_id": "invented",
        "creative_ids": [c["creative_id"] for c in data["report"]["candidates"]],
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "PRIVATE_BRIEF_MARKER",
    }
    return source, request


def envelope(selection):
    return json.dumps(
        {
            "model": nim.MODEL,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": selection},
                }
            ],
        }
    ).encode()


def metadata_envelope(selection, *, service_tier="default", nvext=None):
    """Invented content in the provider's observed optional-metadata shape."""
    body = json.loads(envelope(selection))
    body.update(
        id="invented-completion",
        object="chat.completion",
        created=1234567890,
        service_tier=service_tier,
        nvext=nvext,
        system_fingerprint=None,
        usage={"prompt_tokens": 123, "completion_tokens": 7, "total_tokens": 130},
    )
    body["choices"][0].update(logprobs=None)
    body["choices"][0]["message"].update(reasoning_content=None, refusal=None)
    return json.dumps(body).encode()


def required_ids(count):
    return [
        f"c{i}_{kind}"
        for i in range(1, count + 1)
        for kind in ("shap_file_properties", "shap_speech_embedding", "references_missing")
    ]


def fake_selection(ids, calls=None):
    async def explicitly_invented_transport(payload):
        if calls is not None:
            calls.append(payload)
        projection = json.loads(payload["messages"][0]["content"].split("Catalogue: ", 1)[1])
        return envelope(
            json.dumps({"packet_sha256": projection["packet_sha256"], "evidence_ids": ids})
        )

    return explicitly_invented_transport


def config(tmp_path, name="one-round"):
    return nim.NimConfig(tmp_path / name, True)


def run_selection(source, request, cfg, transport):
    return asyncio.run(
        nim.select_and_review(
            source, request, cfg, input_origin="invented", _test_transport=transport
        )
    )


@pytest.mark.parametrize("count", [1, 3, 5])
def test_dynamic_projection_never_transmits_private_or_source_text(count):
    source, request = invented(count)
    source["analysis"]["warnings"] = ["PRIVATE_WARNING_TRANSCRIPT_PATH_TITLE_VECTOR"]
    source["evidence_packet"]["analysis_sha256"] = digest(source["analysis"])
    source["explanation"]["packet_sha256"] = digest(source["evidence_packet"])
    context, projection = nim.project_source(source)
    raw = json.dumps(nim.provider_payload(projection))
    for marker in (
        request["brief"],
        "PRIVATE_WARNING",
        "creative_id",
        "statement_pt",
        "cr_",
        "transcript",
        "media_sha256",
        "model_artifact_sha256",
    ):
        assert marker not in raw
    assert context.packet_sha256 == digest(source["evidence_packet"])
    assert set(projection) == {"packet_sha256", "evidence"}
    assert all(
        r.get("candidate", "c1") in {f"c{i}" for i in range(1, count + 1)}
        for r in projection["evidence"]
    )
    assert "largest magnitude" in raw and "at most 12" in raw
    assert nim.provider_payload(projection)["chat_template_kwargs"] == {"enable_thinking": False}
    assert nim.CONFIGURATION["reasoning_mode"] == "instruct"
    assert "reasoning_budget" not in nim.CONFIGURATION


@pytest.mark.parametrize("count", [1, 3, 5])
def test_actual_remote_ids_local_mandatory_and_original_numbers_remain_separate(tmp_path, count):
    source, request = invented(count)
    before = copy.deepcopy(source)
    ids = required_ids(count)[:12]  # Deliberate invented response; production never truncates.
    result = run_selection(source, request, config(tmp_path), fake_selection(ids))
    assert result["status"] == "reviewed"
    assert result["source_result"] == source == before
    assert result["selected_report"]["analysis"] == source["analysis"]
    assert result["selected_report"]["analysis"]["ranking"] == before["analysis"]["ranking"]
    assert result["remote_evidence_ids"] == ids
    assert len(result["locally_added_mandatory_ids"]) == 3 + count
    claims = result["selected_report"]["explanation"]["claims"]
    assert {f["evidence_id"] for f in claims} == set(ids + result["locally_added_mandatory_ids"])
    quality = result["review"]["quality_review"]
    assert quality["presentation_scope"] == "selected"
    assert quality["status"] == (
        "insufficient" if count == 5 else "sufficient_for_exploratory_comparison"
    )
    if count == 5:
        assert [r["sufficient"] for r in quality["candidates"]] == [True, True, True, True, False]
    provenance = result["nim_provenance"]
    assert provenance["transport"] == "invented_test_callback_not_native"
    assert (
        provenance["new_predictions"]
        == provenance["new_extractions"]
        == provenance["new_external_calls"]
        == 0
    )
    assert not provenance["final_configuration_validated"]
    assert result["review"]["review_provenance"]["new_external_calls"] == 0
    assert result["source_sha256"] == digest(before)


def test_zero_groups_and_missing_evidence_remain_visible(tmp_path):
    source, request = invented(1, signed=False)
    result = run_selection(
        source,
        request,
        config(tmp_path),
        fake_selection(["c1_shap_sector", "c1_references_missing"]),
    )
    assert result["review"]["quality_review"]["candidates"][0]["all_group_contributions_zero"]
    assert "todos os grupos SHAP" in result["review"]["display_text"]
    second = run_selection(
        source, request, config(tmp_path, "insufficient"), fake_selection(["c1_prediction"])
    )
    assert second["review"]["quality_review"]["status"] == "insufficient"
    assert "insuficiente" in second["review"]["display_text"]


def test_recognized_reference_is_numeric_only_and_campaign_case_stays_local(tmp_path):
    source, request = invented(1, references=True)
    projection = nim.project_source(source)[1]
    reference = next(r for r in projection["evidence"] if r["type"] == "reference")
    assert reference["similarity"] == 0.8 and reference["minimum_similarity"] == 0.5
    assert "example.invalid" not in json.dumps(projection)
    cid = request["creative_ids"][0]
    case = CampaignCase(
        case_id="invented-private-case",
        brief_id="invented-private-brief",
        campaign_id="invented",
        sector="moda",
        purpose="campaign",
        data_origin="invented",
        brief_sha256=brief_digest(request["brief"]),
        requirements=({"requirement_id": "r1", "attribute": "portrait", "expected": True},),
        media=({"creative_id": cid, "media_sha256": "a" * 64},),
        observations=(),
    )
    calls = []
    result = asyncio.run(
        nim.select_and_review(
            source,
            request,
            config(tmp_path),
            case=case,
            media_bindings={cid: "a" * 64},
            input_origin="invented",
            _test_transport=fake_selection(
                ["c1_shap_file_properties", "c1_shap_speech_embedding", "c1_reference_1"], calls
            ),
        )
    )
    assert result["review"]["quality_review"]["status"] == "sufficient_for_exploratory_comparison"
    assert result["review"]["campaign_adherence"]["status"] == "partial"
    assert "invented-private-case" not in json.dumps(calls)
    assert "invented-private-brief" not in json.dumps(calls)


def test_campaign_binding_failure_prevents_reservation_and_call(tmp_path):
    source, request = invented(1)
    case = CampaignCase(
        case_id="invented",
        brief_id="invented",
        campaign_id="invented",
        sector="moda",
        purpose="campaign",
        data_origin="invented",
        brief_sha256=brief_digest(request["brief"]),
        requirements=({"requirement_id": "r1", "attribute": "portrait", "expected": True},),
        media=({"creative_id": request["creative_ids"][0], "media_sha256": "a" * 64},),
        observations=(),
    )
    calls = []
    with pytest.raises(ValueError, match="^invalid_nim_review_input_or_configuration$"):
        asyncio.run(
            nim.select_and_review(
                source,
                request,
                config(tmp_path),
                case=case,
                media_bindings={},
                input_origin="invented",
                _test_transport=fake_selection(["c1_prediction"], calls),
            )
        )
    assert not calls and not (tmp_path / "one-round").exists()


@pytest.mark.parametrize("with_optional_metadata", [False, True])
@pytest.mark.parametrize(
    "bad",
    [
        "hash",
        "duplicate_key",
        "unknown_id",
        "too_many",
        "duplicate_id",
        "extra_key",
        "bad_type",
        "empty",
    ],
)
def test_untrusted_selection_rejected_without_repair(tmp_path, bad, with_optional_metadata):
    source, request = invented(5)
    body = {"packet_sha256": digest(source["evidence_packet"]), "evidence_ids": ["c1_prediction"]}
    if bad == "hash":
        body["packet_sha256"] = "f" * 64
    elif bad == "unknown_id":
        body["evidence_ids"] = ["PRIVATE_UNKNOWN_ID"]
    elif bad == "too_many":
        body["evidence_ids"] = required_ids(5)[:13]
    elif bad == "duplicate_id":
        body["evidence_ids"] *= 2
    elif bad == "extra_key":
        body["PRIVATE_KEY"] = "PRIVATE_VALUE"
    elif bad == "bad_type":
        body["evidence_ids"] = [7]
    elif bad == "empty":
        body["evidence_ids"] = []
    raw = json.dumps(body)
    if bad == "duplicate_key":
        raw = raw.replace('"evidence_ids":', '"evidence_ids": [], "evidence_ids":')

    async def invented_bad_response(_):
        return metadata_envelope(raw) if with_optional_metadata else envelope(raw)

    result = run_selection(source, request, config(tmp_path), invented_bad_response)
    assert result["status"] == "unavailable" and result["selected_report"] is None
    assert result["failure_stage_code"] == "selection_schema_or_binding"
    assert (
        json.loads((tmp_path / "one-round/outcome.json").read_text())["failure_stage_code"]
        == "selection_schema_or_binding"
    )
    assert result["source_result"] == source
    assert not result["remote_evidence_ids"]
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize(
    "service_tier,nvext",
    [
        (None, None),
        ("default", {}),
        ("PRIVATE_SERVICE_TIER", {"invented_metadata": {"text": "PRIVATE_NVEXT"}}),
    ],
)
def test_optional_provider_metadata_is_ignored_without_payload_or_projection_change(
    tmp_path, service_tier, nvext
):
    source, request = invented(3)
    before = copy.deepcopy(source)
    projection = nim.project_source(source)[1]
    payload_bytes = nim._payload_bytes(nim.provider_payload(projection))
    ids = required_ids(3)
    calls = []

    async def invented_response(payload):
        calls.append(copy.deepcopy(payload))
        return metadata_envelope(
            json.dumps({"packet_sha256": projection["packet_sha256"], "evidence_ids": ids}),
            service_tier=service_tier,
            nvext=nvext,
        )

    cfg = config(tmp_path)
    result = run_selection(source, request, cfg, invented_response)
    assert result["status"] == "reviewed" and result["failure_stage_code"] is None
    assert result["remote_evidence_ids"] == ids
    assert result["source_result"] == source == before
    assert result["selected_report"]["analysis"] == before["analysis"]
    assert result["selected_report"]["analysis"]["ranking"] == before["analysis"]["ranking"]
    assert nim.project_source(source)[1] == projection
    assert len(calls) == 1 and nim._payload_bytes(calls[0]) == payload_bytes
    assert nim._payload_bytes(nim.provider_payload(projection)) == payload_bytes
    saved = json.dumps(result) + "".join(p.read_text() for p in cfg.reservation_dir.iterdir())
    assert "service_tier" not in saved and "nvext" not in saved and "PRIVATE_" not in saved


@pytest.mark.parametrize(
    "field,value",
    [
        ("service_tier", False),
        ("service_tier", 1),
        ("service_tier", []),
        ("service_tier", {}),
        ("nvext", False),
        ("nvext", 1),
        ("nvext", []),
        ("nvext", "PRIVATE_NVEXT"),
    ],
)
def test_invalid_optional_metadata_type_rejected_before_selection(tmp_path, field, value):
    source, request = invented(1)
    selection = json.dumps(
        {"packet_sha256": digest(source["evidence_packet"]), "evidence_ids": ["c1_prediction"]}
    )

    async def invented_bad_response(_):
        return metadata_envelope(selection, **{field: value})

    result = run_selection(source, request, config(tmp_path), invented_bad_response)
    assert result["status"] == "unavailable" and result["selected_report"] is None
    assert result["failure_stage_code"] == "response_envelope"
    assert result["source_result"] == source and result["remote_evidence_ids"] == []
    assert "PRIVATE_NVEXT" not in json.dumps(result)


@pytest.mark.parametrize("with_optional_metadata", [False, True])
@pytest.mark.parametrize(
    "bad",
    [
        "length",
        "model",
        "envelope_duplicate",
        "extra",
        "multiple",
        "role",
        "index",
        "refusal",
        "oversize",
        "nan",
        "not_bytes",
    ],
)
def test_closed_http_envelope_validates_stop_model_and_bounds(
    tmp_path, bad, with_optional_metadata
):
    source, request = invented(1)
    raw = envelope(
        json.dumps(
            {"packet_sha256": digest(source["evidence_packet"]), "evidence_ids": ["c1_prediction"]}
        )
    )
    body = json.loads(raw)
    if with_optional_metadata:
        body = json.loads(metadata_envelope(body["choices"][0]["message"]["content"]))
    if bad == "length":
        body["choices"][0]["finish_reason"] = "length"
    elif bad == "model":
        body["model"] = "different-model"
    elif bad == "extra":
        body["private"] = "PRIVATE_HTTP_RESPONSE"
    elif bad == "multiple":
        body["choices"] *= 2
    elif bad == "role":
        body["choices"][0]["message"]["role"] = "tool"
    elif bad == "index":
        body["choices"][0]["index"] = True
    elif bad == "refusal":
        body["choices"][0]["message"]["refusal"] = "PRIVATE_REFUSAL"
    raw = json.dumps(body).encode()
    if bad == "envelope_duplicate":
        raw = raw.replace(b'"model":', b'"model": "wrong", "model":')
    elif bad == "oversize":
        raw = b"x" * 16385
    elif bad == "nan":
        raw = raw.replace(b'"model":', b'"usage": NaN, "model":')
    elif bad == "not_bytes":
        raw = raw.decode()

    async def invented_bad_response(_):
        return raw

    result = run_selection(source, request, config(tmp_path), invented_bad_response)
    assert result["status"] == "unavailable" and result["source_result"] == source
    assert result["failure_stage_code"] == "response_envelope"
    assert (
        json.loads((tmp_path / "one-round/outcome.json").read_text())["failure_stage_code"]
        == "response_envelope"
    )
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize(
    "bad",
    [
        "packet",
        "claim",
        "ranking",
        "driver",
        "nonfinite",
        "unknown_fact",
        "unknown_reason",
        "missing_limit",
        "association",
        "request",
        "projection_size",
    ],
)
def test_invalid_input_never_reserves_or_calls(tmp_path, monkeypatch, bad):
    source, request = invented(3)
    packet = source["evidence_packet"]
    if bad == "packet":
        packet["analysis_sha256"] = "0" * 64
    elif bad == "claim":
        source["explanation"]["claims"][0]["statement_pt"] = "PRIVATE_UNRECOGNIZED_TEXT"
    elif bad == "ranking":
        source["analysis"]["ranking"]["entries"].reverse()
    elif bad in {"driver", "nonfinite"}:
        fact = next(f for f in packet["evidence"] if f["evidence_id"] == "c3_shap_sector")
        fact["statement_pt"] = fact["statement_pt"].replace(
            "0.1 em", ("9.1" if bad == "driver" else "1e999") + " em"
        )
    elif bad == "unknown_fact":
        packet["evidence"].append(
            {
                "evidence_id": "c1_private",
                "creative_id": request["creative_ids"][0],
                "statement_pt": "PRIVATE_MARKER",
            }
        )
    elif bad == "unknown_reason":
        packet["evidence"][-1]["statement_pt"] = "Sem comparáveis: PRIVATE_REASON."
    elif bad == "missing_limit":
        packet["evidence"] = [f for f in packet["evidence"] if f["evidence_id"] != "limit_quality"]
        source["explanation"]["claims"] = [
            f for f in source["explanation"]["claims"] if f["evidence_id"] != "limit_quality"
        ]
    elif bad == "association":
        packet["evidence"][-1]["creative_id"] = request["creative_ids"][0]
    elif bad == "request":
        request["creative_ids"].reverse()
    elif bad == "projection_size":
        monkeypatch.setattr(nim, "MAX_PROJECTION_BYTES", 1)
    source["explanation"]["packet_sha256"] = digest(packet)
    calls = []
    with pytest.raises(ValueError, match="^invalid_nim_review_input_or_configuration$") as caught:
        run_selection(source, request, config(tmp_path), fake_selection(["c1_prediction"], calls))
    assert "PRIVATE" not in str(caught.value)
    assert not calls and not (tmp_path / "one-round").exists()


def test_reservation_is_durable_exclusive_and_private_even_after_rejection(tmp_path):
    source, request = invented(1)
    cfg = config(tmp_path)
    calls = []
    result = run_selection(source, request, cfg, fake_selection(["unknown"], calls))
    assert result["status"] == "unavailable"
    assert stat.S_IMODE(cfg.reservation_dir.stat().st_mode) == 0o700
    for name in ("reservation.json", "outcome.json"):
        path = cfg.reservation_dir / name
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert "invented_test_key" not in path.read_text()
    receipt = json.loads((cfg.reservation_dir / "reservation.json").read_text())
    assert receipt["status"] == "consumed_before_spawn"
    assert receipt["packet_sha256"] == digest(source["evidence_packet"])
    assert receipt["projection_sha256"] == digest(nim.project_source(source)[1])
    assert receipt["model"] == nim.MODEL and not receipt["billing_measured"]
    with pytest.raises(ValueError, match="^nim_reservation_unavailable$"):
        run_selection(source, request, cfg, fake_selection(["c1_prediction"], calls))
    assert len(calls) == 1


def test_reservation_cannot_be_reused_concurrently(tmp_path):
    source, request = invented(1)
    cfg = config(tmp_path)
    calls = []

    async def scenario():
        async def delayed(payload):
            await asyncio.sleep(0.01)
            return await fake_selection(["c1_prediction"], calls)(payload)

        return await asyncio.gather(
            *(
                nim.select_and_review(
                    source, request, cfg, input_origin="invented", _test_transport=delayed
                )
                for _ in range(2)
            ),
            return_exceptions=True,
        )

    results = asyncio.run(scenario())
    assert len(calls) == 1
    assert sum(isinstance(r, ValueError) for r in results) == 1


@pytest.mark.parametrize("bad", ["missing_key", "authorization", "public_parent", "fake_origin"])
def test_operator_configuration_cannot_silently_enable_external_calls(tmp_path, bad):
    source, request = invented(1)
    cfg = config(tmp_path)
    if bad == "authorization":
        with pytest.raises(ValueError, match="invalid_nim_operator_configuration"):
            nim.NimConfig(tmp_path / "new", False)
        return
    if bad == "public_parent":
        tmp_path.chmod(0o755)
    with pytest.raises(ValueError):
        asyncio.run(
            nim.select_and_review(
                source,
                request,
                cfg,
                input_origin="unverified" if bad == "fake_origin" else "invented",
                _test_transport=None if bad == "missing_key" else fake_selection(["c1_prediction"]),
            )
        )
    assert not cfg.reservation_dir.exists()


@pytest.mark.parametrize("mode", ["timeout", "cancel", "cancel_during_spawn", "repeated_cancel"])
def test_owned_subprocess_is_killed_and_reaped_on_timeout_and_cancel(monkeypatch, mode):
    monkeypatch.setattr(nim, "_HTTP_CHILD", "import time; time.sleep(60)")
    monkeypatch.setattr(nim, "TIMEOUT_SECONDS", 0.08 if mode == "timeout" else 45)
    original = asyncio.create_subprocess_exec
    children, options = [], []
    receipt = nim._transport_receipt()

    async def controlled_spawn(*args, **kwargs):
        options.append((args, kwargs))
        child = await original(*args, **kwargs)
        children.append(child)
        if mode in {"cancel_during_spawn", "repeated_cancel"}:
            await asyncio.sleep(0.05)
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", controlled_spawn)

    async def scenario():
        task = asyncio.create_task(
            nim._invoke_provider({}, "INVENTED_SECRET_KEY", transport_receipt=receipt)
        )
        if mode != "timeout":
            while not children:
                await asyncio.sleep(0.001)
            task.cancel()
            if mode == "repeated_cancel":
                await asyncio.sleep(0.005)
                task.cancel()
        with pytest.raises(TimeoutError if mode == "timeout" else asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(children) == 1 and children[0].returncode is not None
    assert receipt["child_reaped"] is True
    assert receipt["timed_out"] is (mode == "timeout")
    assert receipt["http_status"] is None
    with pytest.raises(ChildProcessError):
        os.waitpid(children[0].pid, os.WNOHANG)
    args, kwargs = options[0]
    assert "INVENTED_SECRET_KEY" not in repr(args)
    assert kwargs["env"] == {nim.KEY_ENV: "INVENTED_SECRET_KEY"}
    assert kwargs["stderr"] == asyncio.subprocess.DEVNULL


@pytest.mark.parametrize("response_status", [302, 401, 500])
def test_http_failure_body_and_redirect_are_never_read_or_echoed(monkeypatch, response_status):
    # Real owned subprocess, stdlib HTTP replaced *inside* it by this invented
    # in-memory transport. No socket and no real provider credentials are used.
    stub = f"""
import http.client
class Response:
    status = {response_status}
    def read(self, count):
        raise AssertionError("PRIVATE_HTTP_BODY_MUST_NOT_BE_READ")
class Connection:
    def __init__(self, host, **kwargs):
        assert host == "integrate.api.nvidia.com"
    def request(self, method, path, **kwargs):
        assert method == "POST" and path == "/v1/chat/completions"
    def getresponse(self): return Response()
    def close(self): pass
http.client.HTTPSConnection = Connection
"""
    monkeypatch.setattr(nim, "_HTTP_CHILD", stub + nim._HTTP_CHILD)
    receipt = nim._transport_receipt()
    with pytest.raises(ValueError, match="^nim_provider_failed$") as caught:
        asyncio.run(nim._invoke_provider({}, "invented_key", transport_receipt=receipt))
    assert "PRIVATE" not in str(caught.value)
    assert receipt["http_status"] == response_status
    assert receipt["child_reaped"] is True and receipt["timed_out"] is False
    assert receipt["response_bytes"] is None and receipt["response_sha256"] is None


def settings(tmp_path):
    return ReviewSettings(
        GraphSettings(
            Path(sys.executable),
            Path(sys.executable),
            tmp_path / "uploads",
            tmp_path / "registry",
            tmp_path / "scratch",
        ),
        data_origin="invented",
    )


def test_mcp_opt_in_uses_same_callable_and_single_original_payload(tmp_path, monkeypatch):
    source, request = invented(1)
    cfg, local_settings = config(tmp_path), settings(tmp_path)
    calls = []

    async def invented_shared(payload, selected_settings, selected_config):
        calls.append((payload, selected_settings, selected_config))
        return {"status": "invented_test_callback_not_native", "source_result": source}

    monkeypatch.setattr(nim, "analyze_nim_reviewed", invented_shared)

    async def scenario():
        async with Client(create_server(local_settings)) as client:
            assert "analyze_creatives_nim_reviewed" not in {
                t.name for t in await client.list_tools()
            }
        async with Client(create_server(local_settings, nim_config=cfg)) as client:
            tool = next(
                t for t in await client.list_tools() if t.name == "analyze_creatives_nim_reviewed"
            )
            assert set(tool.input_schema["properties"]) == {"payload"}
            assert set(tool.input_schema["properties"]["payload"]["properties"]) == set(request)
            assert (
                tool.annotations.read_only_hint is False
                and tool.annotations.open_world_hint is True
            )
            result = await client.call_tool(tool.name, {"payload": request})
            assert result.structured_content == await invented_shared(request, local_settings, cfg)

    asyncio.run(asyncio.wait_for(scenario(), 10))
    assert len(calls) == 2 and calls[0] == calls[1]


def test_shared_adapter_reuses_graph_once_without_reextraction(tmp_path, monkeypatch):
    source, request = invented(3)
    graph_calls, selector_calls = [], []

    async def invented_prior(payload, selected_settings):
        graph_calls.append(payload)
        return {
            "review_status": "reviewed",
            "source_result": source,
            "integration_receipt": {"external_provider_configured": False},
        }

    async def invented_selector(selected_source, payload, cfg, **kwargs):
        selector_calls.append((selected_source, payload, kwargs))
        return {"status": "invented_test_callback_not_native", "source_result": selected_source}

    monkeypatch.setattr(historical, "analyze_reviewed", invented_prior)
    monkeypatch.setattr(nim, "select_and_review", invented_selector)
    result = asyncio.run(nim.analyze_nim_reviewed(request, settings(tmp_path), config(tmp_path)))
    assert len(graph_calls) == len(selector_calls) == 1
    assert graph_calls[0] == selector_calls[0][1] == request
    assert result["source_result"] == source
    assert result["prior_review"]["integration_receipt"]["external_provider_configured"] is False


@pytest.mark.parametrize("valid_request", [True, False])
def test_adapter_invalid_or_missing_source_never_selects(tmp_path, monkeypatch, valid_request):
    _, request = invented(1)
    calls = []

    async def unavailable(payload, selected_settings):
        calls.append(payload)
        return {
            "review_status": "unavailable",
            "source_result": {"orchestration_error": "local_graph_failed"},
        }

    async def forbidden(*args, **kwargs):
        raise AssertionError("must_not_select")

    monkeypatch.setattr(historical, "analyze_reviewed", unavailable)
    monkeypatch.setattr(nim, "select_and_review", forbidden)
    result = asyncio.run(
        nim.analyze_nim_reviewed(
            request if valid_request else {}, settings(tmp_path), config(tmp_path)
        )
    )
    assert result["status"] == "unavailable"
    assert len(calls) == int(valid_request)
    assert not (tmp_path / "one-round").exists()


@pytest.mark.parametrize("output_format", ["json", "text"])
def test_cli_uses_same_opt_in_callable_without_launching_graph(
    tmp_path, monkeypatch, capsys, output_format
):
    from scripts import explanation_review_mcp_v1 as facade

    _, request = invented(1)
    request_path = tmp_path / "invented-request.json"
    request_path.write_text(json.dumps(request))
    calls = []

    async def invented_shared(payload, local_settings, selected_config):
        calls.append((payload, selected_config))
        return {
            "status": "reviewed",
            "reason_code": "nim_selection_reviewed",
            "failure_stage_code": None,
            "review": {"display_text": "Invented local test.\n"},
            "prior_review": {"display_text": "Invented prior catalogue.\n"},
            "source_result": {"invented_numeric_checkpoint": 200.0},
        }

    monkeypatch.setattr(nim, "analyze_nim_reviewed", invented_shared)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invented-cli",
            "--graph-python",
            sys.executable,
            "--request-file",
            str(request_path),
            "--nim-provider",
            "nvidia",
            "--nim-reservation-dir",
            str(tmp_path / "new"),
            "--nim-authorized-zero-brl",
            "--format",
            output_format,
        ],
    )
    assert facade.main() == 0
    output = capsys.readouterr().out
    if output_format == "json":
        assert json.loads(output) == {
            "status": "reviewed",
            "reason_code": "nim_selection_reviewed",
            "failure_stage_code": None,
            "review": {"display_text": "Invented local test.\n"},
            "prior_review": {"display_text": "Invented prior catalogue.\n"},
            "source_result": {"invented_numeric_checkpoint": 200.0},
        }
    else:
        assert "Etapa NIM: seleção validada e revisada localmente (reviewed)" in output
        assert "Relatório da seleção remota NIM, renderizado e revisado localmente" in output
        assert output.endswith("Invented local test.\n")
        assert "Invented prior catalogue" not in output
    assert len(calls) == 1 and calls[0][0] == request
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("with_prior", [True, False])
@pytest.mark.parametrize(
    "stage", ["transport", "response_envelope", "selection_schema_or_binding", "local_review", None]
)
def test_cli_text_shows_failed_nim_stage_and_preserved_local_origin(
    tmp_path, monkeypatch, capsys, with_prior, stage
):
    from scripts import explanation_review_mcp_v1 as facade

    _, request = invented(1)
    request_path = tmp_path / "invented-request.json"
    request_path.write_text(json.dumps(request))
    calls = []
    result = {
        "status": "unavailable",
        "reason_code": "nim_selection_unavailable",
        "failure_stage_code": stage,
        "review": None,
        "prior_review": {
            "display_text": "Catálogo inventado suficiente para comparação exploratória; q50=200.0.\n"
        }
        if with_prior
        else None,
    }

    async def invented_shared(*args):
        calls.append(True)
        return copy.deepcopy(result)

    monkeypatch.setattr(nim, "analyze_nim_reviewed", invented_shared)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invented-cli",
            "--graph-python",
            sys.executable,
            "--request-file",
            str(request_path),
            "--nim-provider",
            "nvidia",
            "--nim-reservation-dir",
            str(tmp_path / "new"),
            "--nim-authorized-zero-brl",
            "--show-local-evidence",
            "--format",
            "text",
        ],
    )
    assert facade.main() == 0
    output = capsys.readouterr().out
    assert output.startswith("Etapa NIM: indisponível (unavailable).\n")
    assert "Motivo: seleção NIM indisponível (nim_selection_unavailable)" in output
    assert (
        f"({stage})" in output if stage is not None else "Etapa da falha: não registrada" in output
    )
    if with_prior:
        assert "Revisão local anterior preservada; catálogo anterior à tentativa NIM" in output
        assert "Catálogo inventado suficiente" in output and "q50=200.0" in output
    else:
        assert "Revisão local anterior indisponível" in output
    assert "Relatório da seleção remota NIM" not in output
    assert len(calls) == 1 and not (tmp_path / "new").exists()


@pytest.mark.parametrize("output_format", ["json", "text"])
def test_cli_default_output_remains_legacy_without_nim(
    tmp_path, monkeypatch, capsys, output_format
):
    from scripts import explanation_review_mcp_v1 as facade

    _, request = invented(1)
    request_path = tmp_path / "invented-request.json"
    request_path.write_text(json.dumps(request))
    result = {
        "display_text": "Catálogo local inventado: q50=200.0.\n",
        "source_result": {"invented_numeric_checkpoint": 200.0},
    }
    calls = []

    async def invented_local(*args):
        calls.append(True)
        return copy.deepcopy(result)

    async def forbidden(*args):
        raise AssertionError("nim_must_not_start")

    monkeypatch.setattr(facade, "analyze_reviewed", invented_local)
    monkeypatch.setattr(nim, "analyze_nim_reviewed", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invented-cli",
            "--graph-python",
            sys.executable,
            "--request-file",
            str(request_path),
            "--format",
            output_format,
        ],
    )
    assert facade.main() == 0
    output = capsys.readouterr().out
    assert (
        json.loads(output) == result
        if output_format == "json"
        else output == result["display_text"]
    )
    assert len(calls) == 1


@pytest.mark.parametrize("unknown", ["PRIVATE_KEY_PATH_REMOTE_ERROR", ["PRIVATE_VALUE"]])
def test_cli_text_uses_closed_nim_status_reason_and_stage_labels(
    tmp_path, monkeypatch, capsys, unknown
):
    from scripts import explanation_review_mcp_v1 as facade

    _, request = invented(1)
    request_path = tmp_path / "invented-request.json"
    request_path.write_text(json.dumps(request))

    async def invented_unknown(*args):
        return {
            "status": unknown,
            "reason_code": unknown,
            "failure_stage_code": unknown,
            "review": None,
            "prior_review": None,
        }

    monkeypatch.setattr(nim, "analyze_nim_reviewed", invented_unknown)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invented-cli",
            "--graph-python",
            sys.executable,
            "--request-file",
            str(request_path),
            "--nim-provider",
            "nvidia",
            "--nim-reservation-dir",
            str(tmp_path / "new"),
            "--nim-authorized-zero-brl",
            "--format",
            "text",
        ],
    )
    assert facade.main() == 0
    output = capsys.readouterr().out
    assert "PRIVATE" not in output and str(tmp_path) not in output
    assert "Etapa NIM: indisponível (unavailable)" in output
    assert "Motivo: não identificado neste resultado" in output
    assert "Etapa da falha: não registrada" in output


@pytest.mark.parametrize("size,accepted", [(65536, True), (65537, False)])
def test_complete_payload_byte_limit(size, accepted):
    base = {"invented_padding": ""}
    base["invented_padding"] = "x" * (size - len(nim._canonical(base).encode("ascii")))
    if accepted:
        assert len(nim._payload_bytes(base)) == size
    else:
        with pytest.raises(ValueError, match="^nim_payload_size_limit$"):
            nim._payload_bytes(base)


def test_payload_wrapper_overflow_rejected_before_reservation_or_transport(tmp_path, monkeypatch):
    source, request = invented(1)
    projection = nim.project_source(source)[1]
    assert len(nim._canonical(projection)) < 65536
    monkeypatch.setattr(nim, "provider_payload", lambda _: {"invented_padding": "x" * 65536})
    calls = []
    with pytest.raises(ValueError, match="^invalid_nim_review_input_or_configuration$"):
        run_selection(source, request, config(tmp_path), fake_selection(["c1_prediction"], calls))
    assert not calls and not (tmp_path / "one-round").exists()


def test_child_rejects_complete_payload_overflow_without_http():
    # Guard inside the isolated child prevents even an accidental network call.
    guard = """
import http.client, sys
def forbidden(*args, **kwargs):
    sys.stdout.buffer.write(b"UNEXPECTED_HTTP")
    raise AssertionError()
http.client.HTTPSConnection = forbidden
"""

    async def scenario():
        child = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-B",
            "-c",
            guard + nim._HTTP_CHILD,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={nim.KEY_ENV: "invented_key"},
        )
        output, _ = await child.communicate(b"x" * 65537)
        assert child.returncode == 10
        metadata = json.loads(output)
        assert metadata["http_status"] is None and metadata["response_bytes"] is None

    asyncio.run(asyncio.wait_for(scenario(), 5))


@pytest.mark.parametrize("http_status", [200, 500])
def test_safe_transport_receipt_persisted_without_reasoning_and_reservation_stays_single(
    tmp_path, monkeypatch, http_status
):
    source, request = invented(1)
    body = json.loads(
        envelope(
            json.dumps(
                {
                    "packet_sha256": digest(source["evidence_packet"]),
                    "evidence_ids": ["c1_prediction"],
                }
            )
        )
    )
    body["choices"][0]["message"].update(
        reasoning="PRIVATE_REASONING_MARKER", reasoning_content="PRIVATE_REASONING_CONTENT_MARKER"
    )
    body["usage"] = {
        "prompt_tokens": 123,
        "completion_tokens": 7,
        "total_tokens": 130,
        "private": "PRIVATE_USAGE_MARKER",
    }
    raw = json.dumps(body).encode()
    wire = f"HTTP/1.1 {http_status} Invented\r\nContent-Length: {len(raw)}\r\n\r\n".encode() + raw
    stub = controlled_http_wire(wire)
    monkeypatch.setattr(nim, "_HTTP_CHILD", stub + nim._HTTP_CHILD)
    monkeypatch.setenv(nim.KEY_ENV, "INVENTED_KEY_NEVER_PERSIST")
    cfg = config(tmp_path)
    result = asyncio.run(nim.select_and_review(source, request, cfg, input_origin="invented"))
    outcome = json.loads((cfg.reservation_dir / "outcome.json").read_text())
    receipt = result["transport_receipt"]
    assert receipt == outcome["transport_receipt"]
    assert receipt["http_status"] == http_status and receipt["child_reaped"] is True
    assert receipt["timed_out"] is False
    assert result["source_result"] == source
    assert result["status"] == ("reviewed" if http_status == 200 else "unavailable")
    assert result["failure_stage_code"] == (None if http_status == 200 else "transport")
    if http_status == 200:
        import hashlib

        assert receipt["response_bytes"] == len(raw)
        assert receipt["response_sha256"] == hashlib.sha256(raw).hexdigest()
        assert receipt["model_matched"] is True and receipt["returned_model"] == nim.MODEL
        assert receipt["finish_reason"] == "stop"
        assert receipt["body_within_limit"] is True and receipt["framing_complete"] is True
        assert receipt["response_complete"] is True
        assert receipt["usage"] == {
            "prompt_tokens": 123,
            "completion_tokens": 7,
            "total_tokens": 130,
        }
        assert result["selected_report"]["analysis"] == source["analysis"]
    else:
        assert receipt["response_bytes"] is None and receipt["usage"] is None
        assert receipt["body_within_limit"] is None and receipt["framing_complete"] is False
    saved = json.dumps(result) + "".join(p.read_text() for p in cfg.reservation_dir.iterdir())
    assert "PRIVATE_" not in saved and "INVENTED_KEY_NEVER_PERSIST" not in saved
    with pytest.raises(ValueError, match="^nim_reservation_unavailable$"):
        asyncio.run(nim.select_and_review(source, request, cfg, input_origin="invented"))


def test_response_metadata_excludes_unrecognized_model_finish_and_usage_text():
    raw = json.dumps(
        {
            "model": "PRIVATE_MODEL",
            "choices": [{"finish_reason": "PRIVATE_FINISH"}],
            "usage": {
                "prompt_tokens": True,
                "completion_tokens": -1,
                "total_tokens": "PRIVATE_USAGE",
            },
        }
    ).encode()
    receipt = nim._transport_receipt()
    nim._response_metadata(raw, receipt)
    assert receipt["model_matched"] is False and receipt["returned_model"] is None
    assert receipt["finish_reason"] is None and receipt["usage"] is None
    assert "PRIVATE" not in json.dumps(receipt)


def controlled_http_wire(wire):
    """Invented wire bytes, real stdlib parser, no socket or provider call."""
    return f"""
import io, http.client
class InventedSocket:
    def makefile(self, mode): return io.BytesIO({wire!r})
class Connection:
    def __init__(self, host, **kwargs): pass
    def request(self, method, path, **kwargs): pass
    def getresponse(self):
        response = self.response_class(InventedSocket())
        response.begin()
        return response
    def close(self): pass
http.client.HTTPSConnection = Connection
"""


@pytest.mark.parametrize(
    "framing",
    [
        "length_complete",
        "length_truncated",
        "chunk_complete",
        "chunk_truncated",
        "chunk_missing_final_crlf",
        "chunk_bad_separator",
        "close_delimited",
        "body_too_large",
    ],
)
def test_child_checks_real_http_framing_separately_from_body_limit(tmp_path, monkeypatch, framing):
    source, request = invented(1)
    raw = envelope(
        json.dumps(
            {"packet_sha256": digest(source["evidence_packet"]), "evidence_ids": ["c1_prediction"]}
        )
    )
    if framing == "body_too_large":
        raw = b"x" * 16385
    if framing.startswith("chunk_"):
        wire = (
            b"HTTP/1.1 200 Invented\r\nTransfer-Encoding: chunked\r\n\r\n"
            + f"{len(raw):x}\r\n".encode()
            + raw
            + b"\r\n"
        )
        if framing == "chunk_complete":
            wire += b"0\r\n\r\n"
        elif framing == "chunk_missing_final_crlf":
            wire += b"0\r\n"
        elif framing == "chunk_bad_separator":
            wire = wire[:-2] + b"XX0\r\n\r\n"
    elif framing == "close_delimited":
        wire = b"HTTP/1.0 200 Invented\r\n\r\n" + raw
    else:
        declared = len(raw) + (8 if framing == "length_truncated" else 0)
        wire = f"HTTP/1.1 200 Invented\r\nContent-Length: {declared}\r\n\r\n".encode() + raw
    monkeypatch.setattr(nim, "_HTTP_CHILD", controlled_http_wire(wire) + nim._HTTP_CHILD)
    monkeypatch.setenv(nim.KEY_ENV, "invented_key_not_real")
    cfg = config(tmp_path)
    result = asyncio.run(nim.select_and_review(source, request, cfg, input_origin="invented"))
    receipt = result["transport_receipt"]
    assert receipt["http_status"] == 200 and receipt["child_reaped"] is True
    assert receipt["body_within_limit"] is (framing != "body_too_large")
    assert receipt["framing_complete"] is (
        framing
        not in {
            "length_truncated",
            "chunk_truncated",
            "chunk_missing_final_crlf",
            "chunk_bad_separator",
        }
    )
    assert receipt["response_complete"] == receipt["framing_complete"]
    assert receipt["response_bytes"] == len(raw)
    assert result["source_result"] == source
    rejected = framing in {
        "length_truncated",
        "chunk_truncated",
        "chunk_missing_final_crlf",
        "chunk_bad_separator",
        "body_too_large",
    }
    assert result["status"] == ("unavailable" if rejected else "reviewed")
    assert result["failure_stage_code"] == ("transport" if rejected else None)
    outcome = json.loads((cfg.reservation_dir / "outcome.json").read_text())
    assert outcome["transport_receipt"] == receipt
    assert outcome["failure_stage_code"] == result["failure_stage_code"]


def test_response_metadata_does_not_certify_http_framing_from_short_body():
    receipt = nim._transport_receipt()
    nim._response_metadata(envelope("{}"), receipt)
    assert receipt["body_within_limit"] is True
    assert receipt["framing_complete"] is False and receipt["response_complete"] is False


@pytest.mark.parametrize("failure_stage", ["transport", "local_review"])
def test_closed_failure_stage_never_echoes_exception_or_changes_source(
    tmp_path, monkeypatch, failure_stage
):
    source, request = invented(1)
    before = copy.deepcopy(source)
    calls = []
    transport = fake_selection(["c1_prediction"], calls)
    if failure_stage == "transport":

        async def transport(_):
            calls.append("invented_transport")
            raise RuntimeError("PRIVATE_REMOTE_ERROR_KEY_VALUE")
    else:
        original = nim.review_recorded
        reviews = []

        def controlled_review(*args, **kwargs):
            reviews.append(True)
            if len(reviews) == 2:
                raise ValueError("PRIVATE_LOCAL_ERROR_KEY_VALUE")
            return original(*args, **kwargs)

        monkeypatch.setattr(nim, "review_recorded", controlled_review)
    cfg = config(tmp_path)
    result = run_selection(source, request, cfg, transport)
    assert result["failure_stage_code"] == failure_stage
    assert result["status"] == "unavailable" and result["selected_report"] is None
    assert result["source_result"] == source == before
    assert len(calls) == 1
    saved = json.dumps(result) + (cfg.reservation_dir / "outcome.json").read_text()
    assert "PRIVATE_" not in saved
    assert (
        json.loads((cfg.reservation_dir / "outcome.json").read_text())["failure_stage_code"]
        == failure_stage
    )


def test_transport_timeout_persists_stage_and_cleanup_without_claiming_body_complete(
    tmp_path, monkeypatch
):
    source, request = invented(1)
    monkeypatch.setattr(nim, "_HTTP_CHILD", "import time; time.sleep(60)")
    monkeypatch.setattr(nim, "TIMEOUT_SECONDS", 0.05)
    monkeypatch.setenv(nim.KEY_ENV, "invented_timeout_key")
    cfg = config(tmp_path)
    result = asyncio.run(nim.select_and_review(source, request, cfg, input_origin="invented"))
    outcome = json.loads((cfg.reservation_dir / "outcome.json").read_text())
    assert result["status"] == "unavailable" and result["source_result"] == source
    assert result["failure_stage_code"] == outcome["failure_stage_code"] == "transport"
    receipt = outcome["transport_receipt"]
    assert receipt == result["transport_receipt"]
    assert receipt["timed_out"] is True and receipt["child_reaped"] is True
    assert receipt["body_within_limit"] is None
    assert receipt["framing_complete"] is False and receipt["response_complete"] is False
