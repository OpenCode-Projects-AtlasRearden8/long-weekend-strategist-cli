"""The "request these dates" note a plan export leaves behind."""

from __future__ import annotations

from .planner import Plan

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def build_note(
    plan: Plan,
    year: int,
    balance: int,
    holiday_names: dict[str, str] | None = None,
) -> str:
    holiday_names = holiday_names or {}
    lines: list[str] = []
    lines.append("# PTO Request Note")
    lines.append("")
    lines.append("Dates to request:")
    lines.append("")
    if plan.pto:
        for d in plan.pto:
            extra = holiday_names.get(d.isoformat(), "")
            suffix = f" — {extra}" if extra else ""
            lines.append(f"- {WEEKDAYS[d.weekday()]} {d.strftime('%b %d, %Y')}{suffix}")
    else:
        lines.append("- None needed! Every good block this year lines up with weekends and holidays.")
    lines.append("")
    lines.append("The math:")
    lines.append("")
    lines.append(f"- PTO days requested: {plan.cost} of {balance} available")
    lines.append(f"- PTO days left over: {balance - plan.cost}")
    if plan.pto:
        blocks = [b for b in plan.blocks if b[2] >= 2 and any(b[0] <= p <= b[1] for p in plan.pto)]
        label = "- Time off blocks those requests create:"
    else:
        blocks = [b for b in plan.blocks if b[2] >= 3]
        label = "- Free time off blocks you already have (no PTO needed):"
    if blocks:
        lines.append(label)
        lines.append("")
        for s, e, n in blocks:
            lines.append(f"  - {WEEKDAYS[s.weekday()]} {s.strftime('%b %d')} – {WEEKDAYS[e.weekday()]} {e.strftime('%b %d')}: {n} consecutive days off")
    lines.append("")
    lines.append("Generated offline by Long Weekend Strategist (Asdale Dynamics, LLC).")
    lines.append("")
    return "\n".join(lines)


def fmt_span(s, e, n) -> str:
    return (
        f"{WEEKDAYS[s.weekday()]} {s.strftime('%b %d')} – "
        f"{WEEKDAYS[e.weekday()]} {e.strftime('%b %d')} ({n} days)"
    )


def fmt_day(d) -> str:
    return f"{WEEKDAYS[d.weekday()]} {d.strftime('%b %d')}"

__all__ = ["build_note", "fmt_span", "fmt_day", "WEEKDAYS"]
