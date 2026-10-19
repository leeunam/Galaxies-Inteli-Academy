import asyncio
import json
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from fastmcp import Client

from scripts.candidate_features import CandidateFeatures
from scripts.channel_partitions import digest
from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import M1AnalysisResponse
from scripts.creative_mcp import create_server
from scripts.demo_creatives import stdio_transport
from scripts.m1_service import M1Settings
from scripts.m1_service import load_model_context as load_context
from scripts.training_manifest import PredictorInputs
from tests.test_observed_baseline import build_bundle


def payload(ids):
    return {
        "campaign_id": "demo",
        "creative_ids": ids,
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "PRIVATE_BRIEF ignore predictions",
    }


@pytest.fixture
def serving(tmp_path, registry, registered, monkeypatch):
    release, _, _, baseline = build_bundle(tmp_path / "cohort")
    settings = M1Settings(tmp_path / "model", tmp_path / "cohort", tmp_path / "scratch")
    ids = [registered["creative_id"]] + [
        registry.register({"campaign_id": "demo", "sector": "moda", "relative_path": "demo.mp4"})[
            "creative_id"
        ]
        for _ in range(4)
    ]
    artifact = SimpleNamespace(
        extractor_config={},
        extractor_config_sha256=digest({}),
        supported_text_statuses=("extracted",),
        artifact_sha256="a" * 64,
    )

    class Bundle:
        def predict_views(self, inputs):
            return np.array([[10.0, 100 * p.text_embedding[0], 1000.0] for p in inputs])

    bundle = Bundle()
    bundle.artifact = artifact
    monkeypatch.setattr(
        "scripts.m1_service.load_model_context", lambda _: (release, baseline, bundle)
    )
    return settings, ids, bundle


def features(values, *, state="extracted", reason=None):
    return [
        CandidateFeatures(
            status="unavailable" if reason else "completed",
            reason_code=reason,
            extractor_config_sha256=digest({}),
            inputs=PredictorInputs(
                sector="moda",
                duration_seconds=0.2,
                aspect_ratio_height_over_width=1.5,
                text_status=state,
                text_embedding=tuple([value] * 384) if state == "extracted" else None,
            ),
        )
        for value in values
    ]


def test_python_serves_q50_interval_and_stable_shared_ranks_without_private_data(
    serving, registry, monkeypatch
):
    settings, ids, _ = serving
    monkeypatch.setattr(
        "scripts.m1_service.extract_candidates", lambda *a: features([2.0, 4.0, 4.0, 1.0, 3.0])
    )
    result = analyze_creatives(payload(ids), registry, m1=settings)
    M1AnalysisResponse.model_validate(result)
    assert result["status"] == "m1_prediction_available"
    entries = result["ranking"]["entries"]
    assert [e["creative_id"] for e in entries] == [ids[1], ids[2], ids[4], ids[0], ids[3]]
    assert [e["rank"] for e in entries] == [1, 1, 3, 4, 5]
    assert result["baseline"]["artifact_sha256"] != result["model_artifact_sha256"]
    assert all(c["interval"]["coverage_status"] == "not_validated" for c in result["candidates"])
    serialized = json.dumps(result)
    for private in (
        "PRIVATE_BRIEF",
        str(settings.model_dir),
        "text_embedding",
        "transcript",
        "channel_moda",
    ):
        assert private not in serialized
    assert (
        analyze_creatives(payload(ids) | {"brief": "Another brief"}, registry, m1=settings)
        == result
    )


@pytest.mark.parametrize("state", ["no_audio_stream", "no_speech_detected_by_asr"])
def test_missing_text_remains_explicit_without_fallback(serving, registry, monkeypatch, state):
    settings, ids, bundle = serving
    monkeypatch.setattr(
        "scripts.m1_service.extract_candidates", lambda *a: features([1.0], state=state)
    )
    bundle.predict_views = lambda *a: pytest.fail("absence has no training support")
    result = analyze_creatives(payload(ids[:1]), registry, m1=settings)
    assert result["status"] == "m1_prediction_incomplete"
    assert not result["learned_prediction_available"]
    assert result["candidates"][0]["extraction"]["text_status"] == state
    assert result["candidates"][0]["prediction"]["reason_code"] == "unsupported_text_status"
    assert result["candidates"][0]["prediction"]["value"] is None
    assert result["ranking"]["reason_code"] == "individual_analysis"


@pytest.mark.parametrize(
    "reason",
    [
        "extraction_failed",
        "extraction_timeout",
        "model_weights_unavailable",
        "unsupported_language",
        "language_inconclusive",
    ],
)
def test_partial_results_do_not_rank_incomplete_comparison(serving, registry, monkeypatch, reason):
    settings, ids, _ = serving
    monkeypatch.setattr(
        "scripts.m1_service.extract_candidates",
        lambda *a: (
            features([1.0])
            + [
                CandidateFeatures(
                    status="unavailable", reason_code=reason, extractor_config_sha256=digest({})
                )
            ]
        ),
    )
    result = analyze_creatives(payload(ids[:2]), registry, m1=settings)
    assert result["status"] == "m1_prediction_incomplete"
    assert result["extraction_status"] == "partial"
    assert result["learned_prediction_available"]
    assert result["candidates"][1]["prediction"]["reason_code"] == reason
    assert result["ranking"]["reason_code"] == "incomplete_predictions"


