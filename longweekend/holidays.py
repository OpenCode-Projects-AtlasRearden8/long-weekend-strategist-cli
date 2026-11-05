"""Holiday calendars: US federal rules plus custom JSON lists.

All computation is offline and standard-library only.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1)
    offset = (d.weekday() - weekday) % 7
    return d - timedelta(days=offset)


def observed(d: date) -> date:
    """Shift a federal holiday off a weekend to the adjacent workday."""
    if d.weekday() == SAT:
        return d - timedelta(days=1)
    if d.weekday() == SUN:
        return d + timedelta(days=1)
    return d


def us_federal_holidays(year: int) -> dict[date, str]:
    """US federal holidays for a year, mapped to their observed dates.

    Holidays observed on a weekend are shifted to the adjacent workday so
    planning matches the day people actually get off. Entries outside the
    requested year (e.g. a Saturday New Year observed the prior Dec 31) are
    dropped because the planner only considers one calendar year.
    """
    fixed = [
        ("New Year's Day", date(year, 1, 1)),
        ("Juneteenth", date(year, 6, 19)),
        ("Independence Day", date(year, 7, 4)),
        ("Veterans Day", date(year, 11, 11)),
        ("Christmas Day", date(year, 12, 25)),
    ]
    floating = [
        ("Martin Luther King Jr. Day", nth_weekday(year, 1, MON, 3)),
        ("Washington's Birthday", nth_weekday(year, 2, MON, 3)),
        ("Memorial Day", last_weekday(year, 5, MON)),
        ("Labor Day", nth_weekday(year, 9, MON, 1)),
        ("Columbus Day", nth_weekday(year, 10, MON, 2)),
        ("Thanksgiving Day", nth_weekday(year, 11, THU, 4)),
    ]
    out: dict[date, str] = {}
    for name, raw in fixed + floating:
        obs = observed(raw)
        if obs.year == year:
            out[obs] = name
    return out


def load_holidays(spec: str, year: int) -> dict[date, str]:
    """Resolve the --holidays argument for a given year.

    spec may be:
      "us-federal"  the built-in US federal preset (the default)
      "none"        no holidays at all
      a path        a JSON file, either a list of "YYYY-MM-DD Name" strings
                    or {"holidays": [{"date": ..., "name": ...}]}
    """
    if spec == "us-federal":
        return us_federal_holidays(year)
    if spec == "none":
        return {}
    if spec.lower().endswith(".json") or "/" in spec or "\\" in spec:
        return _load_holiday_file(spec, year)
    raise ValueError(
        f"unknown holidays spec {spec!r}: use 'us-federal', 'none', or a .json file"
    )


def _load_holiday_file(path: str, year: int) -> dict[date, str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    entries: list = []
    if isinstance(data, dict):
        entries = data.get("holidays", [])
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError(f"{path}: expected a list or an object with a 'holidays' key")
    out: dict[date, str] = {}
    for entry in entries:
        if isinstance(entry, dict):
            day = _parse_date(str(entry["date"]), path)
            name = str(entry.get("name", "Holiday"))
        else:
            parts = str(entry).strip().split(None, 1)
            day = _parse_date(parts[0], path)
            name = parts[1] if len(parts) > 1 else "Holiday"
        if day.year == year:
            out[day] = name
    return out


def _parse_date(text: str, context: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError as exc:
        raise ValueError(f"{context}: bad date {text!r}") from exc


def parse_blackouts(items: list[str]) -> set[date]:
    """Parse blackout arguments: single ISO dates or inclusive A..B ranges."""
    out: set[date] = set()
    tokens: list[str] = []
    for item in items:
        tokens.extend(t for t in item.replace(",", " ").split() if t)
    for token in tokens:
        if ".." in token:
            start_s, _, end_s = token.partition("..")
            start = _parse_date(start_s, "--blackout")
            end = _parse_date(end_s, "--blackout")
            if end < start:
                raise ValueError(f"--blackout: range {token!r} ends before it starts")
            out.update(start + timedelta(days=i) for i in range((end - start).days + 1))
        else:
            out.add(_parse_date(token, "--blackout"))
    return out
