import copy
import hashlib
import io
import json
import subprocess
import sys
import uuid

import pytest

from orchestration.galaxies_orchestration.observation_cases_v2 import EXPECTED, content
from scripts.explanation_observer_v2 import ObservationSession
from scripts.explanation_synthetic_worker import SyntheticSession
from scripts.explanation_worker import serve
from scripts.selection_observation_v2 import after_sealed_validation
from tests.test_explanation_evidence import evidence_inputs  # noqa: F401
from tests.test_m1_service import serving  # noqa: F401


@pytest.mark.parametrize("case", EXPECTED)
def test_sealed_acceptance_rendering_and_numeric_parity(case, capfd):
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    old, new = SyntheticSession(), ObservationSession()
    prepare = {"op": "prepare", "payload": {}}
    assert old.handle(prepare) == new.handle(prepare)
    raw = content(case, secret=secret)
    message = {"op": "render", "selection": raw, "reason": None}
    expected, observed = old.handle(message), new.handle(message)
    observation = observed.pop("selection_observation")
    assert observed == expected
    assert (observation["phase"], observation["code"]) == EXPECTED[case]
    assert observation["classifier_parity"] is True
    assert observation["authority_accepted"] is (case in {"valid", "valid_whitespace"})
    assert observation["raw_response_sha256"] is None
    encoded = json.dumps(observation).encode()
    assert secret.encode() not in encoded and b"Authorization" not in encoded
    if case in {"valid", "valid_whitespace", "duplicate_ids"}:
        canonical = json.dumps(observation["safe_response_projection"], sort_keys=True).encode()
        assert observation["retained_projection_sha256"] == hashlib.sha256(canonical).hexdigest()
    else:
        assert observation["safe_response_projection"] is None
        assert observation["retained_projection_sha256"] is None
    output = capfd.readouterr()
    assert secret not in output.out + output.err


def test_private_context_never_enters_projection():
    session = SyntheticSession()
    session.handle({"op": "prepare", "payload": {}})
    context = copy.copy(session.context)
    # Different analysis fingerprint changes the packet binding; still a valid local context.
    object.__setattr__(
        context, "packet", context.packet.model_copy(update={"analysis_sha256": "f" * 64})
    )
    raw = json.dumps({"packet_sha256": context.packet_sha256, "evidence_ids": ["c1_prediction"]})
    from scripts.explanation_evidence import validate_selection

    result = validate_selection(context, raw)
    observation = after_sealed_validation(context, raw, result)
    assert observation["authority_accepted"] is True
    assert observation["safe_response_projection"] is None
    assert observation["retained_projection_sha256"] is None


def test_original_recursion_failure_remains_failure_with_safe_json_telemetry():
    old, new = SyntheticSession(), ObservationSession()
    for session in (old, new):
        session.handle({"op": "prepare", "payload": {}})
    raw = "[" * 2500 + "]" * 2500
    message = {"op": "render", "selection": raw, "reason": None}
    with pytest.raises(RecursionError):
        old.handle(message)
    result = new.handle(message)
    assert result["observer_worker_failure"] is True
    assert result["selection_observation"]["code"] == "json_depth_limit"
    assert result["selection_observation"]["authority_status"] == "failed_before_result"
    assert "analysis" not in result and "explanation" not in result


def test_comparative_numbers_and_ranking_are_unchanged(evidence_inputs):  # noqa: F811
    from scripts.explanation_evidence import build_explanation_context, validate_selection

    report, shap, references = evidence_inputs
    context = build_explanation_context(report, shap=shap, comparables=references)
    raw = json.dumps(
        {
            "packet_sha256": context.packet_sha256,
            "evidence_ids": ["c1_prediction", "c2_prediction", "c3_prediction"],
        }
    )
    result = validate_selection(context, raw)
    before = json.dumps(result, sort_keys=True)
    observation = after_sealed_validation(context, raw, result)
    assert json.dumps(result, sort_keys=True) == before
    assert result["analysis"] == report
    assert result["analysis"]["ranking"] == report["ranking"]
    assert observation["authority_accepted"] is True
    assert observation["safe_response_projection"] is None


def test_root_worker_stdout_bytes_never_echo_secret_headers_or_error_inputs():
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    for case in ("secret_extra", "secret_fieldname", "secret_id", "secret_digest"):
        messages = [
            {"op": "prepare", "payload": {}},
            {"op": "render", "selection": content(case, secret=secret), "reason": None},
        ]
        source = io.BytesIO(b"".join(json.dumps(m).encode() + b"\n" for m in messages))
        output = io.BytesIO()
        serve(ObservationSession(), source, output)
        assert secret.encode() not in output.getvalue()
        assert b"Authorization" not in output.getvalue()
        assert b"schema_extra_field" in output.getvalue() or b"references" in output.getvalue()


@pytest.mark.parametrize(
    "case", ["envelope_extra_secret", "content_extra_secret", "read_exception"]
)
def test_real_worker_stdout_and_stderr_bytes_suppress_secret(tmp_path, case):
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    messages = [
        {"op": "prepare", "payload": {}},
        {"op": "observe_http_fixture", "case": case, "fixture_secret": secret},
    ]
    run = subprocess.run(
        [sys.executable, "-m", "scripts.explanation_observer_v2"],
        input=b"".join(json.dumps(m).encode() + b"\n" for m in messages),
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert run.returncode == 0
    assert secret.encode() not in run.stdout + run.stderr
    assert b"Authorization" not in run.stdout + run.stderr
    assert b"Bearer " not in run.stdout + run.stderr
    assert run.stderr == b""
    result = json.loads(run.stdout.splitlines()[-1])
    assert "selection_observation" in result
