"""Invented connection only; no key getter, socket, model or provider call."""

import pytest

from orchestration.galaxies_orchestration.nim_graph_contract_v1 import fixture
from scripts import nim_global_fixed_http_v1 as transport
from scripts.nim_global_http_fakes_v1 import INVENTED_KEY, connection_factory
from scripts.nim_http_error_observer_v1 import observe_opened_response
from tests.test_nim_graph_rejection_audit_v1 import (
    no_network_key_or_model,  # noqa: F401
    prepared_session,
)


def test_exact_global_opening_and_bounded_response_use_invented_connection():
    trace = {}
    connection, response = transport._open_response(
        INVENTED_KEY, factory=connection_factory("valid", fixture(), trace), timeout=1.25
    )
    try:
        result = observe_opened_response(prepared_session().session.context, response)
        assert result["transport"]["code"] == "selection_accepted"
        assert result["diagnostic"]["authority_status"] == "accepted"
        assert result["http_error_metadata"] is None
    finally:
        connection.close()
    assert trace == {"created": 1, "posts": 1, "responses": 1, "closed": 1}


@pytest.mark.parametrize(
    "key,timeout",
    [
        ("invalid", 1),
        (INVENTED_KEY, 0),
        (INVENTED_KEY, True),
        (INVENTED_KEY, float("nan")),
        (INVENTED_KEY, 45.001),
    ],
)
def test_bad_key_or_deadline_stops_before_constructor(key, timeout):
    def forbidden(*args, **kwargs):
        raise AssertionError("constructor_must_not_run")

    with pytest.raises(ValueError, match="^global_fixed_"):
        transport._open_response(key, factory=forbidden, timeout=timeout)


@pytest.mark.parametrize("body", [b"invented wrong body", b"x" * 10065])
def test_payload_bytes_and_hash_are_checked_before_constructor(monkeypatch, body):
    monkeypatch.setattr(transport, "payload_bytes", lambda: body)

    def forbidden(*args, **kwargs):
        raise AssertionError("constructor_must_not_run")

    with pytest.raises(ValueError, match="^global_fixed_payload_changed_before_socket$"):
        transport._open_response(INVENTED_KEY, factory=forbidden, timeout=1)


def test_send_failure_closes_owned_connection_once_without_retry():
    trace = {"created": 0, "posts": 0, "closed": 0}

    class Failed:
        def set_debuglevel(self, level):
            assert level == 0

        def request(self, *args, **kwargs):
            trace["posts"] += 1
            raise RuntimeError("ENTIRELY_INVENTED_SEND_FAILURE")

        def close(self):
            trace["closed"] += 1

    def factory(*args, **kwargs):
        trace["created"] += 1
        return Failed()

    with pytest.raises(RuntimeError, match="^ENTIRELY_INVENTED_SEND_FAILURE$"):
        transport._open_response(INVENTED_KEY, factory=factory, timeout=1)
    assert trace == {"created": 1, "posts": 1, "closed": 1}
