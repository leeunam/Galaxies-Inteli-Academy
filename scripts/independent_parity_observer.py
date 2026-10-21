"""Private, opt-in return observer loaded through a read-only namespace overlay.

The operator executes this file with PARITY_DIRECTORY/PARITY_LABEL globals.
It never wraps/replaces application functions, changes RNG state, or predicts.
Trace data is private; none of its content digests is a public evidence file.
"""

import atexit
import hashlib
import json
import os
import sys
import time

ALLOW_ENV = (
    "PATH",
    "LANG",
    "LC_ALL",
    "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE",
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "TOKENIZERS_PARALLELISM",
    "CUDA_VISIBLE_DEVICES",
    "HF_HUB_OFFLINE",
    "TRANSFORMERS_OFFLINE",
    "HF_HUB_DISABLE_TELEMETRY",
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING_V2",
    "GALAXIES_SUPERVISED",
    "GALAXIES_SUPERVISED_GROUP",
    "TMPDIR",
)
MODULES = (
    "numpy",
    "numpy.random",
    "torch",
    "catboost",
    "ctranslate2",
    "faster_whisper",
    "sentence_transformers",
    "transformers",
    "onnxruntime",
    "langgraph.graph",
    "scripts.candidate_features",
    "scripts.pilot_licensed_media",
    "scripts.m1_service",
    "scripts.explanation_worker_v2",
    "scripts.explanation_graph_service_v2",
    "scripts.explanation_graph_mcp_v2",
    "sentence_transformers.SentenceTransformer",
    "sentence_transformers.models.Transformer",
    "transformers.models.clip.modeling_clip",
    "faster_whisper.transcribe",
    "ctranslate2._ext",
    "catboost._catboost",
    "torch._C",
)
TARGETS = {
    "audio_features.py": {"extract_audio"},
    "pilot_licensed_media.py": {"extract_features", "cached_model"},
    "candidate_features.py": {"_extract_one", "extract_candidates"},
    "experiment_a_artifact.py": {"predict_views", "predict_logs"},
    "experiment_a_data.py": {"feature_matrix"},
    "m1_service.py": {"load_model_context", "serve_m1"},
    "m1_evidence.py": {"explain_m1"},
    "training_comparables.py": {"search", "load_training_index"},
    "explanation_evidence.py": {"build_explanation_context"},
    "explanation_session_v2.py": {"handle"},
}
FILE_HASHES = {}


def plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def semantic(value):
    return hashlib.sha256(
        json.dumps(plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def state_snapshot():
    """Read only already imported generators; never import an ML/RNG library."""
    result = {"cpu_mask": sorted(os.sched_getaffinity(0)), "rng": {}, "modules": {}}
    for name in MODULES:
        module = sys.modules.get(name)
        path = getattr(module, "__file__", None)
        if path and path not in FILE_HASHES:
            with open(path, "rb") as source:
                FILE_HASHES[path] = hashlib.file_digest(source, "sha256").hexdigest()
        result["modules"][name] = {
            "file": path,
            "file_sha256": FILE_HASHES.get(path),
            "version": getattr(module, "__version__", None),
        }
    random = sys.modules.get("random")
    if random is not None:
        result["rng"]["python"] = semantic(random.getstate())
    numpy_random = sys.modules.get("numpy.random")
    if numpy_random is not None and hasattr(numpy_random, "get_state"):
        result["rng"]["numpy_legacy"] = semantic(numpy_random.get_state())
    torch = sys.modules.get("torch")
    if torch is not None and hasattr(torch, "get_rng_state"):
        result["rng"]["torch_cpu"] = hashlib.sha256(
            torch.get_rng_state().numpy().tobytes()
        ).hexdigest()
        result["torch"] = {
            "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        }
    result["rng_unreadable"] = [
        "ctranslate2_internal",
        "onnxruntime_internal",
        "numpy_new_generators_not_exposed",
    ]
    threadpoolctl = sys.modules.get("threadpoolctl")
    if threadpoolctl is not None and hasattr(threadpoolctl, "threadpool_info"):
        result["thread_pools"] = threadpoolctl.threadpool_info()
    return result


def observe(frame, event, value):
    if event not in ("call", "return"):
        return
    filename, name = frame.f_code.co_filename, frame.f_code.co_name
    base = filename.rsplit("/", 1)[-1]
    selected = name in TARGETS.get(base, ()) and "/scripts/" in filename
    spawn = (
        base == "subprocess.py" and frame.f_code.co_qualname == "Popen.__init__" and event == "call"
    )
    if not (selected or spawn):
        return
    try:
        row = {"kind": "phase", "event": event, "source": filename, "function": name}
        local = frame.f_locals
        if spawn:
            row.update(
                command=plain(local["args"]),
                cwd=str(local.get("cwd")),
                environment={k: local.get("env", {}).get(k) for k in ALLOW_ENV}
                if local.get("env") is not None
                else None,
                start_new_session=local.get("start_new_session"),
            )
        elif event == "call":
            row["state"] = state_snapshot()
            if name == "cached_model":
                row["cache_key"] = plain(local.get("key"))
            if name in ("predict_views", "predict_logs", "feature_matrix"):
                row["inputs_sha256"] = semantic(local["inputs"])
                row["input_items_sha256"] = (
                    [semantic(item) for item in local["inputs"]]
                    if isinstance(local["inputs"], (list, tuple))
                    else None
                )
                row["repaired"] = local.get("repaired")
            if name == "search":
                row["query_sha256"] = semantic(local["query"])
            if name == "_extract_one":
                row["position"] = int(local["work"].parent.name)
            if name == "handle":
                row["operation"] = local["message"]["op"]
        elif value is None:
            row["return_absent_or_exception"] = True
        elif name == "extract_audio":
            row["digests"] = {
                "audio": value["decoded_audio_float32_16khz_sha256"],
                "audio_properties": semantic(
                    {k: value[k] for k in ("audio_status", "audio_rms", "audio_duration_seconds")}
                ),
                "transcript": semantic(value["transcript"]),
                "segments": semantic(value["speech_segments"]),
                "segment_content": semantic(
                    [{k: s[k] for k in ("start", "end", "text")} for s in value["speech_segments"]]
                ),
                "language": semantic(value["asr_language"]),
                "language_probability": semantic(value["asr_language_probability"]),
                "asr_confidence": semantic(
                    [
                        {k: s[k] for k in ("avg_logprob", "no_speech_prob")}
                        for s in value["speech_segments"]
                    ]
                ),
            }
        elif name == "extract_features":
            row["digests"] = {
                "embedding": semantic(value["text_embedding"]),
                "properties": semantic(
                    {k: value["properties"][k] for k in ("duration_seconds", "width", "height")}
                ),
            }
        elif name == "_extract_one":
            row.update(
                position=int(local["work"].parent.name),
                feature_sha256=semantic(value),
                predictor_inputs_sha256=semantic(value.inputs),
                status=value.status,
                reason=value.reason_code,
            )
        elif name in (
            "extract_candidates",
            "predict_views",
            "predict_logs",
            "feature_matrix",
            "serve_m1",
            "explain_m1",
            "search",
        ):
            row["result_sha256"] = semantic(value)
            if name == "extract_candidates":
                row["feature_items_sha256"] = [semantic(item) for item in value]
                row["predictor_items_sha256"] = [semantic(item.inputs) for item in value]
            if name in ("predict_views", "predict_logs"):
                row["result"] = plain(value)
        elif name == "build_explanation_context":
            row.update(
                packet_sha256=value.packet_sha256, packet_value_sha256=semantic(value.packet)
            )
        elif name == "handle":
            session = local["self"]
            row.update(
                operation=local["op"],
                result_sha256=semantic(value),
                shap_sha256=semantic(session.shap),
                comparables_sha256=semantic(session.comparables),
            )
        emit(row)
    except Exception:  # noqa: BLE001 - observation cannot replace an application return
        # Observation failures are diagnostics, never replacements for a return.
        emit({"kind": "observation_error", "function": name, "event": event})


def emit(value):
    global TRACE_BYTES, OBSERVATION_ERRORS
    if value.get("kind") == "observation_error":
        OBSERVATION_ERRORS += 1
    try:
        value = {**value, "observation_errors_so_far": OBSERVATION_ERRORS}
        raw = json.dumps(value, allow_nan=False).encode() + b"\n"
        if TRACE_BYTES + len(raw) > 512 * 1024:
            OBSERVATION_ERRORS += 1
            return
        written = os.write(TRACE_FD, raw)
        if written != len(raw):
            OBSERVATION_ERRORS += 1
        TRACE_BYTES += written
    except (OSError, TypeError, ValueError):
        OBSERVATION_ERRORS += 1


def finish():
    sys.setprofile(None)
    emit(
        {
            "kind": "exit",
            "observation_errors": OBSERVATION_ERRORS,
            "state": state_snapshot(),
            "elapsed_seconds": time.monotonic() - STARTED,
        }
    )
    os.close(TRACE_FD)


if "PARITY_DIRECTORY" in globals():
    STARTED = time.monotonic()
    TRACE_BYTES = OBSERVATION_ERRORS = 0
    TRACE_FD = os.open(
        os.path.join(
            globals()["PARITY_DIRECTORY"], f"{globals()['PARITY_LABEL']}-{os.getpid()}.jsonl"
        ),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    emit(
        {
            "kind": "startup",
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "argv": sys.argv,
            "orig_argv": sys.orig_argv,
            "executable": sys.executable,
            "prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "environment": {k: os.environ.get(k) for k in ALLOW_ENV},
            "state": state_snapshot(),
            "instrumentation": "readonly_pth_overlay_and_sys_setprofile; no application replacement",
        }
    )
    sys.setprofile(observe)
    atexit.register(finish)
