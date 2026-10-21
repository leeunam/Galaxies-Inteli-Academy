"""Production branch ordering with injected objects; no real authority or HTTP."""


def test_dispatch_precedes_fake_getter_and_fake_transport(tmp_path, monkeypatch):
    # Exercise the production branch with injected objects only: no real review,
    # reservation, nonce codec, credential getter, socket or provider verification.
    import time

    from orchestration.galaxies_orchestration import nim_http
    from scripts import nim_diagnostic_release_worker_v1 as worker
    from scripts.nim_diagnostic_worker_v1 import invented_response
    from scripts.nim_graph_bridge_v1 import BridgeSession

    session = worker.AttemptSession.__new__(worker.AttemptSession)
    BridgeSession.__init__(session, "valid", "1" * 32)
    session.offline = False
    session.folder = tmp_path / "invented-unit"
    session.folder.mkdir()
    session.plan = {}
    session.bound = {"deadline_monotonic": time.monotonic() + 10}
    session.nonce = b"x" * 32
    session.attempted = False
    events = []
    monkeypatch.setattr(worker.c, "verify_plan", dict)
    monkeypatch.setattr(worker.c, "check_review", lambda plan: "INVENTED")
    monkeypatch.setattr(worker.c, "check_binding", lambda *args, **kwargs: session.bound)

    def dispatch(*args, **kwargs):
        events.append("dispatch")

    def getter():
        assert events == ["dispatch"]
        events.append("fake_getter")
        return "ENTIRELY_INVENTED_NON_CREDENTIAL"

    class Connection:
        def close(self):
            events.append("closed")

    def transport(key, *, timeout):
        assert events == ["dispatch", "fake_getter"]
        events.append("fake_transport")
        return Connection(), invented_response("wrong_hash", session.public)

    monkeypatch.setattr(worker, "authorize", dispatch)
    monkeypatch.setattr(nim_http, "existing_key", getter)
    monkeypatch.setattr(worker, "live_response", transport)
    for op in ("analyze", "shap", "comparables", "context"):
        session.handle({"op": op, "payload": {}} if op == "analyze" else {"op": op})
    result = session.handle(
        {"op": "select", "request": worker.c.canonical(session.public["request"]).decode()}
    )
    assert events == ["dispatch", "fake_getter", "fake_transport", "closed"]
    assert result["selection"] is None
    assert result["diagnostic"]["code"] == "packet_hash_mismatch"
