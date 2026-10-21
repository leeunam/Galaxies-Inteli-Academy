"""Fixed global-cap payload transport; called only by the reviewed nonce-bound worker."""

import http.client
import re
import ssl

from orchestration.galaxies_orchestration.nim_global_selection_payload_v1 import payload_bytes
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import digest

PAYLOAD_SHA256 = "b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987"


def _open_response(key, *, factory, timeout):
    # Mandatory factory is the offline seam, never an automatic fallback.
    if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{20,512}", key):
        raise ValueError("global_fixed_key_invalid")
    body = payload_bytes()
    if len(body) != 10065 or digest(body) != PAYLOAD_SHA256:
        raise ValueError("global_fixed_payload_changed_before_socket")
    if type(timeout) not in (int, float) or not 0 < timeout <= 45:
        raise ValueError("global_fixed_socket_deadline_invalid")
    connection = factory(
        "integrate.api.nvidia.com", port=443, timeout=timeout, context=ssl.create_default_context()
    )
    try:
        connection.set_debuglevel(0)
        connection.request(
            "POST",
            "/v1/chat/completions",
            body=body,
            headers={
                "Authorization": "Bearer " + key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        return connection, connection.getresponse()
    except BaseException:
        connection.close()
        raise


def live_response(key, *, timeout):
    # No CLI, retry, redirect, proxy, SDK or caller-selected host/body/model.
    return _open_response(key, factory=http.client.HTTPSConnection, timeout=timeout)
