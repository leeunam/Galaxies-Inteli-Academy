"""Invented metadata only; no scientific data, installed models or network."""

import contextlib
import hashlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.final_evaluation_preflight import (
    PROCEDURE_ID,
    REQUIRED_GATES,
    REQUIRED_IDENTITIES,
    SPLIT_COUNTS,
    assess_readiness,
    main,
)


def invented_metadata():
    return {
        "schema_version": "final-evaluation-readiness-v1",
        "procedure_id": PROCEDURE_ID,
        "cohort_size": 300,
        "split_counts": dict(SPLIT_COUNTS),
        "identities": {
            key: hashlib.sha256(f"invented:{key}".encode()).hexdigest()
            for key in REQUIRED_IDENTITIES
        },
        "gates": dict.fromkeys(REQUIRED_GATES, True),
    }


class FinalReadinessTests(unittest.TestCase):
    def test_each_missing_prerequisite_blocks_without_io_or_dynamic_import(self):
        for group, names in (("identities", REQUIRED_IDENTITIES), ("gates", REQUIRED_GATES)):
            for name in names:
                with self.subTest(name=name):
                    metadata = invented_metadata()
                    del metadata[group][name]
                    with (
                        patch("builtins.open", side_effect=AssertionError("unexpected IO")),
                        patch.object(Path, "open", side_effect=AssertionError("unexpected IO")),
                        patch("importlib.import_module", side_effect=AssertionError("loader")),
                    ):
                        result = assess_readiness(metadata)
                    self.assertEqual(result["status"], "blocked")
                    self.assertFalse(result["holdout_opened"])
                    self.assertFalse(result["inference_executed"])

    def test_complete_invented_declarations_never_authorize_or_verify(self):
        result = assess_readiness(invented_metadata())
        self.assertEqual(result["status"], "metadata_complete_requires_independent_review")
        for key in (
            "identities_verified", "holdout_access_authorized", "inference_authorized",
            "holdout_opened", "inference_executed",
        ):
            self.assertIs(result[key], False)

    def test_partial_models_and_truthy_gates_cannot_substitute_for_complete_bc(self):
        metadata = invented_metadata()
        del metadata["identities"]["b_complete_artifact_sha256"]
        metadata["identities"]["b_cache_artifact_sha256"] = "not-an-accepted-identity"
        metadata["gates"]["visual_audit_accepted"] = 1
        result = assess_readiness(metadata)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("not_accepted:visual_audit_accepted", result["blockers"])
        self.assertIn("missing_or_invalid:b_complete_artifact_sha256", result["blockers"])

    def test_malformed_and_wrong_split_metadata_are_blocked(self):
        for metadata in (None, [], {"identities": [], "gates": []}):
            self.assertEqual(assess_readiness(metadata)["status"], "blocked")
        metadata = invented_metadata()
        metadata["split_counts"]["test"] = 32
        self.assertIn("cohort_or_splits_mismatch", assess_readiness(metadata)["blockers"])

    def test_cli_opens_only_explicit_metadata_and_does_not_echo_values(self):
        metadata = invented_metadata()
        metadata["identities"]["c_complete_artifact_sha256"] = "private-value-not-a-hash"
        with (
            patch.object(
                Path, "open", return_value=io.BytesIO(json.dumps(metadata).encode())
            ) as read,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            code = main(["--metadata", "invented-readiness.json"])
        self.assertEqual(code, 2)
        read.assert_called_once_with("rb")
        self.assertNotIn("private-value", output.getvalue())

    def test_cli_invalid_input_is_sanitized_and_bounded(self):
        for raw in (b"{not JSON", b" " * 16_385):
            with (
                patch.object(Path, "open", return_value=io.BytesIO(raw)),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(main(["--metadata", "invented-readiness.json"]), 2)
            self.assertEqual(json.loads(output.getvalue())["code"], "invalid_readiness_metadata")


if __name__ == "__main__":
    unittest.main()
