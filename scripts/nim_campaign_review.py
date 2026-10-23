"""Opt-in dynamic NVIDIA selection of bound evidence, followed by local review.

No extraction or prediction lives here. Authorization, origin and R$0 are operator
declarations, not authentication of input or measurement of provider billing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.channel_partitions import digest
from scripts.explanation_evidence import (
    GROUP_NAMES,
    ExplanationContext,
    build_explanation_context,
    validate_selection,
)
from scripts.explanation_review_v1 import DRIVER, NUMBER, bound_source, review_recorded

MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
TIMEOUT_SECONDS = 45
MAX_RESPONSE_BYTES = 16384
MAX_PROJECTION_BYTES = 65536
MAX_PAYLOAD_BYTES = 65536
KEY_ENV = "NVIDIA_API_KEY"
CONFIGURATION = {
    "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    "model": MODEL,
    "max_tokens": 2048,
    "chat_template_kwargs": {"enable_thinking": False},
    "reasoning_mode": "instruct",
    "temperature": 0,
    "stream": False,
    "timeout_seconds": TIMEOUT_SECONDS,
    "max_response_bytes": MAX_RESPONSE_BYTES,
    "max_http_payload_bytes": MAX_PAYLOAD_BYTES,
    "selection_policy": "largest_available_positive_and_negative_plus_reference_or_reason",
}
REFERENCE = re.compile(
    r"Referência descritiva ([1-3]) do treino, mesmo setor e formato técnico "
    r"vertical até 60 s: cosseno MiniLM da fala "
    + NUMBER
    + r", limiar "
    + NUMBER
    + re.escape(
        ". Sem uso de views/curtidas na seleção; não demonstra causalidade ou alcance futuro."
    )
)
ABSENCE_REASONS = {
    "speech_embedding_unavailable",
    "zero_query_embedding",
    "semantic_format_not_available",
    "no_matching_training_reference",
}

# Isolated stdlib-only child. No urllib proxy discovery, redirects, retry, shell,
# third-party HTTP, or exception text. Only this child receives the API key.
_HTTP_CHILD = r"""
import hashlib, http.client, json, os, re, ssl, sys
class CompleteResponse(http.client.HTTPResponse):
    # Python 3.11's chunk parser tolerates missing CRLF/trailer EOF. Keep its
    # bounded reads, but require the actual chunk delimiters and final blank line.
    def _get_chunk_left(self):
        left = self.chunk_left
        if left is not None and left != 0:
            return left
        if left == 0 and self._safe_read(2) != b"\r\n":
            raise http.client.IncompleteRead(b"")
        line = self.fp.readline(65537)
        if len(line) > 65536 or not line.endswith(b"\r\n"):
            raise http.client.IncompleteRead(b"")
        token = line[:-2].split(b";", 1)[0]
        if not re.fullmatch(b"[0-9a-fA-F]+", token):
            raise http.client.IncompleteRead(b"")
        left = int(token, 16)
        if left == 0:
            for _ in range(101):
                trailer = self.fp.readline(65537)
                if len(trailer) > 65536 or not trailer.endswith(b"\r\n"):
                    raise http.client.IncompleteRead(b"")
                if trailer == b"\r\n":
                    break
            else:
                raise http.client.IncompleteRead(b"")
            self._close_conn()
            left = None
        self.chunk_left = left
        return left
metadata = {"http_status": None, "response_bytes": None,
    "response_sha256": None, "body_within_limit": None,
    "framing_complete": False, "response_complete": False}