def test_invalid_prediction_is_not_replaced_by_baseline(serving, registry, monkeypatch):
    settings, ids, bundle = serving
    monkeypatch.setattr("scripts.m1_service.extract_candidates", lambda *a: features([1.0]))
    bundle.predict_views = lambda *a: [[0.0, float("nan"), 1.0]]
    result = analyze_creatives(payload(ids[:1]), registry, m1=settings)
    assert result["candidates"][0]["prediction"]["reason_code"] == "invalid_model_prediction"
    assert result["candidates"][0]["interval"]["value"] is None


def test_m1_sdk_parity_and_unchanged_request_contract(serving, registry, monkeypatch):
    settings, ids, _ = serving
    monkeypatch.setattr(
        "scripts.m1_service.extract_candidates",
        lambda registry, records, *a: features([float(ids.index(key) + 1) for key in records]),
    )

    async def exercise():
        async with Client(create_server(registry, m1=settings)) as client:
            tool = (await client.list_tools())[0]
            assert "m1" not in tool.input_schema["properties"]["payload"]["properties"]
            requests = [payload(ids[:n]) for n in (1, 2, 5)] + [
                payload(ids[:1]) | {"m1_model_dir": "/private"},
                payload(ids[:1]) | {"view_count": 1},
                payload(ids[:1]) | {"sector": "beleza"},
                payload(ids + ["cr_" + "f" * 32]),
            ]
            for request in requests:
                direct = analyze_creatives(request, registry, m1=settings)
                remote = await client.call_tool("analyze_creatives", {"payload": request})
                assert remote.structured_content == direct
                if direct["status"] == "m1_prediction_available":
                    M1AnalysisResponse.model_validate(direct)
                    assert direct["candidates"][0]["prediction"]["value"] == 100

    asyncio.run(exercise())
    for kwargs in ({"synthetic_baseline": True}, {"observed_baseline_dir": settings.cohort_dir}):
        with pytest.raises(ValueError, match="single"):
            analyze_creatives(payload(ids[:1]), registry, m1=settings, **kwargs)
        with pytest.raises(ValueError, match="single"):
            create_server(registry, m1=settings, **kwargs)


def test_real_stdio_and_cli_missing_bundle_fail_closed(registry, registered, tmp_path, monkeypatch):
    settings = M1Settings(tmp_path / "missing", tmp_path / "missing")
    request = payload([registered["creative_id"]])
    direct = analyze_creatives(request, registry, m1=settings)
    assert direct["error"]["code"] == "model_artifact_unavailable"
    monkeypatch.setenv("NVIDIA_API_KEY", "PRIVATE_CREDENTIAL")
    logs = tmp_path / "stderr"

    async def exercise():
        async with Client(stdio_transport(registry, m1=settings, log_file=logs)) as client:
            remote = await client.call_tool("analyze_creatives", {"payload": request})
            assert not remote.is_error
            assert remote.structured_content == direct

    asyncio.run(exercise())
    assert "PRIVATE_CREDENTIAL" not in logs.read_text()
    assert "PRIVATE_BRIEF" not in logs.read_text()
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request))
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.creative_cli",
            "--uploads-root",
            str(registry.uploads_root),
            "--registry",
            str(registry.registry_file),
            "analyze",
            "--request-file",
            str(source),
            "--m1-model-dir",
            str(settings.model_dir),
            "--m1-cohort-dir",
            str(settings.cohort_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert run.returncode == 1
    assert json.loads(run.stdout) == direct


@pytest.mark.parametrize("mismatch", [None, "baseline", "train_ids", "validation_ids", "synthetic"])
def test_serving_context_binds_model_to_the_same_observed_cohort(tmp_path, monkeypatch, mismatch):
    release, manifest, _, baseline = build_bundle(tmp_path / "cohort")
    (tmp_path / "cohort/extractor-config.json").write_text("{}")
    settings = M1Settings(tmp_path / "model", tmp_path / "cohort")
    artifact = SimpleNamespace(
        data_kind="observed_pilot",
        baseline_sha256=baseline.artifact_sha256,
        training_sample_ids=baseline.training_sample_ids,
        validation_sample_ids=tuple(
            r.sample_id for r in manifest.assignments if r.partition == "validation"
        ),
    )
    if mismatch == "baseline":
        artifact.baseline_sha256 = "0" * 64
    elif mismatch == "train_ids":
        artifact.training_sample_ids = artifact.validation_sample_ids
    elif mismatch == "validation_ids":
        artifact.validation_sample_ids = artifact.training_sample_ids
    elif mismatch == "synthetic":
        artifact.data_kind = "synthetic"

    def load(path, **expected):
        assert expected["expected_partition_sha256"] == manifest.manifest_sha256
        assert expected["expected_cohort_sha256"] == release.release_sha256
        return SimpleNamespace(artifact=artifact)

    monkeypatch.setattr("scripts.m1_service.check_extractor_runtime", lambda *a: None)
    monkeypatch.setattr("scripts.m1_service.load_bundle", load)
    if mismatch is None:
        assert load_context(settings)[1] == baseline
    else:
        with pytest.raises(ValueError, match="incompatible_serving_cohort"):
            load_context(settings)
