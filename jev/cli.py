from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path

from .config import load_config
from .core import JevCore
from .errors import ConfigurationError, JevError
from .http_api import create_server
from .interfaces import invoke
from .mcp import run_stdio
from .mcp_http import create_mcp_server
from .models import DecisionRequest


def _config_path(value: str | None) -> str:
    return value or os.environ.get("JEV_CONFIG", "config/jev.yaml")


def _core(path: str | None, *, require_credentials: bool = False) -> JevCore:
    config = load_config(_config_path(path))
    problems = config.validate(require_credentials=require_credentials)
    if problems:
        raise ConfigurationError("; ".join(problems))
    return JevCore(config)


def _requested_config(args: argparse.Namespace) -> str | None:
    return getattr(args, "config_path", None) or getattr(args, "provider_config", None) or args.config


def _request_args(args: argparse.Namespace) -> dict:
    state = json.loads(Path(args.state).read_text()) if args.state else {}
    choices = [value.strip() for value in args.choices.split(",") if value.strip()] if args.choices else []
    value = {"decision": args.decision, "goal": args.goal, "state": state, "choices": choices}
    if getattr(args, "metadata", None):
        value["metadata"] = json.loads(args.metadata)
    if getattr(args, "threshold", None) is not None:
        value["accept_threshold"] = args.threshold
    return value


