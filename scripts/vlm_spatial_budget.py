"""Two fixed revealed crops, new image budget only; no automatic candidate promotion."""

import argparse
import fcntl
import json
import shutil
import tempfile
import time
from pathlib import Path

from PIL import Image

from scripts import vlm_perception_grammar as prior

base = prior.base
ROOT = prior.ROOT
QUEUE = "data/private/issue-4-vlm-spatial-1024-v1"
REFERENCE = "docs/evidence/issue-4-vlm-percepcao-gramatica-resultados.json"
REFERENCE_SHA256 = "32dd838f11789234db51accf97787a7dda96a6b2014ed6cb845518807f4c76f6"
SEQUENCE = ("negative", "positive")
LIMITS = {
    **base.LIMITS,
    "calls": 2,
    "seconds": 100,
    "per_call_seconds": 45,
    "cleanup_seconds": 5,
    "preparation_allowance_seconds": 10,
}
SOURCES = (
    "scripts/vlm_spatial_budget.py",
    "tests/test_vlm_spatial_budget.py",
    "docs/issue-4-vlm-espacial-1024-protocolo.md",
)


def command(original, image, schema):
    argv = prior.command(original, image, schema, True)
    for flag, old in (("--image-min-tokens", "64"), ("--image-max-tokens", "128")):
        position = argv.index(flag) + 1
        if argv[position] != old:
            raise ValueError("reference_image_budget_changed")
        argv[position] = "1024"
    return argv


def configuration(root=ROOT):
    path = root / REFERENCE
    if base.sha(path) != REFERENCE_SHA256:
        raise ValueError("sealed_reference_changed")
    reference = json.loads(path.read_bytes())
    old = root / prior.QUEUE
    if base.sha(old / "checkpoint.json") != reference["checkpoint_sha256"]:
        raise ValueError("sealed_reference_checkpoint_changed")
    tokens = {}
    for row in reference["cells"]:
        if not row["grammar_applied"]:
            continue
        if base.sha(old / f"result-{row['cell']}.json") != row["receipt_sha256"]:
            raise ValueError("sealed_reference_result_changed")
        tokens[row["case_role"]] = row["observation"]["image_tokens_observed"]
    if tokens != {"positive": 100, "negative": 100}:
        raise ValueError("reference_tokens_changed")
    inherited = prior.configuration(root)
    return {
        "protocol": "fixed-real-pair-spatial-budget-1024-v1",
        "limits": LIMITS,
        "inherited_configuration": inherited,
        "sequence": list(SEQUENCE),
        "grammar_applied": True,
        "reference_evidence_sha256": REFERENCE_SHA256,
        "reference_tokens": tokens,
        "normalized_argv": command(inherited["base"]["original_argv"], "<PNG>", "<SCHEMA>"),
        "sources": {name: base.sha(root / name) for name in SOURCES},
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


def effective_budget(result, reference_tokens):
    result["effective_visual_budget"] = None
    if result["stop_code"] is None:
        tokens = result["image_tokens_observed"]
        increased = type(tokens) is int and tokens > reference_tokens
        result["effective_visual_budget"] = increased
        if not increased:
            result["stop_code"] = "visual_budget_not_increased"
    return result


def execute(root=ROOT):
    folder = root / QUEUE
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise ValueError("spatial_symlink_queue_forbidden")
    with (folder / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if (
            state != {"calls": 0, "operations": [], "sealed": False}
            or (folder / "started.json").exists()
        ):
            raise ValueError("spatial_consumed_or_uncertain_no_reentry")
        plan = json.loads((folder / "plan.json").read_bytes())
        if (
            base.digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            != plan["plan_sha256"]
            or base.digest(plan["configuration"]) != plan["configuration_sha256"]
            or configuration(root) != plan["configuration"]
        ):
            raise ValueError("spatial_identity_changed")
        clearance = prior.release(folder, plan)
        started = time.monotonic()
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "technical_release_sha256": clearance,
                "uncertain_seconds_upper_bound": 100,
            },
            exclusive=True,
        )
        error = None
        try:
            if base.workers():
                raise base.ProbeStop("concurrent_worker")
            config = plan["configuration"]
            cases = {c["alias"]: c for c in config["inherited_configuration"]["pair"]["cases"]}
            parent = root / "data/private/media-temp"
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for index, alias in enumerate(SEQUENCE, 1):
                case = cases[alias]
                work = Path(tempfile.mkdtemp(prefix="galaxies-spatial-budget-", dir=parent))
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
                    schema.write_text(json.dumps(prior.SCHEMA))
                    if configuration(root) != config or prior.release(folder, plan) != clearance:
                        raise ValueError("spatial_identity_before_dispatch_changed")
                    if base.workers():
                        raise base.ProbeStop("concurrent_worker")
                    remaining = min(45, 100 - (time.monotonic() - started)) - 5
                    if remaining <= 0:
                        raise TimeoutError("spatial_global_budget")

                    def reserve(index=index, alias=alias, case=case):
                        if state["calls"] != index - 1 or index > 2:
                            raise ValueError("spatial_call_budget")
                        base.write(
                            folder / f"reservation-{index}.json",
                            {
                                "number": index,
                                "alias": alias,
                                "plan_sha256": plan["plan_sha256"],
                                "input_png_sha256": case["png_sha256"],
                            },
                            exclusive=True,
                        )
                        state.update(calls=index, elapsed_seconds=100)
                        state["operations"].append(
                            {"number": index, "alias": alias, "status": "reserved_uncertain"}
                        )
                        base.write(folder / "checkpoint.json", state)

                    result = prior.short.capture(
                        command(
                            config["inherited_configuration"]["base"]["original_argv"],
                            image,
                            schema,
                        ),
                        seconds=remaining,
                        reserve=reserve,
                    )
                    cleanup_allowed = result["cleanup_confirmed"]
                    effective_budget(result, config["reference_tokens"][alias])
                    outcome = prior.comparison(result, case["expected_answer"])
                    base.write(
                        folder / f"result-{index}.json",
                        {
                            "plan_sha256": plan["plan_sha256"],
                            "alias": alias,
                            "grammar": True,
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
                finally:
                    try:
                        if cleanup_allowed:
                            shutil.rmtree(work)
                        else:
                            state["preserved_scratch_cleanup_unconfirmed"] = str(
                                work.relative_to(root)
                            )
                    except BaseException as caught:  # noqa: BLE001 -- preserve uncertain cleanup
                        state["cleanup_error_type"] = type(caught).__name__
                        state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
                        raise base.ProbeStop("cleanup_unconfirmed") from None
        except BaseException as caught:  # noqa: BLE001 -- seal cancellation and uncertain outcome
            error = caught
        finally:
            if time.monotonic() - started > 100 and error is None:
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
    except Exception as error:  # noqa: BLE001 -- do not print private exception values
        result = {"status": "stopped", "error_type": type(error).__name__}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
