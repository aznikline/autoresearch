from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autoresearch.config import ConfigError, load_config, write_example_config
from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.runner import PipelineRunner


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoresearch")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init", help="write an example config")
    init_parser.add_argument("--path", default="config.yaml")
    init_parser.set_defaults(func=_cmd_init)

    run_parser = subparsers.add_parser("run", help="run the local pipeline spine")
    run_parser.add_argument("--config", default="config.yaml")
    run_parser.add_argument("--topic", default="")
    run_parser.add_argument("--run-id", default="")
    run_parser.add_argument("--auto-approve", action="store_true")
    run_parser.set_defaults(func=_cmd_run)

    status_parser = subparsers.add_parser("status", help="show run checkpoint")
    status_parser.add_argument("run_dir")
    status_parser.set_defaults(func=_cmd_status)

    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    path = write_example_config(args.path)
    print(f"wrote {path}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    runner = PipelineRunner(config)
    result = runner.run(
        topic=args.topic or config.research.topic,
        run_id=args.run_id or None,
        auto_approve=args.auto_approve,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"done", "paused"} else 1


def _cmd_status(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    checkpoint = read_checkpoint(run_dir)
    if checkpoint is None:
        print(f"not found: {run_dir}")
        return 1
    print(json.dumps(checkpoint, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
