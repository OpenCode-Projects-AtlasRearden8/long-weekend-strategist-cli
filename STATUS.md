# STATUS.md — Long Weekend Strategist

Last updated: 2026-11-05 · Version 1.0.0

## What was built

`longweekend` — a stdlib-only, offline Python CLI that stretches limited
vacation days into long weekends:

- **Holiday input**: built-in US federal preset (with correct weekend→observed
  workday shifting), `none`, or a custom JSON file of the holidays you observe
  (see `examples/holidays-2026.json`).
- **Blackouts**: single dates or inclusive `A..B` ranges that leave can't
  touch and that split any block running through them.
- **Scoring**: enumerates every useful combination of leave requests within
  the PTO balance (each requested day must connect to existing days off), then
  ranks plans by (1) longest consecutive block of days off, (2) number of
  blocks meeting `--min-length`, (3) fewest PTO days spent, (4) earliest first
  request date. Finalists are rescored exactly against the full-year calendar.
- **Output**: top plans with exact request dates, cost, and day-count spans.
- **Exports**: an RFC 5545 `.ics` (all-day events per block + per PTO day,
  CRLF endings, unique UIDs, text escaping) and a markdown "request these
  dates" note with the balance math.
- **Packaging**: console script entry point (`longweekend`), `pyproject.toml`,
  wheel builds cleanly (`pip wheel` verified).

## How to run it

```bash
python3 -m longweekend --year 2026 --balance 15
# or, after `pip install .`:
longweekend --year 2026 --balance 15 --blackout 2026-12-24..2026-12-31 --top 5
longweekend --year 2026 --balance 10 --export 1 --outdir ./exports
longweekend --year 2026 --balance 0 --list-holidays
```

Requires Python 3.10+. Installing for real caps at PEP 668 boundaries; on
externally managed systems use a venv or run via `python3 -m longweekend`
(no dependencies are needed either way).

## Verification results

- `python3 -m pytest` → **38 passed** (7.0s). Coverage includes: federal
  holiday observation rules for real 2026/2027 dates, bridging math
  (one PTO day bridging Thanksgiving 2026 → 4-day block for cost 1), the
  no-PTO plan, balance caps, blackout exclusions and block splitting,
  exact block merging, ICS structure/escaping/UIDs, note contents, and CLI
  end-to-end runs including error paths.
- `python3 -m compileall` on package and tests → clean.
- `python3 -m pip wheel --no-deps .` → builds
  `long_weekend_strategist-1.0.0` with LICENSE and entry point bundled.
- Installed from that wheel in this environment and ran `longweekend`
  end-to-end (list-holidays, planning, export) → all good.
- Manual smoke runs: blackouts redirect plans away from frozen windows;
  balance 0 produces the "free blocks" plan; custom holiday files are
  respected; `--export 1` writes both artifacts.

## Known gaps

- Enumeration uses dominance pruning with caps (≤600 partial signatures per
  day, 4 representatives each). Practically exhaustive for real PTO balances,
  but an extreme input could theoretically prune an exotic tie combination;
  finalists are always rescored exactly so ranking stays correct for whatever
  survives.
- `--min-length` behaves as a count threshold for "long blocks" and export
  blocks, but the printed plan view and the note include blocks created by
  the requests regardless (so you can see what your days bought).
- The US federal preset covers federal holidays only (with Columbus Day);
  banks, states, companies, and other countries need a custom JSON file.
- No auto-generated multi-year planning (one year per run) and no HTML/PDF
  output; `.ics` + markdown note are the only exports.
- Dec 31 observed shifts for a Saturday New Year belong to the prior year and
  are intentionally dropped so each run plans exactly one calendar year.
- ICS `DTSTAMP` uses current UTC time, so exports are not byte-identical
  between runs (IDs and dates remain stable).

## Layout

```
longweekend/            package (cli, planner, holidays, ics_export, note)
tests/                  pytest suite (scoring math, holidays, export, CLI)
examples/               holidays-2026.json sample
pyproject.toml          metadata, console script, pytest config
README.md, LICENSE, STATUS.md
```

MIT License — Copyright (c) 2026 Asdale Dynamics, LLC.
