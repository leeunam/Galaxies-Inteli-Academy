"""Opt-in read of one operator-pinned historical demo report; never computes ML."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from scripts.channel_partitions import Digest, FrozenContract, digest
from scripts.creative_contracts import AnalysisRequest, M1AnalysisResponse
from scripts.creative_registry import CreativeRegistry, RegistryState
from scripts.explanation_evidence import _check_report
from scripts.explanation_graph_service_v2 import IntegratedResponse

SCHEMA = "demo-canonical-consultation-v1"
ROLES = {
    "request",
    "registry",
    "config",
    "acquired",
    "report",
    "execution_receipt",
    "python_job_receipt",
    "origin",
}
RETENTION_CEILING = datetime.fromisoformat("2026-10-21T23:59:00-03:00")
# Anchors audited before creating a canonical manifest. Inventing a manifest
# and report together cannot qualify another report as this real demo source.
REAL_SOURCE_PINS = {
    "report": "bb45d32e00eb2cf6a1c3c5102b2f6471b5660a2462406117b1134b9ff695bcfd",
    "execution_receipt": "868aee86b7eec674bca79bd6068acb32d47895d8ba57b459758df34a6fd8ff5d",
    "origin": "816324ecf9054f4e3f20b82232c07a98b7c4961940619fe37754434c42eee48a",
}


class PinnedFile(FrozenContract):
    relative_path: str = Field(min_length=1, max_length=512)
    sha256: Digest


class CanonicalManifest(FrozenContract):
    schema_version: Literal["demo-canonical-report-manifest-v1"]
    data_kind: Literal["preserved_real_demo", "synthetic_fixture"]
    expires_at: str
    files: dict[str, PinnedFile]
    inputs_root: str
    model_artifact_sha256: Digest
    extractor_config_sha256: Digest
    baseline_sha256: Digest
    packet_sha256: Digest
    analysis_sha256: Digest
    cold_run_exact_parity: Literal[False]


@dataclass(frozen=True)
class CanonicalDemoSettings:
    # Trusted operator only. No path or manifest can be selected through payload.
    root: Path
    manifest_file: Path
    manifest_sha256: str


def _path(root, relative):
    value = Path(relative)
    if not value.parts or value.is_absolute() or ".." in value.parts:
        raise ValueError("canonical_path")
    target = root / value
    for item in (root, *reversed(target.parents), target):
        if (item == root or item.is_relative_to(root)) and item.is_symlink():
            raise ValueError("canonical_symlink")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("canonical_path")
    return target


def _pinned_json(root, pin):
    path = _path(root, pin.relative_path)
    # Read/hash/parse the same bytes; no separate check-then-read of report data.
    raw = _read_bytes(path)
    if hashlib.sha256(raw).hexdigest() != pin.sha256:
        raise ValueError("canonical_digest")
    from scripts.demo_recovery_policy import unique_pairs

    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=_reject_constant)


def _reject_constant(_):
    raise ValueError("canonical_nonfinite")


def _read_bytes(path):
    import os
    import stat

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("canonical_file")
        raw = handle.read(262145)
    if len(raw) > 262144:
        raise ValueError("canonical_limit")
    return raw


def _consult(payload, settings):
    root = Path(settings.root).absolute()
    manifest_path = Path(settings.manifest_file).absolute()
    relative = str(manifest_path.relative_to(root))
    body = _pinned_json(root, PinnedFile(relative_path=relative, sha256=settings.manifest_sha256))
    manifest = CanonicalManifest.model_validate_json(json.dumps(body, allow_nan=False))
    expiry = datetime.fromisoformat(manifest.expires_at)
    if expiry.tzinfo is None or not datetime.now(expiry.tzinfo) < expiry <= RETENTION_CEILING:
        raise ValueError("canonical_expired")
    if set(manifest.files) != ROLES:
        raise ValueError("canonical_roles")
    if manifest.data_kind == "preserved_real_demo" and any(
        manifest.files[role].sha256 != expected for role, expected in REAL_SOURCE_PINS.items()
    ):
        raise ValueError("canonical_real_source_anchor")
    files = {role: _pinned_json(root, pin) for role, pin in manifest.files.items()}
    request = AnalysisRequest.model_validate(payload).model_dump(mode="json")
    saved_request = AnalysisRequest.model_validate(files["request"]).model_dump(mode="json")
    if request != saved_request or len(request["creative_ids"]) != 3:
        raise ValueError("canonical_request")
    report = files["report"]
    validated = IntegratedResponse.model_validate_json(json.dumps(report, allow_nan=False))
    analysis = M1AnalysisResponse.model_validate_json(json.dumps(report["analysis"]))
    _check_report(analysis)
    if validated.model_dump(mode="json") != report:
        raise ValueError("canonical_report_defaults")
    if (
        analysis.status != "m1_prediction_available"
        or any(c.prediction.status != "estimated" for c in analysis.candidates)
        or [c.creative_id for c in analysis.candidates] != request["creative_ids"]
        or (analysis.campaign_id, analysis.sector, analysis.objective)
        != (request["campaign_id"], request["sector"], request["objective"])
        or analysis.model_artifact_sha256 != manifest.model_artifact_sha256
        or analysis.extractor_config_sha256 != manifest.extractor_config_sha256
        or analysis.baseline.artifact_sha256 != manifest.baseline_sha256
        or digest(report["analysis"]) != manifest.analysis_sha256
        or validated.evidence_packet is None
        or validated.evidence_packet.analysis_sha256 != manifest.analysis_sha256
        or validated.evidence_packet.model_artifact_sha256 != manifest.model_artifact_sha256
        or validated.evidence_packet.sector != analysis.sector
        or validated.evidence_packet.objective != analysis.objective
        or digest(report["evidence_packet"]) != manifest.packet_sha256
        or validated.explanation.packet_sha256 != manifest.packet_sha256
        or len({f.evidence_id for f in validated.evidence_packet.evidence})
        != len(validated.evidence_packet.evidence)
        or any(
            f.creative_id not in (None, *request["creative_ids"])
            for f in validated.evidence_packet.evidence
        )
    ):
        raise ValueError("canonical_context")
    # Parse the existing registry contract, but never decode media/register anew.
    state = RegistryState.model_validate_json(json.dumps(files["registry"]))
    uploads = _path(root, manifest.inputs_root)
    registry = CreativeRegistry(uploads, _path(root, manifest.files["registry"].relative_path))
    acquired = files["acquired"]["inputs"]
    if len(acquired) != 3 or files["config"]["inputs"] != acquired:
        raise ValueError("canonical_inputs")
    by_path = {row["relative_path"]: row for row in acquired}
    if len(by_path) != 3 or files["config"]["campaign_id"] != request["campaign_id"]:
        raise ValueError("canonical_inputs")
    for cid in request["creative_ids"]:
        record = state.creatives[cid]
        expected = by_path.pop(record.relative_path)
        if (
            record.campaign_id != request["campaign_id"]
            or record.sector != request["sector"]
            or record.media.sha256 != expected["sha256"]
            or record.media.size_bytes != expected["size_bytes"]
            or record.media.size_bytes > 32 * 1024**2
        ):
            raise ValueError("canonical_registry")
        with registry.open_media(record.relative_path) as handle:
            import os

            if os.fstat(handle.fileno()).st_size != expected["size_bytes"]:
                raise ValueError("canonical_media")
            if hashlib.file_digest(handle, "sha256").hexdigest() != expected["sha256"]:
                raise ValueError("canonical_media")
    job, receipt, origin = (files[k] for k in ("python_job_receipt", "execution_receipt", "origin"))
    if not (
        job["code"] == "completed" and job["cleanup_confirmed"] is True and job["returncode"] == 0
    ):
        raise ValueError("canonical_execution")
    if not (
        receipt["analyze"]["python_status"] == analysis.status
        and receipt["analyze"]["estimated_count"] == 3
    ):
        raise ValueError("canonical_execution")
    if manifest.data_kind == "preserved_real_demo":
        event = origin["entry"]
        if (
            origin["evidence_kind"] != "read_thread_command_execution"
            or event["type"] != "commandExecution"
            or event["status"] not in {"completed", "failed"}
            or not event["id"].startswith("exec-")
            or "scripts.demo_recovery analyze" not in event["command"]
            or event["exitCode"] != receipt["analyze"]["exitcode"]
            or origin["source_release_entry_id"] != receipt["release_origin_actual_entry_id"]
        ):
            raise ValueError("canonical_origin")
    elif origin != {"evidence_kind": "synthetic_fixture", "actual_execution_claimed": False}:
        raise ValueError("canonical_fixture")
    return {
        "schema_version": SCHEMA,
        "status": "canonical_report_cache_hit",
        "cache": {
            "cache_hit": True,
            "origin": "preserved_native_python_report"
            if manifest.data_kind == "preserved_real_demo"
            else "explicit_invented_fixture_report",
            "data_kind": manifest.data_kind,
            "manifest_sha256": settings.manifest_sha256,
            "report_sha256": manifest.files["report"].sha256,
            "source_execution_receipt_sha256": manifest.files["execution_receipt"].sha256,
            "source_origin_sha256": manifest.files["origin"].sha256,
            "expires_at": manifest.expires_at,
            "new_extraction_performed": False,
            "new_model_inference_performed": False,
            "new_native_execution_performed": False,
            "fresh_extraction": False,
            "fresh_stategraph": False,
            "fresh_provider_call": False,
            "report_flags_describe_historical_execution": True,
            "cold_run_exact_parity": False,
        },
        "report": report,
    }


def get_canonical_demo_report(payload, settings: CanonicalDemoSettings):
    """Read one pinned historical result, refusing mismatch without recomputation."""
    try:
        return _consult(payload, settings)
    except Exception:  # noqa: BLE001 - no private value/path/exception crosses API
        return {
            "schema_version": SCHEMA,
            "status": "canonical_report_rejected",
            "cache_hit": False,
            "reason_code": "bound_report_unavailable_or_mismatch",
            "new_native_execution_performed": False,
        }
