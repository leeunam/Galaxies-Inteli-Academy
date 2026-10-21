"""Four fixed revealed cells: grammar intervention, no attribute approval."""

import argparse
import fcntl
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

from PIL import Image

from scripts import vlm_encoder_probe as base
from scripts import vlm_short_answer_capture as short

ROOT = base.ROOT
QUEUE = "data/private/issue-4-vlm-perception-grammar-v1"
PAIR = "data/private/issue-4-vlm-perception-grammar-preflight-v1/selected-pair.json"
PAIR_SHA256 = "f96800d63ce4d2218d379e9e281355621888de5bf9b25268be325c05608eaefe"
LIMITS = {**base.LIMITS, "calls": 4, "seconds": 180, "per_call_seconds": 45, "cleanup_seconds": 5}
SEQUENCE = (("positive", True), ("positive", False), ("negative", False), ("negative", True))
PROMPT = (
    "Does the image show a hand directly gripping and pulling outward the fabric of a garment "
    "that someone is wearing? In this question, pulling outward means a visible hand-to-fabric "
    "grip with that same fabric held away from the wearer's body in this single image; do not "
    'infer motion or intent. Return exactly one JSON object with the single key "answer" and '
    'one string value: "yes", "no", or "uncertain". Use "uncertain" when the image does '
    "not allow a decision. Do not add other keys or text."
)
SCHEMA = {
    "type": "object",
    "properties": {"answer": {"enum": list(short.ANSWERS)}},
    "required": ["answer"],
    "additionalProperties": False,
}
SOURCES = (
    "scripts/vlm_perception_grammar.py",
    "scripts/vlm_short_answer_capture.py",
    "tests/test_vlm_perception_grammar.py",
    "tests/test_vlm_short_answer_capture.py",
    "docs/issue-4-vlm-percepcao-gramatica-proposta.md",
)


def command(original, image, schema, grammar):
    argv = base.command(original, image, schema)
    argv[argv.index("--verbosity") + 1] = "4"
    argv[argv.index("--prompt") + 1] = PROMPT
    if not grammar:
        i = argv.index("--json-schema-file")
        del argv[i : i + 2]
    return argv


def configuration(root=ROOT):
    path = root / PAIR
    if base.sha(path) != PAIR_SHA256:
        raise ValueError("selected_pair_changed")
    pair = json.loads(path.read_bytes())
    for name, wanted in pair["source_files_sha256"].items():
        source = root / name
        if (
            source.is_symlink()
            or not source.resolve().is_relative_to(root.resolve())
            or base.sha(source) != wanted
        ):
            raise ValueError("selected_pair_provenance_changed")
    if [c["alias"] for c in pair["cases"]] != ["positive", "negative"] or [
        c["expected_answer"] for c in pair["cases"]
    ] != ["yes", "no"]:
        raise ValueError("fixed_pair_contract_changed")
    native_path = path.parent / "native-preflight.json"
    native = json.loads(native_path.read_bytes())
    if (
        native["model_loaded"] is not False
        or native["forward_passes"] != 0
        or native["mismatches"] != 0
        or native["schema_semantic_sha256"] != base.digest(SCHEMA)
    ):
        raise ValueError("short_native_grammar_preflight_changed")
    for name, key in (
        ("short-schema.json", "schema_file_sha256"),
        ("short-final-grammar.gbnf", "grammar_sha256"),
        ("short-final-native-results.jsonl", "results_sha256"),
    ):
        if base.sha(path.parent / name) != native[key]:
            raise ValueError("short_native_grammar_file_changed")
    return {
        "protocol": "fixed-real-pair-grammar-intervention-v1",
        "limits": LIMITS,
        "base": base.configuration(root),
        "pair": pair,
        "pair_file_sha256": PAIR_SHA256,
        "native_grammar_preflight_sha256": base.sha(native_path),
        "native_probes_sha256": base.sha(path.parent / "short-final-probes.jsonl"),
        "sequence": list(map(list, SEQUENCE)),
        "prompt": PROMPT,
        "schema": SCHEMA,
        "sources": {n: base.sha(root / n) for n in SOURCES},
    }


