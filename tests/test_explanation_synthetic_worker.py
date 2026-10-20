"""Fixed invented report only; never open models, registry or media."""

import json

import pytest

from scripts.explanation_synthetic_worker import SyntheticSession, invented_report


def test_invented_report_is_explicit_and_uses_no_input():
    session = SyntheticSession()
    packet = session.handle({"op": "prepare", "payload": {}})
    assert packet["fixture_entirely_invented"] is True
    result = session.handle(
        {
            "op": "render",
            "selection": json.dumps(
                {
                    "packet_sha256": packet["packet_sha256"],
                    "evidence_ids": ["c1_interval"],
                }
            ),
            "reason": None,
        }
    )
    assert result["fixture_entirely_invented"] is True
    assert result["analysis"] == invented_report({})
    assert result["explanation"]["status"] == "validated_catalogue_selection"


@pytest.mark.parametrize("payload", [{"private": "REJECT"}, {"synthetic": True}])
def test_arbitrary_inputs_cannot_be_declared_synthetic(payload):
    with pytest.raises(ValueError, match="synthetic_probe_accepts_no_input"):
        invented_report(payload)
