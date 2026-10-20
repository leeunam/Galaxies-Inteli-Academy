"""Model-free preflight against the installed b11716 shared libraries, never inference."""

from __future__ import annotations

import argparse
import itertools
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.gguf_visual_attributes import RUNTIME
from scripts.private_checkpoint import digest, file_hash, private_path
from scripts.vlm_product_limited import verify_runtime
from scripts.vlm_product_limited_plan import no_workers
from scripts.vlm_product_states import CATEGORIES, STATES
from scripts.vlm_product_v16 import (
    PROJECTION,
    VARIANTS,
    decode,
    ordered_schema_hash,
    save,
    specification,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    "scripts/vlm_product_v16.py",
    "scripts/vlm_product_v16_grammar.py",
    "scripts/vlm_product_v13_grammar.cpp",
)
HEADER_HASHES = {
    "common__json.h": "a352f31307f1be2bdb34c027b876f42a1c5d1ea775cc8e4f11d703b16c40d22f",
    "src__llama-grammar.h": "db730e5aff77f96274aba4a43670f036400d89c7ed44b6e98d3ced41c7b9d193",
    "include__llama.h": "961430f89e2553dbcd99e3e6c59826af9ec143f05911520c74f804d986ff3cd2",
    "ggml__include__ggml.h": "475beaa7e959be8c383279d9ce9d5191f37426e6b338270cfb12b26a798129d3",
    "ggml__include__ggml-cpu.h": "316279e004cdeb8e6ef78599acb602bf79a8abdf897fed9fd1914808c1518c6e",
    "ggml__include__ggml-backend.h": "0e5e8e1f16d11ebbf501e38bc6705d79eee819b5f0b17476533f2100ed9674e2",
    "ggml__include__ggml-alloc.h": "d114067f9099c4a0e2bbc0625c676d4894d9cf0ea27168ee072c7de0e71bb51d",
    "ggml__include__ggml-opt.h": "3586de1bc8a934b5c72339e2b6937b0641e8f149b512231e666f67de0736eea2",
    "ggml__include__gguf.h": "e56714aab702e5ce62ee587a409643c08f7e93e8fbb77f48ef7cc85075f96fa4",
}


def source_hashes():
    return {n: file_hash(ROOT / n) for n in SOURCES}


def library_hashes():
    return {n: file_hash(RUNTIME.parent / n) for n in ("libllama-common.so", "libllama.so")}


def probes(variant):
    """All 13,640 finite combinations; 22 native objects plus raw mutations."""
    rows, valid = [], []
    fields = specification(variant)["fields"]
    for size in range(5):
        for cats in itertools.product(CATEGORIES, repeat=size):
            for state in STATES:
                for config in PROJECTION:
                    body = {
                        "item_configuration": config,
                        "state": state,
                        "presented_categories": list(cats),
                    }
                    body = {k: body[k] for k in fields}
                    raw = json.dumps(body, separators=(",", ":"))
                    try:
                        decode(raw, variant)
                        expected = True
                    except ValueError:
                        expected = False
                    rows.append({"raw": raw, "expected": expected, "group": "finite_domain"})
                    if expected:
                        valid.append(raw)
    for raw in valid:
        rows.append(
            {
                "raw": raw.replace(',"state":', ',\n  "state": ').replace(
                    ',"presented_categories":', ',\n  "presented_categories": '
                ),
                "expected": True,
                "group": "field_whitespace",
            }
        )
    for raw in valid:
        body = json.loads(raw)
        opposite = {k: body[k] for k in (fields[1], fields[0], fields[2])}
        rows.append(
            {
                "raw": json.dumps(opposite, separators=(",", ":")),
                "expected": False,
                "group": "cross_order",
            }
        )
    negative = valid[0]
    mutations = [
        "",
        "{}",
        "[]",
        "true",
        "null",
        "invalid",
        negative[:-1],
        negative + "{}",
        negative.replace('"absent"', '"absent","item_configuration":"absent"'),
        negative.replace('"absent"', '"incidental"'),
        negative.replace('"absent"', "null"),
        negative.replace('"absent"', '"invented"'),
        negative.replace('"no_target"', "false"),
        negative.replace("[]", "null"),
        negative.replace("[]", '["garment"]'),
        negative.replace("}", ',"presentation_cue":"absent"}'),
        '{"item_configuration":"absent","state":"no_target"}',
        '{"state":"no_target","presented_categories":[],"presentation_cue":"absent"}',
        json.dumps(
            {k: json.loads(negative)[k] for k in (fields[1], fields[0], fields[2])},
            separators=(",", ":"),
        ),
    ]
    rows.extend({"raw": raw, "expected": False, "group": "raw_mutation"} for raw in mutations)
    return rows


