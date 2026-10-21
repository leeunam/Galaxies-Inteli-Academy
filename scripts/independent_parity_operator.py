"""Bounded offline operator; only a code-bound technical window enables real routes."""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from types import FunctionType

from scripts import demo_recovery
from scripts.demo_recovery_policy import digest, exclusive_json, read_json

ROOT = Path(__file__).resolve().parents[1]
PTH = (
    ".venv/lib/python3.11/site-packages/_virtualenv.pth",
    "orchestration/.venv/lib/python3.11/site-packages/_virtualenv.pth",
)


def overlay(run, label, enabled):
    result = []
    if enabled:
        for i, relative in enumerate(PTH):
            original = ROOT / relative
            namespace = {
                "__name__": "_independent_parity_observer",
                "__file__": str(ROOT / "scripts/independent_parity_observer.py"),
                "PARITY_DIRECTORY": str(run / "traces"),
                "PARITY_LABEL": label,
            }
            command = f"import sys; exec(compile(open({namespace['__file__']!r}).read(), {namespace['__file__']!r}, 'exec'), {namespace!r})\n"
            source = run / "receipts" / f"{label}-{i}.pth"
            with source.open("x") as output:
                os.chmod(source, 0o600)
                output.write(original.read_text().rstrip("\n") + "\n" + command)
            result += ["--ro-bind", str(source), str(original)]
    return result


def guarded(run, label, argv, budgets, timeout, hf_cache, *, enabled, registry_file=None):
    mounts = overlay(run, label, enabled)
    if registry_file is not None:
        registry_file = Path(registry_file)
        target = registry_file.with_suffix(".lock")
        assert registry_file.is_file() and target.is_file() and not target.is_symlink()
        source = run / "scratch" / (label + "-registry-control.lock")
        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        # Namespace-only operational lock. JSON, original lock inode, sources,
        # uploads and models stay RO; only this new scratch file is writable.
        mounts += ["--bind", str(source), str(target)]

    def sandbox(_base, environment, *, offline):
        assert offline
        command = [
            "/usr/bin/bwrap",
            "--ro-bind",
            "/",
            "/",
            "--bind",
            str(run),
            str(run),
            "--dev",
            "/dev",
            "--die-with-parent",
            "--unshare-net",
            "--clearenv",
            "--ro-bind",
            hf_cache,
            str(ROOT / "data/cache/huggingface"),
            *mounts,
        ]
        for key, value in environment.items():
            command += ["--setenv", key, value]
        return command + [
            "--chdir",
            str(ROOT),
            str(ROOT / ".venv/bin/python"),
            "-B",
            "-m",
            "scripts.demo_recovery_process",
        ]

    # Only the OUTER operator's sandbox construction is bound privately. The
    # entire application process tree, argv/env and functions remain original.
    namespace = demo_recovery.guarded_command.__globals__.copy()
    namespace["sandbox_command"] = sandbox
    bounded = FunctionType(demo_recovery.guarded_command.__code__, namespace)
    return bounded(run, label, argv, {"budgets": budgets}, {}, timeout, offline=True)


def new_run(path):
    path.mkdir(mode=0o700)
    for name in ("scratch", "receipts", "traces"):
        (path / name).mkdir(mode=0o700)


def validate_trace(file):
    terminal = read_json(Path(str(file) + ".terminal.json"))
    assert terminal["observation_errors"] == 0
    assert terminal["trace_bytes"] == file.stat().st_size <= 512 * 1024
    assert terminal["trace_sha256"] == digest(file)
    current = [json.loads(line) for line in file.read_text().splitlines()]
    assert current and current[0]["kind"] == "startup"
    first = current[0]
    assert all(terminal[k] == first[k] for k in ("pid", "start_ticks", "startup_generation"))
    assert not any(
        x["kind"] == "observation_error" or x.get("observation_errors_so_far", 0) for x in current
    )
    if terminal["status"] == "replaced_by_exec":
        assert len(current) == 1 and first["orig_argv"][2].endswith(
            "/scripts/demo_recovery_child.py"
        )
        successor = file.with_name(terminal["successor_trace"])
        assert successor.parent == file.parent and successor.name.startswith(
            file.name.rsplit("-", 1)[0] + "-"
        )
        assert read_json(Path(str(successor) + ".terminal.json"))["status"] == "completed"
        successor_rows = validate_trace(successor)
        next_start = successor_rows[0]
        assert (first["pid"], first["start_ticks"], first["startup_generation"] + 1) == (
            next_start["pid"],
            next_start["start_ticks"],
            next_start["startup_generation"],
        )
        assert first["orig_argv"][4:] == next_start["orig_argv"]
    else:
        assert terminal["status"] == "completed"
        last, reason = current[-1], terminal["completion_reason"]
        assert (
            (reason == "normal_exit" and last["kind"] == "exit")
            or (
                reason == "native_render_return"
                and last.get("function") == "handle"
                and last.get("event") == "return"
                and last.get("operation") == "render"
            )
            or (
                reason == "graph_result_emit"
                and last.get("function") == "_emit"
                and last.get("event") == "call"
            )
            or (
                reason == "graph_service_result_return"
                and last.get("function") == "analyze_via_graph"
                and last.get("event") == "return"
            )
        )
    return current


