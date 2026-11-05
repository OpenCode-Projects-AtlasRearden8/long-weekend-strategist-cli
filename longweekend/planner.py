"""Plan enumeration and scoring.

Every calendar day of the year is walked left to right. At each workday a
state may either request the day as PTO (only when doing so touches an
existing block of days off, so every enumerated request is actually useful)
or leave it as a workday. Each reachable (cost, open-block, closed-blocks)
signature tracks a few representative request-date sets, and the survivors
are rescored exactly against the full-year calendar and ranked by
(1) longest consecutive block of days off, (2) number of blocks meeting the
minimum length, (3) fewer PTO days spent, (4) earlier first request date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .holidays import SAT, SUN

MAX_PARTIALS = 600
REPS_PER_KEY = 4


def build_status(
    year: int, holidays: dict[date, str], blackouts: set[date]
) -> dict[date, str]:
    """Classify every day of the year as OFF, WORK, or BLACKOUT.

    Blackouts beat everything: a frozen day is unrequestable and cuts any
    block that would otherwise run through it.
    """
    status: dict[date, str] = {}
    d = date(year, 1, 1)
    while d.year == year:
        if d in blackouts:
            status[d] = "BLACKOUT"
        elif d.weekday() in (SAT, SUN) or d in holidays:
            status[d] = "OFF"
        else:
            status[d] = "WORK"
        d += timedelta(days=1)
    return status


@dataclass(frozen=True)
class Plan:
    pto: tuple[date, ...]  # requested PTO days, sorted
    cost: int
    blocks: tuple[tuple[date, date, int], ...]  # every off-block: (start, end, length)

    @property
    def longest(self) -> int:
        return max((n for _, _, n in self.blocks), default=0)

    def long_blocks(self, min_len: int) -> tuple[tuple[date, date, int], ...]:
        return tuple((s, e, n) for s, e, n in self.blocks if n >= min_len)

    def rank_key(self, min_len: int) -> tuple:
        return (
            -self.longest,
            -len(self.long_blocks(min_len)),
            self.cost,
            self.pto[0].toordinal() if self.pto else date.max.toordinal(),
            tuple(-n for _, _, n in sorted(self.blocks, key=lambda b: (b[0]))),
        )


def exact_blocks(status: dict[date, str], pto: frozenset[date], year: int) -> tuple[tuple[date, date, int], ...]:
    """All maximal consecutive days-off blocks for the full year."""
    blocks: list[tuple[date, date, int]] = []
    start: date | None = None
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        is_off = d in pto or status[d] == "OFF"
        if is_off and start is None:
            start = d
        if not is_off or d == end:
            if start is not None:
                last = d if is_off else d - timedelta(days=1)
                blocks.append((start, last, (last - start).days + 1))
                start = None
        d += timedelta(days=1)
    return tuple(blocks)


def enumerate_plans(
    year: int,
    holidays: dict[date, str],
    blackouts: set[date],
    balance: int,
) -> list[Plan]:
    """Enumerate useful leave-request combinations within the balance.

    A request day is admitted only if it touches an existing off-day either
    through the previous day still being part of the open block or through
    the next calendar day being a weekend/holiday. Stray mid-week PTO days
    that connect to nothing are therefore never enumerated.
    """
    status = build_status(year, holidays, blackouts)
    span = [(date(year, 1, 1) + timedelta(days=i)) for i in range(366 if _is_leap(year) else 365)]
    span = [d for d in span if d.year == year]

    # state: (cost, open_block_len, closed_block_lengths_chronological)
    # value: representative pto-date tuples for that signature
    entries: dict[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]] = {
        (0, 0, ()): [()]
    }

    for i, d in enumerate(span):
        kind = status[d]
        next_off = i + 1 < len(span) and status[span[i + 1]] == "OFF"
        adv: dict[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]] = {}
        for key, picks in entries.items():
            cost, cur, blocks = key
            if kind == "OFF":
                ncur = cur + 1 if cur > 0 else 1
                _push(adv, (cost, ncur, blocks), picks)
            elif kind == "BLACKOUT":
                nblocks = blocks + (cur,) if cur > 0 else blocks
                _push(adv, (cost, 0, nblocks), picks)
            else:  # WORK
                # option 1: do not request
                nblocks = blocks + (cur,) if cur > 0 else blocks
                _push(adv, (cost, 0, nblocks), picks)
                # option 2: request the day, if it connects to time off
                if cost + 1 <= balance and (cur > 0 or next_off):
                    for p in picks:
                        _push(adv, (cost + 1, cur + 1, blocks), [(p + (d,))])
        entries = _compact(adv)

    final: list[Plan] = []
    seen: set[frozenset[date]] = set()
    for (cost, cur, blocks), picks in sorted(entries.items()):
        all_blocks = blocks + (cur,) if cur > 0 else blocks
        for p in picks:
            pto_fs = frozenset(p)
            if pto_fs in seen:
                continue
            seen.add(pto_fs)
            plan_blocks = exact_blocks(status, pto_fs, year)
            final.append(Plan(pto=tuple(sorted(p)), cost=cost, blocks=plan_blocks))
    return final


def _compact(
    adv: dict[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]],
) -> dict[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]]:
    """Trim the frontier: cap representatives per signature and cap the total."""
    capped: dict[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]] = {}
    for key, picks in adv.items():
        uniq: list[tuple[date, ...]] = []
        for p in picks:
            if p not in uniq:
                uniq.append(p)
        capped[key] = uniq[:REPS_PER_KEY]
    if len(capped) <= MAX_PARTIALS:
        return capped
    ordered = sorted(capped.items(), key=_frontier_sort_key)
    return dict(ordered[:MAX_PARTIALS])


def _frontier_sort_key(item: tuple[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]]) -> tuple:
    (cost, cur, blocks), _ = item
    desc = tuple(-n for n in sorted(blocks, reverse=True))
    return (cost, desc, -cur, len(blocks))


def _push(
    target: dict[tuple[int, int, tuple[int, ...]], list[tuple[date, ...]]],
    key: tuple[int, int, tuple[int, ...]],
    picks: list[tuple[date, ...]],
) -> None:
    bucket = target.setdefault(key, [])
    for p in picks:
        if p not in bucket:
            bucket.append(p)


def _is_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