def prepare(root=ROOT):
    config = configuration(root)
    plan = {
        "configuration": config,
        "configuration_sha256": base.digest(config),
        "technical_release_required": True,
    }
    plan["plan_sha256"] = base.digest(plan)
    folder = root / QUEUE
    folder.mkdir(parents=True, mode=0o700)
    base.write(folder / "plan.json", plan, exclusive=True)
    base.write(
        folder / "checkpoint.json", {"calls": 0, "operations": [], "sealed": False}, exclusive=True
    )
    return plan


def release(folder, plan):
    path = folder / "technical-release.json"
    if path.is_symlink() or path.stat().st_size > 16384:
        raise ValueError("perception_technical_release_required")
    body = json.loads(path.read_bytes())
    if (
        body.get("plan_sha256") != plan["plan_sha256"]
        or body.get("configuration_sha256") != plan["configuration_sha256"]
        or body.get("decision") != "released_for_this_perception_contrast_only"
        or body.get("reviewer_thread_id") != "01a15713-2572-7544-8329-c229ea2ff0f5"
        or not body.get("source_message_id")
        or type(body.get("literal_message")) is not str
        or not body["literal_message"]
        or body.get("literal_message_sha256")
        != hashlib.sha256(body["literal_message"].encode()).hexdigest()
    ):
        raise ValueError("perception_technical_release_required")
    return base.sha(path)


def comparison(result, expected):
    if result["stop_code"]:
        return "not_assessed_technical_failure"
    if result["format_status"] != "valid":
        return "format_invalid"
    if result["answer"] == "uncertain":
        return "abstention"
    return "correct" if result["answer"] == expected else "incorrect"


