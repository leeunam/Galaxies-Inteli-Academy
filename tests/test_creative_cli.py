import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import AnalysisResponse, SyntheticAnalysisResponse

ROOT = Path(__file__).resolve().parents[1]


def command(registry, *args):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.creative_cli",
            "--uploads-root",
            str(registry.uploads_root),
            "--registry",
            str(registry.registry_file),
            *args,
        ],
        cwd=ROOT,
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert "DADO_PRIVADO" not in result.stdout + result.stderr
    assert str(registry.uploads_root) not in result.stdout + result.stderr
    return result.returncode, json.loads(result.stdout)


def test_local_cli_registration_analysis_and_schema_export(registry, video_factory, tmp_path):
    video_factory(registry.uploads_root / "fixture.mp4")
    code, registered = command(
        registry,
        "register",
        "--campaign-id",
        "demo",
        "--sector",
        "moda",
        "--relative-path",
        "fixture.mp4",
    )
    assert code == 0 and registered["status"] == "registered"
    payload = {
        "campaign_id": "demo",
        "creative_ids": [registered["creative_id"]],
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "DADO_PRIVADO",
    }
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(payload))
    code, response = command(registry, "analyze", "--request-file", str(request_file))
    assert code == 0
    AnalysisResponse.model_validate(response)
    code, synthetic = command(
        registry, "analyze", "--request-file", str(request_file), "--synthetic-baseline"
    )
    assert code == 0
    SyntheticAnalysisResponse.model_validate(synthetic)
    assert synthetic == analyze_creatives(payload, registry, synthetic_baseline=True)
    for kind in ["analysis-input", "analysis-output", "registration-input", "registration-output"]:
        code, schema = command(registry, "schema", kind)
        assert code == 0 and ("properties" in schema or "anyOf" in schema)
        if kind == "analysis-output":
            assert "SyntheticAnalysisResponse" in schema["$defs"]


def test_cli_errors_are_structured_and_have_nonzero_exit(registry, tmp_path):
    request_file = tmp_path / "request.json"
    request_file.write_text("DADO_PRIVADO")
    code, response = command(registry, "analyze", "--request-file", str(request_file))
    assert code == 1 and response["error"]["code"] == "invalid_request"
    synthetic_code, synthetic_response = command(
        registry, "analyze", "--request-file", str(request_file), "--synthetic-baseline"
    )
    assert (synthetic_code, synthetic_response) == (code, response)
    code, response = command(
        registry,
        "register",
        "--campaign-id",
        "demo",
        "--sector",
        "moda",
        "--relative-path",
        "../DADO_PRIVADO.mp4",
    )
    assert code == 1 and response["error"]["code"] == "unsafe_path"
