"""Invented receipts only; native preflight is separately recorded, never run by pytest."""

import copy
import json

import pytest

from scripts import vlm_product_v16_grammar as module
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_product_v16 import VARIANTS, ordered_schema_hash, save, specification


@pytest.fixture(params=VARIANTS)
def receipt(tmp_path, monkeypatch, request):
    variant = request.param
    folder = tmp_path / "data/private/preflight"
    folder.mkdir(parents=True)
    header = tmp_path / "data/private/headers/dummy.h"
    header.parent.mkdir()
    header.write_text("invented header, not runtime code")
    sources, libraries = {"source": digest("source")}, {"library": digest("library")}
    monkeypatch.setattr(module, "source_hashes", lambda: sources)
    monkeypatch.setattr(module, "library_hashes", lambda: libraries)
    monkeypatch.setattr(module, "HEADER_HASHES", {header.name: file_hash(header)})
    rows = module.probes(variant)
    save(folder / "schema.json", specification(variant)["schema"])
    (folder / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (folder / "native-results.jsonl").write_text(
        "".join(
            json.dumps({"index": i, "accepted": r["expected"]}) + "\n" for i, r in enumerate(rows)
        )
    )
    (folder / "grammar.gbnf").write_text('root ::= "invented"\n')
    (folder / "native-grammar-check").write_text("invented non-executable receipt fixture")
    body = {
        "status": "native_b11716_grammar_preflight_passed",
        "variant": variant,
        "ordered_schema_sha256": ordered_schema_hash(specification(variant)["schema"]),
        "sources": sources,
        "libraries": libraries,
        "schema_sha256": digest(specification(variant)["schema"]),
        "specification_sha256": digest(specification(variant)),
        "headers_sha256": {str(header.relative_to(tmp_path)): file_hash(header)},
        "files_sha256": {p.name: file_hash(p) for p in folder.iterdir()},
        "grammar_sha256": file_hash(folder / "grammar.gbnf"),
        "probes": len(rows),
        "finite_domain_probes": 13640,
        "finite_domain_accepted": 22,
        "expected_mismatches": 0,
        "model_loaded": False,
        "forward_passes": 0,
    }
    publish(folder, body)
    return tmp_path, folder, body, header, variant


def publish(folder, body):
    body = copy.deepcopy(body)
    body["receipt_sha256"] = digest(body)
    save(folder / "receipt.json", body)


def test_receipt_pure_check_no_subprocess_or_model_loading(receipt, monkeypatch):
    root, folder, body, _, variant = receipt

    def denied(*args, **kwargs):
        raise AssertionError("subprocess_not_allowed_in_receipt_check")

    monkeypatch.setattr(module.subprocess, "run", denied)
    assert module.check_receipt(folder, variant, root)["receipt_sha256"] == digest(body)


@pytest.mark.parametrize(
    "key,value",
    [
        ("model_loaded", True),
        ("forward_passes", 1),
        ("expected_mismatches", 1),
        ("finite_domain_accepted", 15),
        ("probes", 1),
        ("finite_domain_probes", 1),
        ("sources", {}),
        ("libraries", {}),
        ("headers_sha256", {}),
        ("grammar_sha256", "0" * 64),
        ("schema_sha256", "0" * 64),
    ],
)
def test_self_consistent_but_wrong_scope_cannot_pass(receipt, key, value):
    root, folder, body, _, variant = receipt
    publish(folder, body | {key: value})
    with pytest.raises(ValueError):
        module.check_receipt(folder, variant, root)


@pytest.mark.parametrize(
    "name",
    ["grammar.gbnf", "schema.json", "native-results.jsonl", "probes.jsonl", "native-grammar-check"],
)
def test_pinned_preflight_file_change_rejected(receipt, name):
    root, folder, _, _, variant = receipt
    with (folder / name).open("a") as output:
        output.write("tampered")
    with pytest.raises(ValueError, match="file_changed"):
        module.check_receipt(folder, variant, root)


def test_native_answers_must_match_every_probe_even_with_new_file_hash(receipt):
    root, folder, body, _, variant = receipt
    path = folder / "native-results.jsonl"
    lines = path.read_text().splitlines()
    row = json.loads(lines[0])
    row["accepted"] = not row["accepted"]
    lines[0] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n")
    body["files_sha256"][path.name] = file_hash(path)
    publish(folder, body)
    with pytest.raises(ValueError, match="probe_changed"):
        module.check_receipt(folder, variant, root)


def test_header_change_rejected(receipt):
    root, folder, _, header, variant = receipt
    header.write_text("changed")
    with pytest.raises(ValueError, match="header_changed"):
        module.check_receipt(folder, variant, root)


def test_existing_preflight_is_never_overwritten(receipt):
    root, folder, _, header, variant = receipt
    before = file_hash(folder / "receipt.json")
    with pytest.raises(ValueError, match="output_exists"):
        module.preflight(header.parent, folder, variant, root)
    assert file_hash(folder / "receipt.json") == before


def test_adapter_command_capture_never_starts_runtime_and_uses_distinct_schema_order(
    tmp_path, monkeypatch
):
    from scripts import gguf_visual_attributes as adapter
    from scripts.vlm_product_v16 import VARIANTS, ordered_schema_hash, specification

    runtime = tmp_path / "invented-cli"
    runtime.write_text("not executable")
    monkeypatch.setattr(adapter, "RUNTIME", runtime)
    monkeypatch.setattr(adapter, "MODEL_DIR", tmp_path)
    for name in (adapter.MODEL_FILE, adapter.PROJECTOR_FILE):
        (tmp_path / name).write_text("invented not weights")
    result = module.capture_commands(tmp_path)
    assert result[VARIANTS[0]]["normalized_argv"] == result[VARIANTS[1]]["normalized_argv"]
    assert result[VARIANTS[0]]["schema_file_sha256"] != result[VARIANTS[1]]["schema_file_sha256"]
    for v in VARIANTS:
        assert result[v]["forward_passes"] == 0 and result[v]["popen_was_stubbed"]
        assert result[v]["ordered_schema_sha256"] == ordered_schema_hash(specification(v)["schema"])
    assert not list(tmp_path.glob("command-only-*"))
