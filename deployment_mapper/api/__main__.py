from __future__ import annotations

import argparse
import os

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deployment-mapper-server")
    parser.add_argument("--host", default=os.getenv("DEPLOYMENT_MAPPER_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("DEPLOYMENT_MAPPER_PORT", "8000")))
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("DEPLOYMENT_MAPPER_RELOAD", "false").strip().lower() in {"1", "true", "yes"},
        help="Enable auto-reload for local development.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    uvicorn.run("deployment_mapper.api.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
