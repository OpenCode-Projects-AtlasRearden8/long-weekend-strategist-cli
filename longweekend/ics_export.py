"""All-day .ics export for a chosen plan, RFC 5545 style."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone

from .planner import Plan


def _esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _day(d: date) -> str:
    return d.strftime("%Y%m%d")


def _uid(plan: Plan, year: int, label: str) -> str:
    fingerprint = "|".join(d.isoformat() for d in plan.pto) or "no-pto"
    digest = hashlib.sha1(f"{year}|{fingerprint}|{label}".encode()).hexdigest()
    return f"{digest}@longweekend-strategist.local"


def build_ics(plan: Plan, year: int, label: str = "Long weekend plan") -> str:
    """Build a VCALENDAR string: one all-day event per block plus one per PTO day."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Asdale Dynamics LLC//Long Weekend Strategist//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    if not plan.pto:
        for i, (s, e, n) in enumerate(plan.blocks, start=1):
            if n < 3:
                continue
            lines += [
                "BEGIN:VEVENT",
                f"UID:{_uid(plan, year, f'{label}-freeblock-{i}')}",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{_day(s)}",
                f"DTEND;VALUE=DATE:{_day(e + timedelta(days=1))}",
                f"SUMMARY:{_esc(f'{label}: Days off (no PTO needed) ({n} days)')}",
                "END:VEVENT",
            ]
    else:
        touched = [b for b in plan.blocks if any(b[0] <= p <= b[1] for p in plan.pto)]
        for n, (s, e, block_len) in enumerate(touched, start=1):
            lines += [
                "BEGIN:VEVENT",
                f"UID:{_uid(plan, year, f'{label}-block-{n}')}",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{_day(s)}",
                f"DTEND;VALUE=DATE:{_day(e + timedelta(days=1))}",
                f"SUMMARY:{_esc(f'{label}: {block_len}-day block')}",
                f"DESCRIPTION:{_esc(f'Days off {s.isoformat()} through {e.isoformat()} ({block_len} days).')}",
                "END:VEVENT",
            ]
        for d in plan.pto:
            lines += [
                "BEGIN:VEVENT",
                f"UID:{_uid(plan, year, f'pto-{d.isoformat()}')}",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{_day(d)}",
                f"DTEND;VALUE=DATE:{_day(d + timedelta(days=1))}",
                f"SUMMARY:{_esc('PTO request: ' + d.strftime('%a %b %d, %Y'))}",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
