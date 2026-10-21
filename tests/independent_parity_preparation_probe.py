"""Exact route preparation with real saved metadata, forbidden numerical work.

Both application dispatches and the MCP client/transport are explicitly false.
No media is decoded and no model is loaded. All receipts remain private.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import fastmcp
import fastmcp.client.transports

from scripts import candidate_features, explanation_graph_service_v2, m1_evidence, m1_service
from scripts.demo_recovery_mcp_only import transport_arguments
from scripts.demo_recovery_native import graph_settings
from scripts.demo_recovery_policy import exclusive_json, read_json
from scripts.experiment_a_artifact import ExperimentBundle
from scripts.independent_parity_route import run


class FakeDispatchReached(Exception):
    pass


def main():
    config_file, directory, expectation = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    config = read_json(config_file)
    counters = {"forbidden_real_calls": 0, "fake_python_dispatch": 0, "fake_mcp_dispatch": 0}
    capture = {}

    def forbidden(*args, **kwargs):
        counters["forbidden_real_calls"] += 1
        raise AssertionError("real_work_forbidden_in_preparation_probe")

    async def fake_analyze(request, settings):
        counters["fake_python_dispatch"] += 1
        assert request == read_json(Path(config["run_dir"]) / "request.json")
        assert settings.graph_python == graph_settings(config).graph_python
        assert settings.timeout_seconds == 480
        raise FakeDispatchReached

    def fake_transport(**kwargs):
        capture.update(kwargs)
        assert kwargs["log_file"] == Path(os.devnull)
        assert kwargs["args"][:3] == ["-B", "-m", "scripts.explanation_graph_mcp_v2"]
        assert kwargs["env"] == {
            "PATH": os.defpath,
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
        }
        return kwargs

    class FakeClient:
        def __init__(self, transport):
            assert transport == capture

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def list_tools(self):
            return [
                SimpleNamespace(name=n)
                for n in ("analyze_creatives", "analyze_creatives_with_explanation")
            ]

        async def call_tool(self, name, arguments, *, timeout):
            counters["fake_mcp_dispatch"] += 1
            assert name == "analyze_creatives_with_explanation" and arguments == {
                "payload": read_json(Path(config["run_dir"]) / "request.json")
            }
            assert timeout == 480
            raise FakeDispatchReached

    explanation_graph_service_v2.analyze_via_graph = fake_analyze
    fastmcp.Client = FakeClient
    fastmcp.client.transports.StdioTransport = fake_transport
    m1_service.load_model_context = forbidden
    candidate_features.extract_candidates = forbidden
    ExperimentBundle.predict_views = forbidden
    m1_evidence.explain_m1 = forbidden
    subprocess.Popen = forbidden
    observed = []
    for route in ("python", "mcp"):
        output = directory / (route + "-response.json")
        try:
            asyncio.run(run(config, route, output))
        except FakeDispatchReached:
            assert expectation == "active"
            invocation = read_json(output.with_suffix(".invocation.json"))
            assert invocation["request"] == read_json(Path(config["run_dir"]) / "request.json")
            assert invocation["registry"] == read_json(Path(config["run_dir"]) / "registry.json")
            assert invocation["configuration"] == config
            if route == "mcp":
                settings = graph_settings(config)
                from dataclasses import replace

                settings = replace(settings, scratch_root=directory / "scratch/mcp/graph")
                assert capture["args"] == transport_arguments(settings)
            observed.append("fake_boundary_reached")
        except RuntimeError as error:
            assert expectation == "missing" and str(error) == "observer_required"
            assert not output.with_suffix(".invocation.json").exists()
            observed.append("observer_required")
    assert counters["forbidden_real_calls"] == 0
    assert (
        counters["fake_python_dispatch"]
        == counters["fake_mcp_dispatch"]
        == (1 if expectation == "active" else 0)
    )
    exclusive_json(
        directory / "result.json",
        {
            "profile_active": sys.getprofile() is not None,
            "observed_control_outcomes": observed,
            "counters": counters,
            "raw_original_runtime_exception_not_retained": True,
            "both_exact_route_preparations_exercised": True,
            "actual_analysis_or_mcp_client_used": False,
        },
    )
    print('{"preparation_probe_complete":true,"real_model_calls":0}')


if __name__ == "__main__":
    main()