def traces(run, prefix):
    rows = []
    for file in sorted((run / "traces").glob(prefix + "-*.jsonl")):
        current = validate_trace(file)
        assert file.stat().st_mode & 0o777 == 0o600 and file.stat().st_size <= 512 * 1024
        rows.extend(current)
    return rows


def verify_input_bindings(rows):
    features = sorted(
        [x for x in rows if x.get("function") == "_extract_one" and x.get("event") == "return"],
        key=lambda x: x["position"],
    )
    assert [x["position"] for x in features] == [0, 1, 2]
    extracted = [
        x for x in rows if x.get("function") == "extract_candidates" and x.get("event") == "return"
    ]
    predicted = [
        x for x in rows if x.get("function") == "predict_views" and x.get("event") == "call"
    ]
    assert len(extracted) == 1 and len(predicted) == 3
    assert extracted[0]["feature_items_sha256"] == [x["feature_sha256"] for x in features]
    expected = [x["predictor_inputs_sha256"] for x in features]
    assert extracted[0]["predictor_items_sha256"] == expected
    assert [x["input_items_sha256"] for x in predicted] == [[x] for x in expected]


def preflight(plan):
    run = Path(plan["preflight_run"])
    new_run(run)
    budgets = {**plan["budgets"], "rss_bytes": 1536 * 1024**2}
    try:
        for label, enabled in (("off", False), ("on", True)):
            folder = run / label
            folder.mkdir(mode=0o700)
            guarded(
                run,
                label + "-job",
                [
                    str(ROOT / ".venv/bin/python"),
                    "-B",
                    "-m",
                    "tests.independent_parity_fixture",
                    str(folder),
                    *(["--observer-required"] if enabled else []),
                ],
                budgets,
                60,
                plan["hf_cache"],
                enabled=enabled,
                registry_file=Path(plan["registry_lock_overlay"]["registry_file"]),
            )
        assert read_json(run / "off/response.json") == read_json(run / "on/response.json")
        rows = traces(run, "on-job")
        assert any(
            x["kind"] == "startup"
            and x["orig_argv"][1:4] == ["-B", "-m", "tests.independent_parity_fixture"]
            for x in rows
        )
        target = next(
            x
            for x in rows
            if x["kind"] == "startup"
            and x["orig_argv"][1:4] == ["-B", "-m", "tests.independent_parity_fixture"]
        )
        same_pid = [x for x in rows if x["kind"] == "startup" and x["pid"] == target["pid"]]
        assert sorted(x["startup_generation"] for x in same_pid) == [0, 1]
        assert any(any("demo_recovery_child.py" in arg for arg in x["orig_argv"]) for x in same_pid)
        assert len([x for x in rows if x["kind"] == "startup"]) >= 8
        assert (
            len([x for x in rows if x.get("function") == "handle" and x.get("event") == "return"])
            == 10
        )
        assert not any(
            x.get("function")
            in ("load_model_context", "predict_views", "explain_m1", "_extract_one")
            for x in rows
        )
        assert all(
            x["state"]["modules"]["torch"]["file"] is None
            and x["state"]["modules"]["sentence_transformers"]["file"] is None
            for x in rows
            if x["kind"] == "startup"
        )
        exclusive_json(
            run / "result.json",
            {
                "invented_only": True,
                "whole_responses_equal_with_and_without_observer": True,
                "python_mcp_equal_each_mode": True,
                "native_model_calls": 0,
                "observed_session_returns": 10,
                "all_startups_before_encoders": True,
                "observation_errors": 0,
                "target_profile_active_after_same_pid_exec": True,
                "same_pid_has_two_distinct_startup_records": True,
                "rng_snapshot_preserved_invented_generator_states": True,
                "cleanup_confirmed": demo_recovery.quiescent_receipts(run),
            },
        )
    finally:
        if demo_recovery.quiescent_receipts(run):
            demo_recovery.clean_scratch(run)


