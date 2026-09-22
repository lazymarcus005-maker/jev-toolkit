import io
import json
import threading
import urllib.request

from jev.config import JevConfig, ProviderConfig, RoutingConfig, TelemetryConfig
from jev.core import JevCore
from jev.http_api import create_server
from jev.mcp import handle_message, run_stdio
from jev.models import ProviderDecision


class Provider:
    name = "fake"
    model = "fake-model"

    def decide(self, request):
        return ProviderDecision(request.choices[0], 0.9, self.model)

    def health(self):
        return True

    def list_models(self):
        return [{"name": self.model}]


def core():
    config = JevConfig({"fake": ProviderConfig("fake", "typesafe", base_url="http://fake")}, RoutingConfig("fake"), telemetry=TelemetryConfig(enabled=False))
    return JevCore(config, providers={"fake": Provider()})


def arguments():
    return {"decision": "next", "goal": "choose", "state": {}, "choices": ["inspect", "conclude"]}


def test_mcp_lists_and_invokes_tools():
    listed = handle_message(core(), {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert names == {"jev_decide", "jev_rank", "jev_evaluate", "jev_enough", "jev_health"}
    called = handle_message(core(), {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "jev_decide", "arguments": arguments()}})
    value = json.loads(called["result"]["content"][0]["text"])
    assert value["choice"] == "inspect"


def test_stdio_mcp_round_trip():
    input_stream = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n")
    output_stream = io.StringIO()
    run_stdio(core(), input_stream, output_stream)
    assert "jev_decide" in output_stream.getvalue()


def test_http_contract_and_health():
    server = create_server(core(), "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    with urllib.request.urlopen(url + "/health") as response:
        assert json.load(response)["status"] == "ok"
    request = urllib.request.Request(url + "/v1/decide", data=json.dumps(arguments()).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request) as response:
        assert json.load(response)["choice"] == "inspect"
    server.shutdown()