raw = None
failed = True
try:
    body = sys.stdin.buffer.read(65537)
    if len(body) > 65536:
        raise ValueError()
    key = os.environ.pop("NVIDIA_API_KEY")
    connection = http.client.HTTPSConnection(
        "integrate.api.nvidia.com", timeout=45, context=ssl.create_default_context())
    connection.response_class = CompleteResponse
    try:
        connection.request("POST", "/v1/chat/completions", body=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        response = connection.getresponse()
        metadata["http_status"] = response.status
        if response.status != 200:
            raise ValueError()
        length = response.length
        lengths = [v for k, v in response.getheaders() if k.lower() == "content-length"]
        transfer = response.getheader("Transfer-Encoding")
        if len(lengths) > 1 or (lengths and (response.chunked or length is None)):
            raise ValueError()
        if transfer is not None and not response.chunked:
            raise ValueError()
        try:
            raw = response.read(16385)
        except http.client.IncompleteRead as failure:
            raw = failure.partial
            metadata.update(response_bytes=len(raw),
                response_sha256=hashlib.sha256(raw).hexdigest(),
                body_within_limit=len(raw) <= 16384)
            raise
        if response.chunked:
            complete = response.chunk_left is None
        elif length is not None:
            # read(amt) can silently return a truncated Content-Length body.
            complete = response.length == 0
        elif len(raw) <= 16384:
            # For close-delimited bodies, explicitly observe EOF within the cap.
            extra = response.read(1)
            raw += extra
            complete = not extra
        else:
            complete = False
        metadata.update(response_bytes=len(raw),
            response_sha256=hashlib.sha256(raw).hexdigest(),
            body_within_limit=len(raw) <= 16384,
            framing_complete=complete, response_complete=complete)
        if len(raw) > 16384 or not complete:
            raise ValueError()
    finally:
        connection.close()
    failed = False
except BaseException:
    pass
sys.stdout.buffer.write(json.dumps(metadata, separators=(",", ":")).encode("ascii") + b"\n")
if not failed:
    sys.stdout.buffer.write(raw)
sys.exit(10 if failed else 0)
"""


@dataclass(frozen=True)
class NimConfig:
    """One invocation/reservation directory, supplied locally by the operator."""

    reservation_dir: Path
    operator_declares_zero_brl: bool

    def __post_init__(self):
        if (
            not isinstance(self.reservation_dir, Path)
            or self.operator_declares_zero_brl is not True
        ):
            raise ValueError("invalid_nim_operator_configuration")


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_nim_json")
        result[key] = value
    return result


def _json(raw):
    return json.loads(
        raw,
        object_pairs_hook=_unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid_nim_json")),
    )


def project_source(source):
    """Recognize every local fact before projecting only closed numeric metadata.

    The complete source is never the provider message. Historical statement
    templates are verified locally, including facts absent from the selection.
    """
    try:
        source, analysis, packet, _ = bound_source(source)
        baseline = build_explanation_context(source["analysis"])
        canonical = {f.evidence_id: f for f in baseline.packet.evidence}
        mandatory = baseline.mandatory_evidence_ids
        context = ExplanationContext(packet, _canonical(source["analysis"]), mandatory)
        rows, available = [], {f.evidence_id for f in packet.evidence}
        if not set(canonical) <= available:
            raise ValueError()
        for fact in packet.evidence:
            key = fact.evidence_id
            row = {"evidence_id": key}
            if key in canonical:
                if fact != canonical[key]:
                    raise ValueError()
                if key.startswith("limit_"):
                    row["type"] = key
                else:
                    ordinal, kind = key.split("_", 1)
                    candidate = analysis.candidates[int(ordinal[1:]) - 1]
                    row.update(candidate=ordinal, type=kind)
                    if kind == "prediction":
                        if candidate.prediction.status == "estimated":
                            row["value"] = candidate.prediction.value
                        else:
                            row["reason"] = candidate.prediction.reason_code
                    else:
                        row.update(
                            lower_views=candidate.interval.lower_views,
                            upper_views=candidate.interval.upper_views,
                        )
            else:
                match = re.fullmatch(
                    r"(c[1-5])_(shap_(\w+)|reference_([1-3])|references_missing)", key
                )
                if not match or int(match[1][1:]) > len(analysis.candidates):
                    raise ValueError()
                row["candidate"] = match[1]
                if match[3]:
                    driver = DRIVER.fullmatch(fact.statement_pt)
                    if (
                        not driver
                        or match[3] not in GROUP_NAMES
                        or driver[1] != GROUP_NAMES[match[3]]
                    ):
                        raise ValueError()
                    row.update(
                        type="shap",
                        group=match[3],
                        contribution_log=float(driver[2]),
                        base_log=float(driver[3]),
                    )
                elif match[4]:
                    reference = REFERENCE.fullmatch(fact.statement_pt)
                    if not reference or reference[1] != match[4]:
                        raise ValueError()
                    similarity, minimum = float(reference[2]), float(reference[3])
                    if not 0 <= minimum <= similarity <= 1:
                        raise ValueError()
                    row.update(
                        type="reference",
                        ordinal=int(match[4]),
                        similarity=similarity,
                        minimum_similarity=minimum,
                    )
                else:
                    reason = fact.statement_pt.removeprefix("Sem comparáveis: ").removesuffix(".")
                    if (
                        reason not in ABSENCE_REASONS
                        or fact.statement_pt != f"Sem comparáveis: {reason}."
                    ):
                        raise ValueError()
                    row.update(type="references_missing", reason=reason)
            if any(type(v) is float and not math.isfinite(v) for v in row.values()):
                raise ValueError()
            rows.append(row)
        for i in range(1, len(analysis.candidates) + 1):
            refs = [r for r in rows if r.get("candidate") == f"c{i}" and r["type"] == "reference"]
            missing = f"c{i}_references_missing" in available
            if refs and (missing or [r["ordinal"] for r in refs] != list(range(1, len(refs) + 1))):
                raise ValueError()
            if refs and (
                len({r["minimum_similarity"] for r in refs}) != 1
                or [r["similarity"] for r in refs]
                != sorted([r["similarity"] for r in refs], reverse=True)
            ):
                raise ValueError()
        # Existing rubric validates finite drivers, their complete groups and
        # signed reconstruction. It does not turn a missing group into evidence.
        from scripts.explanation_review_v1 import review_sufficiency

        review_sufficiency(source)
        projection = {"packet_sha256": context.packet_sha256, "evidence": rows}
        if len(_canonical(projection).encode("ascii")) > MAX_PROJECTION_BYTES:
            raise ValueError()
        return context, projection
    except Exception:  # noqa: BLE001 - never echo input, private statements or schema errors
        raise ValueError("invalid_nim_source_projection") from None


def provider_payload(projection):
    instruction = (
        "Select evidence IDs only; emit exactly one JSON object with packet_sha256 and "
        "evidence_ids (1 to 12 unique catalogue IDs total, no prose or other keys). "
        "For every candidate select the largest magnitude available positive and negative "
        "SHAP group (one tied maximum per sign suffices), and one training reference or "
        "its absence reason. If all groups are zero select one zero group. Never invent "
        "semantics for embeddings, evidence, numbers or missing groups. Mandatory limits "
        "and predictions are added locally; prioritize signed drivers and references. "
        "If 12 IDs cannot cover all candidates, return at most 12; local review will "
        "expose insufficiency without repair. Catalogue: "
    )
    return {
        "model": MODEL,
        "max_tokens": 2048,
        "temperature": 0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "user", "content": instruction + _canonical(projection)}],
    }


def _payload_bytes(payload):
    raw = _canonical(payload).encode("ascii")
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("nim_payload_size_limit")
    return raw


def _transport_receipt():
    return {
        "http_status": None,
        "returned_model": None,
        "model_matched": False,
        "finish_reason": None,
        "response_bytes": None,
        "response_sha256": None,
        "body_within_limit": None,
        "framing_complete": False,
        "response_complete": False,
        "usage": None,
        "child_reaped": None,
        "timed_out": False,
    }


def _response_metadata(raw, receipt):
    """Record only validated scalar metadata, never message/reasoning/error text."""
    receipt.update(
        response_bytes=len(raw),
        response_sha256=hashlib.sha256(raw).hexdigest(),
        body_within_limit=len(raw) <= MAX_RESPONSE_BYTES,
    )
    try:
        value = _json(raw)
        if type(value) is not dict:
            return
        receipt["model_matched"] = value.get("model") == MODEL
        receipt["returned_model"] = MODEL if receipt["model_matched"] else None
        choices = value.get("choices")
        if type(choices) is list and len(choices) == 1 and type(choices[0]) is dict:
            finish = choices[0].get("finish_reason")
            if type(finish) is str and finish in {
                "stop",
                "length",
                "tool_calls",
                "function_call",
                "content_filter",
            }:
                receipt["finish_reason"] = finish
        usage = value.get("usage")
        if type(usage) is dict:
            integers = {
                k: usage[k]
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                if type(usage.get(k)) is int and usage[k] >= 0
            }
            receipt["usage"] = integers or None
    except Exception:  # noqa: BLE001 - invalid metadata is absent, never echoed
        return


def _private_write(directory, name, value):
    try:
        fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(_canonical(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:  # noqa: BLE001 - never expose private receipt destinations
        raise ValueError("nim_receipt_unavailable") from None


def _reserve(config, projection, provenance):
    directory = config.reservation_dir
    parent = directory.parent
    try:
        metadata = parent.stat()
        if (
            parent.is_symlink()
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_mode & 0o077
            or metadata.st_uid != os.geteuid()
        ):
            raise ValueError()
        directory.mkdir(mode=0o700, exist_ok=False)
        _private_write(
            directory,
            "reservation.json",
            provenance
            | {
                "status": "consumed_before_spawn",
                "operator_declared_budget_brl": 0,
                "billing_measured": False,
                "packet_sha256": projection["packet_sha256"],
            },
        )
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:  # noqa: BLE001 - do not expose destination or permit reuse
        raise ValueError("nim_reservation_unavailable") from None


async def _invoke_provider(payload, key, *, transport_receipt=None):
    body = _payload_bytes(payload)
    receipt = transport_receipt if transport_receipt is not None else _transport_receipt()
    child = None
    # Shield spawn so cancellation during creation cannot orphan a process.
    spawn = asyncio.create_task(
        asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-B",
            "-c",
            _HTTP_CHILD,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={KEY_ENV: key},
        )
    )
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            child = await asyncio.shield(spawn)
            output, _ = await child.communicate(body)
            line, separator, raw = output.partition(b"\n")
            metadata = _json(line) if separator and len(line) <= 1024 else None
            if type(metadata) is not dict or set(metadata) != {
                "http_status",
                "response_bytes",
                "response_sha256",
                "body_within_limit",
                "framing_complete",
                "response_complete",
            }:
                raise ValueError("nim_provider_failed")
            status, count, checksum, within_limit, framed, complete = (
                metadata[k]
                for k in (
                    "http_status",
                    "response_bytes",
                    "response_sha256",
                    "body_within_limit",
                    "framing_complete",
                    "response_complete",
                )
            )
            if status is not None and (type(status) is not int or not 100 <= status <= 599):
                raise ValueError("nim_provider_failed")
            if count is not None and (
                type(count) is not int or not 0 <= count <= MAX_RESPONSE_BYTES + 1
            ):
                raise ValueError("nim_provider_failed")
            if checksum is not None and (
                type(checksum) is not str or not re.fullmatch(r"[0-9a-f]{64}", checksum)
            ):
                raise ValueError("nim_provider_failed")
            if within_limit is not None and type(within_limit) is not bool:
                raise ValueError("nim_provider_failed")
            if type(framed) is not bool or type(complete) is not bool or complete != framed:
                raise ValueError("nim_provider_failed")
            receipt.update(metadata)
            if (
                child.returncode != 0
                or status != 200
                or within_limit is not True
                or not framed
                or len(raw) > MAX_RESPONSE_BYTES
                or count != len(raw)
                or checksum != hashlib.sha256(raw).hexdigest()
            ):
                raise ValueError("nim_provider_failed")
            _response_metadata(raw, receipt)
            return raw
    except TimeoutError:
        receipt["timed_out"] = True
        raise
    finally:
        # Cancellation of shielded spawn still requires retrieving and reaping
        # the owned child, even if cancellation is repeated during cleanup.
        async def reap():
            owned = child if child is not None else await spawn
            if owned.returncode is None:
                try:
                    owned.kill()
                except ProcessLookupError:
                    pass  # child exited between returncode inspection and kill
            await owned.wait()
            receipt["child_reaped"] = owned.returncode is not None

        cleanup = asyncio.create_task(reap())
        cancelled_during_cleanup = False
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                cancelled_during_cleanup = True
        cleanup.result()
        if cancelled_during_cleanup:
            raise asyncio.CancelledError


def _selection_response(raw):
    try:
        if type(raw) is not bytes or len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError()
        value = _json(raw)
        if (
            type(value) is not dict
            or not set(value)
            <= {
                "id",
                "object",
                "created",
                "model",
                "choices",
                "usage",
                "system_fingerprint",
                "service_tier",
                "nvext",
            }
            or value["model"] != MODEL
            # Optional provider metadata is never evidence or returned content.
            or (value.get("service_tier") is not None and type(value["service_tier"]) is not str)
            or (value.get("nvext") is not None and type(value["nvext"]) is not dict)
        ):
            raise ValueError()
        choices = value["choices"]
        if type(choices) is not list or len(choices) != 1:
            raise ValueError()
        choice = choices[0]
        if (
            not set(choice) <= {"index", "message", "finish_reason", "logprobs"}
            or choice["finish_reason"] != "stop"
            or type(choice["index"]) is not int
            or choice["index"] != 0
        ):
            raise ValueError()
        message = choice["message"]
        if (
            not set(message) <= {"role", "content", "reasoning_content", "reasoning", "refusal"}
            or message["role"] != "assistant"
            or message.get("refusal") is not None
            or type(message["content"]) is not str
        ):
            raise ValueError()
        return message["content"]
    except Exception:  # noqa: BLE001 - HTTP/JSON output is untrusted and never echoed
        raise ValueError("invalid_nim_response") from None


async def select_and_review(
    source,
    request,
    config: NimConfig,
    *,
    case=None,
    media_bindings=None,
    input_origin="unverified",
    _test_transport=None,
):
    """Select once, preserve source, and review the actual selection separately.

    _test_transport is restricted to explicitly invented tests and is never a
    provider/native proof. Production callers configure no callable transport.
    """
    try:
        context, projection = project_source(source)
        source = bound_source(source)[0]
        review_recorded(
            source, request, case=case, media_bindings=media_bindings, input_origin=input_origin
        )
        if not isinstance(config, NimConfig) or (
            _test_transport is not None and input_origin != "invented"
        ):
            raise ValueError()
        payload = provider_payload(projection)
        _payload_bytes(payload)  # complete HTTP body, before consuming the reservation
        key = "invented_test_key" if _test_transport else os.environ.get(KEY_ENV)
        if not key or not key.isascii() or "\n" in key or "\r" in key:
            raise ValueError()
    except Exception:  # noqa: BLE001 - no invalid input can launch the provider
        raise ValueError("invalid_nim_review_input_or_configuration") from None
    provenance = {
        "stage": "new_nim_selection",
        "input_origin_declared_by_operator": input_origin,
        "transport": "invented_test_callback_not_native"
        if _test_transport
        else "owned_https_subprocess",
        "new_extractions": 0,
        "new_predictions": 0,
        "model": MODEL,
        "new_external_calls": 0 if _test_transport else 1,
        "external_call_count_basis": "reserved_single_attempt_not_provider_confirmation",
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "configuration_sha256": digest(CONFIGURATION),
        "projection_sha256": digest(projection),
        "operator_declared_budget_brl": 0,
        "billing_measured": False,
        "final_configuration_validated": False,
    }
    result = {
        "status": "unavailable",
        "reason_code": "nim_selection_unavailable",
        "failure_stage_code": None,
        "source_result": source,
        "source_sha256": digest(source),
        "selected_report": None,
        "review": None,
        "nim_provenance": provenance,
        "remote_evidence_ids": [],
        "locally_added_mandatory_ids": [],
        "transport_receipt": _transport_receipt(),
        "limitations": [
            "operator_origin_not_authenticated",
            "selection_is_not_factual_or_predictive_validation",
            "global_12_id_limit_may_leave_candidates_insufficient",
            "no_embedding_semantics",
            "final_configuration_not_validated",
        ],
    }
    _reserve(config, projection, provenance)
    stage = "transport"
    try:
        raw = await (
            _test_transport(payload)
            if _test_transport
            else _invoke_provider(payload, key, transport_receipt=result["transport_receipt"])
        )
        if type(raw) is bytes:
            _response_metadata(raw, result["transport_receipt"])
        stage = "response_envelope"
        selection = _selection_response(raw)
        stage = "selection_schema_or_binding"
        selected = validate_selection(context, selection)
        remote_ids = _json(selection)["evidence_ids"]
        selected["evidence_packet"] = context.packet.model_dump(mode="json")
        stage = "local_review"
        review = review_recorded(
            selected, request, case=case, media_bindings=media_bindings, input_origin=input_origin
        )
        result.update(
            status="reviewed",
            reason_code="nim_selection_reviewed",
            selected_report=selected,
            review=review,
            remote_evidence_ids=remote_ids,
            locally_added_mandatory_ids=[
                k for k in context.mandatory_evidence_ids if k not in remote_ids
            ],
        )
    except asyncio.CancelledError:
        _private_write(
            config.reservation_dir,
            "outcome.json",
            {
                "status": "cancelled",
                "failure_stage_code": stage,
                "projection_sha256": provenance["projection_sha256"],
                "transport_receipt": result["transport_receipt"],
            },
        )
        raise
    except Exception:  # noqa: BLE001 - preserve original numbers without provider text
        result["reason_code"] = "nim_selection_unavailable"
        result["failure_stage_code"] = stage
    _private_write(
        config.reservation_dir,
        "outcome.json",
        {
            "status": result["status"],
            "failure_stage_code": result["failure_stage_code"],
            "projection_sha256": provenance["projection_sha256"],
            "remote_evidence_count": len(result["remote_evidence_ids"]),
            "transport_receipt": result["transport_receipt"],
        },
    )
    return result


async def analyze_nim_reviewed(payload, settings, config):
    """Same callable for CLI/MCP: existing graph once, then opt-in selection."""
    from scripts.campaign_evidence_v1 import brief_digest
    from scripts.creative_contracts import AnalysisRequest
    from scripts.explanation_review_service_v1 import analyze_reviewed, registry_bindings

    case = bindings = None
    try:
        request = AnalysisRequest.model_validate(payload)
        case = next(
            (
                c
                for c in settings.cases
                if c.campaign_id == request.campaign_id
                and c.brief_sha256 == brief_digest(request.brief)
            ),
            None,
        )
        if case:
            bindings = registry_bindings(settings.graph, request)
    except Exception:  # noqa: BLE001 - shared analysis owns invalid-input responses
        return {
            "status": "unavailable",
            "reason_code": "invalid_nim_input_or_binding",
            "source_result": None,
            "selected_report": None,
            "review": None,
        }
    prior = await analyze_reviewed(payload, settings)
    if prior["review_status"] != "reviewed":
        return {
            "status": "unavailable",
            "reason_code": "source_review_unavailable",
            "source_result": prior["source_result"],
            "selected_report": None,
            "review": None,
            "prior_review": prior,
        }
    try:
        if case and bindings != registry_bindings(settings.graph, request):
            raise ValueError()
        result = await select_and_review(
            prior["source_result"],
            payload,
            config,
            case=case,
            media_bindings=bindings,
            input_origin=settings.data_origin,
        )
    except Exception:  # noqa: BLE001 - preserve checkpoint, never expose registry/key errors
        return {
            "status": "unavailable",
            "reason_code": "nim_input_configuration_or_reservation_unavailable",
            "source_result": prior["source_result"],
            "selected_report": None,
            "review": None,
            "prior_review": prior,
        }
    result["prior_review"] = prior
    return result
