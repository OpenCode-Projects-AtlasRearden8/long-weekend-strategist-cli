import io
import json
from datetime import date

from longweekend.ics_export import build_ics
from longweekend.note import build_note
from longweekend.planner import Plan, enumerate_plans
from longweekend.holidays import us_federal_holidays
from longweekend.cli import main

FED2026 = us_federal_holidays(2026)


def sample_plan() -> Plan:
    blocks = ((date(2026, 11, 26), date(2026, 11, 29), 4),)
    return Plan(pto=(date(2026, 11, 27),), cost=1, blocks=blocks)


class TestIcs:
    def test_structure_and_all_day_dates(self):
        ics = build_ics(sample_plan(), 2026)
        assert ics.startswith("BEGIN:VCALENDAR")
        assert ics.endswith("END:VCALENDAR\r\n")
        assert "VERSION:2.0" in ics
        assert "Asdale Dynamics LLC" in ics
        assert "DTSTART;VALUE=DATE:20261126" in ics
        assert "DTEND;VALUE=DATE:20261130" in ics  # block end + 1
        assert "SUMMARY:PTO request" in ics
        # unique UIDs per event
        uids = [ln for ln in ics.split("\r\n") if ln.startswith("UID:")]
        assert len(uids) == len(set(uids))
        # CRLF line endings per RFC 5545
        assert "\n" not in ics.replace("\r\n", "")

    def test_escapes_commas_in_summaries(self):
        p = sample_plan()
        ics = build_ics(p, 2026)
        assert "Fri Nov 27\\, 2026" in ics

    def test_free_plan_has_long_block_events(self):
        plans = enumerate_plans(2026, FED2026, set(), 0)
        ics = build_ics(plans[0], 2026)
        assert "no PTO needed" in ics
        # a free Sat-Sun-Mon block (Martin Luther King Jr. weekend)
        assert "DTSTART;VALUE=DATE:20260117" in ics


class TestNote:
    def test_note_lists_dates_and_math(self):
        note = build_note(sample_plan(), 2026, 15, FED2026)
        assert "Fri Nov 27, 2026" in note
        assert "PTO days requested: 1 of 15" in note
        assert "PTO days left over: 14" in note
        assert "4 consecutive days off" in note
        assert "Asdale Dynamics, LLC" in note

    def test_free_plan_note(self):
        plans = enumerate_plans(2026, FED2026, set(), 0)
        note = build_note(plans[0], 2026, 0)
        assert "None needed" in note


class TestCliEndToEnd:
    def test_top_plans_and_export(self, tmp_path, capsys):
        rc = main(
            [
                "--year", "2026",
                "--balance", "3",
                "--top", "2",
                "--export", "1",
                "--outdir", str(tmp_path),
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "#1" in out and "PTO day" in out
        ics = tmp_path / "longweekend-2026-plan1.ics"
        note = tmp_path / "longweekend-2026-plan1.md"
        assert ics.exists() and note.exists()
        data = io.open(ics, newline="", encoding="utf-8").read()
        assert "BEGIN:VCALENDAR" in data
        assert "SUMMARY:PTO request" in data or "no PTO needed" in data

    def test_blackouts_and_custom_holidays_respected(self, tmp_path, capsys):
        hfile = tmp_path / "h.json"
        hfile.write_text(
            json.dumps(["2026-11-26 Family Day"]), encoding="utf-8"
        )
        rc = main(
            [
                "--year", "2026",
                "--balance", "2",
                "--holidays", str(hfile),
                "--blackout", "2026-11-26..2026-11-27",
                "--top", "1",
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "custom (1)" in out
        assert "blackouts: 2 days" in out

    def test_bad_balance_exits_noisy(self, capsys):
        rc = main(["--year", "2026", "--balance", "-1"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error:" in err

    def test_export_out_of_range(self, capsys):
        rc = main(["--year", "2026", "--balance", "3", "--export", "99999"])
        assert rc == 2

    def test_list_holidays(self, capsys):
        rc = main(["--year", "2026", "--balance", "0", "--list-holidays"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Thanksgiving Day" in out
