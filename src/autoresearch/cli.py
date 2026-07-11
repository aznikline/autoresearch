from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autoresearch.audit.completion import audit_repository
from autoresearch.audit.reference import ReferenceBundleError, export_reference_bundle
from autoresearch.config import ConfigError, load_config, write_example_config
from autoresearch.hitl.session import HITLError, record_decision
from autoresearch.ideation.session import IdeationSession, write_ideation_report
from autoresearch.multivenue.report import generate_fit_report, write_fit_report
from autoresearch.pipeline.checkpoint import read_checkpoint
from autoresearch.pipeline.runner import PipelineRunner, cancel_run
from autoresearch.pipeline.verification import verify_run
from autoresearch.strategy.registry import VenueStrategyRegistry


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (ConfigError, HITLError, ReferenceBundleError) as exc:
        print(f"workflow error: {exc}", file=sys.stderr)
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

    resume_parser = subparsers.add_parser("resume", help="resume a decided gate")
    resume_parser.add_argument("run_dir")
    resume_parser.add_argument("--config", default="config.yaml")
    resume_parser.add_argument("--actor", default="operator")
    resume_parser.set_defaults(func=_cmd_resume)

    recover_parser = subparsers.add_parser(
        "recover", help="recover a running or failed stage"
    )
    recover_parser.add_argument("run_dir")
    recover_parser.add_argument("--config", default="config.yaml")
    recover_parser.add_argument("--auto-approve", action="store_true")
    recover_parser.set_defaults(func=_cmd_recover)

    approve_parser = subparsers.add_parser("approve", help="approve a paused gate")
    approve_parser.add_argument("run_dir")
    approve_parser.add_argument("--reason", default="")
    approve_parser.add_argument("--actor", default="operator")
    approve_parser.set_defaults(func=_cmd_approve)

    reject_parser = subparsers.add_parser("reject", help="reject a paused gate")
    reject_parser.add_argument("run_dir")
    reject_parser.add_argument("--reason", default="")
    reject_parser.add_argument("--actor", default="operator")
    reject_parser.set_defaults(func=_cmd_reject)

    cancel_parser = subparsers.add_parser("cancel", help="cancel an active run")
    cancel_parser.add_argument("run_dir")
    cancel_parser.add_argument("--actor", required=True)
    cancel_parser.add_argument("--reason", required=True)
    cancel_parser.set_defaults(func=_cmd_cancel)

    export_parser = subparsers.add_parser("export", help="show a completed export bundle")
    export_parser.add_argument("run_dir")
    export_parser.set_defaults(func=_cmd_export)

    audit_parser = subparsers.add_parser(
        "audit-completion",
        help="audit all MD-001..MD-015 completion evidence",
    )
    audit_parser.add_argument("--root", default=".")
    audit_parser.add_argument("--output", default="")
    audit_parser.set_defaults(func=_cmd_audit_completion)

    reference_parser = subparsers.add_parser(
        "reference-bundle",
        help="export a verified real run as an MD-013 reference bundle",
    )
    reference_parser.add_argument("run_dir")
    reference_parser.add_argument("--config", default="config.yaml")
    reference_parser.add_argument("--output-root", default="docs/audits/reference-runs")
    reference_parser.set_defaults(func=_cmd_reference_bundle)

    capabilities_parser = subparsers.add_parser(
        "capabilities",
        help="report the configured profile and venue capability level",
    )
    capabilities_parser.add_argument("--config", default="config.yaml")
    capabilities_parser.set_defaults(func=_cmd_capabilities)

    plan_parser = subparsers.add_parser("plan", help="show the configured run plan")
    plan_parser.add_argument("--config", default="config.yaml")
    plan_parser.add_argument("--topic", default="")
    plan_parser.set_defaults(func=_cmd_plan)

    verify_parser = subparsers.add_parser("verify", help="verify a completed run")
    verify_parser.add_argument("run_dir")
    verify_parser.add_argument("--config", default="config.yaml")
    verify_parser.set_defaults(func=_cmd_verify)

    ideate_parser = subparsers.add_parser(
        "ideate",
        help="analyze a research idea against venue strategy before running the pipeline",
    )
    ideate_parser.add_argument("--config", default="config.yaml")
    ideate_parser.add_argument(
        "--idea", required=True, help="your research idea (one sentence)"
    )
    ideate_parser.add_argument(
        "--output", default="", help="write report to this path (default: stdout only)"
    )
    ideate_parser.set_defaults(func=_cmd_ideate)

    fit_parser = subparsers.add_parser(
        "fit",
        help="rank all 17 venues by fit for your research idea",
    )
    fit_parser.add_argument("--config", default="config.yaml")
    fit_parser.add_argument(
        "--idea", required=True, help="your research idea (one sentence)"
    )
    fit_parser.add_argument(
        "--output", default="", help="write report to this path (default: stdout only)"
    )
    fit_parser.set_defaults(func=_cmd_fit)

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