def check_receipt(folder, variant, root=ROOT):
    """Pure integrity/gate check, with no compilation, model loading or dispatch."""
    folder = private_path(folder, root)
    body = json.loads((folder / "receipt.json").read_bytes())
    if (
        body["variant"] != variant
        or body["ordered_schema_sha256"] != ordered_schema_hash(specification(variant)["schema"])
        or body["status"] != "native_b11716_grammar_preflight_passed"
        or body["receipt_sha256"]
        != digest({k: v for k, v in body.items() if k != "receipt_sha256"})
        or body["sources"] != source_hashes()
        or body["libraries"] != library_hashes()
        or body["schema_sha256"] != digest(specification(variant)["schema"])
        or body["specification_sha256"] != digest(specification(variant))
        or body["model_loaded"] is not False
        or body["forward_passes"] != 0
        or body["expected_mismatches"] != 0
        or body["finite_domain_accepted"] != 22
    ):
        raise ValueError("v16_native_grammar_preflight_changed")
    for name, expected in body["files_sha256"].items():
        path = folder / name
        if path.parent != folder or path.is_symlink() or file_hash(path) != expected:
            raise ValueError("v16_native_grammar_preflight_file_changed")
    if (
        set(body["files_sha256"])
        != {
            "schema.json",
            "probes.jsonl",
            "native-results.jsonl",
            "grammar.gbnf",
            "native-grammar-check",
        }
        or body["grammar_sha256"] != body["files_sha256"]["grammar.gbnf"]
        or json.loads((folder / "schema.json").read_bytes()) != specification(variant)["schema"]
        or ordered_schema_hash(json.loads((folder / "schema.json").read_bytes()))
        != ordered_schema_hash(specification(variant)["schema"])
        or len(body["headers_sha256"]) != len(HEADER_HASHES)
        or {Path(n).name: h for n, h in body["headers_sha256"].items()} != HEADER_HASHES
    ):
        raise ValueError("v16_native_grammar_preflight_scope_changed")
    for relative, expected in body["headers_sha256"].items():
        path = private_path(root / relative, root)
        if path.is_symlink() or file_hash(path) != expected:
            raise ValueError("v16_native_grammar_header_changed")
    wanted = probes(variant)
    recorded = [json.loads(line) for line in (folder / "probes.jsonl").read_text().splitlines()]
    responses = [
        json.loads(line) for line in (folder / "native-results.jsonl").read_text().splitlines()
    ]
    if (
        body["probes"] != len(wanted)
        or body["finite_domain_probes"] != 13640
        or recorded != wanted
        or len(responses) != len(wanted)
        or any(
            response != {"index": i, "accepted": row["expected"]}
            for i, (response, row) in enumerate(zip(responses, wanted, strict=True))
        )
    ):
        raise ValueError("v16_native_grammar_probe_changed")
    return body