def load(plan_file):
    plan = read_json(plan_file)
    assert plan["schema"] == "independent-real-python-mcp-pair-v1"
    assert Path(plan["clone_root"]) == ROOT
    for name, sha in plan["pins"].items():
        assert digest(Path(name)) == sha
    assert plan["budgets"] == {
        "global_seconds": 1200,
        "per_route_seconds": 480,
        "cleanup_allowance_seconds": 30,
        "outer_job_envelope_seconds": 510,
        "rss_bytes": 3584 * 1024**2,
        "workspace_bytes": 384 * 1024**2,
        "file_bytes": 32 * 1024**2,
        "io_bytes": 65536,
    }
    assert plan["max_real_route_calls"] == {"python": 1, "mcp": 1}
    assert plan["retention_until"] == "2026-10-21T23:59:00-03:00"
    assert (
        plan["retries"]
        == plan["downloads"]
        == plan["nim_calls"]
        == plan["vlm_calls"]
        == plan["training_calls"]
        == 0
    )
    config = read_json(Path(plan["config_file"]))
    registry_file = Path(config["run_dir"]) / "registry.json"
    assert plan["registry_lock_overlay"] == {
        "registry_file": str(registry_file),
        "target": str(registry_file.with_suffix(".lock")),
        "only_new_scratch_control_file_writable": True,
        "original_registry_and_lock_unchanged": True,
    }
    return plan


def execute(plan, plan_file, release_file):
    release = read_json(release_file)
    assert release["plan_sha256"] == digest(plan_file)
    assert release["technical_window_open"] is True
    assert release["actual_origin_entry_id"] and release["source_output_untruncated"] is True
    assert digest(plan_file) in release["literal_release_input"]
    expires = datetime.fromisoformat(release["window_expires_at"]).timestamp()
    assert 0 < expires - time.time() <= 3600
    assert (
        read_json(Path(plan["preflight_run"]) / "result.json")[
            "whole_responses_equal_with_and_without_observer"
        ]
        is True
    )
    demo_recovery.no_other_model_jobs()
    run = Path(plan["real_run"])
    new_run(run)
    started = time.monotonic()
    exclusive_json(
        run / "started.json",
        {
            "plan_sha256": digest(plan_file),
            "release_sha256": digest(release_file),
            "consumed": True,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        },
    )
    completed = []
    try:
        for route in ("python", "mcp"):
            demo_recovery.no_other_model_jobs()
            remaining = min(
                1200 - (time.monotonic() - started),
                expires - time.time(),
                datetime.fromisoformat(plan["retention_until"]).timestamp() - time.time(),
            )
            assert remaining > 0
            exclusive_json(
                run / "receipts" / (route + "-reserved.json"),
                {"consumed_before_spawn": True, "max_calls": 1},
            )
            guarded(
                run,
                route + "-job",
                [
                    str(ROOT / ".venv/bin/python"),
                    "-B",
                    "-m",
                    "scripts.independent_parity_route",
                    route,
                    "--config",
                    plan["config_file"],
                    "--output",
                    str(run / (route + "-response.json")),
                ],
                plan["budgets"],
                min(plan["budgets"]["outer_job_envelope_seconds"], remaining),
                plan["hf_cache"],
                enabled=True,
                registry_file=Path(plan["registry_lock_overlay"]["registry_file"]),
            )
            rows = traces(run, route + "-job")
            verify_input_bindings(rows)
            assert (
                len(
                    [
                        x
                        for x in rows
                        if x.get("function") == "_extract_one" and x.get("event") == "call"
                    ]
                )
                == 3
            )
            assert (
                len(
                    [
                        x
                        for x in rows
                        if x.get("function") == "predict_views" and x.get("event") == "call"
                    ]
                )
                == 3
            )
            assert (
                len(
                    [
                        x
                        for x in rows
                        if x.get("function") == "explain_m1" and x.get("event") == "call"
                    ]
                )
                == 1
            )
            assert (
                len(
                    [
                        x
                        for x in rows
                        if x.get("function") == "predict_logs" and x.get("event") == "call"
                    ]
                )
                == 4
            )
            assert (
                len(
                    [
                        x
                        for x in rows
                        if x.get("function") == "handle" and x.get("event") == "return"
                    ]
                )
                == 5
            )
            completed.append(route)
        first, second = [read_json(run / (r + "-response.json")) for r in ("python", "mcp")]
        exclusive_json(
            run / "whole-response-comparison.json",
            {
                "entire_response_equal": first == second,
                "python_response_sha256": digest(run / "python-response.json"),
                "mcp_response_sha256": digest(run / "mcp-response.json"),
                "no_fields_removed_or_normalized_for_equality": True,
                "historical_cause_proven": False,
                "canonical_source_changed": False,
            },
        )
    finally:
        cleanup = demo_recovery.quiescent_receipts(run)
        if cleanup:
            demo_recovery.clean_scratch(run)
        exclusive_json(
            run / "authorization-closed.json",
            {
                "completed_routes": completed,
                "no_remaining_calls": True,
                "automatic_retry_allowed": False,
                "cleanup_confirmed": cleanup,
                "elapsed_seconds": time.monotonic() - started,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "preflight", "run"))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--release", type=Path)
    args = parser.parse_args()
    plan = load(args.plan)
    if args.mode == "preflight":
        preflight(plan)
    elif args.mode == "run":
        assert args.release is not None, "technical_window_required"
        execute(plan, args.plan, args.release)
    print(json.dumps({"mode": args.mode, "completed": True}))


if __name__ == "__main__":
    main()