def _add_request_arguments(parser: argparse.ArgumentParser, *, choices_required: bool = True) -> None:
    parser.add_argument("--config", dest="config_path")
    parser.add_argument("--decision", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--state", help="JSON state file")
    parser.add_argument("--choices", required=choices_required, help="comma-separated bounded choices")
    parser.add_argument("--metadata", help="metadata JSON object")
    parser.add_argument("--threshold", type=float)


def _provider_diagnostics(provider: object) -> dict:
    diagnostics = getattr(provider, "diagnostics", None)
    if diagnostics:
        return diagnostics()
    started = time.perf_counter()
    healthy = bool(provider.health())
    result = {"status": "ok" if healthy else "error", "model": getattr(provider, "model", None), "latency_ms": int((time.perf_counter() - started) * 1000)}
    return result


def _benchmark(provider_name: str, provider: object, runs: int, warmup: int) -> dict:
    if runs < 1 or warmup < 0:
        raise ConfigurationError("benchmark runs must be positive and warmup cannot be negative")
    request = DecisionRequest("benchmark", "select the most appropriate bounded action", {"source": "benchmark"}, ("continue", "conclude"))
    for _ in range(warmup):
        provider.decide(request)
    latencies: list[float] = []
    successes = 0
    for _ in range(runs):
        started = time.perf_counter()
        try:
            provider.decide(request)
            successes += 1
        except Exception:
            pass
        latencies.append((time.perf_counter() - started) * 1000)
    values = sorted(latencies)
    percentile = lambda fraction: values[max(0, min(len(values) - 1, math.ceil(fraction * len(values)) - 1))]
    config = getattr(provider, "config", None)
    return {
        "provider": provider_name,
        "model": getattr(provider, "model", None),
        "device": getattr(config, "device", None),
        "runs": runs,
        "warmup": warmup,
        "latency_ms": {
            "mean": sum(values) / len(values),
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "min": min(values),
            "max": max(values),
        },
        "success_rate": successes / runs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jev")
    parser.add_argument("--config", help="YAML config path; defaults to JEV_CONFIG or config/jev.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("decide", "evaluate", "enough"):
        child = sub.add_parser(command)
        _add_request_arguments(child, choices_required=command != "enough")
    rank = sub.add_parser("rank")
    _add_request_arguments(rank, choices_required=False)
    rank.add_argument("--items", required=True, help="JSON items file")
    validate = sub.add_parser("config-validate")
    validate.add_argument("--require-credentials", action="store_true")
    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_validate = config_sub.add_parser("validate")
    config_validate.add_argument("--require-credentials", action="store_true")
    config_validate.add_argument("--config", dest="config_path")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--config", dest="config_path")
    doctor.add_argument("--network", action="store_true", help="also check provider readiness")
    providers = sub.add_parser("providers")
    providers.add_argument("--config", dest="provider_config")
    provider_sub = providers.add_subparsers(dest="provider_command", required=True)
    provider_test = provider_sub.add_parser("test")
    provider_test.add_argument("provider_name", nargs="?")
    provider_test.add_argument("--config", dest="config_path")
    provider_list = provider_sub.add_parser("list")
    provider_list.add_argument("--config", dest="config_path")
    provider_models = provider_sub.add_parser("list-models")
    provider_models.add_argument("--config", dest="config_path")
    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument("provider_name")
    benchmark.add_argument("--config", dest="config_path")
    benchmark.add_argument("--runs", type=int, default=20)
    benchmark.add_argument("--warmup", type=int, default=3)
    health = sub.add_parser("health")
    health.add_argument("--url", default="http://127.0.0.1:8080/health")
    serve = sub.add_parser("serve")
    serve.add_argument("--config", dest="config_path")
    serve.add_argument("--no-mcp", action="store_true")
    mcp = sub.add_parser("mcp")
    mcp.add_argument("--config", dest="config_path")
    mcp.add_argument("--stdio", action="store_true", default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "config-validate" or (args.command == "config" and args.config_command == "validate"):
            config = load_config(_config_path(_requested_config(args)))
            problems = config.validate(require_credentials=args.require_credentials)
            if problems:
                raise ConfigurationError("; ".join(problems))
            print(json.dumps({"valid": True}))
            return 0
        core = _core(_requested_config(args))
        if args.command in {"decide", "evaluate", "enough"}:
            print(json.dumps(invoke(core, args.command, _request_args(args))))
            return 0
        if args.command == "rank":
            value = _request_args(args)
            value["items"] = json.loads(Path(args.items).read_text())
            print(json.dumps(invoke(core, "rank", value)))
            return 0
        if args.command == "doctor":
            print(json.dumps({"config": "ok", "ready": core.ready() if args.network else None}))
            return 0 if not args.network or core.ready() else 1
        if args.command == "health":
            with urllib.request.urlopen(args.url, timeout=3) as response:
                value = json.load(response)
            print(json.dumps(value))
            return 0 if value.get("status") == "ok" else 1
        if args.command == "providers":
            if args.provider_command == "test":
                if args.provider_name:
                    provider = core.providers.get(args.provider_name)
                    if provider is None:
                        raise ConfigurationError(f"unknown provider: {args.provider_name}")
                    result = {"provider": args.provider_name, **_provider_diagnostics(provider)}
                    print(json.dumps(result))
                    return 0 if result["status"] == "ok" else 1
                print(json.dumps({name: _provider_diagnostics(provider) for name, provider in core.providers.items()}))
            elif args.provider_command == "list":
                statuses = {}
                for name, provider_config in core.config.providers.items():
                    provider = core.providers.get(name)
                    statuses[name] = {"status": "disabled", "model": provider_config.model} if provider is None else provider.status()
                print(json.dumps(statuses))
            else:
                print(json.dumps({name: provider.list_models() for name, provider in core.providers.items()}))
            return 0
        if args.command == "benchmark":
            provider = core.providers.get(args.provider_name)
            if provider is None:
                raise ConfigurationError(f"unknown provider: {args.provider_name}")
            print(json.dumps(_benchmark(args.provider_name, provider, args.runs, args.warmup)))
            return 0
        if args.command == "mcp":
            run_stdio(core)
            return 0
        if args.command == "serve":
            http_server = create_server(core, core.config.server.http_host, core.config.server.http_port)
            mcp_server = None
            if not args.no_mcp and core.config.server.mcp_http_enabled:
                mcp_server = create_mcp_server(core, core.config.server.mcp_http_host, core.config.server.mcp_http_port)
            import threading
            threading.Thread(target=http_server.serve_forever, daemon=True).start()
            if mcp_server:
                threading.Thread(target=mcp_server.serve_forever, daemon=True).start()
            print(json.dumps({"http": f"http://{core.config.server.http_host}:{core.config.server.http_port}", "mcp": f"http://{core.config.server.mcp_http_host}:{core.config.server.mcp_http_port}/mcp" if mcp_server else None}), flush=True)
            threading.Event().wait()
            return 0
    except (JevError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
