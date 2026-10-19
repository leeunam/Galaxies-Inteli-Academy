"""Local, bounded candidate extraction using the unmodified reference extractor.

The worker sees only private copies of revalidated media, never briefs, outcomes,
registry IDs or API credentials. Only predictor inputs and states leave the worker.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter, model_validator

from scripts.channel_partitions import Digest, FrozenContract, digest
from scripts.creative_media import MAX_BYTES, ROOT, CreativeError
from scripts.training_manifest import PredictorInputs


class CandidateFeatures(FrozenContract):
    status: Literal["completed", "unavailable"]
    reason_code: (
        Literal[
            "extraction_failed",
            "extraction_timeout",
            "model_weights_unavailable",
            "unsupported_language",
            "language_inconclusive",
        ]
        | None
    ) = None
    inputs: PredictorInputs | None = None
    extractor_config_sha256: Digest

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.status == "completed" and (self.reason_code is not None or self.inputs is None)
        ) or (self.status == "unavailable" and self.reason_code is None):
            raise ValueError("inconsistent_candidate_extraction")
        return self


def _copy_registered(handle, destination, expected):
    hasher, size = hashlib.sha256(), 0
    with destination.open("xb") as output:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                raise CreativeError("media_changed")
            hasher.update(chunk)
            output.write(chunk)
    if size != expected.size_bytes or hasher.hexdigest() != expected.sha256:
        raise CreativeError("media_changed")


def _run_worker(folder: Path, count: int):
    process = subprocess.Popen(
        [sys.executable, "-m", "scripts.candidate_features", str(folder)],
        cwd=ROOT,
        env={
            "PATH": os.defpath,
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "4",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "CUDA_VISIBLE_DEVICES": "",
            "TMPDIR": str(folder),
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=120 + 30 * count)
        return process.returncode == 0
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def extract_candidates(registry, records: dict, config: dict, scratch_root: Path):
    """Own the scratch lifetime in the parent, including worker timeout/cancellation."""
    config_sha = digest(config)
    Path(scratch_root).mkdir(parents=True, exist_ok=True, mode=0o700)
    unavailable = lambda reason: [
        CandidateFeatures(
            status="unavailable", reason_code=reason, extractor_config_sha256=config_sha
        )
        for _ in records
    ]
    with tempfile.TemporaryDirectory(prefix="m1-", dir=scratch_root) as name:
        folder = Path(name)
        requests = []
        for i, record in enumerate(records.values()):
            with registry.open_media(record.relative_path) as handle:
                _copy_registered(handle, folder / f"{i}.media", record.media)
            requests.append({"sector": record.sector, "media": record.media.model_dump()})
        (folder / "request.json").write_text(json.dumps({"config": config, "items": requests}))
        try:
            if not _run_worker(folder, len(requests)):
                return unavailable("extraction_failed")
        except subprocess.TimeoutExpired:
            return unavailable("extraction_timeout")
        from scripts.observed_baseline import read_json

        try:
            results = TypeAdapter(list[CandidateFeatures]).validate_json(
                read_json(folder / "result.json")
            )
            if len(results) != len(requests) or any(
                r.extractor_config_sha256 != config_sha for r in results
            ):
                raise ValueError
            for result, request in zip(results, requests, strict=True):
                if result.status == "completed":
                    inputs, media = result.inputs, request["media"]
                    if (
                        inputs is None
                        or inputs.sector != request["sector"]
                        or abs(inputs.duration_seconds - media["duration_seconds"]) > 1e-6
                        or inputs.aspect_ratio_height_over_width != media["height"] / media["width"]
                    ):
                        raise ValueError
            return results
        except (OSError, ValueError):
            return unavailable("extraction_failed")


def _local_models():
    from huggingface_hub import snapshot_download

    from scripts.pilot_licensed_media import MODELS

    return {
        name: Path(
            snapshot_download(
                repo,
                revision=revision,
                local_files_only=True,
                token=False,
                cache_dir=str(ROOT / "data/cache/huggingface/hub"),
            )
        )
        for name, (repo, revision) in MODELS.items()
    }


def _extract_one(media, work, models, config_sha, cache):
    from scripts.language_audit import language_status
    from scripts.pilot_licensed_media import extract_features

    features = extract_features(media, work, models, False, model_cache=cache)
    status = features["text_features_status"]
    reason = None
    if status == "extracted":
        language = language_status(
            features["asr_language"],
            features["asr_language_probability"],
            features["speech_segments"],
        )
        if language != "portuguese_detected_review_locale":
            reason = (
                "unsupported_language"
                if language == "other_language_detected"
                else "language_inconclusive"
            )
    props = features["properties"]
    inputs = PredictorInputs(
        sector=work.name,
        duration_seconds=props["duration_seconds"],
        aspect_ratio_height_over_width=props["height"] / props["width"],
        text_status=status,
        text_embedding=tuple(features["text_embedding"])
        if features["text_embedding"] is not None
        else None,
    )
    return CandidateFeatures(
        status="unavailable" if reason else "completed",
        reason_code=reason,
        inputs=inputs,
        extractor_config_sha256=config_sha,
    )


def main():
    import resource

    from scripts.experiment_a_data import check_extractor_runtime

    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024, 32 * 1024 * 1024))
    folder = Path(sys.argv[1])
    request = json.loads((folder / "request.json").read_bytes())
    config_sha = digest(request["config"])
    check_extractor_runtime(request["config"], Path(__file__).parent)
    try:
        models = _local_models()
    except (OSError, ValueError, RuntimeError):
        results = [
            CandidateFeatures(
                status="unavailable",
                reason_code="model_weights_unavailable",
                extractor_config_sha256=config_sha,
            )
            for _ in request["items"]
        ]
    else:
        results, cache = [], {}
        for i, item in enumerate(request["items"]):
            work = folder / str(i) / item["sector"]
            work.mkdir(parents=True)
            try:
                result = _extract_one(folder / f"{i}.media", work, models, config_sha, cache)
            except (OSError, ValueError, RuntimeError, KeyError, TypeError):
                result = CandidateFeatures(
                    status="unavailable",
                    reason_code="extraction_failed",
                    extractor_config_sha256=config_sha,
                )
            results.append(result)
    path = folder / "result.json"
    with path.open("x") as output:
        os.chmod(path, 0o600)
        json.dump([r.model_dump() for r in results], output, allow_nan=False)


if __name__ == "__main__":
    main()
