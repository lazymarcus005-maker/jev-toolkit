from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .config import load_config
from .core import JevCore
from .errors import ConfigurationError, JevError
from .http_api import create_server
from .interfaces import invoke
from .mcp import run_stdio
from .mcp_http import create_mcp_server


def _config_path(value: str | None) -> str:
    return value or os.environ.get("JEV_CONFIG", "config/jev.yaml")


def _core(path: str | None, *, require_credentials: bool = False) -> JevCore:
    config = load_config(_config_path(path))
    problems = config.validate(require_credentials=require_credentials)
    if problems:
        raise ConfigurationError("; ".join(problems))
    return JevCore(config)


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
    parser.add_argument("--decision", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--state", help="JSON state file")
    parser.add_argument("--choices", required=choices_required, help="comma-separated bounded choices")
    parser.add_argument("--metadata", help="metadata JSON object")
    parser.add_argument("--threshold", type=float)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jev")
    parser.add_argument("--config", help="YAML config path; defaults to JEV_CONFIG or config/jev.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("decide", "evaluate", "enough"):
        child = sub.add_parser(command)
        _add_request_arguments(child, choices_required=command != "enough")
    rank = sub.add_parser("rank")
    _add_request_arguments(rank)
    rank.add_argument("--items", required=True, help="JSON items file")
    validate = sub.add_parser("config-validate")
    validate.add_argument("--require-credentials", action="store_true")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--network", action="store_true", help="also check provider readiness")
    providers = sub.add_parser("providers")
    providers.add_argument("action", choices=("test", "list-models"))
    serve = sub.add_parser("serve")
    serve.add_argument("--no-mcp", action="store_true")
    mcp = sub.add_parser("mcp")
    mcp.add_argument("--stdio", action="store_true", default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "config-validate":
            config = load_config(_config_path(args.config))
            problems = config.validate(require_credentials=args.require_credentials)
            if problems:
                raise ConfigurationError("; ".join(problems))
            print(json.dumps({"valid": True}))
            return 0
        core = _core(args.config)
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
        if args.command == "providers":
            if args.action == "test":
                print(json.dumps({name: provider.health() for name, provider in core.providers.items()}))
            else:
                print(json.dumps({name: provider.list_models() for name, provider in core.providers.items()}))
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
