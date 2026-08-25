"""CLI entry point: python -m market_intel_pystrat.scripts.run {calibration|update|view|fusion|daily} [name].

Excel inputs are read from the MARKET_INTEL_DATA_DIR environment variable.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from market_intel_pystrat.jobs.run.run_calibration import run_calibration
from market_intel_pystrat.jobs.run.run_daily import FOLLOWED_PROFILES, has_failures, run_daily
from market_intel_pystrat.jobs.run.run_update import run_update
from market_intel_pystrat.jobs.run.run_view import run_view
from market_intel_pystrat.profiles.catalog_data import REGISTRY, FUSIONS

from market_intel_pystrat.jobs.run.run_fusion import run_fusion

def _default_run_dir(args: argparse.Namespace) -> Path:
    return args.out or Path("artifacts/runs") / args.profile


def _cmd_calibration(args):
    out_dir = _default_run_dir(args)
    run_calibration(args.profile, out_dir,
                    os.environ.get("MARKET_INTEL_DATA_DIR"), source=args.source)
    print(f"run: {out_dir.resolve()}")


def _cmd_update(args):
    run_dir = _default_run_dir(args)
    run_update(args.profile, run_dir,
               os.environ.get("MARKET_INTEL_DATA_DIR"), source=args.source)
    print(f"run: {run_dir.resolve()}")


def _cmd_view(args):
    run_dir = _default_run_dir(args)
    run_view(run_dir)
    print(f"run: {run_dir.resolve()}")

def _cmd_fusion(args):
    out_dir = args.out or Path("artifacts/runs") / args.fusion
    run_fusion(args.fusion, out_dir,
               os.environ.get("MARKET_INTEL_DATA_DIR"), source=args.source)
    print(f"run: {out_dir.resolve()}")


def _cmd_daily(args):
    report = run_daily(
        args.runs_root,
        profiles=tuple(args.profiles) if args.profiles else FOLLOWED_PROFILES,
        source=args.source,
        ingest=not args.skip_ingest,
        duration=args.duration,
        data_dir=os.environ.get("MARKET_INTEL_DATA_DIR"),
    )
    print(json.dumps(report, indent=2))
    if args.notify:
        # deferred import: publish deps ([publish] extra) only needed when enabled
        from market_intel_pystrat.publish.publish_services import format_daily_report, send_slack_message
        send_slack_message(format_daily_report(report))
    if has_failures(report):
        raise SystemExit(1)


def _add_profile_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("profile", choices=sorted(REGISTRY), help="profile name")
    p.add_argument("--out", type=Path, default=None,
                   help="run directory (default: artifacts/runs/<profile>)")
    p.add_argument("--source", choices=("excel", "postgres"), default="excel",
                   help="data source for the profile inputs")


def main() -> None:
    """Parse the command line and dispatch to the matching job."""
    parser = argparse.ArgumentParser(description="market_intel run jobs")
    sub = parser.add_subparsers(dest="job", required=True)

    p_cal = sub.add_parser("calibration", help="calibrate a profile and write its report")
    _add_profile_args(p_cal)
    p_cal.set_defaults(func=_cmd_calibration)

    p_upd = sub.add_parser("update", help="extend a saved schedule on current data and rewrite the view")
    _add_profile_args(p_upd)
    p_upd.set_defaults(func=_cmd_update)

    p_view = sub.add_parser("view", help="(re)render the HTML report of a saved run")
    _add_profile_args(p_view)
    p_view.set_defaults(func=_cmd_view)

    p_fus = sub.add_parser("fusion", help="replay component schedules under a fused strategy")
    p_fus.add_argument("fusion", choices=sorted(FUSIONS), help="fusion name")
    p_fus.add_argument("--out", type=Path, default=None,
                       help="run directory (default: artifacts/runs/<fusion>)")
    p_fus.add_argument("--source", choices=("excel", "postgres"), default="excel",
                       help="data source for the fusion inputs")
    p_fus.set_defaults(func=_cmd_fusion)

    p_daily = sub.add_parser("daily", help="ingest latest IBKR bars then update every followed profile")
    p_daily.add_argument("--profiles", nargs="*", default=None, choices=sorted(REGISTRY),
                         help=f"profiles to update (default: {', '.join(FOLLOWED_PROFILES)})")
    p_daily.add_argument("--source", choices=("excel", "postgres"), default="postgres",
                         help="data source for the profile inputs")
    p_daily.add_argument("--skip-ingest", action="store_true",
                         help="skip the IBKR ingestion step")
    p_daily.add_argument("--duration", default="2 D",
                         help="IBKR history duration (e.g. '2 D'; '15 Y' for a backfill)")
    p_daily.add_argument("--runs-root", type=Path, default=Path("artifacts/runs"),
                         help="directory containing the run folders")
    p_daily.add_argument("--notify", action="store_true",
                         help="send the report to Slack (requires [publish] extra and SLACK_* settings)")
    p_daily.set_defaults(func=_cmd_daily)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()