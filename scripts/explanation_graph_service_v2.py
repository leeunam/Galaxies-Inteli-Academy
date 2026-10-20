"""Shared Python/MCP use case. No provider, credentials, installation or network."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import anyio
from pydantic import ValidationError

from scripts.channel_partitions import FrozenContract
from scripts.creative_contracts import AnalysisRequest, AnalysisResult
from scripts.explanation_composition import CatalogueExplanation, ExplanationNotice
from scripts.explanation_evidence import EvidencePacket
from scripts.m1_service import M1Settings

ROOT = Path(__file__).resolve().parents[1]
MAX_LINE = 262144


class OrchestrationStatus(FrozenContract):
    kind: Literal["integrated_stategraph_v2"] = "integrated_stategraph_v2"
    stategraph_executed: bool
    explainer_subgraph_executed: bool
    native_feature_handoff: bool
    real_provider_verified: Literal[False] = False
    selector_kind: Literal["absent", "trusted_local_callback"] = "absent"


class IntegratedResponse(FrozenContract):
    schema_version: Literal["creative-explanation-integrated-v2"]
    analysis: AnalysisResult
    explanation: ExplanationNotice | CatalogueExplanation
    evidence_packet: EvidencePacket | None
    orchestration: OrchestrationStatus


class GraphError(FrozenContract):
    orchestration_error: Literal["local_graph_failed", "supervisor_failed"]


@dataclass(frozen=True)
class GraphSettings:
    graph_python: Path
    worker_python: Path
    uploads_root: Path
    registry_file: Path
    scratch_root: Path
    m1: M1Settings | None = None
    evidence_root: Path | None = None
    minimum_similarity: float | None = None
    synthetic_baseline: bool = False
    observed_baseline_dir: Path | None = None
    timeout_seconds: float = 480
    # Trusted local operator only; never a field of the analysis request.
    worker_module: str = "scripts.explanation_worker_v2"
    worker_arguments_extra: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.synthetic_baseline) is not bool or not 0 < self.timeout_seconds <= 480:
            raise ValueError("invalid_graph_settings")
        if (
            sum(
                (
                    self.m1 is not None,
                    self.synthetic_baseline,
                    self.observed_baseline_dir is not None,
                )
            )
            > 1
        ):
            raise ValueError("Choose a single model or baseline source")
        if (self.evidence_root is None) != (self.minimum_similarity is None):
            raise ValueError("index_requires_explicit_threshold")
        if self.minimum_similarity is not None and not 0 <= self.minimum_similarity <= 1:
            raise ValueError("invalid_comparable_threshold")
        for python in (self.graph_python, self.worker_python):
            if not Path(python).is_absolute():
                raise ValueError("absolute_python_required")

    def arguments(self, scratch):
        result = [
            "--uploads-root",
            str(self.uploads_root),
            "--registry",
            str(self.registry_file),
            "--scratch-root",
            str(scratch),
        ]
        if self.m1 is not None:
            result += [
                "--m1-model-dir",
                str(self.m1.model_dir),
                "--m1-cohort-dir",
                str(self.m1.cohort_dir),
            ]
        elif self.synthetic_baseline:
            result += ["--synthetic-baseline"]
        elif self.observed_baseline_dir is not None:
            result += ["--observed-baseline-dir", str(self.observed_baseline_dir)]
        if self.evidence_root is not None:
            result += [
                "--evidence-root",
                str(self.evidence_root),
                "--minimum-similarity",
                str(self.minimum_similarity),
            ]
        return [*result, *self.worker_arguments_extra]


async def analyze_via_graph(payload, settings: GraphSettings):
    """One supervisor/request. It outlives and collects the killable graph group."""
    try:
        payload = AnalysisRequest.model_validate(payload).model_dump(mode="json")
    except ValidationError:
        # Canonical invalid input reaches the unchanged root validation without
        # serializing arbitrary Python objects or private invalid values.
        payload = {}
    settings.scratch_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    run_dir = Path(tempfile.mkdtemp(prefix="integrated-v2-", dir=settings.scratch_root))
    job = {
        "payload": payload,
        "graph_python": str(settings.graph_python),
        "worker_python": str(settings.worker_python),
        "arguments": settings.arguments(run_dir),
        "worker_module": settings.worker_module,
        "timeout": settings.timeout_seconds,
        "scratch": str(run_dir),
    }
    raw = json.dumps(job, allow_nan=False).encode()
    if len(raw) > MAX_LINE:
        shutil.rmtree(run_dir)
        return {"orchestration_error": "local_graph_failed"}
    environment = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"}
    process = None
    cleanup_confirmed = False
    try:
        spawning = asyncio.create_task(
            asyncio.create_subprocess_exec(
                str(settings.worker_python),
                "-B",
                "-m",
                "scripts.explanation_supervisor_v2",
                cwd=ROOT,
                env=environment,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                limit=MAX_LINE + 1024,
                start_new_session=True,
            )
        )
        try:
            process = await asyncio.shield(spawning)
        except asyncio.CancelledError:
            # No job bytes have been released. Retain the spawn handle even if
            # cancellation arrives between OS process creation and assignment.
            with anyio.CancelScope(shield=True):
                try:
                    process = await asyncio.shield(spawning)
                    if process.returncode is None:
                        process.kill()
                    await process.wait()
                    cleanup_confirmed = True
                except Exception:  # noqa: BLE001 - spawn failure has no launched graph job
                    cleanup_confirmed = False
            raise
        communication = asyncio.create_task(process.communicate(raw))
        try:
            async with asyncio.timeout(settings.timeout_seconds + 15):
                stdout, _ = await asyncio.shield(communication)
        except (asyncio.CancelledError, TimeoutError):
            if process.returncode is None:
                process.terminate()  # request cleanup; never kill graph's external supervisor first
            with anyio.CancelScope(shield=True):
                try:
                    stdout, _ = await asyncio.wait_for(asyncio.shield(communication), 12)
                    cleanup_confirmed = json.loads(stdout)["cleanup_confirmed"] is True
                except Exception:  # noqa: BLE001 - preserve scratch for explicit recovery
                    if process.returncode is None:
                        process.kill()
                        await process.wait()
            raise
        if len(stdout) > MAX_LINE + 512:
            raise ValueError("supervisor_output_limit")
        envelope = json.loads(stdout)
        cleanup_confirmed = envelope["cleanup_confirmed"] is True
        if not cleanup_confirmed:
            raise ValueError("cleanup_not_confirmed")
        result = envelope["result"]
        model = GraphError if "orchestration_error" in result else IntegratedResponse
        return model.model_validate_json(json.dumps(result, allow_nan=False)).model_dump(
            mode="json"
        )
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 - paths, payloads and raw exception objects are private
        return {"orchestration_error": "local_graph_failed"}
    finally:
        if (process is None or cleanup_confirmed) and run_dir.exists():
            shutil.rmtree(run_dir)
        # A killed/crashed supervisor leaves its exclusive directory for recovery;
        # absence of a cleanup acknowledgement must never masquerade as cleanup.
