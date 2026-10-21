"""Invented files/numbers only; no media decoding, extraction or model execution."""

import asyncio
import copy
import hashlib
import json
import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.channel_partitions import digest
from scripts.demo_canonical_report import CanonicalDemoSettings, get_canonical_demo_report
from scripts.explanation_composition import ExplanationNotice
from scripts.explanation_evidence import build_explanation_context
from scripts.explanation_graph_service_v2 import IntegratedResponse
from tests.native_v2_fixture import public_data

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False) + "\n")


class InventedFixtureClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls.fromisoformat("2026-10-20T12:00:00-03:00").astimezone(tz)


@pytest.fixture
def canonical(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.demo_canonical_report.datetime", InventedFixtureClock)
    report = public_data()["report"]
    context = build_explanation_context(report)
    full = IntegratedResponse.model_validate_json(
        json.dumps(
            {
                "schema_version": "creative-explanation-integrated-v2",
                "analysis": report,
                "explanation": ExplanationNotice(
                    reason_code="transport_not_configured",
                    packet_sha256=context.packet_sha256,
                ).model_dump(mode="json"),
                "evidence_packet": context.packet.model_dump(mode="json"),
                "orchestration": {
                    "kind": "integrated_stategraph_v2",
                    "stategraph_executed": True,
                    "explainer_subgraph_executed": True,
                    "native_feature_handoff": True,
                    "real_provider_verified": False,
                    "selector_kind": "absent",
                },
            }
        )
    ).model_dump(mode="json")
    request = {
        "campaign_id": "invented",
        "sector": "moda",
        "objective": "divulgacao",
        "creative_ids": [c["creative_id"] for c in report["candidates"]],
        "brief": "EXPLICIT_INVENTED_FIXTURE_NOT_REAL_MODEL",
    }
    inputs, records = [], {}
    (tmp_path / "inputs").mkdir()
    for i, cid in enumerate(request["creative_ids"]):
        name = f"invented-{i}.mp4"
        media = tmp_path / "inputs" / name
        media.write_bytes(f"invented bytes {i}".encode())
        row = {
            "alias": f"invented_{i}",
            "relative_path": name,
            "sha256": file_hash(media),
            "size_bytes": media.stat().st_size,
        }
        inputs.append(row)
        records[cid] = {
            "campaign_id": "invented",
            "sector": "moda",
            "relative_path": name,
            "media": {
                "sha256": row["sha256"],
                "size_bytes": row["size_bytes"],
                "duration_seconds": 0.2,
                "width": 64,
                "height": 96,
            },
        }
    values = {
        "request": request,
        "report": full,
        "registry": {"version": "creative-registry-v1", "creatives": records},
        "config": {"campaign_id": "invented", "inputs": inputs},
        "acquired": {"inputs": inputs},
        "execution_receipt": {"analyze": {"python_status": report["status"], "estimated_count": 3}},
        "python_job_receipt": {"code": "completed", "cleanup_confirmed": True, "returncode": 0},
        "origin": {"evidence_kind": "synthetic_fixture", "actual_execution_claimed": False},
    }
    for role, value in values.items():
        write_json(tmp_path / (role + ".json"), value)
    manifest = {
        "schema_version": "demo-canonical-report-manifest-v1",
        "data_kind": "synthetic_fixture",
        "expires_at": "2026-10-21T23:59:00-03:00",
        "inputs_root": "inputs",
        "files": {
            k: {"relative_path": k + ".json", "sha256": file_hash(tmp_path / (k + ".json"))}
            for k in values
        },
        "model_artifact_sha256": report["model_artifact_sha256"],
        "extractor_config_sha256": report["extractor_config_sha256"],
        "baseline_sha256": report["baseline"]["artifact_sha256"],
        "packet_sha256": context.packet_sha256,
        "analysis_sha256": digest(report),
        "cold_run_exact_parity": False,
    }
    write_json(tmp_path / "manifest.json", manifest)
    settings = CanonicalDemoSettings(
        tmp_path, tmp_path / "manifest.json", file_hash(tmp_path / "manifest.json")
    )
    return settings, request, full, manifest


def reseal(settings, manifest, role=None):
    if role:
        manifest["files"][role]["sha256"] = file_hash(settings.root / (role + ".json"))
    write_json(settings.manifest_file, manifest)
    return replace(settings, manifest_sha256=file_hash(settings.manifest_file))


def assert_rejected(reply):
    assert reply["status"] == "canonical_report_rejected"
    assert reply["cache_hit"] is False and reply["new_native_execution_performed"] is False
    assert "report" not in reply and "EXPLICIT_INVENTED" not in json.dumps(reply)


def test_reads_identical_historical_report_without_execution(canonical, monkeypatch):
    settings, request, report, _ = canonical

    def forbidden(*args, **kwargs):
        pytest.fail("canonical consultation attempted decoding, extraction, model or graph")

    for target in [
        "scripts.creative_media.inspect_media",
        "scripts.candidate_features.extract_candidates",
        "scripts.m1_service.load_model_context",
        "scripts.explanation_graph_service_v2.analyze_via_graph",
        "catboost.CatBoostRegressor.load_model",
        "subprocess.Popen",
    ]:
        monkeypatch.setattr(target, forbidden)
    result = get_canonical_demo_report(request, settings)
    assert result["status"] == "canonical_report_cache_hit"
    assert result["report"] == report
    assert result["cache"]["data_kind"] == "synthetic_fixture"
    assert result["cache"]["origin"] == "explicit_invented_fixture_report"
    assert result["cache"]["new_model_inference_performed"] is False
    assert result["cache"]["new_extraction_performed"] is False
    assert result["cache"]["report_flags_describe_historical_execution"] is True
    assert result["report"]["orchestration"]["stategraph_executed"] is True
    assert result["cache"]["cold_run_exact_parity"] is False


@pytest.mark.parametrize("mutation", ["brief", "order", "operator_path"])
def test_request_key_is_complete_and_order_sensitive(canonical, mutation):
    settings, request, _, _ = canonical
    request = copy.deepcopy(request)
    if mutation == "brief":
        request["brief"] += " changed"
    elif mutation == "order":
        request["creative_ids"].reverse()
    else:
        request["manifest_file"] = "/invented/untrusted"
    assert_rejected(get_canonical_demo_report(request, settings))


@pytest.mark.parametrize(
    "role",
    sorted(
        [
            "request",
            "report",
            "registry",
            "config",
            "acquired",
            "execution_receipt",
            "python_job_receipt",
            "origin",
        ]
    ),
)
def test_any_pinned_file_change_is_rejected(canonical, role):
    settings, request, _, _ = canonical
    with (settings.root / (role + ".json")).open("ab") as f:
        f.write(b" ")
    assert_rejected(get_canonical_demo_report(request, settings))


@pytest.mark.parametrize(
    "mutation",
    [
        "media",
        "symlink",
        "manifest_hash",
        "expired",
        "extended",
        "bad_packet",
        "model",
        "extractor",
        "baseline",
        "config",
        "job_failed",
        "false_real_origin",
    ],
)
def test_binding_or_retention_failure_never_recomputes(canonical, mutation):
    settings, request, _, manifest = canonical
    if mutation == "media":
        (settings.root / "inputs/invented-0.mp4").write_bytes(b"different")
    elif mutation == "symlink":
        path = settings.root / "inputs/invented-0.mp4"
        path.unlink()
        path.symlink_to(settings.root / "inputs/invented-1.mp4")
    elif mutation == "manifest_hash":
        settings = replace(settings, manifest_sha256="0" * 64)
    elif mutation in {"expired", "extended"}:
        manifest["expires_at"] = (
            "2020-01-01T00:00:00+00:00" if mutation == "expired" else "2030-01-01T00:00:00+00:00"
        )
        settings = reseal(settings, manifest)
    elif mutation in {"bad_packet", "model", "extractor", "baseline", "false_real_origin"}:
        key = {
            "bad_packet": "packet_sha256",
            "model": "model_artifact_sha256",
            "extractor": "extractor_config_sha256",
            "baseline": "baseline_sha256",
        }.get(mutation)
        if key:
            manifest[key] = "0" * 64
        else:
            manifest["data_kind"] = "preserved_real_demo"
        settings = reseal(settings, manifest)
    elif mutation == "config":
        value = json.loads((settings.root / "config.json").read_text())
        value["campaign_id"] = "changed"
        write_json(settings.root / "config.json", value)
        settings = reseal(settings, manifest, "config")
    elif mutation == "job_failed":
        value = json.loads((settings.root / "python_job_receipt.json").read_text())
        value["returncode"] = 1
        write_json(settings.root / "python_job_receipt.json", value)
        settings = reseal(settings, manifest, "python_job_receipt")
    assert_rejected(get_canonical_demo_report(request, settings))


def test_real_stdio_queries_same_invented_report(canonical, tmp_path):
    settings, request, _, _ = canonical
    direct = get_canonical_demo_report(request, settings)

    async def run():
        transport = StdioTransport(
            command=sys.executable,
            args=[
                "-B",
                "-m",
                "tests.test_demo_canonical_report",
                "--root",
                str(settings.root),
                "--manifest",
                str(settings.manifest_file),
                "--manifest-sha256",
                settings.manifest_sha256,
            ],
            cwd=str(ROOT),
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            keep_alive=False,
            log_file=tmp_path / "canonical-stdio.log",
        )
        async with Client(transport) as client:
            tools = await client.list_tools()
            assert [t.name for t in tools] == ["get_canonical_demo_report"]
            assert set(tools[0].input_schema["properties"]) == {"payload"}
            response = await client.call_tool("get_canonical_demo_report", {"payload": request})
            assert response.structured_content == direct

    asyncio.run(run())
    assert direct["status"] == "canonical_report_cache_hit"
    assert "EXPLICIT_INVENTED_FIXTURE" not in (tmp_path / "canonical-stdio.log").read_text()


def test_stdio_invalid_payload_reaches_sanitized_getter(canonical, tmp_path):
    settings, _, _, _ = canonical
    sentinel = "INVENTED_INVALID_CANONICAL_PAYLOAD_SENTINEL"
    log = tmp_path / "invalid-payload-stdio.log"

    async def run():
        transport = StdioTransport(
            command=sys.executable,
            args=[
                "-B",
                "-m",
                "tests.test_demo_canonical_report",
                "--root",
                str(settings.root),
                "--manifest",
                str(settings.manifest_file),
                "--manifest-sha256",
                settings.manifest_sha256,
            ],
            cwd=str(ROOT),
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            keep_alive=False,
            log_file=log,
        )
        async with Client(transport) as client:
            response = await client.call_tool("get_canonical_demo_report", {"payload": sentinel})
            assert response.is_error is False
            assert_rejected(response.structured_content)
            assert sentinel not in json.dumps(response.structured_content)
            assert sentinel not in str(response.content)

    asyncio.run(run())
    assert sentinel not in log.read_text()


if __name__ == "__main__":
    # Only the invented test server uses a fixed clock; production CLI does not.
    import scripts.demo_canonical_report as canonical_module
    from scripts.demo_canonical_mcp import main

    canonical_module.datetime = InventedFixtureClock
    main()
