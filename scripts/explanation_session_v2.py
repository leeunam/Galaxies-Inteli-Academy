"""Local staged session; raw features and reference identities stay in this process."""

import json

from scripts.explanation_composition import ExplanationNotice
from scripts.explanation_evidence import build_explanation_context, validate_selection
from scripts.m1_evidence import explain_m1
from scripts.m1_handoff_v2 import M1_A200_SHA256, analyze_once
from scripts.training_comparables import load_training_index

SCHEMA = "creative-explanation-integrated-v2"


def finish(report, *, context=None, reason="transport_not_configured", selected=None):
    if selected is None:
        selected = {
            "analysis": report,
            "explanation": ExplanationNotice(
                reason_code=reason, packet_sha256=context.packet_sha256 if context else None
            ).model_dump(mode="json"),
        }
    return {
        **selected,
        "schema_version": SCHEMA,
        "evidence_packet": context.packet.model_dump(mode="json") if context else None,
    }


class Session:
    OPERATIONS = ("analyze", "shap", "comparables", "context", "render")

    def __init__(
        self,
        analyzer,
        *,
        evidence_root=None,
        minimum_similarity=None,
        shap_explainer=None,
        index_loader=None,
    ):
        self.analyzer = analyzer
        self.evidence_root, self.minimum_similarity = evidence_root, minimum_similarity
        self.step = 0
        self.handoff = self.context = self._report = None
        self.shap, self.comparables = {}, {}
        self.reason = None
        self._explain = shap_explainer or explain_m1
        self._load_index = index_loader or load_training_index

    def report(self):
        return json.loads(self._report)

    def handle(self, message):
        op = self.OPERATIONS[self.step] if self.step < len(self.OPERATIONS) else None
        expected = (
            {"op", "payload"}
            if op == "analyze"
            else {"op", "selection", "reason"}
            if op == "render"
            else {"op"}
        )
        if type(message) is not dict or set(message) != expected or message.get("op") != op:
            raise ValueError("invalid_session_transition")
        self.step += 1  # failures/cancellation cannot repeat a stage
        if op == "analyze":
            report, self.handoff = self.analyzer(message["payload"])
            self._report = json.dumps(report, allow_nan=False)
            if report.get("schema_version") != "creative-m1-v1":
                self.reason = "m1_prediction_required"
            elif not report["learned_prediction_available"]:
                self.reason = "learned_prediction_unavailable"
            return {
                "analysis": self.report(),
                "native_feature_handoff": bool(
                    self.handoff is not None and self.handoff._features is not None
                ),
            }
        if op == "render":
            if message["reason"] not in (None, "transport_not_configured", "transport_failed"):
                raise ValueError("invalid_render_reason")
            if self.context and message["selection"] is not None:
                try:
                    selected = validate_selection(self.context, message["selection"])
                    return finish(self.report(), context=self.context, selected=selected)
                except Exception:  # noqa: BLE001 - sealed validator may raise before returning
                    return finish(self.report(), context=self.context, reason="invalid_selection")
            return finish(
                self.report(),
                context=self.context,
                reason=self.reason or message["reason"] or "transport_not_configured",
            )
        if self.reason is None:
            try:
                ready = self.handoff.ready_inputs(self.report())
                if op == "shap":
                    rows = self._explain(self.handoff.context[2], [p for _, p, _ in ready])
                    self.shap = {cid: row for (cid, _, _), row in zip(ready, rows, strict=True)}
                elif op == "comparables":
                    if self.evidence_root is None or self.minimum_similarity is None:
                        raise ValueError("training_index_not_configured")
                    index = self._load_index(
                        self.handoff.settings,
                        self.evidence_root,
                        minimum_similarity=self.minimum_similarity,
                    )
                    if (
                        index.model_artifact_sha256 != self.report()["model_artifact_sha256"]
                        or index.training_samples != 124
                    ):
                        raise ValueError("training_index_mismatch")
                    self.comparables = {
                        cid: index.search(p, media_sha256=sha) for cid, p, sha in ready
                    }
                elif op == "context":
                    self.context = build_explanation_context(
                        self.report(), shap=self.shap, comparables=self.comparables
                    )
            except Exception:  # noqa: BLE001 - fixed code; numerical checkpoint survives
                self.reason = {
                    "shap": "shap_preparation_failed",
                    "comparables": "comparable_preparation_failed",
                    "context": "evidence_binding_failed",
                }[op]
        if op == "context":
            return {
                "packet": self.context.packet.model_dump(mode="json") if self.context else None,
                "packet_sha256": self.context.packet_sha256 if self.context else None,
                "reason": self.reason,
            }
        return {"stage": op, "status": "completed" if self.reason is None else "incomplete"}


def create_session(
    registry,
    *,
    m1=None,
    evidence_root=None,
    minimum_similarity=None,
    launcher=None,
    synthetic_baseline=False,
    observed_baseline_dir=None,
):
    return Session(
        lambda payload: analyze_once(
            payload,
            registry,
            m1=m1,
            launcher=launcher,
            expected_artifact=M1_A200_SHA256,
            synthetic_baseline=synthetic_baseline,
            observed_baseline_dir=observed_baseline_dir,
        ),
        evidence_root=evidence_root,
        minimum_similarity=minimum_similarity,
    )
