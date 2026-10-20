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
from scripts.vlm_product_v11 import OTHER_CUES, POSITIVE_CUES
from scripts.vlm_product_v14 import decode, save, specification

ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    "scripts/vlm_product_v14.py",
    "scripts/vlm_product_v14_grammar.py",
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


def probes():
    """Entire finite enum/array domain plus raw mutations; ASCII canonical key order."""
    rows = []
    valid = []
    for size in range(5):
        for cats in itertools.product(CATEGORIES, repeat=size):
            for state in STATES:
                for cue in (*POSITIVE_CUES, *OTHER_CUES.values()):
                    body = {
                        "state": state,
                        "presented_categories": list(cats),
                        "presentation_cue": cue,
                    }
                    raw = json.dumps(body, separators=(",", ":"))
                    try:
                        decode(raw)
                        expected = True
                    except ValueError:
                        expected = False
                    rows.append({"raw": raw, "expected": expected, "group": "finite_domain"})
                    if expected:
                        valid.append(raw)
    for raw in valid:
        rows.append(
            {
                "raw": raw.replace(',"presented_categories":', ',\n  "presented_categories": '),
                "expected": True,
                "group": "field_whitespace",
            }
        )
    negative = '{"state":"no_target","presented_categories":[],"presentation_cue":"absent"}'
    mutations = [
        "",
        "{}",
        "[]",
        "true",
        "null",
        "invalid",
        negative[:-1],
        negative + "{}",
        negative.replace('"absent"', '"incidental"'),
        negative.replace('"absent"', '"absent","presentation_cue":"absent"'),
        negative.replace('"no_target"', "false"),
        negative.replace('"no_target"', '"invented"'),
        negative.replace('"absent"', "null"),
        negative.replace('"absent"', '"\\ud800"'),
        negative.replace("[]", '["garment"]'),
        negative.replace("[]", "null"),
        negative.replace("}", ',"extra":true}'),
        '{"state":"no_target","presented_categories":[]}',
        '{"state":"presented_target","presented_categories":["garment","garment"],"presentation_cue":"held_display"}',
        '{"state":"presented_target","presented_categories":["accessory"],"presentation_cue":"worn_detail_focus"}',
        '{"state":"presented_target","presented_categories":["other"],"presentation_cue":"held_display"}',
        '{"state":"presented_target","presented_categories":["cosmetic","applicator","garment","accessory","garment"],"presentation_cue":"held_display"}',
        '{"presentation_cue":"absent","state":"no_target","presented_categories":[]}',
        '{"state":"presented_target","presented_categories":["garment","cosmetic"],"presentation_cue":"held_display"}',
        '{"state":"presented_target","presented_categories":["cosmetic"],"presentation_cue":"worn_detail_focus"}',
    ]
    rows.extend({"raw": raw, "expected": False, "group": "raw_mutation"} for raw in mutations)
    return rows


def check_receipt(folder, root=ROOT):
    """Pure integrity/gate check, with no compilation, model loading or dispatch."""
    folder = private_path(folder, root)
    body = json.loads((folder / "receipt.json").read_bytes())
    if (
        body["status"] != "native_b11716_grammar_preflight_passed"
        or body["receipt_sha256"]
        != digest({k: v for k, v in body.items() if k != "receipt_sha256"})
        or body["sources"] != source_hashes()
        or body["libraries"] != library_hashes()
        or body["schema_sha256"] != digest(specification()["schema"])
        or body["specification_sha256"] != digest(specification())
        or body["model_loaded"] is not False
        or body["forward_passes"] != 0
        or body["expected_mismatches"] != 0
        or body["finite_domain_accepted"] != 16
    ):
        raise ValueError("v14_native_grammar_preflight_changed")
    for name, expected in body["files_sha256"].items():
        path = folder / name
        if path.parent != folder or path.is_symlink() or file_hash(path) != expected:
            raise ValueError("v14_native_grammar_preflight_file_changed")
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
        or json.loads((folder / "schema.json").read_bytes()) != specification()["schema"]
        or len(body["headers_sha256"]) != len(HEADER_HASHES)
        or {Path(n).name: h for n, h in body["headers_sha256"].items()} != HEADER_HASHES
    ):
        raise ValueError("v14_native_grammar_preflight_scope_changed")
    for relative, expected in body["headers_sha256"].items():
        path = private_path(root / relative, root)
        if path.is_symlink() or file_hash(path) != expected:
            raise ValueError("v14_native_grammar_header_changed")
    wanted = probes()
    recorded = [json.loads(line) for line in (folder / "probes.jsonl").read_text().splitlines()]
    responses = [
        json.loads(line) for line in (folder / "native-results.jsonl").read_text().splitlines()
    ]
    if (
        body["probes"] != len(wanted)
        or body["finite_domain_probes"] != 9548
        or recorded != wanted
        or len(responses) != len(wanted)
        or any(
            response != {"index": i, "accepted": row["expected"]}
            for i, (response, row) in enumerate(zip(responses, wanted, strict=True))
        )
    ):
        raise ValueError("v14_native_grammar_probe_changed")
    return body


def preflight(headers, folder, root=ROOT):
    folder, headers = private_path(folder, root), private_path(headers, root)
    if folder.exists():
        raise ValueError("v14_preflight_output_exists")
    no_workers(root)
    verify_runtime()
    if any(
        (headers / n).is_symlink() or file_hash(headers / n) != h for n, h in HEADER_HASHES.items()
    ):
        raise ValueError("v14_official_header_mismatch")
    folder.mkdir(parents=True, mode=0o700)
    spec = specification()
    save(folder / "schema.json", spec["schema"])
    rows = probes()
    (folder / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    compiler = shutil.which("c++")
    if compiler is None:
        raise ValueError("v14_native_bridge_compiler_unavailable")
    with tempfile.TemporaryDirectory(prefix="v14-native-headers-", dir=folder) as temp:
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
            raise ValueError("v14_native_bridge_compile_diagnostic")
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
        raise ValueError("v14_native_grammar_conversion_diagnostic")
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    if len(responses) != len(rows) or any(
        r != {"index": i, "accepted": p["expected"]}
        for i, (r, p) in enumerate(zip(responses, rows, strict=True))
    ):
        raise ValueError("v14_native_grammar_acceptance_mismatch")
    body = {
        "status": "native_b11716_grammar_preflight_passed",
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
        "finite_domain_probes": 9548,
        "finite_domain_accepted": 16,
        "expected_mismatches": 0,
        "model_loaded": False,
        "forward_passes": 0,
    }
    body["receipt_sha256"] = digest(body)
    save(folder / "receipt.json", body)
    return check_receipt(folder, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headers", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    args = parser.parse_args()
    body = preflight(args.headers, args.folder)
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