def preflight(headers, folder, variant, root=ROOT):
    folder, headers = private_path(folder, root), private_path(headers, root)
    if folder.exists():
        raise ValueError("v16_preflight_output_exists")
    no_workers(root)
    verify_runtime()
    if any(
        (headers / n).is_symlink() or file_hash(headers / n) != h for n, h in HEADER_HASHES.items()
    ):
        raise ValueError("v16_official_header_mismatch")
    folder.mkdir(parents=True, mode=0o700)
    spec = specification(variant)
    save(folder / "schema.json", spec["schema"])
    rows = probes(variant)
    (folder / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    compiler = shutil.which("c++")
    if compiler is None:
        raise ValueError("v16_native_bridge_compiler_unavailable")
    with tempfile.TemporaryDirectory(prefix="v16-native-headers-", dir=folder) as temp:
        directory = Path(temp)
        for name in HEADER_HASHES:
            shutil.copyfile(headers / name, directory / name.rsplit("__", 1)[-1])
        command = [
            compiler,
            "-std=c++17",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(directory),
            str(root / SOURCES[2]),
            "-L",
            str(RUNTIME.parent),
            "-Wl,-rpath," + str(RUNTIME.parent),
            "-l:libllama-common.so",
            "-l:libllama.so",
            "-o",
            str(folder / "native-grammar-check"),
        ]
        compilation = subprocess.run(command, check=True, capture_output=True, timeout=60)
        if compilation.stdout or compilation.stderr:
            raise ValueError("v16_native_bridge_compile_diagnostic")
    binary = folder / "native-grammar-check"
    environment = dict(os.environ)
    environment.pop("LD_PRELOAD", None)
    environment["LD_LIBRARY_PATH"] = str(RUNTIME.parent)
    result = subprocess.run(
        [
            str(binary),
            str(folder / "schema.json"),
            str(folder / "probes.jsonl"),
            str(folder / "grammar.gbnf"),
        ],
        check=True,
        capture_output=True,
        timeout=120,
        env=environment,
    )
    (folder / "native-results.jsonl").write_bytes(result.stdout)
    if result.stderr:
        raise ValueError("v16_native_grammar_conversion_diagnostic")
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    if len(responses) != len(rows) or any(
        r != {"index": i, "accepted": p["expected"]}
        for i, (r, p) in enumerate(zip(responses, rows, strict=True))
    ):
        raise ValueError("v16_native_grammar_acceptance_mismatch")
    body = {
        "status": "native_b11716_grammar_preflight_passed",
        "variant": variant,
        "ordered_schema_sha256": ordered_schema_hash(specification(variant)["schema"]),
        "sources": source_hashes(),
        "libraries": library_hashes(),
        "headers_sha256": {
            str((headers / n).relative_to(root)): h for n, h in HEADER_HASHES.items()
        },
        "compiler_sha256": file_hash(Path(compiler)),
        "compiler_version": subprocess.run(
            [compiler, "--version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0],
        "schema_sha256": digest(spec["schema"]),
        "specification_sha256": digest(spec),
        "grammar_sha256": file_hash(folder / "grammar.gbnf"),
        "files_sha256": {
            n: file_hash(folder / n)
            for n in (
                "schema.json",
                "probes.jsonl",
                "native-results.jsonl",
                "grammar.gbnf",
                "native-grammar-check",
            )
        },
        "probes": len(rows),
        "finite_domain_probes": 13640,
        "finite_domain_accepted": 22,
        "expected_mismatches": 0,
        "model_loaded": False,
        "forward_passes": 0,
    }
    body["receipt_sha256"] = digest(body)
    save(folder / "receipt.json", body)
    return check_receipt(folder, variant, root)


def capture_commands(folder):
    """Execute only the adapter's command construction with Popen replaced by a recorder."""
    from unittest.mock import patch

    from PIL import Image

    from scripts import gguf_visual_attributes as adapter

    recorded = {}
    for variant in VARIANTS:
        captured = []

        class CommandOnly:
            pid = os.getpid()
            returncode = 0

            def __init__(self, command, _captured=captured, **kwargs):
                _captured.append(list(command))
                if kwargs.get("start_new_session") is not True:
                    raise ValueError("v16_command_process_group_changed")

            def communicate(self, timeout=None):
                if timeout != 180:
                    raise ValueError("v16_command_timeout_changed")
                return "{}", ""

        with tempfile.TemporaryDirectory(prefix="command-only-", dir=folder) as temp:
            work = Path(temp)
            image = work / "crop.png"
            Image.new("RGB", (320, 330)).save(image)
            spec = specification(variant)
            with patch.object(adapter.subprocess, "Popen", CommandOnly):
                adapter.invoke_local_vlm(
                    [image], spec["prompt"], work, spec["schema"], max_tokens=64
                )
            if len(captured) != 1:
                raise ValueError("v16_command_capture_count")
            command = captured[0]
            actual_schema = json.loads((work / "vlm-schema.json").read_bytes())
            if ordered_schema_hash(actual_schema) != ordered_schema_hash(spec["schema"]):
                raise ValueError("v16_adapter_serialization_changed")
            normalized = [
                "<PNG>"
                if arg == str(image)
                else "<SCHEMA>"
                if arg == str(work / "vlm-schema.json")
                else arg
                for arg in command
            ]
            recorded[variant] = {
                "normalized_argv": normalized,
                "schema_file_sha256": file_hash(work / "vlm-schema.json"),
                "ordered_schema_sha256": ordered_schema_hash(actual_schema),
                "popen_was_stubbed": True,
                "forward_passes": 0,
            }
    if recorded[VARIANTS[0]]["normalized_argv"] != recorded[VARIANTS[1]]["normalized_argv"]:
        raise ValueError("v16_condition_command_difference")
    argv = recorded[VARIANTS[0]]["normalized_argv"]
    for flag, expected in {
        "--n-predict": "64",
        "--threads": "4",
        "--threads-batch": "4",
        "--temp": "0",
        "--seed": "42",
        "--image-min-tokens": "64",
        "--image-max-tokens": "128",
        "--ctx-size": "3072",
        "--n-gpu-layers": "0",
    }.items():
        if argv[argv.index(flag) + 1] != expected:
            raise ValueError("v16_runtime_parameter_changed")
    return recorded


def complete_preflight(headers, folder, root=ROOT):
    from scripts.gguf_visual_attributes import HASHES, MODEL_DIR
    from scripts.vlm_product_v16 import CUE_PROVENANCE, PROJECTION

    folder = private_path(folder, root)
    if (folder / "offline-preflight.json").exists():
        raise ValueError("v16_complete_preflight_already_exists")
    native = {}
    accepted = {}
    for variant in VARIANTS:
        path = folder / ("native-" + variant)
        receipt = preflight(headers, path, variant, root)
        native[variant] = {
            "receipt_file_sha256": file_hash(path / "receipt.json"),
            "receipt_sha256": receipt["receipt_sha256"],
            "grammar_sha256": receipt["grammar_sha256"],
        }
        valid = [
            json.loads(p["raw"])
            for p in probes(variant)
            if p["group"] == "finite_domain" and p["expected"]
        ]
        accepted[variant] = valid
    a, b = (specification(v) for v in VARIANTS)
    if (
        a["prompt"] != b["prompt"]
        or a["schema"] != b["schema"]
        or {digest(n) for n in accepted[VARIANTS[0]]} != {digest(n) for n in accepted[VARIANTS[1]]}
        or any(len(accepted[v]) != 22 for v in VARIANTS)
        or native[VARIANTS[0]]["grammar_sha256"] == native[VARIANTS[1]]["grammar_sha256"]
    ):
        raise ValueError("v16_no_equivalent_contrast")
    save(
        folder / "semantic-equivalence.json",
        {
            "same_prompt": True,
            "same_22_semantic_objects": True,
            "same_branches_categories_required_arrays_projection": True,
            "semantic_schema_sha256": digest(a["schema"]),
            "ordered_schema_sha256": {
                v: ordered_schema_hash(specification(v)["schema"]) for v in VARIANTS
            },
            "native_grammar_differs": True,
            "correct_order_accepted_each": 22,
            "opposite_order_rejected_each": 22,
            "projection_sha256": digest(PROJECTION),
            "cue_provenance": CUE_PROVENANCE,
            "forward_passes": 0,
        },
    )
    model = next(MODEL_DIR / n for n in HASHES if "mmproj" not in n)
    tokenizer = RUNTIME.parent / "llama-tokenize"
    token_rows = []
    for variant in VARIANTS:
        for p in probes(variant):
            if p["expected"]:
                result = subprocess.run(
                    [
                        str(tokenizer),
                        "-m",
                        str(model),
                        "--offline",
                        "--stdin",
                        "--ids",
                        "--no-bos",
                        "--no-parse-special",
                    ],
                    input=p["raw"],
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
                ids = json.loads(result.stdout)
                if type(ids) is not list or len(ids) + 1 > 64:
                    raise ValueError("v16_token_budget_failed")
                token_rows.append(
                    {
                        "variant": variant,
                        "raw": p["raw"],
                        "group": p["group"],
                        "tokens": len(ids),
                        "with_end_reserve": len(ids) + 1,
                    }
                )
    if len(token_rows) != 88:
        raise ValueError("v16_tokenization_scope_failed")
    save(
        folder / "tokenization.json",
        {
            "samples": token_rows,
            "tokenizer_sha256": file_hash(tokenizer),
            "model_sha256": file_hash(model),
            "output_limit": 64,
            "forward_passes": 0,
            "passed": True,
        },
    )
    save(folder / "commands.json", capture_commands(folder))
    names = ("semantic-equivalence.json", "tokenization.json", "commands.json")
    body = {
        "status": "equivalent_semantics_tokenization_and_commands_passed",
        "native_preflights": native,
        "sources_sha256": source_hashes()
        | {
            "scripts/gguf_visual_attributes.py": file_hash(
                root / "scripts/gguf_visual_attributes.py"
            )
        },
        "files_sha256": {n: file_hash(folder / n) for n in names},
        "model_loaded_for_generation": False,
        "forward_passes": 0,
        "semantic_objects_each": 22,
        "opposite_order_rejected_each": 22,
        "token_serializations": 88,
    }
    body["preflight_sha256"] = digest(body)
    save(folder / "offline-preflight.json", body)
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headers", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--variant", choices=VARIANTS)
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    if args.complete:
        body = complete_preflight(args.headers, args.folder)
        print(
            json.dumps(
                {
                    "status": body["status"],
                    "preflight_sha256": body["preflight_sha256"],
                    "forward_passes": 0,
                }
            )
        )
        return
    if args.variant is None:
        parser.error("--variant is required unless --complete")
    body = preflight(args.headers, args.folder, args.variant)
    print(
        json.dumps(
            {
                k: body[k]
                for k in (
                    "status",
                    "probes",
                    "finite_domain_accepted",
                    "grammar_sha256",
                    "receipt_sha256",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
