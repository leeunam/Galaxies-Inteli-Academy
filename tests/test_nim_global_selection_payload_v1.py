"""Offline structural regressions, explicitly not an exact replay of the rejected body."""

import json

import pytest
from pydantic import ValidationError

from orchestration.galaxies_orchestration import nim_global_selection_payload_v1 as proposal
from orchestration.galaxies_orchestration import nim_graph_contract_v1 as original
from scripts.explanation_evidence import EvidenceSelection, validate_selection
from scripts.nim_selection_diagnostic_v1 import evaluate_original
from tests.test_nim_graph_rejection_audit_v1 import (
    no_network_key_or_model,  # noqa: F401
    prepared_session,
)

PAYLOAD = original.ROOT / "orchestration/fixtures/nim-global-selection-payload-v1.json"


def test_only_user_instruction_changes_and_original_payload_remains_sealed():
    original.verify_plan()
    previous = original.payload_bytes()
    raw = proposal.payload_bytes()
    assert len(raw) == 10065
    assert (
        original.digest(raw) == "b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987"
    )
    assert len(previous) == 8576
    assert original.digest(previous) == proposal.PREVIOUS_SHA256
    before, after = json.loads(previous), json.loads(raw)
    assert set(before) == set(after)
    assert {key: value for key, value in before.items() if key != "messages"} == {
        key: value for key, value in after.items() if key != "messages"
    }
    assert len(after["messages"]) == 1
    assert after["messages"][0]["role"] == "user"
    content = after["messages"][0]["content"]
    assert before["messages"][0]["content"] in content
    assert proposal.GLOBAL_RULE in content
    assert "1 <= count <= 12" in content
    assert "response_format" not in after and "nvext" not in after
    assert original.canonical(original.response_schema()).decode("ascii") in content
    assert original.canonical(original.fixture()["request"]).decode("ascii") in content
    assert raw == PAYLOAD.read_bytes()


@pytest.mark.parametrize("index,count", [(0, 1), (1, 12)])
def test_counting_examples_are_valid_under_the_original_authority(index, count):
    example = proposal.counting_examples()[index]
    assert len(example["evidence_ids"]) == count
    assert len(set(example["evidence_ids"])) == count
    context = prepared_session().session.context
    result = validate_selection(context, original.canonical(example).decode("ascii"))
    assert result["analysis"] == original.fixture()["data"]["report"]
    assert result["explanation"]["status"] == "validated_catalogue_selection"
    assert (
        original.canonical(example).decode("ascii")
        in json.loads(proposal.payload_bytes())["messages"][0]["content"]
    )


@pytest.mark.parametrize(
    "count,accepted", [(0, False), (1, True), (12, True), (13, False), (21, False)]
)
def test_global_count_boundaries_and_invented_21_id_structural_regression(count, accepted):
    # Deliberately pick public catalog order; the actual rejected ID values were
    # not retained. This recreates a structural condition, not its exact response.
    public = original.fixture()
    catalog = [fact["evidence_id"] for fact in public["request"]["packet"]["evidence"]]
    value = {"packet_sha256": public["request"]["packet_sha256"], "evidence_ids": catalog[:count]}
    raw = original.canonical(value).decode("ascii")
    context = prepared_session().session.context
    evaluated = evaluate_original(context, raw)
    diagnostic = evaluated["diagnostic"]
    assert diagnostic["cardinality"] == count
    assert diagnostic["duplicates"] is False
    assert diagnostic["all_ids_in_catalog"] is True
    assert diagnostic["packet_hash_equal"] is True
    assert diagnostic["classifier_parity"] is True
    if count == 21:
        captured = json.loads(
            (
                original.ROOT / "docs/evidence/issue-5-nim-worker-diagnostic-v3-resultados.json"
            ).read_bytes()
        )
        assert diagnostic == captured["selection_diagnostic"]
    assert diagnostic["types"] == {
        "selection": ["object"],
        "packet_sha256": ["string"],
        "evidence_ids": ["array"],
        "evidence_ids[*]": ["string"] if count else [],
    }
    if accepted:
        selected = validate_selection(context, raw)
        assert selected["analysis"] == public["data"]["report"]
        assert diagnostic["authority_status"] == "accepted"
        assert diagnostic["code"] == "accepted"
        assert evaluated["selection"] == raw
    else:
        with pytest.raises(ValidationError):
            EvidenceSelection.model_validate(value)
        with pytest.raises(ValueError):
            validate_selection(context, raw)
        assert evaluated["selection"] is None
        assert diagnostic["authority_status"] == "rejected"
        assert diagnostic["phase"] == "schema"
        assert diagnostic["code"] == "schema_constraint"
    # Neither the proposal nor the evaluation edits/truncates the input array.
    assert len(value["evidence_ids"]) == count


def test_schema_and_authority_still_apply_one_global_1_to_12_array():
    schema = original.response_schema()["properties"]["evidence_ids"]
    assert schema["minItems"] == 1 and schema["maxItems"] == 12
    assert schema["uniqueItems"] is True
    assert len(schema["items"]["enum"]) == 24
    field = EvidenceSelection.model_json_schema()["properties"]["evidence_ids"]
    assert field["minItems"] == 1 and field["maxItems"] == 12
