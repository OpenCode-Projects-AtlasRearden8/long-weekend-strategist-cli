"""Command line interface for the Long Weekend Strategist.

Usage example:
    longweekend --year 2026 --balance 15 --blackout 2026-12-24..2026-12-26 --top 5
    longweekend --year 2026 --balance 15 --holidays my-holidays.json --export 1
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .holidays import load_holidays, parse_blackouts, us_federal_holidays
from .ics_export import build_ics
from .note import build_note, fmt_day, fmt_span
from .planner import Plan, build_status, enumerate_plans

DEFAULT_TOP = 8


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="longweekend",
        description=(
            "Stretch your vacation days into long weekends. Enter the holidays "
            "you observe, your PTO balance, and any blackout dates; it scores "
            "every useful combination of leave requests, shows the top plans "
            "with day counts, and can export an .ics plus a request-these-dates note."
        ),
        epilog="Stdlib only. Fully offline. No data ever leaves your machine. (c) 2026 Asdale Dynamics, LLC",
    )
    p.add_argument("--year", type=int, default=date.today().year, help="planning year (default: this year)")
    p.add_argument(
        "--holidays",
        default="us-federal",
        help="'us-federal', 'none', or a JSON file of dates you observe (default: us-federal)",
    )
    p.add_argument("--balance", type=int, required=True, help="vacation/PTO days available for the year")
    p.add_argument(
        "--blackout",
        dest="blackouts",
        action="append",
        default=[],
        help="blackout dates: single ISO dates or inclusive A..B ranges, comma separated; repeatable",
    )
    p.add_argument("--min-length", type=int, default=3, help="minimum block length to call a long weekend (default 3)")
    p.add_argument("--top", type=int, default=DEFAULT_TOP, help="how many plans to show (default 8)")
    p.add_argument("--export", type=int, metavar="RANK", help="export the plan at this rank (1-based) and exit")
    p.add_argument("--outdir", default=".", help="directory for exported files (default: current directory)")
    p.add_argument("--list-holidays", action="store_true", help="print the observed holidays for the year and exit")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def run(args: argparse.Namespace) -> int:
    year = args.year
    if not 1900 <= year <= 2200:
        raise ValueError(f"year {year} is out of the supported 1900..2200 range")
    if args.balance < 0 or args.balance > 60:
        raise ValueError("--balance must be between 0 and 60")
    if args.min_length < 2:
        raise ValueError("--min-length must be at least 2")
    if args.top < 1:
        raise ValueError("--top must be at least 1")

    try:
        holidays = load_holidays(args.holidays, year)
    except json_error_types() as exc:  # type: ignore[misc]
        raise ValueError(f"holiday data problem: {exc}") from exc
    blackouts = parse_blackouts(args.blackouts)
    blackouts = {d for d in blackouts if d.year == year}

    if args.list_holidays:
        print(f"Holidays observed in {year} ({args.holidays}):")
        for d in sorted(holidays):
            print(f"  {fmt_day(d)}  {holidays[d]}")
        return 0

    plans = enumerate_plans(year, holidays, blackouts, args.balance)
    ranked = sorted(plans, key=lambda pl: pl.rank_key(args.min_length))

    print(f"Long Weekend Strategist — {year}")
    print(
        f"balance: {args.balance} PTO | min block: {args.min_length} days | "
        f"holidays: {describe_holidays(args.holidays, len(holidays))} | blackouts: {len(blackouts)} days"
    )
    print(f"graded {len(plans)} unique plans; top {min(args.top, len(ranked))}:")
    print()
    for rank, plan in enumerate(ranked[: args.top], start=1):
        print_plan(rank, plan, year, args.min_length, args.balance)

    if args.export is None:
        return 0
    if not 1 <= args.export <= len(ranked):
        raise ValueError(f"--export must be between 1 and {len(ranked)}")
    plan = ranked[args.export - 1]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"longweekend-{year}-plan{args.export}"
    ics_path = outdir / f"{stem}.ics"
    note_path = outdir / f"{stem}.md"
    ics_path.write_text(build_ics(plan, year), encoding="utf-8")
    note_path.write_text(build_note(plan, year, args.balance, holidays), encoding="utf-8")
    print()
    print(f"Exported plan #{args.export}:")
    print(f"  calendar: {ics_path}")
    print(f"  note:     {note_path}")
    return 0


def json_error_types():
    import json

    return (ValueError, json.JSONDecodeError)


def describe_holidays(spec: str, count: int) -> str:
    if spec == "us-federal":
        return f"US federal ({count})"
    if spec == "none":
        return "none"
    return f"custom ({count})"


def print_plan(rank: int, plan: Plan, year: int, min_len: int, balance: int) -> None:
    longs = plan.long_blocks(min_len)
    best = longs[0] if longs else (None, None, 0)
    if plan.pto:
        req = ", ".join(fmt_day(d) for d in plan.pto)
    else:
        req = "no PTO needed"
    print(f"#{rank}  {plan.cost} PTO day{'s' if plan.cost != 1 else ''} (of {balance})  |  request: {req}")
    if best[0] is not None:
        s, e, n = best
        print(f"    best block: {fmt_span(s, e, n)}")
    shown = [b for b in longs if b != best][:2]
    for s, e, n in shown:
        print(f"    also block: {fmt_span(s, e, n)}")
    if not longs:
        print(f"    no {min_len}-day block reachable with this balance")


if __name__ == "__main__":
    raise SystemExit(main())
