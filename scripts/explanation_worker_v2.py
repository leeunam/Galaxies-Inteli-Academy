"""Five-message worker; code root and interpreter are deliberately independent."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from scripts.creative_registry import CreativeRegistry
from scripts.explanation_session_v2 import create_session
from scripts.m1_service import M1Settings

ROOT = Path(__file__).resolve().parents[1]
MAX_LINE = 262144


def _terminate_tree(process):
    """Freeze before enumerating; all descendants remain in the outer owned group.

    The dedicated subreaper supervisor collects orphaned zombies and removes
    scratch only after group termination. Never signal unrelated process groups.
    """
    import psutil

    try:
        parent = psutil.Process(process.pid)
        parent.suspend()
        found = {parent.pid: parent}
        for _ in range(8):
            children = parent.children(recursive=True)
            new = [p for p in children if p.pid not in found]
            for child in new:
                try:
                    child.suspend()
                    found[child.pid] = child
                except psutil.NoSuchProcess:
                    pass
            if not new:
                break
        else:
            _abort_group()
        for child in reversed(tuple(found.values())):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        deadline = time.monotonic() + 2
        while True:
            live = []
            for child in found.values():
                try:
                    if child.status() not in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
                        live.append(child)
                except psutil.NoSuchProcess:
                    pass
            if not live:
                break
            if time.monotonic() >= deadline:
                _abort_group()
            time.sleep(0.01)
    except psutil.NoSuchProcess:
        pass
    process.wait(timeout=5)


def _abort_group():
    """Do not unwind scratch while descendants may live; external owner cleans."""
    group = os.getpgrp()
    if os.environ.get("GALAXIES_SUPERVISED_GROUP") != str(group):
        raise RuntimeError("supervisor_required")
    os.killpg(group, signal.SIGKILL)


def supervised_launcher(folder, count):
    """Same extraction command/limits/env; child stays in supervisor-owned group."""
    if os.environ.get("GALAXIES_SUPERVISED_GROUP") != str(os.getpgrp()):
        raise RuntimeError("extraction_supervisor_required")
    process = subprocess.Popen(
        [sys.executable, "-B", "-m", "scripts.candidate_features", str(folder)],
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
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=False,
    )
    try:
        process.wait(timeout=120 + 30 * count)
        return process.returncode == 0
    finally:
        if process.poll() is None:
            try:
                _terminate_tree(process)
            except BaseException:
                # Never unwind TemporaryDirectory while child termination is
                # uncertain. The external supervisor will reap and clean.
                _abort_group()
                raise


def serve(session, source, target):
    for _ in range(5):
        raw = source.readline(MAX_LINE + 1)
        if not raw:
            return
        try:
            if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                raise ValueError("worker_limit")
            result = session.handle(json.loads(raw))
            encoded = json.dumps(result, allow_nan=False).encode() + b"\n"
            if len(encoded) > MAX_LINE:
                raise ValueError("worker_limit")
        except Exception:  # noqa: BLE001 - no raw input, paths or exception detail
            encoded = b'{"worker_error":"worker_failed"}\n'
        target.write(encoded)
        target.flush()
        if encoded == b'{"worker_error":"worker_failed"}\n':
            return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uploads-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--synthetic-baseline", action="store_true")
    mode.add_argument("--observed-baseline-dir", type=Path)
    mode.add_argument("--m1-model-dir", type=Path)
    parser.add_argument("--m1-cohort-dir", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--minimum-similarity", type=float)
    args = parser.parse_args()
    if bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
        parser.error("M1 requires model and cohort")
    if (args.evidence_root is None) != (args.minimum_similarity is None):
        parser.error("Index requires evidence root and explicit similarity")
    m1 = (
        M1Settings(args.m1_model_dir, args.m1_cohort_dir, args.scratch_root)
        if args.m1_model_dir
        else None
    )
    session = create_session(
        CreativeRegistry(args.uploads_root, args.registry),
        m1=m1,
        evidence_root=args.evidence_root,
        minimum_similarity=args.minimum_similarity,
        launcher=supervised_launcher,
        synthetic_baseline=args.synthetic_baseline,
        observed_baseline_dir=args.observed_baseline_dir,
    )
    serve(session, sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()
