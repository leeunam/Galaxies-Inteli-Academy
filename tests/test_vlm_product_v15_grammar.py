"""Invented receipts only; native preflight is separately recorded, never run by pytest."""

import copy
import json

import pytest

from scripts import vlm_product_v15_grammar as module
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_product_v15 import save, specification


@pytest.fixture
def receipt(tmp_path, monkeypatch):
    folder = tmp_path / "data/private/preflight"
    folder.mkdir(parents=True)
    header = tmp_path / "data/private/headers/dummy.h"
    header.parent.mkdir()
    header.write_text("invented header, not runtime code")
    sources, libraries = {"source": digest("source")}, {"library": digest("library")}
    monkeypatch.setattr(module, "source_hashes", lambda: sources)
    monkeypatch.setattr(module, "library_hashes", lambda: libraries)
    monkeypatch.setattr(module, "HEADER_HASHES", {header.name: file_hash(header)})
    rows = module.probes()
    save(folder / "schema.json", specification()["schema"])
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
        "sources": sources,
        "libraries": libraries,
        "schema_sha256": digest(specification()["schema"]),
        "specification_sha256": digest(specification()),
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
    return tmp_path, folder, body, header


def publish(folder, body):
    body = copy.deepcopy(body)
    body["receipt_sha256"] = digest(body)
    save(folder / "receipt.json", body)


def test_receipt_pure_check_no_subprocess_or_model_loading(receipt, monkeypatch):
    root, folder, body, _ = receipt

    def denied(*args, **kwargs):
        raise AssertionError("subprocess_not_allowed_in_receipt_check")

    monkeypatch.setattr(module.subprocess, "run", denied)
    assert module.check_receipt(folder, root)["receipt_sha256"] == digest(body)


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
    root, folder, body, _ = receipt
    publish(folder, body | {key: value})
    with pytest.raises(ValueError):
        module.check_receipt(folder, root)


@pytest.mark.parametrize(
    "name",
    ["grammar.gbnf", "schema.json", "native-results.jsonl", "probes.jsonl", "native-grammar-check"],
)
def test_pinned_preflight_file_change_rejected(receipt, name):
    root, folder, _, _ = receipt
    with (folder / name).open("a") as output:
        output.write("tampered")
    with pytest.raises(ValueError, match="file_changed"):
        module.check_receipt(folder, root)


def test_native_answers_must_match_every_probe_even_with_new_file_hash(receipt):
    root, folder, body, _ = receipt
    path = folder / "native-results.jsonl"
    lines = path.read_text().splitlines()
    row = json.loads(lines[0])
    row["accepted"] = not row["accepted"]
    lines[0] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n")
    body["files_sha256"][path.name] = file_hash(path)
    publish(folder, body)
    with pytest.raises(ValueError, match="probe_changed"):
        module.check_receipt(folder, root)


def test_header_change_rejected(receipt):
    root, folder, _, header = receipt
    header.write_text("changed")
    with pytest.raises(ValueError, match="header_changed"):
        module.check_receipt(folder, root)


def test_existing_preflight_is_never_overwritten(receipt):
    root, folder, _, header = receipt
    before = file_hash(folder / "receipt.json")
    with pytest.raises(ValueError, match="output_exists"):
        module.preflight(header.parent, folder, root)
    assert file_hash(folder / "receipt.json") == before
