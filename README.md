# Long Weekend Strategist

Stretch your vacation days into long weekends. You enter the holidays you
observe, your vacation-day balance, and any blackout dates; the tool scores
every useful combination of leave requests, prints the top long-weekend plans
with day counts, and exports an `.ics` calendar file plus a
"request these dates" note.

Pure Python standard library. Fully offline. Nothing leaves your machine.

```
$ longweekend --year 2026 --balance 10 --top 3
Long Weekend Strategist — 2026
balance: 10 PTO | min block: 3 days | holidays: US federal (11) | blackouts: 0 days
graded 1934 unique plans; top 3:

#1  2 PTO days (of 10)  |  request: Fri Jan 02, Mon Jan 05
    best block: Thu Jan 01 – Mon Jan 05 (5 days)
    also block: Sat Jan 17 – Mon Jan 19 (3 days)
    also block: Sat Feb 14 – Mon Feb 16 (3 days)
...
```

## Why it exists

Adjacency is free money. One PTO day next to a holiday and a weekend can turn
a two-day break into four or five days off, but finding those moments by hand
across a whole year is tedious. This tool walks the calendar for you and
answers two questions: *where should I spend my limited PTO days?* and *what
exactly do I need to ask for?*

## How it scores plans

Every plan gets a rank key, compared lexicographically (earlier wins):

1. **Longest consecutive block of days off** — weekends, observed holidays,
   and requested PTO days merged into one run. A 5-day block beats everything.
2. **More blocks that meet the minimum length** (`--min-length`, default 3:
   a true long weekend).
3. **Fewer PTO days spent.** A plan that reaches the same result with fewer
   requests wins.
4. **Earlier first request date**, then a stable tiebreak.

Only "useful" requests are enumerated: a requested day must connect to days
off either through the previous day being off (or already requested) or
through the next calendar day being a weekend or holiday. Stray mid-week
PTO days that touch nothing would just burn balance, so the scorer never
proposes them. Enumeration covers every such combination affordable within
your balance, with dominance pruning keeping only genuinely distinct partial
plans; finalists are then rescored exactly against the full-year calendar.

## Install & run

Requires Python 3.10+. No dependencies; pytest only for development.

```bash
# from the repo folder — run directly:
python3 -m longweekend --help

# or install the CLI entry point:
pip install .
longweekend --help
```

## Everyday recipes

```bash
# top 8 plans for 15 PTO days in 2026, US federal holidays
longweekend --year 2026 --balance 15

# audit long weekends you'd get with ZERO pto days
longweekend --year 2026 --balance 0

# company is frozen over the holidays; pesky commuter company
longweekend --year 2026 --balance 12 --blackout 2026-12-24..2026-12-31 --top 5

# your shop doesn't do federal holidays; enter only what you observe
longweekend --year 2026 --balance 10 --holidays my-holidays.json

# export plan #1 as calendar + submission-ready note
longweekend --year 2026 --balance 10 --export 1 --outdir ./exports
```

### Key options

| Flag | Meaning |
| --- | --- |
| `--year YEAR` | Planning year (default: this year). |
| `--balance N` | Vacation/PTO days available (required). |
| `--holidays SPEC` | `us-federal` (default), `none`, or a JSON file of the holidays *you* observe. |
| `--blackout ITEMS` | Dates leave can't touch: `2026-12-24` or inclusive ranges `2026-12-24..2026-12-26`, comma separated; repeatable. |
| `--min-length N` | Smallest run still counted as a long weekend (default 3). |
| `--top N` | Plans to print (default 8). |
| `--export RANK` | Export the plan at that rank: writes `<outdir>/longweekend-<year>-plan<R>.ics` and `.md`. |
| `--list-holidays` | Print the observed holidays for the year and exit. |

### Holiday file format

Either a list of ISO dates (optionally followed by a name), or an object with
`holidays` entries:

```json
{
  "holidays": [
    {"date": "2026-11-26", "name": "Thanksgiving"},
    {"date": "2026-12-24", "name": "Company Eve"}
  ]
}
```

A working example lives in [`examples/holidays-2026.json`](examples/holidays-2026.json).
Dates you observe outside the planning year are ignored; the US federal preset
maps weekend holidays to the adjacent observed workday, matching the day
people actually get off.

## What the export is

- **`.ics`** — RFC 5545 all-day events: one per off-block that your requests
  create, one per requested PTO day. Imports into nearly any calendar app.
- **Note (`.md`)** — the exact dates to submit, the balance math, and the
  blocks those dates produce. Hand it to your manager or paste it into a
  request form.

## Development

```bash
pip install .[test]   # or: pip install pytest
pytest
```

The test suite covers the scoring math: federal holiday observation rules,
bridging costs (e.g. one day turning Thanksgiving 2026 into a 4-day block),
blackout handling, balance caps, exact block merging, and end-to-end CLI
including export artifacts.

## Design notes

- **Stdlib only, offline.** No network calls, no non-Python deps, no telemetry.
- **No personal data.** Inputs live only for the process run; exports go
  wherever you point `--outdir`.
- **Honest limitations** are listed in [`STATUS.md`](STATUS.md).

## Crediting

Built and maintained by **Asdale Dynamics, LLC** — practical, beginner-friendly
AI tools and guides. MIT licensed; see [`LICENSE`](LICENSE).

This CLI is unrelated to (and deliberately different from) reminder-style
calendar tools: it is specifically about *strategizing limited leave days*,
not generating generic reminders.
