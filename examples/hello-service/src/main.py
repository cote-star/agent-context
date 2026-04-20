"""Command-line entry point for hello-service."""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .server import serve_forever


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hello-service")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--greeting", default=None)
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> Config:
    base = Config.from_env()
    return Config(
        host=args.host or base.host,
        port=args.port if args.port is not None else base.port,
        greeting=args.greeting or base.greeting,
    )


def main(argv: list) -> int:
    args = parse_args(argv)
    config = build_config(args)
    print(f"hello-service listening on {config.host}:{config.port}")
    serve_forever(config)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