def execute(root=ROOT):
    folder = root / QUEUE
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise ValueError("perception_symlink_queue_forbidden")
    with (folder / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if (
            state != {"calls": 0, "operations": [], "sealed": False}
            or (folder / "started.json").exists()
        ):
            raise ValueError("perception_consumed_or_uncertain_no_reentry")
        plan = json.loads((folder / "plan.json").read_bytes())
        if (
            base.digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            != plan["plan_sha256"]
            or base.digest(plan["configuration"]) != plan["configuration_sha256"]
            or configuration(root) != plan["configuration"]
        ):
            raise ValueError("perception_plan_or_identity_changed")
        clearance = release(folder, plan)
        started = time.monotonic()
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "technical_release_sha256": clearance,
                "uncertain_seconds_upper_bound": 180,
            },
            exclusive=True,
        )
        error = None
        try:
            if base.workers():
                raise base.ProbeStop("concurrent_worker")
            cases = {c["alias"]: c for c in plan["configuration"]["pair"]["cases"]}
            parent = root / "data/private/media-temp"
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for index, (alias, grammar) in enumerate(SEQUENCE, 1):
                case = cases[alias]
                work = Path(tempfile.mkdtemp(prefix="galaxies-perception-grammar-", dir=parent))
                cleanup_allowed = True
                try:
                    image, schema = work / "crop.png", work / "schema.json"
                    source = root / case["sheet_path"]
                    if base.sha(source) != case["sheet_sha256"]:
                        raise ValueError("frozen_sheet_changed")
                    with Image.open(source) as sheet:
                        if (
                            sheet.mode != "RGB"
                            or sheet.size != (1280, 360)
                            or case["source_frame"] not in range(1, 5)
                        ):
                            raise ValueError("frozen_sheet_geometry_changed")
                        x = 320 * (case["source_frame"] - 1)
                        sheet.crop((x, 25, x + 320, 355)).save(image)
                    if base.sha(image) != case["png_sha256"]:
                        raise ValueError("frozen_pixels_changed")
                    schema.write_text(json.dumps(SCHEMA))
                    if (
                        configuration(root) != plan["configuration"]
                        or release(folder, plan) != clearance
                    ):
                        raise ValueError("perception_identity_before_dispatch_changed")
                    if base.workers():
                        raise base.ProbeStop("concurrent_worker")
                    remaining = min(45, 180 - (time.monotonic() - started)) - 5
                    if remaining <= 0:
                        raise TimeoutError("perception_global_budget")

                    def reserve(index=index, case=case, alias=alias, grammar=grammar):
                        if state["calls"] != index - 1 or index > 4:
                            raise ValueError("perception_call_budget")
                        base.write(
                            folder / f"reservation-{index}.json",
                            {
                                "plan_sha256": plan["plan_sha256"],
                                "input_png_sha256": case["png_sha256"],
                                "alias": alias,
                                "grammar": grammar,
                                "number": index,
                            },
                            exclusive=True,
                        )
                        state.update(calls=index, elapsed_seconds=180)
                        state["operations"].append(
                            {
                                "number": index,
                                "alias": alias,
                                "grammar": grammar,
                                "status": "reserved_uncertain",
                            }
                        )
                        base.write(folder / "checkpoint.json", state)

                    result = short.capture(
                        command(
                            plan["configuration"]["base"]["original_argv"], image, schema, grammar
                        ),
                        seconds=remaining,
                        reserve=reserve,
                    )
                    cleanup_allowed = result["cleanup_confirmed"]
                    outcome = comparison(result, case["expected_answer"])
                    base.write(
                        folder / f"result-{index}.json",
                        {
                            "plan_sha256": plan["plan_sha256"],
                            "alias": alias,
                            "grammar": grammar,
                            "input_png_sha256": case["png_sha256"],
                            "source_seconds": case["seconds"],
                            "observation": result,
                            "diagnostic_comparison": outcome,
                        },
                        exclusive=True,
                    )
                    if base.sha(image) != case["png_sha256"]:
                        raise ValueError("frozen_pixels_after_call_changed")
                    state["operations"][-1].update(
                        status="completed", diagnostic_comparison=outcome
                    )
                    base.write(folder / "checkpoint.json", state)
                    if result["stop_code"]:
                        raise base.ProbeStop(result["stop_code"])
                    if time.monotonic() - started > 180:
                        raise base.ProbeStop("global_deadline")
                finally:
                    try:
                        if cleanup_allowed:
                            shutil.rmtree(work)
                        else:
                            state["preserved_scratch_cleanup_unconfirmed"] = str(
                                work.relative_to(root)
                            )
                    except BaseException as caught:  # noqa: BLE001 -- do not lose uncertain cleanup
                        state["cleanup_error_type"] = type(caught).__name__
                        state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
                        raise base.ProbeStop("cleanup_unconfirmed") from None
        except BaseException as caught:  # noqa: BLE001 -- terminal receipt even on cancellation
            error = caught
        finally:
            if time.monotonic() - started > 180 and error is None:
                error = base.ProbeStop("global_deadline")
            state.update(
                sealed=True,
                elapsed_seconds=time.monotonic() - started,
                stop_code=error.code
                if isinstance(error, base.ProbeStop)
                else type(error).__name__
                if error
                else "scope_completed",
                candidates=[],
                released_fields=[],
                test_opened=False,
                m1_changed=False,
            )
            base.write(folder / "checkpoint.json", state)
        if error:
            raise error
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "execute", "inspect"])
    operation = parser.parse_args().operation
    try:
        result = (
            prepare()
            if operation == "prepare"
            else execute()
            if operation == "execute"
            else json.loads((ROOT / QUEUE / "checkpoint.json").read_bytes())
        )
        if operation == "prepare":
            result = {k: result[k] for k in ("plan_sha256", "configuration_sha256")}
    except Exception as error:  # noqa: BLE001 -- no arbitrary exception text in receipts
        result = {"status": "stopped", "error_type": type(error).__name__}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