def _cmd_resume(args: argparse.Namespace) -> int:
    result = PipelineRunner(load_config(args.config)).resume(
        Path(args.run_dir), actor=args.actor
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"done", "paused"} else 1


def _cmd_recover(args: argparse.Namespace) -> int:
    result = PipelineRunner(load_config(args.config)).recover(
        Path(args.run_dir),
        auto_approve=args.auto_approve,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"done", "paused"} else 1


def _cmd_approve(args: argparse.Namespace) -> int:
    decision = record_decision(
        Path(args.run_dir),
        decision="approve",
        reason=args.reason,
        actor=args.actor,
    )
    print(json.dumps(decision, indent=2))
    return 0


def _cmd_reject(args: argparse.Namespace) -> int:
    if not args.reason.strip():
        raise HITLError("reason is required when rejecting a gate")
    decision = record_decision(
        Path(args.run_dir),
        decision="reject",
        reason=args.reason,
        actor=args.actor,
    )
    print(json.dumps(decision, indent=2))
    return 0


def _cmd_cancel(args: argparse.Namespace) -> int:
    result = cancel_run(
        Path(args.run_dir),
        actor=args.actor,
        reason=args.reason,
    )
    print(json.dumps(result, indent=2))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    checkpoint = read_checkpoint(run_dir)
    if checkpoint is None or checkpoint.get("status") != "done":
        raise HITLError("run is not complete; finish all gates before export")
    bundle_dir = run_dir / "stage-12-final_verification_export"
    index_path = bundle_dir / "bundle_index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HITLError(f"export bundle not found: {index_path}") from exc
    payload = {
        "status": "ready",
        "run_dir": str(run_dir),
        "bundle_dir": str(bundle_dir),
        **index,
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_audit_completion(args: argparse.Namespace) -> int:
    payload = audit_repository(Path(args.root)).to_dict()
    rendered = json.dumps(payload, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["complete"] else 1


def _cmd_reference_bundle(args: argparse.Namespace) -> int:
    output = export_reference_bundle(
        Path(args.run_dir),
        config=load_config(args.config),
        output_root=Path(args.output_root),
    )
    print(json.dumps({"status": "exported", "bundle": output.as_posix()}, indent=2))
    return 0


def _cmd_capabilities(args: argparse.Namespace) -> int:
    runner = PipelineRunner(load_config(args.config))
    payload = {
        "level": runner.capability.level.name.lower(),
        "profile": runner.profile.profile_id,
        "venue_id": runner.venue_contract.venue_id,
        "venue_year": runner.venue_contract.year,
        "venue_track": runner.venue_contract.track,
        "venue_contract_status": runner.venue_contract.status.value,
        "blockers": list(runner.capability.blockers),
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["level"] != "unsupported" else 1


def _cmd_plan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    payload = PipelineRunner(config).plan(
        topic=args.topic or config.research.topic
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload["capability"]["level"] != "unsupported" else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    payload = verify_run(Path(args.run_dir), config=load_config(args.config))
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


def _cmd_ideate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    strategy_root = (
        Path(__file__).resolve().parent / "strategy" / "profiles"
    )
    if not strategy_root.is_dir():
        print(
            "venue strategy profiles not found; run from the autoresearch repo root",
            file=sys.stderr,
        )
        return 2
    registry = VenueStrategyRegistry.load(strategy_root)
    try:
        strategy = registry.resolve(config.research.venue_id)
    except Exception as exc:
        print(f"venue strategy not found for {config.research.venue_id}: {exc}", file=sys.stderr)
        print(f"available: {', '.join(registry.venue_ids())}", file=sys.stderr)
        return 2

    session = IdeationSession(strategy, idea=args.idea)
    report = session.analyze()

    rendered = report.to_markdown()
    print(rendered)

    if args.output:
        output_path = Path(args.output)
        write_ideation_report(report, output_path)
        print(f"\nReport written to {output_path}")

    return 0


def _cmd_fit(args: argparse.Namespace) -> int:
    strategy_root = (
        Path(__file__).resolve().parent / "strategy" / "profiles"
    )
    if not strategy_root.is_dir():
        print(
            "venue strategy profiles not found; run from the autoresearch repo root",
            file=sys.stderr,
        )
        return 2
    registry = VenueStrategyRegistry.load(strategy_root)

    report = generate_fit_report(
        idea=args.idea,
        registry=registry,
    )

    rendered = report.to_markdown()
    print(rendered)

    if args.output:
        output_path = Path(args.output)
        write_fit_report(report, output_path)
        print(f"\nReport written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
