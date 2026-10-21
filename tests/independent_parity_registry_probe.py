"""Real registry validation/metadata decode only; no M1 import or model call."""

import errno
import os
import sys
from pathlib import Path

from scripts.creative_contracts import AnalysisRequest
from scripts.creative_media import CreativeError
from scripts.creative_registry import CreativeRegistry
from scripts.demo_recovery_policy import digest, exclusive_json, read_json


def main():
    config, output, expectation = read_json(Path(sys.argv[1])), Path(sys.argv[2]), sys.argv[3]
    original = Path(config["run_dir"])
    registry_file = original / "registry.json"
    before = digest(registry_file)
    request = AnalysisRequest.model_validate(read_json(original / "request.json"))
    try:
        fd = os.open(
            registry_file.with_suffix(".lock"),
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
        )
    except OSError as error:
        assert expectation == "readonly" and error.errno == errno.EROFS
        lock_errno = "EROFS"  # No raw exception/path retained.
    else:
        os.close(fd)
        assert expectation == "overlay"
        lock_errno = None
    try:
        records = CreativeRegistry(original / "inputs", registry_file).validate_creatives(request)
    except CreativeError as error:
        assert expectation == "readonly" and error.code == "registry_unavailable"
        outcome = "registry_unavailable"
        validated = 0
    else:
        assert expectation == "overlay" and tuple(records) == tuple(request.creative_ids)
        expected = read_json(registry_file)["creatives"]
        assert all(row.model_dump(mode="json") == expected[cid] for cid, row in records.items())
        outcome, validated = "native_registry_validation_completed", len(records)
    assert digest(registry_file) == before
    assert not any(
        name in sys.modules
        for name in ("scripts.m1_service", "torch", "catboost", "sentence_transformers")
    )
    exclusive_json(
        output,
        {
            "lock_open_errno_redacted": lock_errno,
            "validation_outcome": outcome,
            "validated_creatives": validated,
            "registry_bytes_unchanged": True,
            "real_m1_or_encoder_imports": 0,
            "model_loads": 0,
            "predictions": 0,
            "shap_calls": 0,
            "feature_extractions": 0,
            "native_metadata_inspections": validated,
            "same_request_and_uploads": True,
        },
    )
    print('{"registry_probe_completed":true,"model_calls":0}')


if __name__ == "__main__":
    main()
